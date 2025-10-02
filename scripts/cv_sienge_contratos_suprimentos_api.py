#!/usr/bin/env python3
"""
Integração com API do Sienge - Contratos de Suprimentos
Endpoint: https://api.sienge.com.br/pratiemp/public/api/v1/supply-contracts/all
Credenciais: Token do Sienge (SIENGE_TOKEN)

Baseado no código fornecido pelo usuário:
- Busca contratos de suprimentos por período
- Processa dados no formato padrão
- Integra com MotherDuck (tabela sienge_contratos_suprimentos)
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

class ContratosSuprimentosSiengeAPIClient:
    """
    Cliente para API de Contratos de Suprimentos do Sienge
    """
    
    def __init__(self):
        # Usar configuração do Sienge (mesmo token das vendas)
        self.config = get_api_config('sienge_contratos_suprimentos')
        
        if not self.config:
            raise ValueError("Configuração da API Sienge não encontrada")
        
        # URL específica para contratos de suprimentos
        self.base_url = "https://api.sienge.com.br/pratiemp/public/api/v1/supply-contracts/all"
        self.headers = self.config.headers
    
    async def buscar_contratos_periodo(self, data_inicio: str, data_fim: str, limit: int = 200) -> List[Dict]:
        """
        Busca contratos de suprimentos para um período específico
        
        Args:
            data_inicio (str): Data de início no formato YYYY-MM-DD
            data_fim (str): Data de fim no formato YYYY-MM-DD
            limit (int): Limite de registros por requisição (máximo 200)
            
        Returns:
            List[Dict]: Lista de contratos encontrados
        """
        todos_contratos = []
        offset = 0
        
        while True:
            # Parâmetros da requisição baseados no código M
            params = {
                'contractStartDate': data_inicio,
                'contractEndDate': data_fim,
                'limit': limit,
                'offset': offset,
                'statusApproval': 'A',  # Aprovados
                'authorization': 'T'    # Autorizados
            }
            
            try:
                logger.info(f"Buscando contratos - Offset: {offset}, Limit: {limit}")
                response = requests.get(self.base_url, headers=self.headers, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                
                # Verifica se há resultados
                if 'results' not in data or not data['results']:
                    logger.info("Nenhum resultado encontrado ou fim dos dados")
                    break
                
                # Adiciona os resultados à lista
                todos_contratos.extend(data['results'])
                
                # Verifica se há mais páginas
                metadata = data.get('resultSetMetadata', {})
                total_count = metadata.get('count', 0)
                current_offset = metadata.get('offset', 0)
                current_limit = metadata.get('limit', limit)
                
                logger.info(f"Total de registros: {total_count}, Processados: {len(todos_contratos)}")
                
                # Se não há mais dados ou atingiu o total
                if len(todos_contratos) >= total_count or len(data['results']) < limit:
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
        
        return todos_contratos
    
    def processar_dados(self, contratos: List[Dict]) -> pd.DataFrame:
        """
        Processa os dados dos contratos no mesmo formato do Power BI
        
        Args:
            contratos (List[Dict]): Lista de contratos da API
            
        Returns:
            pd.DataFrame: DataFrame processado
        """
        if not contratos:
            return pd.DataFrame()
        
        # Converte para DataFrame
        df = pd.DataFrame(contratos)
        
        # Remove colunas desnecessárias (baseado no código M)
        colunas_remover = ['buildings', 'links']
        for col in colunas_remover:
            if col in df.columns:
                df = df.drop(columns=[col])
        
        # Renomeia colunas conforme o código M
        mapeamento_colunas = {
            'documentId': 'Documento',
            'contractNumber': 'Numero_Contrato',
            'supplierId': 'ID_Fornecedor',
            'supplierName': 'Fornecedor',
            'companyName': 'Empresa',
            'responsibleId': 'Responsavel',
            'status': 'Status',
            'statusApproval': 'Aprovacao',
            'isAuthorized': 'Autorizacao',
            'contractDate': 'Data_Contrato',
            'startDate': 'Data_Inicio_Contrato',
            'endDate': 'Data_Final_Contrato',
            'object': 'Objeto',
            'totalLaborValue': 'Total_MaoObra',
            'totalMaterialValue': 'Total_Material',
            'consistent': 'Consistente',
            'internalNotes': 'Notas'
        }
        
        df = df.rename(columns=mapeamento_colunas)
        
        # Reordena colunas conforme o código M
        ordem_colunas = [
            'Documento', 'Numero_Contrato', 'ID_Fornecedor', 'Fornecedor', 
            'Empresa', 'Responsavel', 'Status', 'Aprovacao', 'Autorizacao',
            'Data_Contrato', 'Data_Inicio_Contrato', 'Data_Final_Contrato',
            'Total_MaoObra', 'Total_Material', 'Consistente', 'Objeto', 'Notas'
        ]
        
        # Mantém apenas as colunas que existem no DataFrame
        colunas_existentes = [col for col in ordem_colunas if col in df.columns]
        df = df[colunas_existentes]
        
        # Converte tipos de dados
        conversoes_tipo = {
            'Documento': 'string',
            'Numero_Contrato': 'string',
            'ID_Fornecedor': 'Int64',
            'Fornecedor': 'string',
            'Empresa': 'string',
            'Responsavel': 'string',
            'Status': 'string',
            'Aprovacao': 'string',
            'Autorizacao': 'boolean',
            'Data_Contrato': 'datetime64[ns]',
            'Data_Inicio_Contrato': 'datetime64[ns]',
            'Data_Final_Contrato': 'datetime64[ns]',
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
        Busca todos os dados de contratos de suprimentos desde a data de início até hoje
        
        Args:
            data_inicio (str): Data de início no formato YYYY-MM-DD (padrão: 2020-01-01)
            
        Returns:
            pd.DataFrame: DataFrame com todos os contratos
        """
        # Data atual
        data_fim = date.today().strftime("%Y-%m-%d")
        
        logger.info(f"Buscando contratos de suprimentos de {data_inicio} até {data_fim}")
        
        # Busca os dados
        contratos = await self.buscar_contratos_periodo(data_inicio, data_fim)
        
        if not contratos:
            logger.warning("Nenhum contrato encontrado")
            return pd.DataFrame()
        
        logger.info(f"Total de contratos encontrados: {len(contratos)}")
        
        # Processa os dados
        df = self.processar_dados(contratos)
        
        return df

