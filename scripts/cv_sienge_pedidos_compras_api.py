#!/usr/bin/env python3
"""
Integração com API do Sienge - Pedidos de Compras
Endpoint: https://api.sienge.com.br/pratiemp/public/api/v1/purchase-orders/all
Credenciais: Token do Sienge (SIENGE_TOKEN)

Baseado no código fornecido pelo usuário:
- Busca pedidos de compras por período
- Processa dados no formato padrão
- Integra com MotherDuck (tabela sienge_pedidos_compras)
"""

import asyncio
import logging
import time
import os
from datetime import datetime, date
from typing import Dict, List, Any, Optional
import pandas as pd
import requests
import json

from scripts.config import get_api_config

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PedidosComprasSiengeAPIClient:
    """
    Cliente para API de Pedidos de Compras do Sienge
    """
    
    def __init__(self):
        # Usar configuração do Sienge (mesmo token das vendas)
        self.config = get_api_config('sienge_pedidos_compras')
        
        if not self.config:
            raise ValueError("Configuração da API Sienge não encontrada")
        
        # URL específica para pedidos de compras
        self.base_url = "https://api.sienge.com.br/pratiemp/public/api/v1/purchase-orders"
        self.headers = self.config.headers
    
    async def buscar_pedidos_periodo(self, data_inicio: str, data_fim: str, limit: int = 200) -> List[Dict]:
        """
        Busca pedidos de compras para um período específico
        
        Args:
            data_inicio (str): Data de início no formato YYYY-MM-DD
            data_fim (str): Data de fim no formato YYYY-MM-DD
            limit (int): Limite de registros por requisição (máximo 200)
            
        Returns:
            List[Dict]: Lista de pedidos encontrados
        """
        todos_pedidos = []
        offset = 0
        
        while True:
            # Parâmetros da requisição mais básicos
            params = {
                'limit': limit,
                'offset': offset
            }
            
            try:
                logger.info(f"Buscando pedidos - Offset: {offset}, Limit: {limit}")
                response = requests.get(self.base_url, headers=self.headers, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                
                # Verifica se há resultados
                if 'results' not in data or not data['results']:
                    logger.info("Nenhum resultado encontrado ou fim dos dados")
                    break
                
                # Adiciona os resultados à lista
                todos_pedidos.extend(data['results'])
                
                # Verifica se há mais páginas
                metadata = data.get('resultSetMetadata', {})
                total_count = metadata.get('count', 0)
                current_offset = metadata.get('offset', 0)
                current_limit = metadata.get('limit', limit)
                
                logger.info(f"Total de registros: {total_count}, Processados: {len(todos_pedidos)}")
                
                # Se não há mais dados ou atingiu o total
                if len(todos_pedidos) >= total_count or len(data['results']) < limit:
                    break
                
                offset += limit
                
                # Pequena pausa para não sobrecarregar a API
                await asyncio.sleep(0.5)
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Erro na requisição: {e}")
                break
            except json.JSONDecodeError as e:
                logger.error(f"Erro ao decodificar JSON: {e}")
                break
        
        return todos_pedidos
    
    def processar_dados(self, pedidos: List[Dict]) -> pd.DataFrame:
        """
        Processa os dados dos pedidos no mesmo formato do Power BI
        
        Args:
            pedidos (List[Dict]): Lista de pedidos da API
            
        Returns:
            pd.DataFrame: DataFrame processado
        """
        if not pedidos:
            return pd.DataFrame()
        
        # Converte para DataFrame
        df = pd.DataFrame(pedidos)
        
        # Remove colunas desnecessárias (baseado no código fornecido)
        colunas_remover = ['buildings', 'links']
        for col in colunas_remover:
            if col in df.columns:
                df = df.drop(columns=[col])
        
        # Renomeia colunas conforme o código fornecido
        mapeamento_colunas = {
            'documentId': 'Documento',
            'orderNumber': 'Numero_Pedido',
            'supplierId': 'ID_Fornecedor',
            'supplierName': 'Fornecedor',
            'companyName': 'Empresa',
            'responsibleId': 'Responsavel',
            'status': 'Status',
            'statusApproval': 'Aprovacao',
            'isAuthorized': 'Autorizacao',
            'orderDate': 'Data_Pedido',
            'startDate': 'Data_Inicio_Pedido',
            'endDate': 'Data_Final_Pedido',
            'object': 'Objeto',
            'totalLaborValue': 'Total_MaoObra',
            'totalMaterialValue': 'Total_Material',
            'consistent': 'Consistente',
            'internalNotes': 'Notas'
        }
        
        # Aplicar mapeamento apenas para colunas que existem
        for col_original, col_nova in mapeamento_colunas.items():
            if col_original in df.columns:
                df = df.rename(columns={col_original: col_nova})
        
        # Reordena colunas conforme o código fornecido
        ordem_colunas = [
            'Documento', 'Numero_Pedido', 'ID_Fornecedor', 'Fornecedor', 
            'Empresa', 'Responsavel', 'Status', 'Aprovacao', 'Autorizacao',
            'Data_Pedido', 'Data_Inicio_Pedido', 'Data_Final_Pedido',
            'Total_MaoObra', 'Total_Material', 'Consistente', 'Objeto', 'Notas'
        ]
        
        # Mantém apenas as colunas que existem no DataFrame
        colunas_existentes = [col for col in ordem_colunas if col in df.columns]
        df = df[colunas_existentes]
        
        # Converte tipos de dados
        conversoes_tipo = {
            'Documento': 'string',
            'Numero_Pedido': 'string',
            'ID_Fornecedor': 'Int64',
            'Fornecedor': 'string',
            'Empresa': 'string',
            'Responsavel': 'string',
            'Status': 'string',
            'Aprovacao': 'string',
            'Autorizacao': 'boolean',
            'Data_Pedido': 'datetime64[ns]',
            'Data_Inicio_Pedido': 'datetime64[ns]',
            'Data_Final_Pedido': 'datetime64[ns]',
            'Total_MaoObra': 'float64',
            'Total_Material': 'Int64',
            'Consistente': 'boolean',
            'Objeto': 'string',
            'Notas': 'string'
        }
        
        for coluna, tipo in conversoes_tipo.items():
            if coluna in df.columns:
                try:
                    if tipo == 'datetime64[ns]':
                        df[coluna] = pd.to_datetime(df[coluna], errors='coerce')
                    else:
                        df[coluna] = df[coluna].astype(tipo)
                except Exception as e:
                    logger.warning(f"Erro ao converter coluna {coluna} para {tipo}: {e}")
        
        return df
    
    async def buscar_dados_completos(self, data_inicio: str = "2020-01-01") -> pd.DataFrame:
        """
        Busca todos os dados de pedidos de compras desde a data de início até hoje
        
        Args:
            data_inicio (str): Data de início no formato YYYY-MM-DD (padrão: 2020-01-01)
            
        Returns:
            pd.DataFrame: DataFrame com todos os pedidos
        """
        # Data atual
        data_fim = date.today().strftime("%Y-%m-%d")
        
        logger.info(f"Buscando pedidos de compras de {data_inicio} até {data_fim}")
        
        # Busca os dados
        pedidos = await self.buscar_pedidos_periodo(data_inicio, data_fim)
        
        if not pedidos:
            logger.warning("Nenhum pedido encontrado")
            return pd.DataFrame()
        
        logger.info(f"Total de pedidos encontrados: {len(pedidos)}")
        
        # Processa os dados
        df = self.processar_dados(pedidos)
        
        return df

def processar_dados_sienge_pedidos_compras(df: pd.DataFrame) -> pd.DataFrame:
    """
    Processa e padroniza dados dos pedidos de compras do Sienge
    
    Args:
        df: DataFrame com dados dos pedidos
    """
    if df.empty:
        logger.warning("Nenhum dado para processar - Sienge Pedidos Compras")
        return pd.DataFrame()
    
    # Adicionar coluna de fonte
    df['fonte'] = 'sienge_pedidos_compras'
    
    # Adicionar timestamp de processamento
    df['processado_em'] = datetime.now()
    
    logger.info(f"Dados processados - Sienge Pedidos Compras: {len(df)} registros")
    return df

async def obter_dados_sienge_pedidos_compras(data_inicio: str = "2020-01-01") -> pd.DataFrame:
    """Obtém todos os dados de pedidos de compras do Sienge."""
    logger.info("Buscando dados do Sienge Pedidos Compras")

    client = PedidosComprasSiengeAPIClient()
    df = await client.buscar_dados_completos(data_inicio)

    return processar_dados_sienge_pedidos_compras(df)

if __name__ == "__main__":
    # Teste da API de Pedidos de Compras
    async def test_sienge_pedidos_compras():
        print("=== Testando API Sienge Pedidos Compras ===")
        
        try:
            df = await obter_dados_sienge_pedidos_compras("2020-01-01")
            
            print(f"Registros encontrados: {len(df)}")
            
            if not df.empty:
                print("\nColunas:", list(df.columns))
                print(df.head())
            
        except Exception as e:
            print(f"Erro no teste: {str(e)}")
    
    asyncio.run(test_sienge_pedidos_compras())
