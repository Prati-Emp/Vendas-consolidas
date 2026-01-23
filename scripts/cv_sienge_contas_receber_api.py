#!/usr/bin/env python3
"""
Integração com API do Sienge - Contas a Receber (Income)
Endpoint: https://api.sienge.com.br/pratiemp/public/api/bulk-data/v1/income
Credenciais: Token do Sienge (SIENGE_TOKEN)

Baseado no código fornecido pelo usuário.
"""

import logging
import os
import sys
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
import pandas as pd
import requests
import json
import numpy as np

# Garante import do projeto quando rodar via Actions
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from scripts.config import get_api_config

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContasReceberSiengeAPIClient:
    """
    Cliente para API de Contas a Receber (Income) do Sienge
    """
    
    def __init__(self):
        self.config = get_api_config('sienge_contas_receber')
        
        if not self.config:
            raise ValueError("Configuração da API Sienge Contas Receber não encontrada")
        
        self.base_url = self.config.base_url
        self.headers = self.config.headers
    
    def buscar_contas_receber(self, 
                           data_inicio: str, 
                           data_fim: str, 
                           selection_type: str = 'D',
                           correction_date: str = None) -> Dict:
        """
        Busca dados de Contas a Receber da API Bulk-Data
        """
        params = {
            'startDate': data_inicio,
            'endDate': data_fim,
            'selectionType': selection_type,
        }
        
        if correction_date:
            params['correctionDate'] = correction_date
        
        try:
            logger.info(f"Buscando contas a receber: {data_inicio} até {data_fim}")
            logger.info(f"Data de correção: {correction_date}")
            
            response = requests.get(self.base_url, headers=self.headers, params=params, timeout=120)
            response.raise_for_status()
            
            data = response.json()
            
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
                logger.error(f"Response: {e.response.text}")
            return {'results': []}

    def processar_dados(self, dados: Any) -> pd.DataFrame:
        if not dados:
            logger.warning("Nenhum dado recebido para processar")
            return pd.DataFrame()
        
        # Normaliza dados para lista
        if isinstance(dados, dict):
            if 'results' in dados: dados = dados['results']
            elif 'data' in dados: dados = dados['data']
            else: dados = [dados]
        
        if not isinstance(dados, list):
            return pd.DataFrame()
        
        if len(dados) == 0:
            logger.warning("Nenhum registro encontrado")
            return pd.DataFrame()
        
        logger.info(f"Processando {len(dados)} registros...")
        df = pd.DataFrame(dados)
        df_relatorio = self.processar_para_relatorio(df)
        
        return df_relatorio
    
    def processar_para_relatorio(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Processa o DataFrame bruto para o formato do relatório (Lógica do usuário)
        """
        logger.info("Processando dados para formato relatório...")
        
        if df.empty:
            return df

        # 1. Extração de dados de recebimento (da lista 'receipts')
        # Cria colunas temporárias
        df['data_recebimento_temp'] = None
        df['valor_recebido_temp'] = 0.0
        df['valor_liquido_temp'] = 0.0
        df['valor_correcao_temp'] = 0.0
        df['acrescimos_temp'] = 0.0
        df['seguro_temp'] = 0.0
        df['taxa_adm_temp'] = 0.0
        df['operacao_temp'] = None
        df['conta_corrente_temp'] = None
        df['tipo_baixa_temp'] = None
        
        if 'receipts' in df.columns:
            def extrair_recebimento(receipts_list):
                if not isinstance(receipts_list, list) or not receipts_list:
                    return (None, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, None, None, None)
                
                try:
                    recebimentos_validos = [r for r in receipts_list if isinstance(r, dict)]
                    if not recebimentos_validos:
                        return (None, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, None, None, None)
                        
                    # Pega o último recebimento para dados únicos
                    ultimo_rec = sorted(recebimentos_validos, key=lambda x: x.get('paymentDate', ''), reverse=True)[0]
                    data_rec = ultimo_rec.get('paymentDate')
                    operacao = ultimo_rec.get('operationTypeName')
                    conta_corrente = ultimo_rec.get('accountNumber')
                    
                    # Soma valores de todos os recebimentos
                    total_recebido = sum(float(r.get('grossAmount', 0) or 0) for r in recebimentos_validos)
                    total_liquido = sum(float(r.get('netAmount', 0) or 0) for r in recebimentos_validos)
                    total_correcao = sum(float(r.get('monetaryCorrectionAmount', 0) or 0) for r in recebimentos_validos)
                    total_acrescimos = sum(float(r.get('interestAmount', 0) or 0) + float(r.get('fineAmount', 0) or 0) + float(r.get('additionAmount', 0) or 0) for r in recebimentos_validos)
                    total_seguro = sum(float(r.get('insuranceAmount', 0) or 0) for r in recebimentos_validos)
                    total_taxa_adm = sum(float(r.get('dueAdmAmount', 0) or 0) for r in recebimentos_validos)
                    
                    # Tipo de baixa (pode ser baseado no operationTypeName ou accountType)
                    tipo_baixa = operacao if operacao else None
                    
                    return (data_rec, total_recebido, total_liquido, total_correcao, 
                           total_acrescimos, total_seguro, total_taxa_adm, 
                           operacao, conta_corrente, tipo_baixa)
                except:
                    return (None, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, None, None, None)

            dados_rec = df['receipts'].apply(extrair_recebimento)
            df['data_recebimento_temp'] = [d[0] if d else None for d in dados_rec]
            df['valor_recebido_temp'] = [d[1] if d else 0.0 for d in dados_rec]
            df['valor_liquido_temp'] = [d[2] if d else 0.0 for d in dados_rec]
            df['valor_correcao_temp'] = [d[3] if d else 0.0 for d in dados_rec]
            df['acrescimos_temp'] = [d[4] if d else 0.0 for d in dados_rec]
            df['seguro_temp'] = [d[5] if d else 0.0 for d in dados_rec]
            df['taxa_adm_temp'] = [d[6] if d else 0.0 for d in dados_rec]
            df['operacao_temp'] = [d[7] if d else None for d in dados_rec]
            df['conta_corrente_temp'] = [d[8] if d else None for d in dados_rec]
            df['tipo_baixa_temp'] = [d[9] if d else None for d in dados_rec]

        # 2. Definição do Status
        def definir_status(row):
            saldo = float(row.get('balanceAmount', 0) or 0)
            original = float(row.get('originalAmount', 0) or 0)
            
            if saldo <= 0.01:
                return 'RECEBIDA'
            elif saldo < original:
                return 'PARCIAL'
            else:
                return 'ABERTA'
                
        df['status_parcela_calc'] = df.apply(definir_status, axis=1)

        # 2.1 Cálculo de Dias de Atraso
        def calcular_atraso(row):
            try:
                vencimento = pd.to_datetime(row.get('dueDate'))
                if pd.isna(vencimento): return 0
                
                status = row.get('status_parcela_calc')
                
                if status == 'RECEBIDA':
                    recebimento = pd.to_datetime(row.get('data_recebimento_temp'))
                    if pd.isna(recebimento): return 0
                    dias = (recebimento - vencimento).days
                else:
                    hoje = pd.to_datetime(date.today())
                    dias = (hoje - vencimento).days
                
                return max(0, dias)
            except:
                return 0
                
        df['dias_atraso_calc'] = df.apply(calcular_atraso, axis=1)

        # Extrai código e descrição da condição de pagamento
        if 'paymentTerm' in df.columns:
             df['condicao_pagamento_codigo'] = df['paymentTerm'].apply(
                 lambda x: str(x.get('id')) if isinstance(x, dict) and x.get('id') is not None else None
             )
             df['condicao_pagamento_desc'] = df['paymentTerm'].apply(
                 lambda x: x.get('descrition') if isinstance(x, dict) else None
             )

        # Extrai Centro de Custo (prioriza receiptsCategories, depois receipts)
        def extrair_centro_custo(row):
            # Tenta primeiro em receiptsCategories
            if 'receiptsCategories' in row and isinstance(row['receiptsCategories'], list) and row['receiptsCategories']:
                cat = row['receiptsCategories'][0]
                return cat.get('costCenterId'), cat.get('costCenterName')
            
            # Se não tiver, tenta em receipts -> bankMovements -> financialCategories
            if 'receipts' in row and isinstance(row['receipts'], list) and row['receipts']:
                for rec in row['receipts']:
                    if isinstance(rec, dict) and 'bankMovements' in rec:
                        for bm in rec.get('bankMovements', []):
                            if isinstance(bm, dict) and 'financialCategories' in bm:
                                for fc in bm.get('financialCategories', []):
                                    if isinstance(fc, dict):
                                        return fc.get('costCenterId'), fc.get('costCenterName')
            
            return None, None
        
        centro_custo_data = df.apply(extrair_centro_custo, axis=1)
        df['costCenterId'] = [d[0] for d in centro_custo_data]
        df['costCenterName'] = [d[1] for d in centro_custo_data]

        # Adiciona campos que não existem na API como vazios
        df['nosso_numero'] = None
        df['serasa'] = None
        df['spc'] = None
        df['cadastrado_por'] = None
        df['data_cadastro_parcela'] = None
        df['observacao_titulo'] = None
        df['observacao_baixa'] = None

        # 3. Mapeamento de Colunas (API -> Relatório CSV)
        mapeamento = {
            'companyId': 'Cod_Empresa',
            'companyName': 'Empresa',
            'clientId': 'Cod_Cliente',
            'clientName': 'Cliente',
            'billId': 'Titulo',
            'installmentNumber': 'Parcela_Sequencial', # Número visual da parcela
            'installmentId': 'ID_Parcela',
            'documentIdentificationName': 'Documento',
            'documentNumber': 'N_Documento',
            'documentForecast': 'Previsao_Financeira',
            'originId': 'Origem',
            'originalAmount': 'Valor_Original',
            'discountAmount': 'Descontos',
            'taxAmount': 'Imposto',
            'indexerName': 'Indexador',
            'dueDate': 'Data_Vencimento',
            'issueDate': 'Data_Emissao',
            'billDate': 'Data_Contabil',
            'installmentBaseDate': 'Data_Competencia',
            'balanceAmount': 'Valor_Devido', # Saldo em aberto = Valor devido
            'correctedBalanceAmount': 'Valor_Corrigido',
            'defaulterSituation': 'Inadimplente',
            'subJudicie': 'Subjudice',
            'mainUnit': 'Unidade',
            'bearerId': 'Portador',
            'condicao_pagamento_codigo': 'Tipo_Condicao',
            'condicao_pagamento_desc': 'Parcela_Condicao',
            'costCenterId': 'Cod_Centro_Custo',
            'costCenterName': 'Centro_Custo',
            # Calculados/Extraídos de receipts
            'data_recebimento_temp': 'Data_Baixa',
            'valor_liquido_temp': 'Valor_Liquido',
            'valor_recebido_temp': 'Valor_Baixa',
            'valor_correcao_temp': 'Valor_Correcao',
            'acrescimos_temp': 'Acrescimos',
            'seguro_temp': 'Seguro',
            'taxa_adm_temp': 'Taxa_Administrativa',
            'operacao_temp': 'Operacao',
            'conta_corrente_temp': 'Conta_Corrente',
            'tipo_baixa_temp': 'Tipo_Baixa',
            'status_parcela_calc': 'Status_Parcela',
            'dias_atraso_calc': 'Dias_Atraso',
            # Campos que não existem na API (vazios)
            'nosso_numero': 'Nosso_Numero',
            'serasa': 'Serasa',
            'spc': 'SPC',
            'cadastrado_por': 'Cadastrado_Por',
            'data_cadastro_parcela': 'Data_Cadastro_Parcela',
            'observacao_titulo': 'Observacao_Titulo',
            'observacao_baixa': 'Observacao_Baixa'
        }
        
        # Garante coluna Parcela se não vier installmentNumber
        if 'installmentNumber' not in df.columns and 'installmentId' in df.columns:
            df['installmentNumber'] = df['installmentId'].astype(str)
        
        df_renomeado = df.rename(columns=mapeamento)
        
        # Tipagem
        conversoes = {
            'Cod_Empresa': 'Int64',
            'Cod_Cliente': 'Int64',
            'Titulo': 'Int64',
            'ID_Parcela': 'Int64',
            'Cod_Centro_Custo': 'Int64',
            'Portador': 'Int64',
            'Descontos': 'float', 
            'Imposto': 'float',
            'Valor_Original': 'float',
            'Valor_Correcao': 'float',
            'Valor_Corrigido': 'float',
            'Valor_Devido': 'float',
            'Valor_Baixa': 'float',
            'Acrescimos': 'float',
            'Seguro': 'float',
            'Taxa_Administrativa': 'float',
            'Valor_Liquido': 'float',
            'Tipo_Condicao': 'string'
        }
        
        for col, dtype in conversoes.items():
            if col in df_renomeado.columns:
                try:
                    if dtype == 'Int64':
                        df_renomeado[col] = pd.to_numeric(df_renomeado[col], errors='coerce').astype('Int64')
                    elif dtype == 'string':
                        df_renomeado[col] = df_renomeado[col].astype(str)
                    else:
                        df_renomeado[col] = pd.to_numeric(df_renomeado[col], errors='coerce')
                except:
                    pass

        # Seleciona colunas finais (na ordem solicitada)
        colunas_finais = [
            'Titulo',
            'Parcela_Sequencial',
            'Parcela_Condicao',
            'Cod_Empresa',
            'Empresa',
            'Cod_Centro_Custo',
            'Centro_Custo',
            'Unidade',
            'Cod_Cliente',
            'Cliente',
            'Documento',
            'N_Documento',
            'Origem',
            'Status_Parcela',
            'Nosso_Numero',
            'Inadimplente',
            'Serasa',
            'SPC',
            'Subjudice',
            'Indexador',
            'Tipo_Condicao',
            'Portador',
            'Operacao',
            'Cadastrado_Por',
            'Data_Emissao',
            'Data_Vencimento',
            'Data_Contabil',
            'Data_Competencia',
            'Data_Cadastro_Parcela',
            'Valor_Original',
            'Valor_Correcao',
            'Valor_Corrigido',
            'Valor_Devido',
            'Data_Baixa',
            'Valor_Baixa',
            'Acrescimos',
            'Descontos',
            'Seguro',
            'Taxa_Administrativa',
            'Valor_Liquido',
            'Tipo_Baixa',
            'Conta_Corrente',
            'Observacao_Titulo',
            'Observacao_Baixa',
            'Dias_Atraso'
        ]
        
        cols_existentes = [c for c in colunas_finais if c in df_renomeado.columns]
        df_final = df_renomeado[cols_existentes].copy()
        
        return df_final

    def buscar_dados_completos(self, 
                             data_inicio: str = None, 
                             data_fim: str = None,
                             correction_date: str = None) -> pd.DataFrame:
        
        hoje = date.today()
        hoje_str = hoje.strftime("%Y-%m-%d")
        
        if data_inicio is None:
            data_inicio = "2018-01-01" # Conforme solicitado na logica original
            logger.info(f"Data inicial definida automaticamente para: {data_inicio}")
        
        if data_fim is None:
            # Data fim fixa em 23/01/2036
            data_fim = "2036-01-23"
            logger.info(f"Data final definida automaticamente para: {data_fim}")
            
        if correction_date is None:
            correction_date = hoje_str
            logger.info(f"Data de correção definida automaticamente para: {correction_date}")
        
        dados = self.buscar_contas_receber(
            data_inicio=data_inicio,
            data_fim=data_fim,
            correction_date=correction_date
        )
        
        if not dados:
            return pd.DataFrame()
        
        df = self.processar_dados(dados)
        return df

def obter_dados_sienge_contas_receber() -> pd.DataFrame:
    """
    Função principal para obter dados de contas a receber do Sienge
    """
    try:
        client = ContasReceberSiengeAPIClient()
        df = client.buscar_dados_completos()
        
        if not df.empty:
            # Adiciona colunas padrão do sistema
            df['fonte'] = 'sienge_contas_receber'
            df['processado_em'] = datetime.now()
            df['Data_Snapshot'] = pd.to_datetime(date.today())
            
        return df
    except Exception as e:
        logger.error(f"Erro ao obter dados: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()

if __name__ == "__main__":
    df = obter_dados_sienge_contas_receber()
    print(f"Registros obtidos: {len(df)}")
