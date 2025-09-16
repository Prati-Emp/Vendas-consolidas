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

from orchestrator import make_api_request
from config import get_api_config

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SiengeAPIClient:
    """Cliente para APIs do Sienge"""
    
    def __init__(self):
        self.config_vendas = get_api_config('sienge_vendas_realizadas')
        self.config_canceladas = get_api_config('sienge_vendas_canceladas')
        
        if not self.config_vendas or not self.config_canceladas:
            raise ValueError("Configurações do Sienge não encontradas")
    
    async def get_vendas_realizadas(self, data_inicio: str, data_fim: str, 
                                   pagina: int = 1, registros_por_pagina: int = 500) -> Dict[str, Any]:
        """
        Busca vendas realizadas do Sienge
        
        Args:
            data_inicio: Data de início (YYYY-MM-DD)
            data_fim: Data de fim (YYYY-MM-DD)
            pagina: Número da página
            registros_por_pagina: Registros por página
        """
        endpoint = "/vendas/realizadas"
        params = {
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'pagina': pagina,
            'registros_por_pagina': registros_por_pagina
        }
        
        logger.info(f"Buscando vendas realizadas - Página {pagina}")
        return await make_api_request('sienge_vendas_realizadas', endpoint, params)
    
    async def get_vendas_canceladas(self, data_inicio: str, data_fim: str,
                                   pagina: int = 1, registros_por_pagina: int = 500) -> Dict[str, Any]:
        """
        Busca vendas canceladas do Sienge
        
        Args:
            data_inicio: Data de início (YYYY-MM-DD)
            data_fim: Data de fim (YYYY-MM-DD)
            pagina: Número da página
            registros_por_pagina: Registros por página
        """
        endpoint = "/vendas/canceladas"
        params = {
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'pagina': pagina,
            'registros_por_pagina': registros_por_pagina
        }
        
        logger.info(f"Buscando vendas canceladas - Página {pagina}")
        return await make_api_request('sienge_vendas_canceladas', endpoint, params)
    
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
