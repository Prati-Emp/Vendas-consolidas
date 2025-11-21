#!/usr/bin/env python3
"""
Integração com API do Sienge - Building Cost Estimation Items (Medições)
Endpoint: https://api.sienge.com.br/pratiemp/public/api/bulk-data/v1/building-cost-estimation-items
Credenciais: Token do Sienge (SIENGE_TOKEN) - mesmo das vendas realizadas

Baseado no código fornecido pelo usuário:
- Busca building cost estimation items por data de referência
- Processa dados no formato padrão
- Integra com MotherDuck (tabela operacoes.sienge_medicoes)
"""

import logging
import os
import sys
from datetime import datetime, date, timedelta
from calendar import monthrange
from typing import List, Dict, Any, Optional
import pandas as pd
import requests
import json
import time

# Garante import do projeto quando rodar via Actions
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from scripts.config import get_api_config

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BuildingCostEstimationItemsAPIClient:
    """
    Cliente para API de Building Cost Estimation Items do Sienge
    """
    
    def __init__(self):
        # Usar configuração do Sienge (mesmo token das vendas)
        self.config = get_api_config('sienge_medicoes')
        
        if not self.config:
            raise ValueError("Configuração da API Sienge Medições não encontrada")
        
        self.base_url = self.config.base_url
        self.headers = self.config.headers
    
    def buscar_dados(self, data_date: str, bdi: float = 999.99, labor_burden: float = 999.99, 
                     include_disbursments: bool = False) -> List[Dict]:
        """
        Busca dados de building cost estimation items
        
        Args:
            data_date (str): Data de referência no formato YYYY-MM-DD
            bdi (float): Valor do BDI (padrão: 999.99)
            labor_burden (float): Valor do Labor Burden (padrão: 999.99)
            include_disbursments (bool): Incluir desembolsos (padrão: False)
            
        Returns:
            List[Dict]: Lista de itens encontrados
        """
        # Parâmetros da requisição baseados no código M
        params = {
            'dataDate': data_date,
            'bdi': bdi,
            'laborBurden': labor_burden,
            'includeDisbursments': str(include_disbursments).lower()
        }
        
        try:
            logger.info(f"Buscando building cost estimation items para data: {data_date}")
            logger.info(f"Parâmetros: BDI={bdi}, Labor Burden={labor_burden}, Include Disbursments={include_disbursments}")
            
            response = requests.get(self.base_url, headers=self.headers, params=params, timeout=60)
            response.raise_for_status()
            
            data = response.json()
            
            # A estrutura da resposta tem um campo 'data' que é uma lista
            if 'data' in data and isinstance(data['data'], list):
                logger.info(f"Total de itens encontrados: {len(data['data'])}")
                return data['data']
            else:
                logger.warning("Estrutura de resposta inesperada")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Status Code: {e.response.status_code}")
                logger.error(f"Response: {e.response.text}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar JSON: {e}")
            return []
    
    def processar_dados(self, dados: List[Dict], aplicar_filtro_wbs: bool = True) -> pd.DataFrame:
        """
        Processa os dados no mesmo formato do Power BI
        
        Args:
            dados (List[Dict]): Lista de itens da API
            aplicar_filtro_wbs (bool): Se deve aplicar o filtro de WBS de serviço (padrão: True)
            
        Returns:
            pd.DataFrame: DataFrame processado
        """
        if not dados:
            return pd.DataFrame()
        
        # Converte para DataFrame
        df = pd.DataFrame(dados)
        
        # Renomeia colunas conforme o código M
        mapeamento_colunas = {
            'buildingId': 'ID_Empreendimento',
            'buildingName': 'Empreendimento',
            'versionNumber': 'Versao',
            'buildingUnitName': 'Unidade_Construtiva',
            'wbsCode': 'wbsCode',  # Mantém para filtro
            'description': 'Descricao',
            'unitOfMeasure': 'Und_Medida',
            'quantity': 'Quantidade',
            'unitPrice': 'Preco_Unitario',
            'totalPrice': 'Preco_total',
            'baseTotalPrice': 'Base_Preco_Total',
            'pricesByCategory': 'pricesByCategory',  # Mantém para referência
            'scheduledPercentComplete': 'Percentual_Previsto',
            'percentComplete': 'Percentual_Realizado',
            'measuredQuantity': 'Quantidade_Medida',
            'tasks': 'tasks'  # Mantém para referência
        }
        
        # Renomeia apenas as colunas que existem
        colunas_renomear = {k: v for k, v in mapeamento_colunas.items() if k in df.columns}
        df = df.rename(columns=colunas_renomear)
        
        # Reordena colunas conforme o código M
        ordem_colunas = [
            'ID_Empreendimento', 'Empreendimento', 'Versao', 'Unidade_Construtiva', 
            'wbsCode', 'Descricao', 'Und_Medida', 'Quantidade', 'Preco_Unitario', 
            'Preco_total', 'Base_Preco_Total', 'Percentual_Previsto', 
            'Percentual_Realizado', 'Quantidade_Medida', 'pricesByCategory', 'tasks'
        ]
        
        # Mantém apenas as colunas que existem no DataFrame
        colunas_existentes = [col for col in ordem_colunas if col in df.columns]
        colunas_restantes = [col for col in df.columns if col not in colunas_existentes]
        df = df[colunas_existentes + colunas_restantes]
        
        # Converte tipos de dados
        conversoes_tipo = {
            'ID_Empreendimento': 'Int64',
            'Empreendimento': 'string',
            'Versao': 'Int64',
            'Unidade_Construtiva': 'string',
            'Descricao': 'string',
            'Und_Medida': 'string',
            'Quantidade': 'float64',
            'Preco_Unitario': 'float64',
            'Preco_total': 'float64',
            'Base_Preco_Total': 'float64',
            'Percentual_Previsto': 'float64',
            'Percentual_Realizado': 'float64',
            'Quantidade_Medida': 'float64'
        }
        
        for coluna, tipo in conversoes_tipo.items():
            if coluna in df.columns:
                try:
                    df[coluna] = df[coluna].astype(tipo)
                except Exception as e:
                    logger.warning(f"Erro ao converter coluna {coluna} para {tipo}: {e}")
        
        # Divide percentuais por 100 (conforme código M)
        if 'Percentual_Previsto' in df.columns:
            df['Percentual_Previsto'] = df['Percentual_Previsto'] / 100
        
        if 'Percentual_Realizado' in df.columns:
            df['Percentual_Realizado'] = df['Percentual_Realizado'] / 100
        
        # Filtra WBS de serviço (wbsCode > 999999999) conforme código M
        if aplicar_filtro_wbs and 'wbsCode' in df.columns:
            logger.info(f"Total de registros antes do filtro: {len(df)}")
            
            # Tenta filtrar usando conversão numérica
            wbs_numerico = pd.to_numeric(df['wbsCode'], errors='coerce')
            df_filtrado = df[wbs_numerico > 999999999]
            
            # Se o filtro numérico não retornou nada, tenta como string
            if len(df_filtrado) == 0:
                logger.info("Filtro numérico não retornou resultados, tentando como string...")
                # Tenta filtrar strings que representam números grandes
                wbs_limpo = df['wbsCode'].astype(str).str.replace('.', '').str.replace('-', '')
                wbs_limpo_numerico = pd.to_numeric(wbs_limpo, errors='coerce')
                df_filtrado = df[wbs_limpo_numerico > 999999999]
            
            df = df_filtrado
            logger.info(f"Registros após filtro de WBS de serviço: {len(df)}")
        elif 'wbsCode' in df.columns:
            logger.info(f"Filtro de WBS desabilitado. Total de registros: {len(df)}")
        
        return df
    
    def gerar_datas_mensais(self, ano: int, mes_inicio: int = 1, mes_fim: int = 12) -> List[str]:
        """
        Gera lista de datas do último dia de cada mês
        
        Args:
            ano (int): Ano de referência
            mes_inicio (int): Mês inicial (padrão: 1)
            mes_fim (int): Mês final (padrão: 12)
            
        Returns:
            List[str]: Lista de datas no formato YYYY-MM-DD
        """
        datas = []
        for mes in range(mes_inicio, mes_fim + 1):
            ultimo_dia = monthrange(ano, mes)[1]
            data = f"{ano}-{mes:02d}-{ultimo_dia:02d}"
            datas.append(data)
        return datas
    
    def obter_mes_anterior(self, data_referencia: Optional[date] = None) -> str:
        """
        Obtém o último dia do mês anterior à data de referência
        
        Args:
            data_referencia (date, optional): Data de referência. Se None, usa data atual
            
        Returns:
            str: Data no formato YYYY-MM-DD (último dia do mês anterior)
        """
        if data_referencia is None:
            data_referencia = date.today()
        
        # Primeiro dia do mês atual
        primeiro_dia_mes_atual = date(data_referencia.year, data_referencia.month, 1)
        
        # Último dia do mês anterior
        ultimo_dia_mes_anterior = primeiro_dia_mes_atual - timedelta(days=1)
        
        return ultimo_dia_mes_anterior.strftime('%Y-%m-%d')
    
    def buscar_multiplos_meses(self, datas: List[str], bdi: float = 999.99, 
                               labor_burden: float = 999.99, 
                               include_disbursments: bool = False,
                               aplicar_filtro_wbs: bool = True) -> pd.DataFrame:
        """
        Busca dados de múltiplos meses e consolida em um único DataFrame
        
        Args:
            datas (List[str]): Lista de datas no formato YYYY-MM-DD (último dia de cada mês)
            bdi (float): Valor do BDI (padrão: 999.99)
            labor_burden (float): Valor do Labor Burden (padrão: 999.99)
            include_disbursments (bool): Incluir desembolsos (padrão: False)
            aplicar_filtro_wbs (bool): Se deve aplicar o filtro de WBS de serviço (padrão: True)
            
        Returns:
            pd.DataFrame: DataFrame consolidado com coluna Data_Snapshot
        """
        resultados = []
        total_requisicoes = len(datas)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"BUSCANDO DADOS DE {total_requisicoes} MESES")
        logger.info(f"{'='*60}\n")
        
        for i, data_snapshot in enumerate(datas, 1):
            logger.info(f"\n[{i}/{total_requisicoes}] Processando mês: {data_snapshot}")
            logger.info("-" * 60)
            
            # Busca os dados para este mês
            df = self.buscar_dados_completos(
                data_date=data_snapshot,
                bdi=bdi,
                labor_burden=labor_burden,
                include_disbursments=include_disbursments,
                aplicar_filtro_wbs=aplicar_filtro_wbs
            )
            
            if not df.empty:
                # Adiciona coluna Data_Snapshot
                df['Data_Snapshot'] = pd.to_datetime(data_snapshot)
                resultados.append(df)
                logger.info(f"✅ Mês {data_snapshot}: {len(df)} registros processados")
            else:
                logger.warning(f"⚠️  Mês {data_snapshot}: Nenhum dado encontrado")
            
            # Pausa entre requisições para não sobrecarregar a API
            if i < total_requisicoes:
                time.sleep(1)
        
        if not resultados:
            logger.warning("\n❌ Nenhum dado foi retornado de nenhum mês")
            return pd.DataFrame()
        
        # Consolida todos os DataFrames
        logger.info(f"\n{'='*60}")
        logger.info("CONSOLIDANDO DADOS...")
        logger.info(f"{'='*60}")
        
        df_final = pd.concat(resultados, ignore_index=True)
        
        logger.info(f"\n✅ Consolidação concluída!")
        logger.info(f"Total de registros consolidados: {len(df_final)}")
        logger.info(f"Meses processados: {df_final['Data_Snapshot'].nunique()}")
        logger.info(f"Datas únicas: {sorted(df_final['Data_Snapshot'].dt.strftime('%Y-%m-%d').unique())}")
        
        return df_final
    
    def buscar_dados_completos(self, data_date: str, bdi: float = 999.99, 
                               labor_burden: float = 999.99, 
                               include_disbursments: bool = False,
                               aplicar_filtro_wbs: bool = True) -> pd.DataFrame:
        """
        Busca e processa todos os dados de building cost estimation items
        
        Args:
            data_date (str): Data de referência no formato YYYY-MM-DD
            bdi (float): Valor do BDI (padrão: 999.99)
            labor_burden (float): Valor do Labor Burden (padrão: 999.99)
            include_disbursments (bool): Incluir desembolsos (padrão: False)
            aplicar_filtro_wbs (bool): Se deve aplicar o filtro de WBS de serviço (padrão: True)
            
        Returns:
            pd.DataFrame: DataFrame com todos os dados processados
        """
        logger.info(f"Buscando building cost estimation items para data: {data_date}")
        
        # Busca os dados
        dados = self.buscar_dados(data_date, bdi, labor_burden, include_disbursments)
        
        if not dados:
            logger.warning("Nenhum dado encontrado")
            return pd.DataFrame()
        
        logger.info(f"Total de itens encontrados: {len(dados)}")
        
        # Processa os dados
        df = self.processar_dados(dados, aplicar_filtro_wbs=aplicar_filtro_wbs)
        
        return df


