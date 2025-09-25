#!/usr/bin/env python3
"""
Integração com API do CV - Leads
Endpoint: https://prati.cvcrm.com.br/api/v1/cvdw/leads
Credenciais: mesmas de CV Vendas (email, token)

Baseado no código fornecido pelo usuário:
- Paginação por 'pagina' e 'registros_por_pagina'
- Filtro por imobiliária: manter "Prati" OU vazio/nulo
- Sem filtro de data (busca dados mais atualizados)
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

class CVLeadsAPIClient:
    """Cliente para API de leads do CV"""
    
    def __init__(self):
        self.config = get_api_config('cv_leads')
        
        if not self.config:
            raise ValueError("Configuração da API CV Leads não encontrada")
    
    async def get_pagina(self, pagina: int = 1, registros_por_pagina: int = 500) -> Dict[str, Any]:
        """
        Busca uma página dos leads do CV.
        """
        endpoint = ""  # base_url já aponta direto para /cvdw/leads
        params = {
            'pagina': pagina,
            'registros_por_pagina': registros_por_pagina
        }

        logger.info(f"Buscando CV Leads - Página {pagina}")
        return await make_api_request('cv_leads', endpoint, params)
    
    async def get_all_leads(self, 
                           registros_por_pagina: int = 500,
                           imobiliaria_match: str = "Prati",
                           include_empty_imobiliaria: bool = True,
                           max_paginas: int = 5000,
                           sleep_between_calls: float = 0.0) -> List[Dict[str, Any]]:
        """
        Busca todos os leads com paginação automática e filtros.
        
        Args:
            registros_por_pagina: Número de registros por página
            imobiliaria_match: Filtro para imobiliária (padrão: "Prati")
            include_empty_imobiliaria: Incluir registros com imobiliária vazia
            max_paginas: Limite máximo de páginas
            sleep_between_calls: Delay entre chamadas (segundos)
        """
        pagina = 1
        results: List[Dict[str, Any]] = []
        total_processed = 0
        total_filtered = 0
        paginas_vazias = 0
        max_paginas_vazias = 3

        logger.info("=== BUSCANDO LEADS SEM FILTRO DE DATA ===")
        logger.info(f"Filtro imobiliária: '{imobiliaria_match}' (incluir vazias: {include_empty_imobiliaria})")

        while pagina <= max_paginas:
            try:
                result = await self.get_pagina(pagina, registros_por_pagina)
                
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
                    
                    # Processar cada item com filtros
                    for item in dados:
                        total_processed += 1
                        imob = (item.get("imobiliaria") or "").strip()

                        # Filtro: manter "Prati" OU vazio/nulo
                        is_prati = imobiliaria_match.lower() in imob.lower() if imob else False
                        is_empty = (imob == "")
                        
                        # Debug: mostrar alguns exemplos de imobiliárias
                        if len(results) < 5:  # Mostrar apenas os primeiros 5 para debug
                            logger.info(f"Debug - Imobiliaria: '{imob}', is_prati: {is_prati}, is_empty: {is_empty}")
                        
                        if not (is_prati or (include_empty_imobiliaria and is_empty)):
                            continue

                        total_filtered += 1
                        row = {
                            "Idlead": item.get("idlead"),
                            "Data_cad": item.get("data_cad"),
                            "Situacao": item.get("situacao"),
                            "Imobiliaria": item.get("imobiliaria"),
                            "nome_situacao_anterior_lead": item.get("nome_situacao_anterior_lead"),
                            "gestor": item.get("gestor"),
                            "empreendimento_ultimo": item.get("empreendimento_ultimo"),
                        }
                        results.append(row)

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

        logger.info(f"\n=== RESUMO ===")
        logger.info(f"Total de registros processados: {total_processed}")
        logger.info(f"Total de registros filtrados (Prati + vazias): {total_filtered}")
        logger.info(f"Registros finais salvos: {len(results)}")
        
        return results

def processar_dados_cv_leads(dados: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Processa e padroniza dados dos leads do CV
    
    Args:
        dados: Lista de dados brutos
    """
    if not dados:
        logger.warning("Nenhum dado para processar - CV Leads")
        return pd.DataFrame()
    
    df = pd.DataFrame(dados)
    
    # Padronizar colunas de data
    if 'Data_cad' in df.columns:
        df['Data_cad'] = pd.to_datetime(df['Data_cad'], errors='coerce')
    
    # Adicionar coluna de fonte
    df['fonte'] = 'cv_leads'
    
    # Adicionar timestamp de processamento
    df['processado_em'] = datetime.now()
    
    logger.info(f"Dados processados - CV Leads: {len(df)} registros")
    return df

async def obter_dados_cv_leads() -> pd.DataFrame:
    """Obtém todos os dados de leads do CV com paginação automática."""
    logger.info("Buscando dados do CV Leads (todas as páginas)")

    client = CVLeadsAPIClient()
    dados = await client.get_all_leads(
        registros_por_pagina=500,
        imobiliaria_match="Prati",
        include_empty_imobiliaria=True,
        max_paginas=5000,
        sleep_between_calls=0.0
    )

    return processar_dados_cv_leads(dados)

if __name__ == "__main__":
    # Teste da API do CV Leads
    async def test_cv_leads():
        print("=== Testando API CV Leads ===")
        
        try:
            df = await obter_dados_cv_leads()
            
            print(f"Registros encontrados: {len(df)}")
            
            if not df.empty:
                print("\nColunas:", list(df.columns))
                print(df.head())
            
        except Exception as e:
            print(f"Erro no teste: {str(e)}")
    
    asyncio.run(test_cv_leads())
