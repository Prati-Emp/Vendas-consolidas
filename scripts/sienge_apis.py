#!/usr/bin/env python3
"""
Integração com APIs do Sienge
APIs para vendas realizadas e vendas canceladas
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd
import duckdb
import os

from scripts.orchestrator import make_api_request
from scripts.config import get_api_config

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _extrair_registros(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extrai a lista de registros do payload retornado pelo orquestrador.

    Suporta variações de chaves como 'data', 'dados', 'items', 'content'.
    Retorna lista vazia quando não encontrar registros.
    """
    try:
        payload = result.get("data", {})
        if isinstance(payload, dict):
            for key in ("data", "dados", "items", "content", "result"):
                value = payload.get(key)
                if isinstance(value, list):
                    return value
        if isinstance(payload, list):
            return payload
    except Exception:
        pass
    return []

def obter_lista_empreendimentos_motherduck() -> List[Dict[str, Any]]:
    """
    Busca lista de empreendimentos da tabela reservas_abril no MotherDuck
    + empreendimento fixo adicional
    Retorna apenas as colunas necessárias para filtrar no Sienge
    """
    try:
        # EMPREENDIMENTO FIXO (não está no conjunto de dados)
        empreendimento_fixo = {
            'id': 19,  # ID do empreendimento Ondina II
            'nome': 'Ondina II'  # Nome do empreendimento fixo
        }
        
        logger.info(f"Empreendimento fixo adicionado: {empreendimento_fixo['nome']} (ID: {empreendimento_fixo['id']})")
        
        # Configurar DuckDB
        duckdb.sql("INSTALL motherduck")
        duckdb.sql("LOAD motherduck")
        
        # Configurar token
        token = os.environ.get('MOTHERDUCK_TOKEN', '').strip()
        if not token:
            logger.error("MOTHERDUCK_TOKEN não encontrado")
            return [empreendimento_fixo]  # Retorna pelo menos o fixo
        
        os.environ['motherduck_token'] = token
        
        # Conectar ao MotherDuck
        conn = duckdb.connect('md:reservas')
        
        # Buscar empreendimentos da tabela cv_vendas
        # Colunas: codigointerno_empreendimento e empreendimento
        query = """
        SELECT DISTINCT 
            codigointerno_empreendimento,
            empreendimento
        FROM main.cv_vendas 
        WHERE codigointerno_empreendimento IS NOT NULL
        ORDER BY empreendimento
        """
        
        logger.info("Buscando lista de empreendimentos da tabela cv_vendas...")
        result = conn.execute(query).fetchall()
        
        # Converter para lista de dicionários
        empreendimentos = [empreendimento_fixo]  # Começar com o fixo
        
        for row in result:
            empreendimentos.append({
                'id': row[0],  # codigointerno_empreendimento
                'nome': row[1]  # empreendimento
            })
        
        conn.close()
        logger.info(f"Total de empreendimentos: {len(empreendimentos)} (1 fixo + {len(result)} da cv_vendas)")
        return empreendimentos
        
    except Exception as e:
        logger.error(f"Erro ao buscar empreendimentos: {str(e)}")
        # Em caso de erro, retorna pelo menos o empreendimento fixo
        return [empreendimento_fixo]

