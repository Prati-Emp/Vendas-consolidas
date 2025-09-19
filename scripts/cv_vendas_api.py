#!/usr/bin/env python3
"""
Integração com API do CV - Vendas
Adaptação conforme código M (Power BI):
- Endpoint: https://prati.cvcrm.com.br/api/v1/cvdw/vendas
- Headers: accept, email, token
- Paginação: parâmetro 'pagina' (inteiro iniciando em 1)
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd

from scripts.orchestrator import make_api_request
from scripts.config import get_api_config

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CVVendasAPIClient:
    """Cliente para API de vendas do CV"""
    
    def __init__(self):
        self.config = get_api_config('cv_vendas')
        
        if not self.config:
            raise ValueError("Configuração da API CV Vendas não encontrada")
    
    async def get_pagina(self, pagina: int = 1) -> Dict[str, Any]:
        """
        Busca uma página das vendas do CV.

        Observação: conforme o código M, a API usa apenas 'pagina'.
        """
        endpoint = ""  # base_url já aponta direto para /cvdw/vendas
        params = {
            'pagina': pagina
        }

        logger.info(f"Buscando CV Vendas - Página {pagina}")
        return await make_api_request('cv_vendas', endpoint, params)
    
    async def get_all_vendas(self) -> List[Dict[str, Any]]:
        """Busca todas as vendas com rate limiting otimizado e lógica robusta"""
        pagina = 1
        todos_dados: List[Dict[str, Any]] = []
        paginas_vazias = 0
        max_paginas_vazias = 3  # Reduzido para ser mais eficiente
        max_paginas_seguranca = 5000  # Aumentado para permitir mais dados
        
        # Rate limiting flexível - sempre otimizado
        agora = datetime.now()
        hora_atual = agora.hour
        
        if hora_atual in [0, 1, 2]:  # Madrugada
            delay_base = 0.2  # Mais rápido (sem concorrência)
            logger.info("🌙 Modo madrugada: Rate limiting otimizado")
        else:
            delay_base = 0.3  # Mais flexível em outros horários (reduzido de 0.5 para 0.3)
            logger.info("☀️ Modo diurno: Rate limiting flexível")

        while True:
            # Verificar limite de segurança
            if pagina > max_paginas_seguranca:
                logger.warning(f"Limite de segurança atingido ({max_paginas_seguranca} páginas)")
                break
                
            try:
                result = await self.get_pagina(pagina)

                if not result['success']:
                    error_msg = result.get('error', 'Erro desconhecido')
                    logger.error(f"Erro na página {pagina}: {error_msg}")
                    
                    # Se for erro 404, pode ser fim dos dados
                    if '404' in str(error_msg) or 'not found' in str(error_msg).lower():
                        logger.info("Fim dos dados detectado (erro 404)")
                        break
                    break

                dados = result['data'].get('dados', [])
                
                if not dados:
                    paginas_vazias += 1
                    logger.info(f"Página {pagina} vazia ({paginas_vazias}/{max_paginas_vazias})")
                    
                    if paginas_vazias >= max_paginas_vazias:
                        logger.info(f"Fim da paginação: {paginas_vazias} páginas vazias consecutivas")
                        break
                else:
                    paginas_vazias = 0  # Reset contador de páginas vazias
                    todos_dados.extend(dados)
                    logger.info(f"Página {pagina} - {len(dados)} registros (Total: {len(todos_dados)})")
                    
                    # Se retornou menos que 100 registros, pode ser fim dos dados
                    if len(dados) < 100:
                        logger.info(f"Página com poucos registros ({len(dados)}), pode ser fim dos dados")
                        # Continuar por mais 2 páginas para confirmar
                        if pagina > 10:  # Só aplicar esta lógica após algumas páginas
                            paginas_vazias += 1

                pagina += 1
                await asyncio.sleep(delay_base)  # Rate limiting inteligente

            except Exception as e:
                logger.error(f"Erro na página {pagina}: {str(e)}")
                break

        logger.info(f"Total de registros CV Vendas: {len(todos_dados)} em {pagina-1} páginas")
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
    
    # Padronizar colunas de data (mantém compatível caso algumas não existam)
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

async def obter_dados_cv_vendas() -> pd.DataFrame:
    """Obtém todos os dados de vendas do CV com paginação automática."""
    logger.info("Buscando dados do CV Vendas (todas as páginas)")

    client = CVVendasAPIClient()
    dados = await client.get_all_vendas()

    return processar_dados_cv_vendas(dados)

if __name__ == "__main__":
    # Teste da API do CV Vendas
    async def test_cv_vendas():
        print("=== Testando API CV Vendas ===")
        
        try:
            df = await obter_dados_cv_vendas()
            
            print(f"Registros encontrados: {len(df)}")
            
            if not df.empty:
                print("\nColunas:", list(df.columns))
                print(df.head())
            
        except Exception as e:
            print(f"Erro no teste: {str(e)}")
    
    asyncio.run(test_cv_vendas())
