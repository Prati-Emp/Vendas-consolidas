#!/usr/bin/env python3
"""
Integração com API do CV - Reservas
Adaptação conforme código fornecido:
- Endpoint: https://prati.cvcrm.com.br/api/v1/cvdw/repasses
- Headers: accept, email, token
- Paginação: parâmetro 'pagina' (inteiro iniciando em 1)
- Usa total_de_paginas da resposta para otimizar busca
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd

from scripts.orchestrator import make_api_request
from scripts.config import get_api_config

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CVReservasAPIClient:
    """Cliente para API de reservas do CV (usando endpoint de repasses)"""
    
    def __init__(self):
        self.config = get_api_config('cv_reservas')
        
        if not self.config:
            raise ValueError("Configuração da API CV Reservas não encontrada")
    
    async def get_pagina(self, pagina: int = 1, a_partir_data: str = "2020-01-01", 
                        ate_data: Optional[str] = None, registros_por_pagina: int = 500) -> Dict[str, Any]:
        """
        Busca uma página das reservas do CV.
        
        Args:
            pagina: Número da página (inicia em 1)
            a_partir_data: Data de início no formato YYYY-MM-DD
            ate_data: Data de fim no formato YYYY-MM-DD (padrão: hoje)
            registros_por_pagina: Quantidade de registros por página (padrão: 500)
        """
        endpoint = ""  # base_url já aponta direto para /cvdw/repasses
        
        if not ate_data:
            ate_data = datetime.now().strftime("%Y-%m-%d")
        
        params = {
            'pagina': str(pagina),
            'a_partir_data_referencia': a_partir_data,
            'ate_data_referencia': ate_data,
            'registros_por_pagina': str(registros_por_pagina)
        }

        logger.info(f"Buscando CV Reservas - Página {pagina}")
        return await make_api_request('cv_reservas', endpoint, params)
    
    async def get_all_reservas(self, a_partir_data: str = "2020-01-01", 
                               ate_data: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Busca todas as reservas com paginação otimizada usando total_de_paginas.
        
        Args:
            a_partir_data: Data de início no formato YYYY-MM-DD
            ate_data: Data de fim no formato YYYY-MM-DD (padrão: hoje)
        """
        if not ate_data:
            ate_data = datetime.now().strftime("%Y-%m-%d")
        
        # Primeira requisição para descobrir total de páginas
        logger.info("Consultando API para descobrir total de páginas...")
        primeira_result = await self.get_pagina(1, a_partir_data, ate_data)
        
        if not primeira_result.get('success'):
            error_msg = primeira_result.get('error', 'Erro desconhecido')
            logger.error(f"Erro na consulta inicial: {error_msg}")
            return []
        
        # Extrair total de páginas da resposta
        total_paginas = primeira_result.get('data', {}).get('total_de_paginas', 1)
        logger.info(f"Total de páginas encontradas: {total_paginas}")
        
        # Coletar dados da primeira página
        todos_dados: List[Dict[str, Any]] = []
        dados_primeira = primeira_result.get('data', {}).get('dados', [])
        if dados_primeira:
            todos_dados.extend(dados_primeira)
            logger.info(f"Página 1 - {len(dados_primeira)} registros (Total: {len(todos_dados)})")
        
        # Rate limiting flexível
        agora = datetime.now()
        hora_atual = agora.hour
        
        if hora_atual in [0, 1, 2]:  # Madrugada
            delay_base = 0.2  # Mais rápido
            logger.info("🌙 Modo madrugada: Rate limiting otimizado")
        else:
            delay_base = 0.3  # Mais flexível em outros horários
            logger.info("☀️ Modo diurno: Rate limiting flexível")
        
        # Buscar páginas restantes
        for pagina in range(2, total_paginas + 1):
            try:
                result = await self.get_pagina(pagina, a_partir_data, ate_data)
                
                if not result.get('success'):
                    error_msg = result.get('error', 'Erro desconhecido')
                    logger.error(f"Erro na página {pagina}: {error_msg}")
                    break
                
                dados = result.get('data', {}).get('dados', [])
                
                if dados:
                    todos_dados.extend(dados)
                    logger.info(f"Página {pagina}/{total_paginas} - {len(dados)} registros (Total: {len(todos_dados)})")
                else:
                    logger.warning(f"Página {pagina} retornou vazia")
                
                await asyncio.sleep(delay_base)  # Rate limiting
                
            except Exception as e:
                logger.error(f"Erro na página {pagina}: {str(e)}")
                break
        
        logger.info(f"Total de registros CV Reservas: {len(todos_dados)} em {total_paginas} páginas")
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

def processar_dados_cv_reservas(dados: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Processa e padroniza dados de reservas do CV
    
    Args:
        dados: Lista de dados brutos
    """
    if not dados:
        logger.warning("Nenhum dado para processar - CV Reservas")
        return pd.DataFrame()
    
    df = pd.DataFrame(dados)
    
    # Padronizar colunas de data (mantém compatível caso algumas não existam)
    colunas_data = ['data_cad', 'data_referencia', 'data_contrato', 'data_emissao']
    for col in colunas_data:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # Padronizar valores monetários com função otimizada
    colunas_valor = ['valor_previsto', 'valor_divida', 'valor_subsidio', 
                     'valor_fgts', 'valor_registro', 'valor_financiado', 'valor_contrato']
    for col in colunas_valor:
        if col in df.columns:
            df[col] = df[col].apply(normalizar_valor_monetario_otimizado)
    
    # Padronizar colunas numéricas
    if 'codigointerno_empreendimento' in df.columns:
        df['codigointerno_empreendimento'] = pd.to_numeric(
            df['codigointerno_empreendimento'], errors='coerce'
        ).astype('Int64')
    
    # Adicionar coluna de fonte
    df['fonte'] = 'cv_reservas'
    
    # Adicionar timestamp de processamento
    df['processado_em'] = datetime.now()
    
    logger.info(f"Dados processados - CV Reservas: {len(df)} registros")
    return df

async def obter_dados_cv_reservas(a_partir_data: str = "2020-01-01", 
                                  ate_data: Optional[str] = None) -> pd.DataFrame:
    """
    Obtém todos os dados de reservas do CV com paginação automática.
    
    Args:
        a_partir_data: Data de início no formato YYYY-MM-DD
        ate_data: Data de fim no formato YYYY-MM-DD (padrão: hoje)
    """
    logger.info("Buscando dados do CV Reservas (todas as páginas)")

    client = CVReservasAPIClient()
    dados = await client.get_all_reservas(a_partir_data, ate_data)

    return processar_dados_cv_reservas(dados)

if __name__ == "__main__":
    # Teste da API do CV Reservas
    async def test_cv_reservas():
        print("=== Testando API CV Reservas ===")
        
        try:
            df = await obter_dados_cv_reservas()
            
            print(f"Registros encontrados: {len(df)}")
            
            if not df.empty:
                print("\nColunas:", list(df.columns))
                print(df.head())
            
        except Exception as e:
            print(f"Erro no teste: {str(e)}")
            import traceback
            traceback.print_exc()
    
    asyncio.run(test_cv_reservas())

