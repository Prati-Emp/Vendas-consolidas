#!/usr/bin/env python3
"""
Integração com API do Sienge - Contas Pagas e a Pagar (Outcome)
Endpoint: https://api.sienge.com.br/pratiemp/public/api/bulk-data/v1/outcome
Credenciais: Token do Sienge (SIENGE_TOKEN) - mesmo das vendas realizadas

Baseado no código fornecido pelo usuário:
- Busca contas pagas por período (data_inicio e data_fim)
- Processa dados no formato padrão
- Integra com MotherDuck (tabela administracao.sienge_contas_pagas_e_a_pagar)
"""

import logging
import os
import sys
from datetime import datetime, date, timedelta
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

class ContasPagasSiengeAPIClient:
    """
    Cliente para API de Contas Pagas e a Pagar (Outcome) do Sienge
    """
    
    def __init__(self):
        # Usar configuração do Sienge (mesmo token das vendas)
        self.config = get_api_config('sienge_contas_pagas')
        
        if not self.config:
            raise ValueError("Configuração da API Sienge Contas Pagas não encontrada")
        
        self.base_url = self.config.base_url
        self.headers = self.config.headers
    
    def buscar_contas_pagas(self, 
                           data_inicio: str, 
                           data_fim: str, 
                           selection_type: str = 'D',
                           correction_indexer_id: int = 0,
                           correction_date: str = None,
                           with_authorizations: bool = True,
                           with_bank_movements: bool = False) -> Dict:
        """
        Busca dados de Contas Pagas da API Bulk-Data
        
        Args:
            data_inicio (str): Data inicial no formato YYYY-MM-DD
            data_fim (str): Data final no formato YYYY-MM-DD
            selection_type (str): Tipo de seleção (padrão: 'D')
            correction_indexer_id (int): ID do indexador de correção (padrão: 0)
            correction_date (str, optional): Data de correção no formato YYYY-MM-DD
            with_authorizations (bool): Incluir autorizações (padrão: True)
            with_bank_movements (bool): Incluir movimentações bancárias (padrão: False)
            
        Returns:
            Dict: Dados retornados pela API
        """
        # Parâmetros da requisição
        params = {
            'startDate': data_inicio,
            'endDate': data_fim,
            'selectionType': selection_type,
            'correctionIndexerId': correction_indexer_id,
            'withAuthorizations': str(with_authorizations).lower(),
            'withBankMovements': str(with_bank_movements).lower()
        }
        
        # Adiciona data de correção se fornecida
        if correction_date:
            params['correctionDate'] = correction_date
        
        try:
            logger.info(f"Buscando contas pagas: {data_inicio} até {data_fim}")
            logger.info(f"Parâmetros: selectionType={selection_type}, correctionIndexerId={correction_indexer_id}")
            
            response = requests.get(self.base_url, headers=self.headers, params=params, timeout=120)
            response.raise_for_status()
            
            data = response.json()
            
            # A estrutura da resposta pode variar
            if isinstance(data, list):
                logger.info(f"Total de registros encontrados: {len(data)}")
                return {'results': data}
            elif isinstance(data, dict):
                if 'results' in data:
                    logger.info(f"Total de registros encontrados: {len(data['results'])}")
                elif 'data' in data:
                    logger.info(f"Total de registros encontrados: {len(data['data'])}")
                return data
            else:
                logger.warning("Estrutura de resposta inesperada")
                return {'results': []}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Status Code: {e.response.status_code}")
                logger.error(f"Response: {e.response.text}")
            return {'results': []}
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar JSON: {e}")
            return {'results': []}
    
    def processar_dados(self, dados: Any) -> pd.DataFrame:
        """
        Processa os dados retornados pela API para o formato do relatório
        
        Args:
            dados (Any): Dados retornados pela API
            
        Returns:
            pd.DataFrame: DataFrame processado
        """
        if not dados:
            logger.warning("Nenhum dado recebido para processar")
            return pd.DataFrame()
        
        # Normaliza dados para lista
        if isinstance(dados, dict):
            if 'results' in dados:
                dados = dados['results']
            elif 'data' in dados:
                dados = dados['data']
            else:
                dados = [dados]
        
        if not isinstance(dados, list):
            logger.warning(f"Formato de dados não esperado: {type(dados)}")
            return pd.DataFrame()
        
        if len(dados) == 0:
            logger.warning("Nenhum registro encontrado")
            return pd.DataFrame()
        
        logger.info(f"Processando {len(dados)} registros...")
        
        # Converte para DataFrame inicial
        df = pd.DataFrame(dados)
        
        # Processa para formato relatório
        df_relatorio = self.processar_para_relatorio(df)
        
        return df_relatorio
    
    def processar_para_relatorio(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Processa o DataFrame bruto para o formato do relatório
        
        Args:
            df (pd.DataFrame): DataFrame bruto da API
            
        Returns:
            pd.DataFrame: DataFrame processado
        """
        logger.info("Processando dados para formato relatório...")
        
        if df.empty:
            return df

        # 1. Extração de dados de pagamento (da lista 'payments')
        df['data_pagamento_temp'] = None
        df['valor_pago_temp'] = 0.0
        df['valor_liquido_temp'] = 0.0
        
        if 'payments' in df.columns:
            def extrair_pagamento(payments_list):
                if not isinstance(payments_list, list) or not payments_list:
                    return None, 0.0, 0.0
                
                try:
                    pagamentos_validos = [p for p in payments_list if isinstance(p, dict)]
                    if not pagamentos_validos:
                        return None, 0.0, 0.0
                    
                    # Ordena por data e pega o último
                    ultimo_pgto = sorted(pagamentos_validos, 
                                        key=lambda x: x.get('paymentDate', ''), 
                                        reverse=True)[0]
                    
                    data_pgto = ultimo_pgto.get('paymentDate')
                    
                    # Soma valores de todos os pagamentos
                    total_pago = sum(float(p.get('grossAmount', 0) or 0) for p in pagamentos_validos)
                    total_liquido = sum(float(p.get('netAmount', 0) or 0) for p in pagamentos_validos)
                    
                    return data_pgto, total_pago, total_liquido
                except Exception as e:
                    logger.warning(f"Erro ao extrair pagamento: {e}")
                    return None, 0.0, 0.0

            dados_pgto = df['payments'].apply(extrair_pagamento)
            df['data_pagamento_temp'] = [d[0] if d else None for d in dados_pgto]
            df['valor_pago_temp'] = [d[1] if d else 0.0 for d in dados_pgto]
            df['valor_liquido_temp'] = [d[2] if d else 0.0 for d in dados_pgto]

        # 2. Definição do Status
        def definir_status(row):
            saldo = float(row.get('balanceAmount', 0) or 0)
            original = float(row.get('originalAmount', 0) or 0)
            
            if saldo <= 0.01:
                return 'PAGA'
            elif saldo < original:
                return 'PARCIAL'
            else:
                return 'ABERTA'
                
        df['status_parcela_calc'] = df.apply(definir_status, axis=1)

        # 3. Cálculo de Dias de Atraso
        def calcular_atraso(row):
            try:
                vencimento = pd.to_datetime(row.get('dueDate'), errors='coerce')
                if pd.isna(vencimento):
                    return 0
                
                status = row.get('status_parcela_calc')
                
                if status == 'PAGA':
                    pagamento = pd.to_datetime(row.get('data_pagamento_temp'), errors='coerce')
                    if pd.isna(pagamento):
                        return 0
                    dias = (pagamento - vencimento).days
                else:
                    hoje = pd.to_datetime(date.today())
                    dias = (hoje - vencimento).days
                
                return max(0, dias)
            except:
                return 0
                
        df['dias_atraso_calc'] = df.apply(calcular_atraso, axis=1)

        # 4. Mapeamento de Colunas (API -> Relatório)
        mapeamento = {
            'companyId': 'Cod_empresa',
            'companyName': 'Empresa',
            'creditorId': 'Cod_credor',
            'creditorName': 'Credor',
            'billId': 'Titulo',
            'installmentId': 'Parcela',
            'documentIdentificationName': 'Documento',
            'documentNumber': 'Numero_documento',
            'forecastDocument': 'Previsao_Financeira',
            'consistencyStatus': 'Consistencia',
            'originalAmount': 'Valor_bruto',
            'discountAmount': 'Desconto',
            'taxAmount': 'Valor_Imposto_Retido',
            'indexerName': 'Indexador',
            'dueDate': 'Data_vencimento',
            'issueDate': 'Data_emissao',
            'balanceAmount': 'Saldo_em_aberto',
            'correctedBalanceAmount': 'Valor_Saldo_Corrigido',
            'authorizationStatus': 'Autorizacao',
            'registeredBy': 'Usuario_cadastrou',
            'registeredDate': 'Data_cadastro',
            'data_pagamento_temp': 'Data_pagamento',
            'valor_liquido_temp': 'Valor_liquido',
            'valor_pago_temp': 'Valor_baixa',
            'status_parcela_calc': 'Status_parcela',
            'dias_atraso_calc': 'Dias_atraso'
        }
        
        # Renomeia as colunas existentes
        df_renomeado = df.rename(columns=mapeamento)
        
        # Tipagem
        conversoes = {
            'Cod_empresa': 'Int64',
            'Cod_credor': 'Int64',
            'Titulo': 'Int64',
            'Parcela': 'Int64',
            'Desconto': 'float64',
            'Valor_Imposto_Retido': 'float64'
        }
        
        for col, dtype in conversoes.items():
            if col in df_renomeado.columns:
                try:
                    df_renomeado[col] = pd.to_numeric(df_renomeado[col], errors='coerce').astype(dtype)
                except:
                    pass

        # Seleciona colunas finais na ordem desejada
        colunas_relatorio = [
            'Titulo', 'Parcela', 'Cod_empresa', 'Empresa', 'Cod_credor', 'Credor', 
            'Documento', 'Numero_documento', 'Previsao_Financeira', 'Consistencia',
            'Data_vencimento', 'Valor_bruto', 'Desconto', 'Valor_Imposto_Retido', 
            'Valor_liquido', 'Valor_baixa', 'Saldo_em_aberto', 'Valor_Saldo_Corrigido',
            'Data_pagamento', 'Data_emissao', 'Indexador', 
            'Status_parcela', 'Dias_atraso', 'Usuario_cadastrou', 'Data_cadastro', 'Autorizacao'
        ]
        
        # Filtra e reordena apenas colunas existentes
        cols_existentes = [c for c in colunas_relatorio if c in df_renomeado.columns]
        df_final = df_renomeado[cols_existentes].copy()
        
        return df_final
    
    def buscar_dados_completos(self, 
                             data_inicio: str = None, 
                             data_fim: str = None, 
                             selection_type: str = 'D',
                             correction_indexer_id: int = 0,
                             correction_date: str = None,
                             with_authorizations: bool = True,
                             with_bank_movements: bool = False) -> pd.DataFrame:
        """
        Busca todos os dados de contas pagas
        
        Args:
            data_inicio (str, optional): Data inicial. Se None, usa 2025-01-01
            data_fim (str, optional): Data final. Se None, usa data atual
            selection_type (str): Tipo de seleção (padrão: 'D')
            correction_indexer_id (int): ID do indexador (padrão: 0)
            correction_date (str, optional): Data de correção. Se None, usa data atual
            with_authorizations (bool): Incluir autorizações (padrão: True)
            with_bank_movements (bool): Incluir movimentações bancárias (padrão: False)
            
        Returns:
            pd.DataFrame: DataFrame com todos os dados processados
        """
        # Define datas padrão
        hoje = date.today().strftime("%Y-%m-%d")
        
        if data_inicio is None:
            data_inicio = "2025-01-01"
            logger.info(f"Data inicial definida automaticamente para: {data_inicio}")
        
        if data_fim is None:
            data_fim = hoje
            logger.info(f"Data final definida automaticamente para: {data_fim}")
        
        if correction_date is None:
            correction_date = hoje
            logger.info(f"Data de correção definida automaticamente para: {correction_date}")
        
        # Busca os dados da API
        dados = self.buscar_contas_pagas(
            data_inicio=data_inicio,
            data_fim=data_fim,
            selection_type=selection_type,
            correction_indexer_id=correction_indexer_id,
            correction_date=correction_date,
            with_authorizations=with_authorizations,
            with_bank_movements=with_bank_movements
        )
        
        if not dados:
            logger.warning("Nenhum dado retornado pela API")
            return pd.DataFrame()
        
        # Processa e limpa os dados
        df = self.processar_dados(dados)
        
        return df


def processar_dados_contas_pagas(dados: List[Dict], data_snapshot: str) -> pd.DataFrame:
    """
    Processa dados de contas pagas e adiciona colunas padrão
    
    Args:
        dados (List[Dict]): Lista de itens da API
        data_snapshot (str): Data do snapshot no formato YYYY-MM-DD
        
    Returns:
        pd.DataFrame: DataFrame processado com colunas padrão
    """
    if not dados:
        return pd.DataFrame()
    
    # Criar cliente
    client = ContasPagasSiengeAPIClient()
    
    # Processar dados
    df = client.processar_dados(dados)
    
    if df.empty:
        return df
    
    # Adiciona coluna Data_Snapshot
    df['Data_Snapshot'] = pd.to_datetime(data_snapshot)
    
    # Adiciona colunas padrão do sistema
    df['fonte'] = 'sienge_contas_pagas'
    df['processado_em'] = datetime.now()
    
    return df


def obter_dados_sienge_contas_pagas(data_inicio: str = None, 
                                     data_fim: str = None,
                                     dias_retrocesso: int = None) -> pd.DataFrame:
    """
    Função principal para obter dados de contas pagas do Sienge
    
    Args:
        data_inicio (str, optional): Data inicial no formato YYYY-MM-DD. 
                                    Se None, usa dias_retrocesso dias atrás
        data_fim (str, optional): Data final no formato YYYY-MM-DD. 
                                 Se None, usa data atual
        dias_retrocesso (int, optional): Número de dias para buscar retroativamente. 
                                        Se None e data_inicio não fornecida, usa 30 dias
        
    Returns:
        pd.DataFrame: DataFrame com dados processados
    """
    try:
        # Criar cliente
        client = ContasPagasSiengeAPIClient()
        
        # Define datas se não fornecidas
        hoje = date.today()
        
        if data_fim is None:
            data_fim = hoje.strftime("%Y-%m-%d")
        
        if data_inicio is None:
            if dias_retrocesso is None:
                dias_retrocesso = 30
            data_inicio = (hoje - timedelta(days=dias_retrocesso)).strftime("%Y-%m-%d")
        
        logger.info(f"Buscando contas pagas de {data_inicio} até {data_fim}")
        
        # Buscar dados
        df = client.buscar_dados_completos(
            data_inicio=data_inicio,
            data_fim=data_fim,
            selection_type='D',
            correction_indexer_id=0,
            correction_date=data_fim,  # Usa data final como data de correção
            with_authorizations=True,
            with_bank_movements=False
        )
        
        if df.empty:
            logger.warning("Nenhum dado encontrado")
            return pd.DataFrame()
        
        # Adiciona coluna Data_Snapshot (usa data final como snapshot)
        df['Data_Snapshot'] = pd.to_datetime(data_fim)
        
        # Adiciona colunas padrão do sistema
        df['fonte'] = 'sienge_contas_pagas'
        df['processado_em'] = datetime.now()
        
        logger.info(f"✅ Dados processados: {len(df)} registros")
        return df
        
    except Exception as e:
        logger.error(f"Erro ao obter dados de contas pagas: {str(e)}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


if __name__ == "__main__":
    # Teste local
    print("Testando API de Contas Pagas do Sienge...")
    df = obter_dados_sienge_contas_pagas(dias_retrocesso=30)
    print(f"Registros obtidos: {len(df)}")
    if not df.empty:
        print(f"Colunas: {list(df.columns)}")
        print(df.head())