def processar_dados_sienge_contratos_suprimentos(df: pd.DataFrame) -> pd.DataFrame:
    """
    Processa e padroniza dados dos contratos de suprimentos do Sienge
    
    Args:
        df: DataFrame com dados dos contratos
    """
    if df.empty:
        logger.warning("Nenhum dado para processar - Sienge Contratos Suprimentos")
        return pd.DataFrame()
    
    # Adicionar coluna de fonte
    df['fonte'] = 'sienge_contratos_suprimentos'
    
    # Adicionar timestamp de processamento
    df['processado_em'] = datetime.now()
    
    logger.info(f"Dados processados - Sienge Contratos Suprimentos: {len(df)} registros")
    return df

async def obter_dados_sienge_contratos_suprimentos(data_inicio: str = "2020-01-01") -> pd.DataFrame:
    """Obtém todos os dados de contratos de suprimentos do Sienge."""
    logger.info("Buscando dados do Sienge Contratos Suprimentos")

    client = ContratosSuprimentosSiengeAPIClient()
    df = await client.buscar_dados_completos(data_inicio)

    return processar_dados_sienge_contratos_suprimentos(df)

if __name__ == "__main__":
    # Teste da API de Contratos de Suprimentos
    async def test_sienge_contratos_suprimentos():
        print("=== Testando API Sienge Contratos Suprimentos ===")
        
        try:
            df = await obter_dados_sienge_contratos_suprimentos("2020-01-01")
            
            print(f"Registros encontrados: {len(df)}")
            
            if not df.empty:
                print("\nColunas:", list(df.columns))
                print(df.head())
            
        except Exception as e:
            print(f"Erro no teste: {str(e)}")
    
    asyncio.run(test_sienge_contratos_suprimentos())
