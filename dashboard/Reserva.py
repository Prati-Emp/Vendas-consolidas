import streamlit as st
import os

# Importar sistema de autenticação avançado
from advanced_auth import require_auth

# Função para obter o caminho absoluto da logo
def get_logo_path():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, "logo.png")

# Configuração da página
st.set_page_config(page_title="Relatório de Reservas", layout="wide")

# Proteger com autenticação
require_auth()

from utils import display_navigation
# Display navigation bar (includes logo)
display_navigation()

# Store current page in session state
st.session_state['current_page'] = __file__

import pandas as pd
from datetime import datetime
import re
import locale
import duckdb
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Set locale to Brazilian Portuguese silently
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except locale.Error:
        try:
            locale.setlocale(locale.LC_ALL, 'pt_BR')
        except locale.Error:
            pass

def format_currency(value):
    """Format currency value to Brazilian Real format"""
    try:
        return f"R$ {value:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return f"R$ {value}"

# Sistema de autenticação removido por questões de segurança
# Para implementar autenticação segura, use:
# - Azure Active Directory
# - AWS Cognito  
# - Auth0
# - ou outro provedor de identidade confiável
# Título do aplicativo
st.title("📊 Relatório de Reservas")

def extract_days(situacao):
    # Extrai o número entre parênteses da situação
    match = re.search(r'\((\d+)\)', situacao)
    if match:
        return int(match.group(1))
    return 0

def check_time_limit(row):
    # Extrai o número entre parênteses da situação
    dias_limite = extract_days(row['situacao'])
    
    if dias_limite == 0:
        return False
        
    # Pega a data da última alteração diretamente da tabela de reservas
    data_ultima_alteracao = pd.to_datetime(row.get('data_ultima_alteracao_situacao'), errors='coerce')
    
    if pd.isna(data_ultima_alteracao):
        return False
    
    # Calcula a diferença entre agora e a última alteração em dias
    dias_decorridos = (pd.Timestamp.now() - data_ultima_alteracao).days
    
    # Verifica se o tempo desde a última alteração excede o limite
    return dias_decorridos >= dias_limite

# MotherDuck connection
@st.cache_resource
def get_motherduck_connection():
    """Create a cached connection to MotherDuck"""
    try:        
        token = os.getenv('MOTHERDUCK_TOKEN')
        
        if not token:
            load_dotenv(override=True)
            token = os.getenv('MOTHERDUCK_TOKEN')
            st.write("Token após reload do .env:", "Sim" if token else "Não")
            
            if not token:
                raise ValueError("MOTHERDUCK_TOKEN não encontrado nas variáveis de ambiente")

        # Sanitize
        token = token.strip().strip('"').strip("'")
        os.environ["MOTHERDUCK_TOKEN"] = token  
        
        conn = duckdb.connect("md:reservas")
        return conn

    except Exception as e:
        st.error(f"Erro ao configurar conexão: {str(e)}")
        raise

# Carregando os dados
@st.cache_data
def load_data():
    try:
        conn = get_motherduck_connection()
        
        # Usando as tabelas do MotherDuck com o esquema correto
        reservas_df = conn.sql("""
            SELECT *
            FROM reservas.main.reservas_abril
        """).df()
        
        workflow_df = conn.sql("""
            SELECT *
            FROM reservas.main.workflow_abril
        """).df()
        
        # Converter colunas de data com tratamento de erros
        for df in [reservas_df, workflow_df]:
            for col in df.select_dtypes(include=['object']).columns:
                try:
                    if 'data' in col.lower():
                        df[col] = pd.to_datetime(df[col], errors='coerce')
                except Exception as e:
                    st.warning(f"Erro ao converter coluna {col}: {str(e)}")
        
        # Remover linhas com datas inválidas apenas das colunas necessárias
        reservas_df = reservas_df.dropna(subset=['data_cad'])
        
        # Se não houver dados válidos, criar DataFrame com dados padrão
        if len(reservas_df) == 0:
            current_date = pd.Timestamp.now()
            reservas_df = pd.DataFrame({
                'data_cad': [current_date],
                'data_ultima_alteracao_situacao': [current_date],
                'empreendimento': ['Sem dados'],
                'situacao': ['Sem dados'],
                'valor_contrato': [0]
            })
            
        return reservas_df, workflow_df
        
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        current_date = pd.Timestamp.now()
        
        # Criar DataFrame com dados padrão em caso de erro
        reservas_df = pd.DataFrame({
            'data_cad': [current_date],
            'data_ultima_alteracao_situacao': [current_date],
            'empreendimento': ['Erro ao carregar dados'],
            'situacao': ['Erro'],
            'valor_contrato': [0]
        })
        workflow_df = pd.DataFrame()
        
        return reservas_df, workflow_df

