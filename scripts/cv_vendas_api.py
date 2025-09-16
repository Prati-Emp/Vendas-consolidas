#!/usr/bin/env python3
"""
Integração com API do CV - Relatório de Vendas
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

class CVVendasAPIClient:
    """Cliente para API de vendas do CV"""
    
    def __init__(self):
        self.config = get_api_config('cv_vendas')
        
        if not self.config:
            raise ValueError("Configuração da API CV Vendas não encontrada")
    
    async def get_relatorio_vendas(self, data_inicio: str, data_fim: str,
                                  pagina: int = 1, registros_por_pagina: int = 500) -> Dict[str, Any]:
        """
        Busca relatório de vendas do CV
        
        Args:
            data_inicio: Data de início (YYYY-MM-DD)
            data_fim: Data de fim (YYYY-MM-DD)
            pagina: Número da página
            registros_por_pagina: Registros por página
        """
        endpoint = "/relatorio/vendas"
        params = {
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'pagina': pagina,
            'registros_por_pagina': registros_por_pagina
        }
        
        logger.info(f"Buscando relatório de vendas CV - Página {pagina}")
        return await make_api_request('cv_vendas', endpoint, params)
    
    async def get_all_relatorio_vendas(self, data_inicio: str, data_fim: str) -> List[Dict[str, Any]]:
        """Busca todo o relatório de vendas paginado"""
        pagina = 1
        todos_dados = []
        
        while True:
            try:
                result = await self.get_relatorio_vendas(data_inicio, data_fim, pagina)
                
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
        
        logger.info(f"Total de registros do relatório CV: {len(todos_dados)}")
        return todos_dados

def processar_dados_cv_vendas(dados: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Processa e padroniza dados do relatório de vendas do CV
    
    Args:
        dados: Lista de dados brutos
    """
    if not dados:
        logger.warning("Nenhum dado para processar - CV Vendas")
        return pd.DataFrame()
    
    df = pd.DataFrame(dados)
    
    # Padronizar colunas de data
    colunas_data = ['data_venda', 'data_contrato', 'data_emissao', 'data_viagem']
    for col in colunas_data:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # Padronizar valores monetários
    colunas_valor = ['valor_venda', 'valor_contrato', 'valor_comissao', 'valor_imposto']
    for col in colunas_valor:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: float(str(x).replace('R$', '').replace('.', '').replace(',', '.')) if pd.notna(x) else 0)
    
    # Adicionar coluna de fonte
    df['fonte'] = 'cv_vendas'
    
    # Adicionar timestamp de processamento
    df['processado_em'] = datetime.now()
    
    logger.info(f"Dados processados - CV Vendas: {len(df)} registros")
    return df

async def obter_dados_cv_vendas(data_inicio: str = "2024-01-01", 
                               data_fim: str = None) -> pd.DataFrame:
    """
    Obtém todos os dados do relatório de vendas do CV
    
    Args:
        data_inicio: Data de início (padrão: 2024-01-01)
        data_fim: Data de fim (padrão: hoje)
    """
    if not data_fim:
        data_fim = datetime.now().strftime("%Y-%m-%d")
    
    logger.info(f"Buscando dados do CV Vendas de {data_inicio} a {data_fim}")
    
    client = CVVendasAPIClient()
    dados = await client.get_all_relatorio_vendas(data_inicio, data_fim)
    
    return processar_dados_cv_vendas(dados)

if __name__ == "__main__":
    # Teste da API do CV Vendas
    async def test_cv_vendas():
        print("=== Testando API CV Vendas ===")
        
        try:
            df = await obter_dados_cv_vendas("2024-01-01", "2024-01-31")
            
            print(f"Registros encontrados: {len(df)}")
            
            if not df.empty:
                print("\nColunas:", list(df.columns))
                print(df.head())
            
        except Exception as e:
            print(f"Erro no teste: {str(e)}")
    
    asyncio.run(test_cv_vendas())
