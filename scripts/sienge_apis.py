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
        
        # Buscar empreendimentos da tabela reservas_abril
        # Colunas corretas: idempreendimento (BIGINT) e empreendimento (VARCHAR)
        query = """
        SELECT DISTINCT 
            idempreendimento,
            empreendimento
        FROM reservas.main.reservas_abril 
        WHERE idempreendimento IS NOT NULL
        ORDER BY empreendimento
        """
        
        logger.info("Buscando lista de empreendimentos do MotherDuck...")
        result = conn.execute(query).fetchall()
        
        # Converter para lista de dicionários
        empreendimentos = [empreendimento_fixo]  # Começar com o fixo
        
        for row in result:
            empreendimentos.append({
                'id': row[0],
                'nome': row[1]
            })
        
        conn.close()
        logger.info(f"Total de empreendimentos: {len(empreendimentos)} (1 fixo + {len(result)} automáticos)")
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
        
        # Controle de limite diário (50 requisições por empreendimento)
        self.limite_diario = 50
        self.requisicoes_hoje = 0
        self.modo_teste = os.environ.get('SIENGE_MODO_TESTE', 'false').lower() == 'true'
        
        # Calcular requisições necessárias por execução
        self.empreendimentos_count = len(self.empreendimentos)
        self.requisicoes_por_execucao = self.empreendimentos_count * 2  # 2 APIs (realizadas + canceladas)
        self.execucoes_possiveis = self.limite_diario // self.requisicoes_por_execucao
        
        logger.info(f"📊 Controle de limite:")
        logger.info(f"   - Empreendimentos: {self.empreendimentos_count}")
        logger.info(f"   - Requisições por execução: {self.requisicoes_por_execucao}")
        logger.info(f"   - Execuções possíveis por dia: {self.execucoes_possiveis}")
        
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
        
        endpoint = "/vendas/realizadas"
        params = {
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'pagina': pagina,
            'registros_por_pagina': registros_por_pagina
        }
        
        # Adicionar lista de empreendimentos se disponível
        if self.empreendimentos:
            empreendimento_ids = [emp['id'] for emp in self.empreendimentos]
            params['empreendimentos'] = empreendimento_ids
            logger.info(f"Filtrando por {len(empreendimento_ids)} empreendimentos")
        
        logger.info(f"🔍 Buscando vendas realizadas - Página {pagina}")
        
        # Fazer requisição real
        result = await make_api_request('sienge_vendas_realizadas', endpoint, params)
        
        # Incrementar contador apenas se a requisição foi bem-sucedida
        if result.get('success', False):
            # Cada empreendimento conta como uma requisição
            self.incrementar_contador(self.empreendimentos_count)
        
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
        
        endpoint = "/vendas/canceladas"
        params = {
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'pagina': pagina,
            'registros_por_pagina': registros_por_pagina
        }
        
        # Adicionar lista de empreendimentos se disponível
        if self.empreendimentos:
            empreendimento_ids = [emp['id'] for emp in self.empreendimentos]
            params['empreendimentos'] = empreendimento_ids
            logger.info(f"Filtrando por {len(empreendimento_ids)} empreendimentos")
        
        logger.info(f"🔍 Buscando vendas canceladas - Página {pagina}")
        
        # Fazer requisição real
        result = await make_api_request('sienge_vendas_canceladas', endpoint, params)
        
        # Incrementar contador apenas se a requisição foi bem-sucedida
        if result.get('success', False):
            # Cada empreendimento conta como uma requisição
            self.incrementar_contador(self.empreendimentos_count)
        
        return result
    
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
                
                dados = result['data'].get('dados', [])
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
    
    async def get_all_vendas_canceladas(self, data_inicio: str, data_fim: str) -> List[Dict[str, Any]]:
        """Busca todas as vendas canceladas paginadas"""
        pagina = 1
        todos_dados = []
        
        while True:
            try:
                result = await self.get_vendas_canceladas(data_inicio, data_fim, pagina)
                
                if not result['success']:
                    logger.error(f"Erro na página {pagina}: {result.get('error', 'Erro desconhecido')}")
                    break
                
                dados = result['data'].get('dados', [])
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
    
    # Padronizar valores monetários
    colunas_valor = ['valor_venda', 'valor_contrato', 'valor_cancelamento']
    for col in colunas_valor:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: float(str(x).replace('R$', '').replace('.', '').replace(',', '.')) if pd.notna(x) else 0)
    
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
    vendas_realizadas_task = client.get_all_vendas_realizadas(data_inicio, data_fim)
    vendas_canceladas_task = client.get_all_vendas_canceladas(data_inicio, data_fim)
    
    vendas_realizadas, vendas_canceladas = await asyncio.gather(
        vendas_realizadas_task,
        vendas_canceladas_task,
        return_exceptions=True
    )
    
    # Processar dados
    df_realizadas = processar_dados_sienge(vendas_realizadas, 'realizadas')
    df_canceladas = processar_dados_sienge(vendas_canceladas, 'canceladas')
    
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