reservas_df, workflow_df = load_data()

# Sidebar para filtros
st.sidebar.header("Filtros")

# Configurar valores padrão seguros para os filtros de data
default_start_date = pd.Timestamp('2025-01-01').date()
default_end_date = datetime.now().date()

try:
    # Converter datas para datetime.date
    valid_dates = reservas_df['data_cad'].dropna().dt.date
    if len(valid_dates) > 0:
        min_date = min(valid_dates)
        max_date = max(valid_dates)
    else:
        min_date = default_start_date
        max_date = default_end_date
except Exception as e:
    st.warning("Usando datas padrão devido a erro na conversão de datas")
    min_date = default_start_date
    max_date = default_end_date

# Garantir que as datas estejam em ordem correta
if min_date > max_date:
    min_date, max_date = max_date, min_date

# Garantir que temos valores válidos para o date_input
initial_value = min(max(default_start_date, min_date), max_date)

# Filtro de data com valores seguros
try:
    data_inicio = st.sidebar.date_input(
        "Data Inicial",
        value=initial_value,
        min_value=min_date,
        max_value=max_date
    )
    
    # Garantir que a data final seja posterior à inicial
    data_fim = st.sidebar.date_input(
        "Data Final",
        value=max(max_date, data_inicio),
        min_value=data_inicio,
        max_value=max_date
    )
except Exception as e:
    st.error(f"Erro ao configurar filtros de data: {str(e)}")
    data_inicio = min_date
    data_fim = max_date

# Filtro de empreendimento
empreendimentos = sorted(reservas_df['empreendimento'].unique())
empreendimento_selecionado = st.sidebar.selectbox("Empreendimento", ["Todos"] + list(empreendimentos))

# Filtro de situação
situacoes = sorted(reservas_df[~reservas_df['situacao'].isin(['Vendida', 'Distrato', 'Cancelada'])]['situacao'].unique())
situacao_selecionada = st.sidebar.selectbox("Situação", ["Todas"] + list(situacoes))

# Separador para filtros de conversão
st.sidebar.markdown("---")
st.sidebar.subheader("📊 Filtros Conversão")

# Buscar a maior data disponível no conjunto de dados
max_data_cad = pd.to_datetime('2025-12-31').date()  # Fallback padrão
try:
    conn_temp = get_motherduck_connection()
    max_date_query = conn_temp.sql("SELECT MAX(data_cad) FROM reservas.main.reservas_abril WHERE data_cad IS NOT NULL").df()
    if not max_date_query.empty and max_date_query.iloc[0, 0] is not None:
        max_data_cad = pd.to_datetime(max_date_query.iloc[0, 0]).date()
except Exception as e:
    st.sidebar.warning(f"⚠️ Não foi possível carregar a data máxima: {e}")

# Filtros específicos para a tabela de conversão
data_inicial_conversao = st.sidebar.date_input(
    "📅 Data Inicial (Conversão)",
    value=pd.to_datetime('2025-01-01').date(),
    help="Filtra reservas a partir desta data"
)

data_final_conversao = st.sidebar.date_input(
    "📅 Data Final (Conversão)",
    value=max_data_cad,
    help="Filtra reservas até esta data"
)

# Aplicar filtros
mask = (
    reservas_df['data_cad'].dt.date >= data_inicio
) & (
    reservas_df['data_cad'].dt.date <= data_fim
) & (
    reservas_df['situacao'].str.strip().str.upper() != 'MÚTUO'
)
if empreendimento_selecionado != "Todos":
    mask = mask & (reservas_df['empreendimento'] == empreendimento_selecionado)
if situacao_selecionada != "Todas":
    mask = mask & (reservas_df['situacao'] == situacao_selecionada)

df_filtrado = reservas_df[mask].copy()

# Métricas principais
df_sem_canceladas_vendidas = df_filtrado[~df_filtrado['situacao'].isin(['Cancelada', 'Vendida', 'Distrato'])].copy()

col1, col2 = st.columns(2)
with col1:
    st.metric(label="Total De Reservas", value=len(df_sem_canceladas_vendidas))