def processar_dados_medicoes(dados: List[Dict], data_snapshot: str) -> pd.DataFrame:
    """
    Processa dados de medições e adiciona colunas padrão
    
    Args:
        dados (List[Dict]): Lista de itens da API
        data_snapshot (str): Data do snapshot no formato YYYY-MM-DD
        
    Returns:
        pd.DataFrame: DataFrame processado com colunas padrão
    """
    if not dados:
        return pd.DataFrame()
    
    # Criar cliente
    client = BuildingCostEstimationItemsAPIClient()
    
    # Processar dados
    df = client.processar_dados(dados, aplicar_filtro_wbs=True)
    
    if df.empty:
        return df
    
    # Adiciona coluna Data_Snapshot
    df['Data_Snapshot'] = pd.to_datetime(data_snapshot)
    
    # Adiciona colunas padrão do sistema
    df['fonte'] = 'sienge_medicoes'
    df['processado_em'] = datetime.now()
    
    return df


def obter_dados_sienge_medicoes(modo_inicial: bool = False, 
                                 ano: int = 2025, 
                                 mes_inicio: int = 1, 
                                 mes_fim: int = None) -> pd.DataFrame:
    """
    Função principal para obter dados de building cost estimation items do Sienge
    
    Args:
        modo_inicial (bool): Se True, busca todos os meses de mes_inicio a mes_fim (primeira execução)
                            Se False, busca apenas o mês anterior (execuções mensais)
        ano (int): Ano de referência para modo inicial (padrão: 2025)
        mes_inicio (int): Mês inicial para modo inicial (padrão: 1)
        mes_fim (int, optional): Mês final para modo inicial. Se None, usa o mês anterior
        
    Returns:
        pd.DataFrame: DataFrame com dados processados
    """
    try:
        # Criar cliente
        client = BuildingCostEstimationItemsAPIClient()
        
        # Parâmetros padrão
        bdi = 999.99
        labor_burden = 999.99
        include_disbursments = False
        aplicar_filtro_wbs = True
        
        if modo_inicial:
            # Modo inicial: busca múltiplos meses
            logger.info("🔄 Modo inicial ativado: buscando múltiplos meses")
            
            # Se mes_fim não foi especificado, usa o mês anterior
            if mes_fim is None:
                mes_anterior_str = client.obter_mes_anterior()
                mes_anterior = datetime.strptime(mes_anterior_str, '%Y-%m-%d')
                if mes_anterior.year == ano:
                    mes_fim = mes_anterior.month
                else:
                    mes_fim = 12
            
            # Gera lista de datas mensais
            datas = client.gerar_datas_mensais(ano, mes_inicio, mes_fim)
            logger.info(f"📅 Meses a processar: {len(datas)}")
            logger.info(f"   Datas: {', '.join(datas)}")
            
            # Busca múltiplos meses
            df = client.buscar_multiplos_meses(
                datas=datas,
                bdi=bdi,
                labor_burden=labor_burden,
                include_disbursments=include_disbursments,
                aplicar_filtro_wbs=aplicar_filtro_wbs
            )
        else:
            # Modo normal: busca apenas o mês anterior
            data_snapshot = client.obter_mes_anterior()
            logger.info(f"Buscando dados para o mês anterior: {data_snapshot}")
            
            # Buscar dados
            df = client.buscar_dados_completos(
                data_date=data_snapshot,
                bdi=bdi,
                labor_burden=labor_burden,
                include_disbursments=include_disbursments,
                aplicar_filtro_wbs=aplicar_filtro_wbs
            )
            
            if not df.empty:
                # Adiciona coluna Data_Snapshot
                df['Data_Snapshot'] = pd.to_datetime(data_snapshot)
        
        if df.empty:
            logger.warning("Nenhum dado encontrado")
            return pd.DataFrame()
        
        # Adiciona colunas padrão do sistema
        df['fonte'] = 'sienge_medicoes'
        df['processado_em'] = datetime.now()
        
        logger.info(f"✅ Dados processados: {len(df)} registros")
        return df
        
    except Exception as e:
        logger.error(f"Erro ao obter dados de medições: {str(e)}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


if __name__ == "__main__":
    # Teste local
    print("Testando API de Medições do Sienge...")
    df = obter_dados_sienge_medicoes()
    print(f"Registros obtidos: {len(df)}")
    if not df.empty:
        print(f"Colunas: {list(df.columns)}")
        print(df.head())

