import requests
import pandas as pd
from datetime import datetime, date, timedelta
from calendar import monthrange
import json
import os
from typing import List, Dict, Any, Optional
import time

class BuildingCostEstimationItems:
    """
    Classe para buscar dados de Building Cost Estimation Items da API Bulk-Data do Sienge
    Baseado no código M do Power BI fornecido
    """
    
    def __init__(self, token: str):
        """
        Inicializa a classe com o token de autenticação
        
        Args:
            token (str): Token de autenticação Basic
        """
        self.base_url = "https://api.sienge.com.br/pratiemp/public/api/bulk-data/v1/building-cost-estimation-items"
        self.token = token
        self.headers = {
            'Authorization': token,
            'Content-Type': 'application/json'
        }
    
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
            print(f"Buscando dados de building cost estimation items...")
            print(f"Data: {data_date}, BDI: {bdi}, Labor Burden: {labor_burden}")
            
            response = requests.get(self.base_url, headers=self.headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # A estrutura da resposta tem um campo 'data' que é uma lista
            if 'data' in data and isinstance(data['data'], list):
                print(f"Total de itens encontrados: {len(data['data'])}")
                return data['data']
            else:
                print("Estrutura de resposta inesperada")
                return []
                
        except requests.exceptions.RequestException as e:
            print(f"Erro na requisição: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Status Code: {e.response.status_code}")
                print(f"Response: {e.response.text}")
            return []
        except json.JSONDecodeError as e:
            print(f"Erro ao decodificar JSON: {e}")
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
                    print(f"Erro ao converter coluna {coluna} para {tipo}: {e}")
        
        # Tenta converter wbsCode para numérico (pode ser string ou número)
        if 'wbsCode' in df.columns:
            # Tenta converter para numérico, mantém original se falhar
            df['wbsCode_numerico'] = pd.to_numeric(df['wbsCode'], errors='coerce')
        
        # Divide percentuais por 100 (conforme código M)
        if 'Percentual_Previsto' in df.columns:
            df['Percentual_Previsto'] = df['Percentual_Previsto'] / 100
        
        if 'Percentual_Realizado' in df.columns:
            df['Percentual_Realizado'] = df['Percentual_Realizado'] / 100
        
        # Filtra WBS de serviço (wbsCode > 999999999) conforme código M
        # Usa a versão numérica se disponível, senão tenta converter na hora
        if aplicar_filtro_wbs and 'wbsCode' in df.columns:
            # Mostra alguns exemplos de wbsCode antes do filtro
            print(f"Exemplos de wbsCode (primeiros 5): {df['wbsCode'].head().tolist()}")
            print(f"Total de registros antes do filtro: {len(df)}")
            
            # Tenta filtrar usando conversão numérica
            wbs_numerico = pd.to_numeric(df['wbsCode'], errors='coerce')
            df_filtrado = df[wbs_numerico > 999999999]
            
            # Se o filtro numérico não retornou nada, tenta como string
            if len(df_filtrado) == 0:
                print("Filtro numérico não retornou resultados, tentando como string...")
                # Tenta filtrar strings que representam números grandes
                # Remove pontos e tenta converter
                wbs_limpo = df['wbsCode'].astype(str).str.replace('.', '').str.replace('-', '')
                wbs_limpo_numerico = pd.to_numeric(wbs_limpo, errors='coerce')
                df_filtrado = df[wbs_limpo_numerico > 999999999]
            
            df = df_filtrado
            print(f"Registros após filtro de WBS de serviço: {len(df)}")
            
            # Remove a coluna auxiliar se foi criada
            if 'wbsCode_numerico' in df.columns:
                df = df.drop(columns=['wbsCode_numerico'])
        elif 'wbsCode' in df.columns:
            print(f"Filtro de WBS desabilitado. Total de registros: {len(df)}")
        
        return df
    
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
        print(f"Buscando building cost estimation items para data: {data_date}")
        
        # Busca os dados
        dados = self.buscar_dados(data_date, bdi, labor_burden, include_disbursments)
        
        if not dados:
            print("Nenhum dado encontrado")
            return pd.DataFrame()
        
        print(f"Total de itens encontrados: {len(dados)}")
        
        # Processa os dados
        df = self.processar_dados(dados, aplicar_filtro_wbs=aplicar_filtro_wbs)
        
        return df
    
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
        
        print(f"\n{'='*60}")
        print(f"BUSCANDO DADOS DE {total_requisicoes} MESES")
        print(f"{'='*60}\n")
        
        for i, data_snapshot in enumerate(datas, 1):
            print(f"\n[{i}/{total_requisicoes}] Processando mês: {data_snapshot}")
            print("-" * 60)
            
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
                print(f"✅ Mês {data_snapshot}: {len(df)} registros processados")
            else:
                print(f"⚠️  Mês {data_snapshot}: Nenhum dado encontrado")
            
            # Pausa entre requisições para não sobrecarregar a API
            if i < total_requisicoes:
                time.sleep(1)
        
        if not resultados:
            print("\n❌ Nenhum dado foi retornado de nenhum mês")
            return pd.DataFrame()
        
        # Consolida todos os DataFrames
        print(f"\n{'='*60}")
        print("CONSOLIDANDO DADOS...")
        print(f"{'='*60}")
        
        df_final = pd.concat(resultados, ignore_index=True)
        
        print(f"\n✅ Consolidação concluída!")
        print(f"Total de registros consolidados: {len(df_final)}")
        print(f"Meses processados: {df_final['Data_Snapshot'].nunique()}")
        print(f"Datas únicas: {sorted(df_final['Data_Snapshot'].dt.strftime('%Y-%m-%d').unique())}")
        
        return df_final
    
    def gerar_relatorio_validacao(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Gera relatório de validação por mês
        
        Args:
            df (pd.DataFrame): DataFrame consolidado com Data_Snapshot
            
        Returns:
            pd.DataFrame: Relatório de validação
        """
        if df.empty or 'Data_Snapshot' not in df.columns:
            return pd.DataFrame()
        
        relatorio = []
        
        for data in sorted(df['Data_Snapshot'].unique()):
            df_mes = df[df['Data_Snapshot'] == data]
            
            info = {
                'Data_Snapshot': data.strftime('%Y-%m-%d'),
                'Total_Registros': len(df_mes),
                'Empreendimentos_Unicos': df_mes['ID_Empreendimento'].nunique() if 'ID_Empreendimento' in df_mes.columns else 0,
                'Preco_Total': df_mes['Preco_total'].sum() if 'Preco_total' in df_mes.columns else 0,
                'Quantidade_Total': df_mes['Quantidade'].sum() if 'Quantidade' in df_mes.columns else 0,
                'Percentual_Medio_Realizado': df_mes['Percentual_Realizado'].mean() if 'Percentual_Realizado' in df_mes.columns else 0
            }
            relatorio.append(info)
        
        return pd.DataFrame(relatorio)
    
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
    
    def verificar_meses_processados(self, arquivo_controle: str = "meses_processados.json") -> List[str]:
        """
        Verifica quais meses já foram processados (lê de arquivo de controle)
        
        Args:
            arquivo_controle (str): Caminho do arquivo de controle
            
        Returns:
            List[str]: Lista de datas já processadas no formato YYYY-MM-DD
        """
        if os.path.exists(arquivo_controle):
            try:
                with open(arquivo_controle, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                    return dados.get('meses_processados', [])
            except Exception as e:
                print(f"⚠️  Erro ao ler arquivo de controle: {e}")
                return []
        return []
    
    def salvar_meses_processados(self, meses: List[str], arquivo_controle: str = "meses_processados.json"):
        """
        Salva lista de meses processados em arquivo de controle
        
        Args:
            meses (List[str]): Lista de datas processadas
            arquivo_controle (str): Caminho do arquivo de controle
        """
        try:
            dados = {
                'ultima_atualizacao': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'meses_processados': sorted(list(set(meses)))
            }
            with open(arquivo_controle, 'w', encoding='utf-8') as f:
                json.dump(dados, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️  Erro ao salvar arquivo de controle: {e}")
    
    def determinar_meses_a_buscar(self, ano: int = 2025, mes_inicio: int = 1, 
                                   mes_fim: int = 10, 
                                   arquivo_controle: str = "meses_processados.json",
                                   modo_inicial: bool = False) -> List[str]:
        """
        Determina quais meses devem ser buscados baseado na lógica inteligente
        
        Args:
            ano (int): Ano de referência (padrão: 2025)
            mes_inicio (int): Mês inicial para primeira execução (padrão: 1)
            mes_fim (int): Mês final para primeira execução (padrão: 10)
            arquivo_controle (str): Arquivo de controle de meses processados
            modo_inicial (bool): Se True, busca todos os meses de mes_inicio a mes_fim
            
        Returns:
            List[str]: Lista de datas a serem buscadas
        """
        if modo_inicial:
            # Primeira execução: busca todos os meses de janeiro a outubro
            print("🔄 Modo inicial: buscando todos os meses de janeiro a outubro de 2025")
            return self.gerar_datas_mensais(ano, mes_inicio, mes_fim)
        
        # Verifica meses já processados
        meses_processados = self.verificar_meses_processados(arquivo_controle)
        
        if not meses_processados:
            # Se não há histórico, busca todos os meses até o mês anterior
            print("🔄 Nenhum histórico encontrado: buscando todos os meses até o mês anterior")
            mes_anterior_str = self.obter_mes_anterior()
            mes_anterior = datetime.strptime(mes_anterior_str, '%Y-%m-%d')
            
            if mes_anterior.year == ano:
                return self.gerar_datas_mensais(ano, mes_inicio, mes_anterior.month)
            else:
                return self.gerar_datas_mensais(ano, mes_inicio, mes_fim)
        
        # Determina qual mês buscar (último mês anterior)
        mes_anterior_str = self.obter_mes_anterior()
        
        # Verifica se o mês anterior já foi processado
        if mes_anterior_str in meses_processados:
            print(f"✅ Mês {mes_anterior_str} já foi processado anteriormente")
            print("ℹ️  Nenhum novo mês para buscar")
            return []
        
        # Busca apenas o mês anterior
        print(f"🔄 Buscando mês anterior: {mes_anterior_str}")
        return [mes_anterior_str]
    
    def exportar_para_excel(self, df: pd.DataFrame, nome_arquivo: Optional[str] = None) -> str:
        """
        Exporta o DataFrame para Excel (apenas dados consolidados)
        
        Args:
            df (pd.DataFrame): DataFrame a ser exportado
            nome_arquivo (str, optional): Nome do arquivo. Se None, gera automaticamente
            
        Returns:
            str: Caminho do arquivo criado
        """
        if df.empty:
            print("DataFrame vazio, nada para exportar")
            return ""
        
        if nome_arquivo is None:
            nome_arquivo = f"building_cost_estimation_items_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        try:
            # Exporta apenas dados consolidados
            df.to_excel(nome_arquivo, index=False, engine='openpyxl')
            print(f"Dados exportados com sucesso para: {nome_arquivo}")
            return nome_arquivo
        except Exception as e:
            print(f"Erro ao exportar para Excel: {e}")
            return ""

def main():
    """
    Função principal para executar a busca de dados com lógica inteligente
    - Primeira execução: busca todos os meses de janeiro a outubro de 2025
    - Execuções seguintes: busca apenas o mês anterior (que ainda não foi processado)
    """
    # Token de autenticação fornecido
    token = "Basic cHJhdGllbXAtYmlkam9udGFoYW46c2pvYnJuaWVad1dSQ1AwbWtRRDBCdGRUNGF4Sk9OcFY="
    
    # Inicializa a classe
    sienge = BuildingCostEstimationItems(token)
    
    # Arquivo de controle
    arquivo_controle = "meses_processados.json"
    
    try:
        # Parâmetros
        bdi = 999.99
        labor_burden = 999.99
        include_disbursments = False
        aplicar_filtro_wbs = True
        
        # Configuração para primeira execução
        # IMPORTANTE: Altere modo_inicial para False após a primeira execução
        # True = busca todos os meses de janeiro a outubro de 2025 (primeira execução)
        # False = busca apenas o mês anterior que ainda não foi processado (execuções mensais)
        modo_inicial = True  # Mude para False após rodar a primeira vez
        
        print("="*60)
        print("BUILDING COST ESTIMATION ITEMS - BUSCA INTELIGENTE")
        print("="*60)
        print(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Modo inicial: {modo_inicial}")
        print(f"BDI: {bdi}")
        print(f"Labor Burden: {labor_burden}")
        print(f"Include Disbursments: {include_disbursments}")
        print(f"Aplicar filtro WBS: {aplicar_filtro_wbs}")
        
        # Determina quais meses buscar
        datas = sienge.determinar_meses_a_buscar(
            ano=2025,
            mes_inicio=1,
            mes_fim=10,
            arquivo_controle=arquivo_controle,
            modo_inicial=modo_inicial
        )
        
        if not datas:
            print("\n✅ Todos os meses já foram processados!")
            print("ℹ️  Nenhuma requisição necessária.")
            return
        
        print(f"\n📅 Meses a processar: {len(datas)}")
        print(f"   Datas: {', '.join(datas)}")
        
        # Busca dados
        df_novos = sienge.buscar_multiplos_meses(
            datas=datas,
            bdi=bdi,
            labor_burden=labor_burden,
            include_disbursments=include_disbursments,
            aplicar_filtro_wbs=aplicar_filtro_wbs
        )
        
        if not df_novos.empty:
            # Atualiza arquivo de controle
            meses_processados = sienge.verificar_meses_processados(arquivo_controle)
            meses_novos = df_novos['Data_Snapshot'].dt.strftime('%Y-%m-%d').unique().tolist()
            todos_meses = list(set(meses_processados + meses_novos))
            sienge.salvar_meses_processados(todos_meses, arquivo_controle)
            
            print(f"\n{'='*60}")
            print("VALIDAÇÃO DOS DADOS")
            print(f"{'='*60}")
            
            # Gera relatório de validação
            relatorio = sienge.gerar_relatorio_validacao(df_novos)
            if not relatorio.empty:
                print("\n📊 Relatório por Mês:")
                print(relatorio.to_string(index=False))
            
            # Estatísticas gerais
            print(f"\n📈 Estatísticas dos Novos Dados:")
            print(f"- Total de registros: {len(df_novos):,}")
            print(f"- Total de meses processados: {df_novos['Data_Snapshot'].nunique()}")
            if 'ID_Empreendimento' in df_novos.columns:
                print(f"- Empreendimentos únicos: {df_novos['ID_Empreendimento'].nunique()}")
            if 'Preco_total' in df_novos.columns:
                print(f"- Preço total: R$ {df_novos['Preco_total'].sum():,.2f}")
            
            # Exporta dados consolidados para Excel
            print(f"\n{'='*60}")
            print("EXPORTANDO DADOS")
            print(f"{'='*60}")
            
            nome_arquivo = f"building_cost_estimation_items_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            arquivo = sienge.exportar_para_excel(df_novos, nome_arquivo)
            
            if arquivo:
                print(f"\n✅ Arquivo Excel criado: {arquivo}")
                print(f"   - Dados consolidados com coluna Data_Snapshot")
            
            print(f"\n{'='*60}")
            print("✅ PROCESSO CONCLUÍDO COM SUCESSO!")
            print(f"{'='*60}")
            print(f"\n📝 Resumo:")
            print(f"   - Meses processados nesta execução: {len(meses_novos)}")
            print(f"   - Total de meses no histórico: {len(todos_meses)}")
            print(f"   - Próxima execução buscará apenas o mês anterior (se ainda não processado)")
            
        else:
            print("\n❌ Nenhum dado foi retornado")
            
    except Exception as e:
        print(f"\n❌ Erro durante a execução: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