with col2:
    valor_total = df_sem_canceladas_vendidas['valor_contrato'].sum()
    st.metric(label="Valor Total", value=format_currency(valor_total))
    
    
# Reservas por Situação
st.subheader("Reservas Por Situação")

# Definir ordem do funil de vendas
ordem_situacoes = [
    'Reserva (7)',
    'Crédito (CEF) (3)',
    'Negociação (5)',
    'Mútuo',
    'Análise Diretoria',
    'Contrato - Elaboração',
    'Contrato - Assinatura',
    #'Vendida',
    # 'Distrato'
]

if df_filtrado.empty:
    st.info("Nenhuma reserva encontrada para os filtros selecionados.")
else:
    if df_sem_canceladas_vendidas.empty:
        st.info("Nenhuma reserva ativa disponível para exibição por situação.")
    else:
        quantidade_por_situacao = (
            df_sem_canceladas_vendidas['situacao']
            .value_counts()
            .rename_axis('Situação')
            .reset_index(name='Quantidade')
        )

        ordem_mapping = {situacao: idx for idx, situacao in enumerate(ordem_situacoes)}
        quantidade_por_situacao['ordem'] = quantidade_por_situacao['Situação'].map(ordem_mapping)
        quantidade_por_situacao = quantidade_por_situacao.sort_values(['ordem', 'Situação']).drop(columns=['ordem'])

        df_sem_canceladas_vendidas['data_ultima_alteracao_situacao'] = pd.to_datetime(
            df_sem_canceladas_vendidas['data_ultima_alteracao_situacao'],
            errors='coerce'
        )

        df_sem_canceladas_vendidas['tempo_excedido'] = df_sem_canceladas_vendidas.apply(check_time_limit, axis=1)
        df_sem_canceladas_vendidas['dias_na_situacao'] = (
            pd.Timestamp.now() - df_sem_canceladas_vendidas['data_ultima_alteracao_situacao']
        ).dt.days
        df_sem_canceladas_vendidas['dias_na_situacao'] = df_sem_canceladas_vendidas['dias_na_situacao'].fillna(0).astype(int)

        tempo_medio = (
            df_sem_canceladas_vendidas.groupby('situacao', dropna=False)['dias_na_situacao']
            .mean()
            .round(0)
            .reset_index()
        )
        tempo_medio.columns = ['Situação', 'Tempo Médio']
        tempo_medio['Tempo Médio'] = tempo_medio['Tempo Médio'].fillna(0).astype(int)

        fora_prazo_por_situacao = (
            df_sem_canceladas_vendidas[df_sem_canceladas_vendidas['tempo_excedido']]
            .groupby('situacao')['tempo_excedido']
            .count()
            .reset_index()
        )
        fora_prazo_por_situacao.columns = ['Situação', 'Fora do Prazo']

        reservas_por_situacao = pd.merge(quantidade_por_situacao, fora_prazo_por_situacao, on='Situação', how='left')
        reservas_por_situacao = pd.merge(reservas_por_situacao, tempo_medio, on='Situação', how='left')
        reservas_por_situacao['Fora do Prazo'] = reservas_por_situacao['Fora do Prazo'].fillna(0).astype(int)
        reservas_por_situacao['Tempo Médio'] = reservas_por_situacao['Tempo Médio'].fillna(0).astype(int)

        reservas_por_situacao['Fora do Prazo'] = reservas_por_situacao.apply(
            lambda row: min(row['Fora do Prazo'], row['Quantidade']),
            axis=1
        )

        reservas_por_situacao['Dentro do Prazo'] = reservas_por_situacao['Quantidade'] - reservas_por_situacao['Fora do Prazo']

        # Reordenar as colunas mantendo os nomes originais exatos
        reservas_por_situacao = reservas_por_situacao[['Situação', 'Quantidade', 'Fora do Prazo', 'Tempo Médio', 'Dentro do Prazo']]

        # Adicionar linha de totais
        totais = pd.DataFrame([{
            'Situação': 'Total',
            'Quantidade': reservas_por_situacao['Quantidade'].sum(),
            'Fora do Prazo': reservas_por_situacao['Fora do Prazo'].sum(),
            'Tempo Médio': round(reservas_por_situacao['Tempo Médio'].mean()) if not reservas_por_situacao.empty else 0,
            'Dentro do Prazo': reservas_por_situacao['Dentro do Prazo'].sum()
        }])

        reservas_por_situacao = pd.concat([reservas_por_situacao, totais], ignore_index=True)

        st.table(reservas_por_situacao)

        # Funil de Reservas por Situação
        try:
            import plotly.graph_objects as go
            funnel_df = reservas_por_situacao[reservas_por_situacao['Situação'] != 'Total']
            if not funnel_df.empty:
                fig = go.Figure(go.Funnel(
                    y=funnel_df['Situação'],
                    x=funnel_df['Quantidade'],
                    textinfo="value+percent initial"
                ))
                fig.update_layout(
                    title="Funil de Reservas por Situação",
                    height=500
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sem dados suficientes para montar o funil com os filtros selecionados.")
        except Exception as e:
            st.warning(f"Não foi possível renderizar o funil: {str(e)}")

    st.divider()

    # Reservas por Empreendimento
    st.subheader("Reservas Por Empreendimento")

    if df_sem_canceladas_vendidas.empty:
        st.info("Nenhuma reserva ativa disponível para exibição por empreendimento.")
    else:
        quantidade_por_empreendimento = (
            df_sem_canceladas_vendidas['empreendimento']
            .value_counts()
            .rename_axis('Empreendimento')
            .reset_index(name='Quantidade')
        )

        fora_prazo_por_empreendimento = (
            df_sem_canceladas_vendidas[df_sem_canceladas_vendidas['tempo_excedido']]
            .groupby('empreendimento')['tempo_excedido']
            .count()
            .reset_index()
        )
        fora_prazo_por_empreendimento.columns = ['Empreendimento', 'Fora do Prazo']

        tempo_medio_empreendimento = (
            df_sem_canceladas_vendidas.groupby('empreendimento')['dias_na_situacao']
            .mean()
            .round(0)
            .reset_index()
        )
        tempo_medio_empreendimento.columns = ['Empreendimento', 'Tempo Médio']
        tempo_medio_empreendimento['Tempo Médio'] = tempo_medio_empreendimento['Tempo Médio'].fillna(0).astype(int)

        reservas_por_empreendimento = pd.merge(quantidade_por_empreendimento, fora_prazo_por_empreendimento, on='Empreendimento', how='left')
        reservas_por_empreendimento = pd.merge(reservas_por_empreendimento, tempo_medio_empreendimento, on='Empreendimento', how='left')
        reservas_por_empreendimento['Fora do Prazo'] = reservas_por_empreendimento['Fora do Prazo'].fillna(0).astype(int)
        reservas_por_empreendimento['Tempo Médio'] = reservas_por_empreendimento['Tempo Médio'].fillna(0).astype(int)

        # Garantir que "Fora do Prazo" não seja maior que "Quantidade"
        reservas_por_empreendimento['Fora do Prazo'] = reservas_por_empreendimento.apply(
            lambda row: min(row['Fora do Prazo'], row['Quantidade']), 
            axis=1
        )

        # Calcular "Dentro do Prazo"
        reservas_por_empreendimento['Dentro do Prazo'] = reservas_por_empreendimento['Quantidade'] - reservas_por_empreendimento['Fora do Prazo']

        # Reordenar as colunas mantendo os nomes originais exatos
        reservas_por_empreendimento = reservas_por_empreendimento[['Empreendimento', 'Quantidade', 'Fora do Prazo', 'Tempo Médio', 'Dentro do Prazo']]

        # Adicionar linha de totais
        totais_empreendimento = pd.DataFrame([{
            'Empreendimento': 'Total',
            'Quantidade': reservas_por_empreendimento['Quantidade'].sum(),
            'Fora do Prazo': reservas_por_empreendimento['Fora do Prazo'].sum(),
            'Tempo Médio': round(reservas_por_empreendimento['Tempo Médio'].mean()) if not reservas_por_empreendimento.empty else 0,
            'Dentro do Prazo': reservas_por_empreendimento['Dentro do Prazo'].sum()
        }])

        reservas_por_empreendimento = pd.concat([reservas_por_empreendimento, totais_empreendimento], ignore_index=True)

        st.table(reservas_por_empreendimento)

# =============================================================================
# NOVA TABELA: CONVERSÃO DE RESERVAS EM VENDAS
# =============================================================================

st.subheader("📊 Conversão de Reservas em Vendas")

# Caixa de informação sobre filtros e observações
st.info("""
📋 **Informações Importantes:**

• **Filtro Próprio:** Esta tabela possui filtros específicos localizados na barra lateral (sidebar) 
  sob a seção "📊 Filtros Conversão"

• ⚠️ **Importante:** Os números podem variar conforme o fechamento das vendas, pois a análise considera a data de cadastro (data_cad) da reserva. Uma venda pode ser cadastrada em um período e efetivada posteriormente, mas será contabilizada conforme a data de cadastro.

• 📌 **Total de Reservas:** A coluna contabiliza todas as situações registradas, incluindo reservas canceladas.
""")

# Dica sobre ordenação
st.write("💡 **Dica:** A primeira coluna (índice) ordena automaticamente pelo número de reservas do maior para o menor.")

try:
    # Carregar dados de reservas para análise de conversão
    conn = get_motherduck_connection()
    
    # Converter datas para string no formato correto
    data_inicial_str = data_inicial_conversao.strftime('%Y-%m-%d')
    data_final_str = data_final_conversao.strftime('%Y-%m-%d')
    
    # Query para buscar dados de reservas com filtro por data_cad
    conversao_df = conn.sql("""
        SELECT 
            corretor,
            situacao,
            data_cad,
            empreendimento
        FROM reservas.main.reservas_abril
        WHERE data_cad IS NOT NULL
        AND corretor IS NOT NULL
        AND corretor != ''
        AND CAST(data_cad AS DATE) >= CAST(? AS DATE)
        AND CAST(data_cad AS DATE) <= CAST(? AS DATE)
    """, params=[data_inicial_str, data_final_str]).df()
    
    if not conversao_df.empty:
        # Remover situação "Mútuo" do conjunto da tabela de conversão
        conversao_df = conversao_df[conversao_df['situacao'].astype(str).str.strip().str.upper() != 'MÚTUO']

        # Aplicar filtros gerais (exceto data, que já é dedicada)
        if empreendimento_selecionado != "Todos":
            conversao_df = conversao_df[conversao_df['empreendimento'] == empreendimento_selecionado]

        if conversao_df.empty:
            st.warning("⚠️ Nenhum dado de reservas encontrado com os filtros selecionados.")
        else:
            # Converter data_cad para datetime
            conversao_df['data_cad'] = pd.to_datetime(conversao_df['data_cad'], errors='coerce')
            
            # Calcular métricas por corretor
            conversao_por_corretor = []
            
            for corretor in conversao_df['corretor'].unique():
                df_corretor = conversao_df[conversao_df['corretor'] == corretor]
                
                # Total de reservas
                total_reservas = len(df_corretor)
                
                # Reservas convertidas (Distrato, Mútuo, Vendida)
                situacoes_convertidas = ['Distrato', 'Mútuo', 'Vendida']
                reservas_convertidas = len(df_corretor[df_corretor['situacao'].isin(situacoes_convertidas)])
                
                # Calcular taxa de conversão
                taxa_conversao = (reservas_convertidas / total_reservas * 100) if total_reservas > 0 else 0
                
                conversao_por_corretor.append({
                    'Corretor': corretor,
                    'Total Reservas': total_reservas,
                    'Reservas Convertidas': reservas_convertidas,
                    'Taxa Conversão (%)': round(taxa_conversao, 2)
                })
            
            # Converter para DataFrame
            conversao_df_final = pd.DataFrame(conversao_por_corretor)
            
            if conversao_df_final.empty:
                st.warning("⚠️ Nenhum dado de reservas encontrado para análise de conversão.")
            else:
                # Ordenar por número de reservas (maior para menor)
                conversao_df_final = conversao_df_final.sort_values('Total Reservas', ascending=False)
                
                # Adicionar linha de totais
                totais_conversao = pd.DataFrame([{
                    'Corretor': 'Total',
                    'Total Reservas': conversao_df_final['Total Reservas'].sum(),
                    'Reservas Convertidas': conversao_df_final['Reservas Convertidas'].sum(),
                    'Taxa Conversão (%)': round(
                        (conversao_df_final['Reservas Convertidas'].sum() / 
                         conversao_df_final['Total Reservas'].sum() * 100) 
                        if conversao_df_final['Total Reservas'].sum() > 0 else 0, 2
                    )
                }])
                
                conversao_df_final = pd.concat([conversao_df_final, totais_conversao], ignore_index=True)
                
                # Exibir tabela
                st.dataframe(conversao_df_final, use_container_width=True)
        
    else:
        st.warning("⚠️ Nenhum dado de reservas encontrado para análise de conversão.")
        
except Exception as e:
    st.error(f"❌ Erro ao carregar dados de conversão: {str(e)}")

# Página Home simplificada - apenas os quadros principais