#!/usr/bin/env python3
"""
Integração com API do CV - Repasses Workflow
Endpoint: https://prati.cvcrm.com.br/api/v1/cvdw/repasses/workflow/tempo
Credenciais: mesmas de CV Vendas (email, token)

Características:
- Sem filtros (trazer todos os dados)
- Sem paginação (endpoint único)
- Dados de workflow de repasses
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

class CVRepassesWorkflowAPIClient:
    """Cliente para API de repasses workflow do CV"""
    
    def __init__(self):
        self.config = get_api_config('cv_repasses_workflow')
        
        if not self.config:
            raise ValueError("Configuração da API CV Repasses Workflow não encontrada")
    
    async def get_workflow_data(self, pagina: int = 1, registros_por_pagina: int = 500) -> Dict[str, Any]:
        """
        Busca dados do workflow de repasses com paginação.
        """
        endpoint = ""  # base_url já aponta direto para /cvdw/repasses/workflow/tempo
        params = {
            'registros_por_pagina': registros_por_pagina,
            'pagina': pagina
        }

        logger.info(f"Buscando CV Repasses Workflow - Página {pagina}")
        return await make_api_request('cv_repasses_workflow', endpoint, params)
    
    async def get_all_workflow_data(self, 
                                   registros_por_pagina: int = 500,
                                   max_paginas: int = 5000,
                                   sleep_between_calls: float = 0.0) -> List[Dict[str, Any]]:
        """
        Busca todos os dados do workflow de repasses com paginação.
        Sem filtros - traz todos os dados disponíveis.
        """
        logger.info("=== BUSCANDO DADOS DE WORKFLOW DE REPASSES ===")
        logger.info("Sem filtros - coletando todos os dados disponíveis com paginação")

        pagina = 1
        results: List[Dict[str, Any]] = []
        total_processed = 0
        paginas_vazias = 0
        max_paginas_vazias = 3

        while pagina <= max_paginas:
            try:
                result = await self.get_workflow_data(pagina, registros_por_pagina)
                
                if not result['success']:
                    error_msg = result.get('error', 'Erro desconhecido')
                    logger.error(f"Erro na página {pagina}: {error_msg}")
                    
                    # Se for erro 404, pode ser fim dos dados
                    if '404' in str(error_msg) or 'not found' in str(error_msg).lower():
                        logger.info("Fim dos dados detectado (erro 404)")
                        break
                    break

                data = result['data']
                dados = data.get("dados", [])
                total_pages = data.get("total_de_paginas")
                registros = data.get("registros", len(dados))
                
                logger.info(f"Dados recebidos: {len(dados) if isinstance(dados, list) else 'não é uma lista'}")
                logger.info(f"Total de páginas: {total_pages}, Registros nesta página: {registros}")
                
                if not isinstance(dados, list) or len(dados) == 0:
                    paginas_vazias += 1
                    logger.info(f"Página {pagina} vazia ({paginas_vazias}/{max_paginas_vazias})")
                    
                    if paginas_vazias >= max_paginas_vazias:
                        logger.info(f"Fim da paginação: {paginas_vazias} páginas vazias consecutivas")
                        break
                else:
                    paginas_vazias = 0  # Reset contador de páginas vazias
                    
                    # Adiciona todos os registros (sem filtros)
                    for item in dados:
                        total_processed += 1
                        results.append(item)

                    # Condições de parada
                    if len(dados) < registros_por_pagina:
                        logger.info("Página com menos registros que o tamanho da página, parando.")
                        break
                    
                    if total_pages and pagina >= total_pages:
                        logger.info(f"Alcançou o total de páginas ({total_pages}), parando.")
                        break

                pagina += 1
                if sleep_between_calls > 0:
                    await asyncio.sleep(sleep_between_calls)

            except Exception as e:
                logger.error(f"Erro na página {pagina}: {str(e)}")
                break

        logger.info(f"\n=== RESUMO REPASSES WORKFLOW ===")
        logger.info(f"Total de registros processados: {total_processed}")
        logger.info(f"Registros finais salvos: {len(results)}")
        
        return results

def processar_dados_cv_repasses_workflow(dados: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Processa e padroniza dados do workflow de repasses do CV
    
    Args:
        dados: Lista de dados brutos
    """
    if not dados:
        logger.warning("Nenhum dado para processar - CV Repasses Workflow")
        return pd.DataFrame()
    
    df = pd.DataFrame(dados)
    
    # Padronizar colunas de data se existirem
    colunas_data = ['data_cad', 'data_alteracao', 'data_vencimento', 'data_processamento']
    for col in colunas_data:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # Padronizar valores numéricos se existirem
    colunas_numericas = ['valor', 'tempo_dias', 'tempo_horas', 'percentual']
    for col in colunas_numericas:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Adicionar coluna de fonte
    df['fonte'] = 'cv_repasses_workflow'
    
    # Adicionar timestamp de processamento
    df['processado_em'] = datetime.now()
    
    logger.info(f"Dados processados - CV Repasses Workflow: {len(df)} registros")
    return df

async def obter_dados_cv_repasses_workflow() -> pd.DataFrame:
    """Obtém todos os dados do workflow de repasses do CV com paginação."""
    logger.info("Buscando dados do CV Repasses Workflow (todas as páginas)")

    client = CVRepassesWorkflowAPIClient()
    dados = await client.get_all_workflow_data(
        registros_por_pagina=500,
        max_paginas=5000,
        sleep_between_calls=0.5  # 0.5s entre chamadas para evitar rate limiting
    )

    return processar_dados_cv_repasses_workflow(dados)

if __name__ == "__main__":
    # Teste da API do CV Repasses Workflow
    async def test_cv_repasses_workflow():
        print("=== Testando API CV Repasses Workflow ===")
        
        try:
            df = await obter_dados_cv_repasses_workflow()
            
            print(f"Registros encontrados: {len(df)}")
            
            if not df.empty:
                print("\nColunas:", list(df.columns))
                print(df.head())
            
        except Exception as e:
            print(f"Erro no teste: {str(e)}")
    
    asyncio.run(test_cv_repasses_workflow())