class SiengeAPIClient:
    """Cliente para APIs do Sienge com controle de limite diário"""
    
    def __init__(self):
        self.config_vendas = get_api_config('sienge_vendas_realizadas')
        self.config_canceladas = get_api_config('sienge_vendas_canceladas')
        
        if not self.config_vendas or not self.config_canceladas:
            raise ValueError("Configurações do Sienge não encontradas")
        
        # Carregar lista de empreendimentos
        self.empreendimentos = obter_lista_empreendimentos_motherduck()
        
        # Controle de limite diário (40 requisições por dia, 16 por execução)
        self.limite_diario = 40
        self.requisicoes_hoje = 0
        self.modo_teste = os.environ.get('SIENGE_MODO_TESTE', 'false').lower() == 'true'
        
        # Calcular requisições necessárias por execução
        self.empreendimentos_count = len(self.empreendimentos)
        self.requisicoes_por_execucao = self.empreendimentos_count * 2  # 2 APIs (realizadas + canceladas) por empreendimento
        self.execucoes_possiveis = self.limite_diario // self.requisicoes_por_execucao
        
        logger.info(f"📊 Controle de limite:")
        logger.info(f"   - Empreendimentos: {self.empreendimentos_count}")
        logger.info(f"   - Requisições por execução: {self.requisicoes_por_execucao}")
        logger.info(f"   - Execuções possíveis por dia: {self.execucoes_possiveis}")
        logger.info(f"   - Limite diário: {self.limite_diario} (permite 2 execuções/dia com 16 requisições cada)")
        
        if self.modo_teste:
            logger.warning("🧪 MODO TESTE ATIVADO - Nenhuma requisição real será feita")
    
    def verificar_limite_requisicoes(self) -> bool:
        """Verifica se ainda há requisições disponíveis para uma execução completa"""
        # Verificar se há requisições suficientes para uma execução completa
        if self.requisicoes_hoje + self.requisicoes_por_execucao > self.limite_diario:
            logger.error(f"❌ LIMITE INSUFICIENTE para execução completa")
            logger.error(f"   - Requisições já usadas: {self.requisicoes_hoje}")
            logger.error(f"   - Requisições necessárias: {self.requisicoes_por_execucao}")
            logger.error(f"   - Limite diário: {self.limite_diario}")
            return False
        
        logger.info(f"📊 Requisições disponíveis: {self.limite_diario - self.requisicoes_hoje}/{self.limite_diario}")
        logger.info(f"   - Requisições necessárias para execução: {self.requisicoes_por_execucao}")
        return True
    
    def incrementar_contador(self, empreendimentos_count: int = 1):
        """Incrementa o contador de requisições baseado no número de empreendimentos"""
        # Cada empreendimento conta como uma requisição
        self.requisicoes_hoje += empreendimentos_count
        logger.info(f"📈 Requisições incrementadas: +{empreendimentos_count} (Total: {self.requisicoes_hoje})")
    
    def validar_parametros(self, data_inicio: str, data_fim: str) -> bool:
        """Valida parâmetros antes de fazer requisições"""
        try:
            from datetime import datetime
            
            # Validar formato das datas
            datetime.strptime(data_inicio, '%Y-%m-%d')
            datetime.strptime(data_fim, '%Y-%m-%d')
            
            # Validar se data_inicio <= data_fim
            if data_inicio > data_fim:
                logger.error("❌ Data de início deve ser menor ou igual à data de fim")
                return False
            
            logger.info(f"✅ Parâmetros válidos: {data_inicio} a {data_fim}")
            return True
            
        except ValueError as e:
            logger.error(f"❌ Formato de data inválido: {str(e)}")
            return False
    
    async def get_vendas_realizadas(self, data_inicio: str, data_fim: str, 
                                   pagina: int = 1, registros_por_pagina: int = 500) -> Dict[str, Any]:
        """
        Busca vendas realizadas do Sienge com controle de limite
        
        Args:
            data_inicio: Data de início (YYYY-MM-DD)
            data_fim: Data de fim (YYYY-MM-DD)
            pagina: Número da página
            registros_por_pagina: Registros por página
        """
        # VALIDAÇÕES PRÉ-REQUISIÇÃO
        if not self.validar_parametros(data_inicio, data_fim):
            return {'success': False, 'error': 'Parâmetros inválidos'}
        
        if not self.verificar_limite_requisicoes():
            return {'success': False, 'error': 'Limite diário de requisições atingido'}
        
        # MODO TESTE - Retorna dados simulados
        if self.modo_teste:
            logger.info("🧪 MODO TESTE - Retornando dados simulados para vendas realizadas")
            return {
                'success': True,
                'data': {
                    'dados': [],
                    'total_registros': 0,
                    'pagina_atual': pagina,
                    'total_paginas': 1
                },
                'modo_teste': True
            }
        
        # Endpoint baseado no código M do Power BI
        endpoint = ""
        
        # Parâmetros baseados no código M (um empreendimento por vez)
        # Usar apenas o primeiro empreendimento para esta requisição específica
        if not self.empreendimentos:
            return {'success': False, 'error': 'Nenhum empreendimento disponível'}
        
        # Para requisições individuais, usar apenas um empreendimento por vez
        # O loop será feito na função que chama esta
        primeiro_empreendimento = self.empreendimentos[0] if self.empreendimentos else None
        
        if not primeiro_empreendimento:
            return {'success': False, 'error': 'Nenhum empreendimento disponível'}
        
        params = {
            'enterpriseId': int(primeiro_empreendimento['id']),  # ID como inteiro
            'createdAfter': '2020-01-01',  # Data inicial fixa (como no Power BI)
            'createdBefore': data_fim,     # Data final (atualizada)
            'situation': 'SOLD'            # Apenas vendas realizadas
        }
        
        logger.info(f"Filtrando por empreendimento: {primeiro_empreendimento['nome']} (ID: {primeiro_empreendimento['id']})")
        logger.info(f"Período: 2020-01-01 a {data_fim}")
        
        logger.info(f"🔍 Buscando vendas realizadas - Página {pagina}")
        
        # Fazer requisição real
        result = await make_api_request('sienge_vendas_realizadas', endpoint, params)
        
        # Incrementar contador apenas se a requisição foi bem-sucedida
        if result.get('success', False):
            # Cada empreendimento conta como uma requisição
            self.incrementar_contador(1)
        
        return result
    
    async def get_vendas_canceladas(self, data_inicio: str, data_fim: str,
                                   pagina: int = 1, registros_por_pagina: int = 500) -> Dict[str, Any]:
        """
        Busca vendas canceladas do Sienge com controle de limite
        
        Args:
            data_inicio: Data de início (YYYY-MM-DD)
            data_fim: Data de fim (YYYY-MM-DD)
            pagina: Número da página
            registros_por_pagina: Registros por página
        """
        # VALIDAÇÕES PRÉ-REQUISIÇÃO
        if not self.validar_parametros(data_inicio, data_fim):
            return {'success': False, 'error': 'Parâmetros inválidos'}
        
        if not self.verificar_limite_requisicoes():
            return {'success': False, 'error': 'Limite diário de requisições atingido'}
        
        # MODO TESTE - Retorna dados simulados
        if self.modo_teste:
            logger.info("🧪 MODO TESTE - Retornando dados simulados para vendas canceladas")
            return {
                'success': True,
                'data': {
                    'dados': [],
                    'total_registros': 0,
                    'pagina_atual': pagina,
                    'total_paginas': 1
                },
                'modo_teste': True
            }
        
        # Endpoint baseado no código M do Power BI (mesmo das vendas realizadas)
        endpoint = ""
        
        # Parâmetros baseados no código M (um empreendimento por vez)
        # Usar apenas o primeiro empreendimento para esta requisição específica
        if not self.empreendimentos:
            return {'success': False, 'error': 'Nenhum empreendimento disponível'}
        
        # Para requisições individuais, usar apenas um empreendimento por vez
        # O loop será feito na função que chama esta
        primeiro_empreendimento = self.empreendimentos[0] if self.empreendimentos else None
        
        if not primeiro_empreendimento:
            return {'success': False, 'error': 'Nenhum empreendimento disponível'}
        
        params = {
            'enterpriseId': int(primeiro_empreendimento['id']),  # ID como inteiro
            'createdAfter': '2020-01-01',  # Data inicial fixa (como no Power BI)
            'createdBefore': data_fim,     # Data final (atualizada)
            'situation': 'CANCELED'        # Apenas vendas canceladas
        }
        
        logger.info(f"Filtrando por empreendimento: {primeiro_empreendimento['nome']} (ID: {primeiro_empreendimento['id']})")
        logger.info(f"Período: 2020-01-01 a {data_fim}")
        
        logger.info(f"🔍 Buscando vendas canceladas - Página {pagina}")
        
        # Fazer requisição real
        result = await make_api_request('sienge_vendas_canceladas', endpoint, params)
        
        # Incrementar contador apenas se a requisição foi bem-sucedida
        if result.get('success', False):
            # Cada empreendimento conta como uma requisição
            self.incrementar_contador(1)
        
        return result
    
    def processar_dados_vendas_realizadas(self, dados: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Processa dados de vendas realizadas baseado no código M do Power BI
        """
        if not dados:
            logger.info("Nenhum dado de vendas realizadas para processar")
            return pd.DataFrame()
        
        logger.info(f"Processando {len(dados)} registros de vendas realizadas")
        
        # Lista de colunas baseada no código M do Power BI
        colunas_esperadas = [
            "id", "enterpriseId", "receivableBillId", "refundBillId", "proRataIndexer",
            "number", "situation", "externalId", "note", "cancellationReason",
            "interestType", "lateInterestCalculationType", "financialInstitutionNumber",
            "discountType", "correctionType", "anualCorrectionType", "associativeCredit",
            "discountPercentage", "value", "totalSellingValue", "interestPercentage",
            "fineRate", "dailyLateInterestValue", "creationDate", "contractDate",
            "issueDate", "cancellationDate", "financialInstitutionDate",
            "customers", "units", "paymentConditions", "brokers"
        ]
        
        # Converter para DataFrame
        df = pd.DataFrame(dados)
        
        # Garantir que todas as colunas esperadas existam
        for coluna in colunas_esperadas:
            if coluna not in df.columns:
                df[coluna] = None
        
        # Selecionar apenas as colunas esperadas
        df = df[colunas_esperadas]
        
        # Converter tipos de dados (baseado no código M)
        try:
            # Converter contractDate para datetime
            if 'contractDate' in df.columns:
                df['contractDate'] = pd.to_datetime(df['contractDate'], errors='coerce')
            
            # CORREÇÃO: Converter valores numéricos com normalização otimizada
            colunas_numericas = ['value', 'totalSellingValue', 'interestPercentage', 'fineRate', 'dailyLateInterestValue']
            for col in colunas_numericas:
                if col in df.columns:
                    df[col] = df[col].apply(normalizar_valor_monetario_otimizado)
            
            # Converter IDs para string
            colunas_id = ['id', 'enterpriseId', 'receivableBillId', 'refundBillId']
            for col in colunas_id:
                if col in df.columns:
                    df[col] = df[col].astype(str)
            
        except Exception as e:
            logger.warning(f"Erro ao converter tipos de dados: {str(e)}")
        
        # Substituir valores de erro por None (como no código M)
        df = df.replace([float('inf'), float('-inf')], None)
        
        logger.info(f"DataFrame processado: {len(df)} registros, {len(df.columns)} colunas")
        return df
    
    def processar_dados_vendas_canceladas(self, dados: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Processa dados de vendas canceladas baseado no código M do Power BI
        (mesma estrutura das vendas realizadas)
        VERSÃO CORRIGIDA com normalização otimizada de valores monetários
        """
        if not dados:
            logger.info("Nenhum dado de vendas canceladas para processar")
            return pd.DataFrame()
        
        logger.info(f"Processando {len(dados)} registros de vendas canceladas")
        
        # Lista de colunas baseada no código M do Power BI (mesma das vendas realizadas)
        colunas_esperadas = [
            "id", "enterpriseId", "receivableBillId", "refundBillId", "proRataIndexer",
            "number", "situation", "externalId", "note", "cancellationReason",
            "interestType", "lateInterestCalculationType", "financialInstitutionNumber",
            "discountType", "correctionType", "anualCorrectionType", "associativeCredit",
            "discountPercentage", "value", "totalSellingValue", "interestPercentage",
            "fineRate", "dailyLateInterestValue", "creationDate", "contractDate",
            "issueDate", "cancellationDate", "financialInstitutionDate",
            "customers", "units", "paymentConditions", "brokers"
        ]
        
        # Converter para DataFrame
        df = pd.DataFrame(dados)
        
        # Garantir que todas as colunas esperadas existam
        for coluna in colunas_esperadas:
            if coluna not in df.columns:
                df[coluna] = None
        
        # Selecionar apenas as colunas esperadas
        df = df[colunas_esperadas]
        
        # Converter tipos de dados (baseado no código M)
        try:
            # Converter contractDate para datetime
            if 'contractDate' in df.columns:
                df['contractDate'] = pd.to_datetime(df['contractDate'], errors='coerce')
            
            # CORREÇÃO: Converter valores numéricos com normalização otimizada
            colunas_numericas = ['value', 'totalSellingValue', 'interestPercentage', 'fineRate', 'dailyLateInterestValue']
            for col in colunas_numericas:
                if col in df.columns:
                    df[col] = df[col].apply(normalizar_valor_monetario_otimizado)
            
            # Converter IDs para string
            colunas_id = ['id', 'enterpriseId', 'receivableBillId', 'refundBillId']
            for col in colunas_id:
                if col in df.columns:
                    df[col] = df[col].astype(str)
            
        except Exception as e:
            logger.warning(f"Erro ao converter tipos de dados: {str(e)}")
        
        # Substituir valores de erro por None (como no código M)
        df = df.replace([float('inf'), float('-inf')], None)
        
        logger.info(f"DataFrame processado: {len(df)} registros, {len(df.columns)} colunas")
        return df
    
    async def get_all_vendas_realizadas(self, data_inicio: str, data_fim: str) -> List[Dict[str, Any]]:
        """Busca todas as vendas realizadas paginadas"""
        pagina = 1
        todos_dados = []
        
        while True:
            try:
                result = await self.get_vendas_realizadas(data_inicio, data_fim, pagina)
                
                if not result['success']:
                    logger.error(f"Erro na página {pagina}: {result.get('error', 'Erro desconhecido')}")
                    break
                
                dados = _extrair_registros(result)
                if not dados:
                    break
                
                todos_dados.extend(dados)
                logger.info(f"Página {pagina} - {len(dados)} registros")
                
                # Se retornou menos que o esperado, é a última página
                if len(dados) < 500:
                    break
                
                pagina += 1
                
            except Exception as e:
                logger.error(f"Erro na página {pagina}: {str(e)}")
                break
        
        logger.info(f"Total de vendas realizadas: {len(todos_dados)}")
        return todos_dados

async def obter_dados_sienge_vendas_realizadas() -> pd.DataFrame:
    """
    Função principal para obter dados de vendas realizadas do Sienge
    Busca dados de todos os empreendimentos
    """
    try:
        from datetime import datetime, timedelta
        
        # Data limite = hoje (otimização: buscar até data atual)
        data_fim = datetime.now().strftime('%Y-%m-%d')
        data_inicio = '2020-01-01'  # Data inicial fixa como no Power BI
        
        logger.info(f"🔍 Buscando vendas realizadas do Sienge: {data_inicio} a {data_fim}")
        
        # Criar cliente
        client = SiengeAPIClient()
        
        todos_dados = []
        
        # Buscar dados de cada empreendimento individualmente
        logger.info(f"📊 Buscando dados de {len(client.empreendimentos)} empreendimentos")
        
        # Buscar dados de cada empreendimento
        for i, empreendimento in enumerate(client.empreendimentos, 1):
            logger.info(f"📊 Empreendimento {i}/{len(client.empreendimentos)}: {empreendimento['nome']} (ID: {empreendimento['id']})")
            
            # Temporariamente modificar a lista para usar apenas este empreendimento
            empreendimentos_originais = client.empreendimentos
            client.empreendimentos = [empreendimento]
            
            # Buscar dados
            result = await client.get_vendas_realizadas(data_inicio, data_fim)
            
            # Restaurar lista original
            client.empreendimentos = empreendimentos_originais
            
            if result.get('success', False):
                dados = _extrair_registros(result)
                if dados:
                    todos_dados.extend(dados)
                    logger.info(f"   ✅ {len(dados)} registros encontrados")
                else:
                    logger.info(f"   ⚪ Nenhum registro encontrado")
            else:
                logger.error(f"   ❌ Erro: {result.get('error', 'Erro desconhecido')}")
            
            # Pequeno delay entre requisições para evitar sobrecarga
            await asyncio.sleep(0.5)
        
        if not todos_dados:
            logger.info("Nenhuma venda realizada encontrada em nenhum empreendimento")
            return pd.DataFrame()
        
        # Processar todos os dados
        df = client.processar_dados_vendas_realizadas(todos_dados)
        
        logger.info(f"✅ Vendas realizadas processadas: {len(df)} registros de {len(client.empreendimentos)} empreendimentos")
        return df
        
    except Exception as e:
        logger.error(f"Erro ao obter vendas realizadas: {str(e)}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()

async def obter_dados_sienge_vendas_canceladas() -> pd.DataFrame:
    """
    Função principal para obter dados de vendas canceladas do Sienge
    Busca dados de todos os empreendimentos
    """
    try:
        from datetime import datetime, timedelta
        
        # Data limite = hoje (otimização: buscar até data atual)
        data_fim = datetime.now().strftime('%Y-%m-%d')
        data_inicio = '2020-01-01'  # Data inicial fixa como no Power BI
        
        logger.info(f"🔍 Buscando vendas canceladas do Sienge: {data_inicio} a {data_fim}")
        
        # Criar cliente
        client = SiengeAPIClient()
        
        todos_dados = []
        
        # Buscar dados de cada empreendimento individualmente
        logger.info(f"📊 Buscando dados de {len(client.empreendimentos)} empreendimentos")
        
        # Buscar dados de cada empreendimento
        for i, empreendimento in enumerate(client.empreendimentos, 1):
            logger.info(f"📊 Empreendimento {i}/{len(client.empreendimentos)}: {empreendimento['nome']} (ID: {empreendimento['id']})")
            
            # Temporariamente modificar a lista para usar apenas este empreendimento
            empreendimentos_originais = client.empreendimentos
            client.empreendimentos = [empreendimento]
            
            # Buscar dados
            result = await client.get_vendas_canceladas(data_inicio, data_fim)
            
            # Restaurar lista original
            client.empreendimentos = empreendimentos_originais
            
            if result.get('success', False):
                dados = _extrair_registros(result)
                if dados:
                    todos_dados.extend(dados)
                    logger.info(f"   ✅ {len(dados)} registros encontrados")
                else:
                    logger.info(f"   ⚪ Nenhum registro encontrado")
            else:
                logger.error(f"   ❌ Erro: {result.get('error', 'Erro desconhecido')}")
            
            # Pequeno delay entre requisições para evitar sobrecarga
            await asyncio.sleep(0.5)
        
        if not todos_dados:
            logger.info("Nenhuma venda cancelada encontrada em nenhum empreendimento")
            return pd.DataFrame()
        
        # Processar todos os dados
        df = client.processar_dados_vendas_canceladas(todos_dados)
        
        logger.info(f"✅ Vendas canceladas processadas: {len(df)} registros de {len(client.empreendimentos)} empreendimentos")
        return df
        
    except Exception as e:
        logger.error(f"Erro ao obter vendas canceladas: {str(e)}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()

async def get_all_vendas_canceladas(data_inicio: str, data_fim: str) -> List[Dict[str, Any]]:
    """Busca todas as vendas canceladas paginadas"""
    client = SiengeAPIClient()
    pagina = 1
    todos_dados = []
    
    while True:
        try:
            result = await client.get_vendas_canceladas(data_inicio, data_fim, pagina)
            
            if not result['success']:
                logger.error(f"Erro na página {pagina}: {result.get('error', 'Erro desconhecido')}")
                break
            
            dados = _extrair_registros(result)
            if not dados:
                break
            
            todos_dados.extend(dados)
            logger.info(f"Página {pagina} - {len(dados)} registros")
            
            # Se retornou menos que o esperado, é a última página
            if len(dados) < 500:
                break
            
            pagina += 1
            
        except Exception as e:
            logger.error(f"Erro na página {pagina}: {str(e)}")
            break
    
    logger.info(f"Total de vendas canceladas: {len(todos_dados)}")
    return todos_dados

def normalizar_valor_monetario_otimizado(valor):
    """
    Normalização otimizada de valores monetários
    - Se tem vírgula: já está no formato brasileiro correto
    - Se tem pontos: substitui apenas o ÚLTIMO ponto por vírgula
    - Se não tem nem pontos nem vírgulas: número simples
    """
    if pd.isna(valor) or valor is None:
        return 0.0
    
    valor_str = str(valor).replace('R$', '').replace('$', '').strip()
    
    # Se já tem vírgula, está no formato brasileiro correto
    if ',' in valor_str:
        return float(valor_str.replace(',', '.'))
    
    # Se tem pontos, substituir apenas o ÚLTIMO ponto por vírgula
    if '.' in valor_str:
        ultimo_ponto = valor_str.rfind('.')
        valor_corrigido = valor_str[:ultimo_ponto] + ',' + valor_str[ultimo_ponto+1:]
        return float(valor_corrigido.replace(',', '.'))
    
    # Número simples sem formatação
    try:
        return float(valor_str)
    except ValueError:
        return 0.0

def processar_dados_sienge(dados: List[Dict[str, Any]], tipo: str) -> pd.DataFrame:
    """
    Processa e padroniza dados do Sienge
    
    Args:
        dados: Lista de dados brutos
        tipo: 'realizadas' ou 'canceladas'
    """
    if not dados:
        logger.warning(f"Nenhum dado para processar - {tipo}")
        return pd.DataFrame()
    
    df = pd.DataFrame(dados)
    
    # Padronizar colunas de data
    colunas_data = ['data_venda', 'data_contrato', 'data_cancelamento']
    for col in colunas_data:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # CORREÇÃO: Padronizar valores monetários com função otimizada
    colunas_valor = ['valor_venda', 'valor_contrato', 'valor_cancelamento']
    for col in colunas_valor:
        if col in df.columns:
            df[col] = df[col].apply(normalizar_valor_monetario_otimizado)
    
    # Adicionar coluna de tipo
    df['tipo_venda'] = tipo
    
    # Adicionar timestamp de processamento
    df['processado_em'] = datetime.now()
    
    logger.info(f"Dados processados - {tipo}: {len(df)} registros")
    return df

async def obter_dados_sienge_completos(data_inicio: str = "2024-01-01", 
                                     data_fim: str = None) -> Dict[str, pd.DataFrame]:
    """
    Obtém todos os dados do Sienge (vendas realizadas e canceladas)
    
    Args:
        data_inicio: Data de início (padrão: 2024-01-01)
        data_fim: Data de fim (padrão: hoje)
    """
    if not data_fim:
        data_fim = datetime.now().strftime("%Y-%m-%d")
    
    logger.info(f"Buscando dados do Sienge de {data_inicio} a {data_fim}")
    
    client = SiengeAPIClient()
    
    # Buscar dados em paralelo
    vendas_realizadas_task = obter_dados_sienge_vendas_realizadas()
    vendas_canceladas_task = obter_dados_sienge_vendas_canceladas()
    
    vendas_realizadas, vendas_canceladas = await asyncio.gather(
        vendas_realizadas_task,
        vendas_canceladas_task,
        return_exceptions=True
    )
    
    # Os dados já vêm processados como DataFrames
    df_realizadas = vendas_realizadas if not isinstance(vendas_realizadas, Exception) else pd.DataFrame()
    df_canceladas = vendas_canceladas if not isinstance(vendas_canceladas, Exception) else pd.DataFrame()
    
    return {
        'vendas_realizadas': df_realizadas,
        'vendas_canceladas': df_canceladas
    }

if __name__ == "__main__":
    # Teste das APIs do Sienge
    async def test_sienge():
        print("=== Testando APIs do Sienge ===")
        
        try:
            dados = await obter_dados_sienge_completos("2024-01-01", "2024-01-31")
            
            print(f"Vendas realizadas: {len(dados['vendas_realizadas'])} registros")
            print(f"Vendas canceladas: {len(dados['vendas_canceladas'])} registros")
            
            if not dados['vendas_realizadas'].empty:
                print("\nColunas vendas realizadas:", list(dados['vendas_realizadas'].columns))
                print(dados['vendas_realizadas'].head())
            
        except Exception as e:
            print(f"Erro no teste: {str(e)}")
    
    asyncio.run(test_sienge())
