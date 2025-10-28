#!/usr/bin/env python3
"""
Integração com API do CV - Leads Workflow Tempo
Endpoint: https://prati.cvcrm.com.br/api/v1/cvdw/leads/workflow/tempo
Credenciais: mesmas de CV Vendas (email, token)

Adaptação do código fornecido:
- Paginação por 'pagina' e 'registros_por_pagina'
- Filtros de data (a_partir_data_referencia, ate_data_referencia)
- Filtro de data de corte: 01/01/2022
- Processamento com pandas e upload para MotherDuck
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from scripts.orchestrator import make_api_request
from scripts.config import get_api_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CVLeadsWorkflowTempoAPIClient:
    """Cliente para API de Leads Workflow Tempo do CV"""
    
    def __init__(self):
        self.config = get_api_config('cv_leads_workflow_tempo')
        
        if not self.config:
            raise ValueError("Configuração da API CV Leads Workflow Tempo não encontrada")
        
        self.base_url = self.config.base_url
        self.headers = self.config.headers
    
    async def get_pagina(self, pagina: int, registros_por_pagina: int = 500, 
                        data_inicio: str = "2022-01-01", data_fim: str = None) -> Dict[str, Any]:
        """
        Busca uma página específica da API
        
        Args:
            pagina (int): Número da página
            registros_por_pagina (int): Quantidade de registros por página
            data_inicio (str): Data de início no formato YYYY-MM-DD
            data_fim (str): Data de fim no formato YYYY-MM-DD
            
        Returns:
            Dict com os dados da resposta
        """
        if data_fim is None:
            data_fim = datetime.now().strftime("%Y-%m-%d")
        
        endpoint = ""  # base_url já aponta direto para /cvdw/leads/workflow/tempo
        params = {
            "pagina": pagina,
            "registros_por_pagina": registros_por_pagina,
            "a_partir_data_referencia": data_inicio,
            "ate_data_referencia": data_fim
        }
        
        logger.info(f"Buscando CV Leads Workflow Tempo - Página {pagina}")
        return await make_api_request('cv_leads_workflow_tempo', endpoint, params)
    
    def filtrar_por_data(self, dados: List[Dict]) -> List[Dict]:
        """
        Filtra dados a partir de 01/01/2022
        
        Args:
            dados (List[Dict]): Lista de dados para filtrar
            
        Returns:
            List[Dict]: Dados filtrados
        """
        DATA_CORTE = datetime(2022, 1, 1)
        dados_filtrados = []
        
        for item in dados:
            try:
                # Tentar diferentes campos de data que podem existir nos dados de leads
                data_str = None
                for campo_data in ['referencia_data', 'data_cad', 'data_criacao', 'created_at', 'data']:
                    if campo_data in item and item[campo_data]:
                        data_str = str(item[campo_data]).split()[0]
                        break
                
                if data_str:
                    data_item = datetime.strptime(data_str, "%Y-%m-%d")
                    if data_item >= DATA_CORTE:
                        dados_filtrados.append(item)
            except (ValueError, AttributeError, TypeError):
                continue
                
        return dados_filtrados
    
    def processar_dados(self, dados: List[Dict]) -> pd.DataFrame:
        """
        Processa os dados coletados e retorna DataFrame
        
        Args:
            dados (List[Dict]): Lista de dados brutos
            
        Returns:
            pd.DataFrame: DataFrame processado
        """
        if not dados:
            logger.warning("Nenhum dado para processar")
            return pd.DataFrame()
        
        logger.info(f"Processando {len(dados)} registros de Leads Workflow Tempo")
        
        # Converter para DataFrame
        df = pd.DataFrame(dados)
        
        # Adicionar colunas de controle
        df['fonte'] = 'cv_leads_workflow_tempo'
        df['processado_em'] = datetime.now()
        
        # Log das colunas disponíveis
        logger.info(f"Colunas disponíveis: {list(df.columns)}")
        
        return df

async def obter_dados_cv_leads_workflow_tempo(data_inicio: str = "2022-01-01") -> pd.DataFrame:
    """
    Função principal para obter dados de Leads Workflow Tempo
    
    Args:
        data_inicio (str): Data de início no formato YYYY-MM-DD
        
    Returns:
        pd.DataFrame: DataFrame com os dados processados
    """
    logger.info("Buscando dados do CV Leads Workflow Tempo")
    
    try:
        client = CVLeadsWorkflowTempoAPIClient()
        
        # Configurar período
        data_fim = datetime.now().strftime("%Y-%m-%d")
        logger.info(f"Buscando Leads Workflow Tempo de {data_inicio} até {data_fim}")
        
        # Coletar todos os dados paginados
        pagina = 1
        registros_por_pagina = 500
        todos_dados = []
        
        while True:
            result = await client.get_pagina(
                pagina=pagina,
                registros_por_pagina=registros_por_pagina,
                data_inicio=data_inicio,
                data_fim=data_fim
            )
            
            if result['success']:
                dados = result['data'].get('dados', [])
                
                if not dados:
                    logger.info("Nenhum dado encontrado nesta página. Finalizando busca.")
                    break
                
                # Debug: mostrar estrutura dos dados na primeira página
                if pagina == 1 and dados:
                    logger.info(f"Estrutura dos dados (primeiro registro): {list(dados[0].keys())}")
                
                # Filtrar por data
                dados_filtrados = client.filtrar_por_data(dados)
                todos_dados.extend(dados_filtrados)
                logger.info(f"Após filtro de data: {len(dados_filtrados)} registros válidos")
                
                if len(dados) < registros_por_pagina:
                    logger.info("Última página atingida.")
                    break
                    
                pagina += 1
                
            else:
                logger.error(f"Erro na página {pagina}: {result.get('error', 'Erro desconhecido')}")
                break
        
        logger.info(f"Total de registros encontrados: {len(todos_dados)}")
        
        # Processar dados
        df_processado = client.processar_dados(todos_dados)
        
        logger.info(f"Dados processados - CV Leads Workflow Tempo: {len(df_processado)} registros")
        
        return df_processado
        
    except Exception as e:
        logger.error(f"Erro ao obter dados de Leads Workflow Tempo: {str(e)}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()

if __name__ == "__main__":
    # Teste local
    async def teste():
        df = await obter_dados_cv_leads_workflow_tempo()
        print(f"Teste concluído: {len(df)} registros")
        if not df.empty:
            print(f"Colunas: {list(df.columns)}")
            print(f"Primeiros registros:")
            print(df.head())
    
    asyncio.run(teste())
