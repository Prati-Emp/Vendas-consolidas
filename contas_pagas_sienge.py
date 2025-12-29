import requests
import pandas as pd
from datetime import datetime, date
import json
from typing import List, Dict, Any
import numpy as np

class ContasPagasSienge:
    """
    Classe para buscar dados de Contas Pagas (Outcome) da API Bulk-Data do Sienge
    API: https://api.sienge.com.br/docs/#/bulk-data-outcome-v1
    """
    
    def __init__(self, token: str):
        """
        Inicializa a classe com o token de autenticação
        
        Args:
            token (str): Token de autenticação Basic
        """
        self.base_url = "https://api.sienge.com.br/pratiemp/public/api/bulk-data/v1/outcome"
        self.token = token
        self.headers = {
            'Authorization': token,
            'Content-Type': 'application/json'
        }
    
    def buscar_contas_pagas(self, 
                           data_inicio: str, 
                           data_fim: str, 
                           selection_type: str = 'I',
                           correction_indexer_id: int = 1,
                           correction_date: str = None,
                           with_authorizations: bool = False,
                           with_bank_movements: bool = True) -> Dict:
        """
        Busca dados de Contas Pagas da API Bulk-Data
        """
        # Parâmetros da requisição (Ajustados para bater com o código M)
        params = {
            'startDate': data_inicio,
            'endDate': data_fim,
            'selectionType': 'D', # Mudado de 'I' para 'D' conforme código M
            'correctionIndexerId': 0, # Mudado de 1 para 0 conforme código M
            'withAuthorizations': 'true', # Mudado de 'false' para 'true' conforme código M
            'withBankMovements': 'false' # Mudado de 'true' para 'false' conforme código M
        }
        
        # Adiciona data de correção se fornecida (O código M usa fixo 2025-12-24, vamos manter dinâmico ou fixar?)
        # O código M fixa 'correctionDate=2025-12-24'. Vamos manter a lógica de receber o parâmetro
        # mas garantir que o padrão seja o esperado.
        if correction_date:
            params['correctionDate'] = correction_date
        
        try:
            print(f"=== BUSCANDO CONTAS PAGAS ===")
            print(f"Período: {data_inicio} até {data_fim}")
            print(f"Data de correção: {correction_date}")
            print(f"Fazendo requisição à API bulk-data...")
            
            response = requests.get(self.base_url, headers=self.headers, params=params)
            response.raise_for_status()
            
            # Retorna os dados JSON
            dados = response.json()
            
            print(f"Requisição realizada com sucesso!")
            
            return dados
            
        except requests.exceptions.HTTPError as e:
            print(f"Erro HTTP na requisição: {e}")
            if hasattr(e.response, 'text'):
                print(f"Resposta do servidor: {e.response.text}")
            return {}
        except requests.exceptions.RequestException as e:
            print(f"Erro na requisição: {e}")
            return {}
        except json.JSONDecodeError as e:
            print(f"Erro ao decodificar JSON: {e}")
            return {}
    
    def expandir_colunas_json(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Expande colunas que contêm JSON/arrays aninhados em colunas separadas
        """
        # Colunas conhecidas que contêm arrays/objetos JSON
        colunas_json = ['paymentsCategories', 'departamentsCosts', 'buildingsCosts', 'payments', 'authorizations']
        
        df_expandido = df.copy()
        
        for coluna in colunas_json:
            if coluna not in df_expandido.columns:
                continue
            
            print(f"Expandindo coluna: {coluna}...")
            
            try:
                # Primeiro, encontra o tamanho máximo do array para criar colunas suficientes
                max_items = 0
                todas_chaves = set()
                
                # Análise prévia para determinar estrutura
                for valor_original in df_expandido[coluna]:
                    # Converte string JSON para objeto Python se necessário
                    if isinstance(valor_original, str):
                        try:
                            if valor_original.strip().startswith('[') or valor_original.strip().startswith('{'):
                                valor = json.loads(valor_original)
                            else:
                                valor = [] if valor_original.strip() == '[]' else valor_original
                        except:
                            valor = []
                    elif valor_original is None:
                        valor = []
                    elif hasattr(valor_original, '__len__') and len(valor_original) == 0:
                        valor = []
                    else:
                        valor = valor_original
                    
                    if isinstance(valor, list):
                        max_items = max(max_items, len(valor))
                        # Coleta todas as chaves possíveis
                        for item in valor:
                            if isinstance(item, dict):
                                todas_chaves.update(item.keys())
                    elif isinstance(valor, dict):
                        max_items = max(max_items, 1)
                        todas_chaves.update(valor.keys())
                
                if max_items == 0 or len(todas_chaves) == 0:
                    print(f"  Coluna {coluna} não contém dados expansíveis")
                    # Se a coluna original for vazia ou listas vazias, podemos removê-la depois na limpeza
                    continue
                
                # Prepara dicionário para novas colunas (mais eficiente que insert repetido)
                novas_colunas = {}
                
                # Preenche os valores
                for idx, valor_original in enumerate(df_expandido[coluna]):
                    # Normalização do valor
                    if isinstance(valor_original, str):
                        try:
                            valor = json.loads(valor_original) if valor_original.strip().startswith(('[', '{')) else valor_original
                        except:
                            valor = []
                    elif valor_original is None:
                        valor = []
                    elif hasattr(valor_original, '__len__') and len(valor_original) == 0:
                        valor = []
                    else:
                        valor = valor_original
                    
                    # Expande o valor
                    if isinstance(valor, list):
                        for item_idx, item in enumerate(valor):
                            if isinstance(item, dict):
                                for chave, val in item.items():
                                    col_name = f"{coluna}_{item_idx}_{chave}"
                                    if col_name not in novas_colunas:
                                        novas_colunas[col_name] = [None] * len(df_expandido)
                                    novas_colunas[col_name][idx] = val
                    elif isinstance(valor, dict):
                        for chave, val in valor.items():
                            col_name = f"{coluna}_0_{chave}"
                            if col_name not in novas_colunas:
                                novas_colunas[col_name] = [None] * len(df_expandido)
                            novas_colunas[col_name][idx] = val
                
                # Adiciona as novas colunas ao DataFrame de uma vez
                if novas_colunas:
                    print(f"  Criadas {len(novas_colunas)} novas colunas a partir de {coluna}")
                    df_novas = pd.DataFrame(novas_colunas, index=df_expandido.index)
                    df_expandido = pd.concat([df_expandido, df_novas], axis=1)
                
            except Exception as e:
                print(f"  Erro ao expandir coluna {coluna}: {e}")
                # import traceback
                # traceback.print_exc()
                continue
        
        return df_expandido
    
    def limpar_colunas_vazias(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Remove colunas que não contêm dados úteis (vazias, apenas None/NaN, ou apenas listas vazias)
        """
        print(f"Total de colunas antes da limpeza: {len(df.columns)}")
        
        # 1. Remove colunas onde todos os valores são NaN/None
        df_limpo = df.dropna(axis=1, how='all')
        
        cols_originais = set(df_limpo.columns)
        cols_para_remover = []
        
        for col in df_limpo.columns:
            # Pega uma amostra para verificar tipo (performance) ou verifica todos se necessário
            # Verifica se todos são listas vazias
            try:
                # Se a coluna contém listas, verifica se todas são vazias
                if df_limpo[col].apply(lambda x: isinstance(x, list) and len(x) == 0).all():
                    cols_para_remover.append(col)
                    continue
                
                # Verifica se todos são strings vazias
                if df_limpo[col].apply(lambda x: isinstance(x, str) and len(x.strip()) == 0).all():
                    cols_para_remover.append(col)
                    continue
                    
                # Verifica se contém apenas 0 ou 0.0 (opcional - removido por segurança, pode ser valor real)
                # if df_limpo[col].apply(lambda x: x == 0 or x == 0.0).all():
                #     cols_para_remover.append(col)
            except:
                pass
        
        if cols_para_remover:
            print(f"Removendo {len(cols_para_remover)} colunas adicionais sem dados...")
            df_limpo = df_limpo.drop(columns=cols_para_remover)
            
        print(f"Total de colunas após limpeza: {len(df_limpo.columns)}")
        return df_limpo

    def processar_para_relatorio(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Processa o DataFrame bruto para o formato do relatório CSV solicitado
        """
        print("=== PROCESSANDO DADOS PARA FORMATO RELATÓRIO ===")
        
        if df.empty:
            return df

        # 1. Extração de dados de pagamento (da lista 'payments')
        # Cria colunas temporárias para armazenar dados agregados de pagamento
        df['data_pagamento_temp'] = None
        df['valor_pago_temp'] = 0.0
        df['valor_liquido_temp'] = 0.0
        
        # Se a coluna payments existir e tiver dados
        if 'payments' in df.columns:
            # Função para extrair dados do pagamento
            def extrair_pagamento(payments_list):
                if not isinstance(payments_list, list) or not payments_list:
                    return None, 0.0, 0.0
                
                # Assume o último pagamento ou soma? 
                # Geralmente pega a data do último e soma valores
                # Aqui vamos pegar o pagamento mais recente
                try:
                    # Ordena por data (se houver)
                    pagamentos_validos = [p for p in payments_list if isinstance(p, dict)]
                    if not pagamentos_validos:
                        return None, 0.0, 0.0
                        
                    ultimo_pgto = sorted(pagamentos_validos, key=lambda x: x.get('paymentDate', ''), reverse=True)[0]
                    
                    data_pgto = ultimo_pgto.get('paymentDate')
                    
                    # Soma valores de todos os pagamentos para 'Valor da baixa'
                    total_pago = sum(float(p.get('grossAmount', 0) or 0) for p in pagamentos_validos)
                    total_liquido = sum(float(p.get('netAmount', 0) or 0) for p in pagamentos_validos)
                    
                    return data_pgto, total_pago, total_liquido
                except Exception as e:
                    return None, 0.0, 0.0

            # Aplica a extração
            dados_pgto = df['payments'].apply(extrair_pagamento)
            
            # Desempacota os resultados
            df['data_pagamento_temp'] = [d[0] if d else None for d in dados_pgto]
            df['valor_pago_temp'] = [d[1] if d else 0.0 for d in dados_pgto]
            df['valor_liquido_temp'] = [d[2] if d else 0.0 for d in dados_pgto]

        # 2. Definição do Status
        # Regra: Se saldo zerado (ou muito próximo de zero) -> PAGA, senão ABERTA
        def definir_status(row):
            saldo = float(row.get('balanceAmount', 0) or 0)
            original = float(row.get('originalAmount', 0) or 0)
            
            if saldo <= 0.01: # Margem de segurança para float
                return 'PAGA'
            elif saldo < original:
                return 'PARCIAL' # Opcional, o usuário pediu status do lote, mas status da parcela é relevante
            else:
                return 'ABERTA' # Ou A VENCER / VENCIDA dependendo da data
                
        df['status_parcela_calc'] = df.apply(definir_status, axis=1)

        # 2.1 Cálculo de Dias de Atraso
        def calcular_atraso(row):
            try:
                vencimento = pd.to_datetime(row.get('dueDate'))
                if pd.isna(vencimento): return 0
                
                status = row.get('status_parcela_calc')
                
                if status == 'PAGA':
                    pagamento = pd.to_datetime(row.get('data_pagamento_temp'))
                    if pd.isna(pagamento): return 0
                    dias = (pagamento - vencimento).days
                else:
                    hoje = pd.to_datetime(date.today())
                    dias = (hoje - vencimento).days
                
                return max(0, dias)
            except:
                return 0
                
        df['dias_atraso_calc'] = df.apply(calcular_atraso, axis=1)

        # 3. Mapeamento de Colunas (API -> Relatório CSV conforme código M + Colunas Calculadas)
        mapeamento = {
            'companyId': 'Cód. empresa',
            'companyName': 'Empresa',
            'creditorId': 'Cód. credor',
            'creditorName': 'Credor',
            'billId': 'Título', # ID interno do título
            'installmentId': 'Parcela', # ID da Parcela
            'documentIdentificationName': 'Documento',
            'documentNumber': 'N° documento',
            'forecastDocument': 'Previsão Financeira',
            'consistencyStatus': 'Consistência',
            'originalAmount': 'Valor bruto',
            'discountAmount': 'Desconto',
            'taxAmount': 'Valor Imposto Retido',
            'indexerName': 'Indexador',
            'dueDate': 'Data vencimento',
            'issueDate': 'Data emissão',
            'balanceAmount': 'Saldo em aberto',
            'correctedBalanceAmount': 'Valor Saldo Corrigido',
            'authorizationStatus': 'Autorização',
            'registeredBy': 'Usuário que cadastrou',
            'registeredDate': 'Data de cadastro',
            # Campos calculados/extraídos
            'data_pagamento_temp': 'Data do pagamento',
            'valor_liquido_temp': 'Valor líquido',
            'valor_pago_temp': 'Valor da baixa',
            'status_parcela_calc': 'Status da parcela',
            'dias_atraso_calc': 'Dias de atraso'
        }
        
        # Renomeia as colunas existentes
        df_renomeado = df.rename(columns=mapeamento)
        
        # Tipagem
        conversoes = {
            'Cód. empresa': 'Int64',
            'Cód. credor': 'Int64',
            'Título': 'Int64',
            'Parcela': 'Int64',
            'Desconto': 'Int64', 
            'Valor Imposto Retido': 'Int64'
        }
        
        for col, dtype in conversoes.items():
            if col in df_renomeado.columns:
                try:
                    df_renomeado[col] = pd.to_numeric(df_renomeado[col], errors='coerce').astype(dtype)
                except:
                    pass

        # Seleciona colunas finais na ordem desejada para o relatório
        colunas_relatorio_original = [
            'Título', 'Parcela', 'Cód. empresa', 'Empresa', 'Cód. credor', 'Credor', 
            'Documento', 'N° documento', 'Previsão Financeira', 'Consistência',
            'Data vencimento', 'Valor bruto', 'Desconto', 'Valor Imposto Retido', 
            'Valor líquido', 'Valor da baixa', 'Saldo em aberto', 'Valor Saldo Corrigido',
            'Data do pagamento', 'Data emissão', 'Indexador', 
            'Status da parcela', 'Dias de atraso', 'Usuário que cadastrou', 'Data de cadastro'
        ]
        
        # Filtra e reordena
        cols_existentes = [c for c in colunas_relatorio_original if c in df_renomeado.columns]
        df_final = df_renomeado[cols_existentes].copy()
        
        return df_final

    def processar_dados(self, dados: Any) -> pd.DataFrame:
        """
        Processa os dados retornados pela API
        """
        if not dados:
            print("Nenhum dado recebido para processar")
            return pd.DataFrame()
        
        # Normaliza dados para lista
        if isinstance(dados, dict):
            if 'results' in dados: dados = dados['results']
            elif 'data' in dados: dados = dados['data']
            else: dados = [dados]
        
        if not isinstance(dados, list):
            print(f"Formato de dados não esperado: {type(dados)}")
            return pd.DataFrame()
        
        if len(dados) == 0:
            print("Nenhum registro encontrado")
            return pd.DataFrame()
        
        print(f"Processando {len(dados)} registros...")
        
        # Converte para DataFrame inicial
        df = pd.DataFrame(dados)
        
        # Aplica o processamento para formato relatório
        df_relatorio = self.processar_para_relatorio(df)
        
        return df_relatorio
    
    def buscar_dados_completos(self, 
                             data_inicio: str = "2025-01-01",  # Padrão fixo solicitado
                             data_fim: str = None, 
                             selection_type: str = 'I',
                             correction_indexer_id: int = 1,
                             correction_date: str = None,
                             with_authorizations: bool = False,
                             with_bank_movements: bool = True) -> pd.DataFrame:
        """
        Busca todos os dados de contas pagas.
        Se datas finais não forem fornecidas, usa a data atual (dinâmico).
        """
        # Define data atual para campos dinâmicos
        hoje = date.today().strftime("%Y-%m-%d")
        
        # Se data_fim não fornecida, usa data atual (dinâmico)
        if data_fim is None:
            data_fim = hoje
            print(f"Data final definida automaticamente para: {data_fim}")
        
        # Se correction_date não fornecida, usa data atual (dinâmico)
        if correction_date is None:
            correction_date = hoje
            print(f"Data de correção definida automaticamente para: {correction_date}")
        
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
            print("Nenhum dado retornado pela API")
            return pd.DataFrame()
        
        # Processa e limpa os dados
        df = self.processar_dados(dados)
        
        if not df.empty:
            print(f"\n=== DADOS CARREGADOS COM SUCESSO ===")
            print(f"Total de registros: {len(df)}")
            print(f"Total de colunas: {len(df.columns)}")
            
            # Salva em CSV
            nome_arquivo = f"contas_pagas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(nome_arquivo, index=False, encoding='utf-8-sig')
            print(f"Dados salvos em CSV: {nome_arquivo}")
            
            # Estatísticas rápidas
            print(f"\n=== ESTATÍSTICAS ===")
            colunas_data = [c for c in df.columns if 'date' in c.lower()]
            if colunas_data:
                try:
                    df[colunas_data[0]] = pd.to_datetime(df[colunas_data[0]], errors='coerce')
                    print(f"- Período ({colunas_data[0]}): {df[colunas_data[0]].min()} até {df[colunas_data[0]].max()}")
                except: pass
            
            colunas_valor = [c for c in df.columns if 'amount' in c.lower() or 'value' in c.lower()]
            if colunas_valor:
                try:
                    val_sum = pd.to_numeric(df[colunas_valor[0]], errors='coerce').sum()
                    print(f"- Valor Total ({colunas_valor[0]}): R$ {val_sum:,.2f}")
                except: pass
            
        else:
            print("Nenhum dado foi processado")
            
        return df

def main():
    """
    Função principal para executar a busca de dados
    """
    # Token de autenticação
    token = "Basic cHJhdGllbXAtYmlkam9udGFoYW46c2pvYnJuaWVad1dSQ1AwbWtRRDBCdGRUNGF4Sk9OcFY="
    
    # Inicializa a classe
    sienge = ContasPagasSienge(token)
    
    try:
        # Busca dados usando os parâmetros ajustados para bater com o código M
        # mas com datas dinâmicas (hoje)
        df = sienge.buscar_dados_completos(
            data_inicio="2025-01-01",
            data_fim=None,       # Automático (hoje)
            correction_date=None # Automático (hoje)
            # selection_type, with_authorizations, etc já estão ajustados no método buscar_contas_pagas
        )
        
        if not df.empty:
            print(f"\n=== PROCESSO CONCLUÍDO ===")
            print(f"Total de registros processados: {len(df)}")
        else:
            print("Nenhum registro encontrado")
            
    except Exception as e:
        print(f"Erro durante a execução: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
