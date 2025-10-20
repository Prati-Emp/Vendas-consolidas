import streamlit as st

# Configuração da página
st.set_page_config(page_title="Imobiliária", layout="wide")

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from utils import display_navigation

# Display navigation bar (includes logo)
display_navigation()

# Store current page in session state
st.session_state['current_page'] = __file__

import pandas as pd
from datetime import datetime
import re
import requests
import locale
import duckdb
from dotenv import load_dotenv
import os
import plotly.express as px

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

# MotherDuck connection
@st.cache_resource
def get_motherduck_connection():
    """Create a cached connection to MotherDuck"""
    try:
        token = os.getenv('MOTHERDUCK_TOKEN')
        if not token:
            raise ValueError("MOTHERDUCK_TOKEN não encontrado nas variáveis de ambiente")
        
        # Sanitize o token
        token = token.strip().strip('"').strip("'")
        
        # Conectar diretamente ao MotherDuck com o token na URL (formato para conta free)
        connection_string = f'motherduck:reservas?motherduck_token={token}'
        
        try:
            conn = duckdb.connect(connection_string)
            return conn
        except Exception as e:
            st.error(f"Erro na conexão com MotherDuck: {str(e)}")
            raise
    except Exception as e:
        st.error(f"Erro ao configurar conexão: {str(e)}")
        raise

# Carregando os dados
@st.cache_data
def load_data():
    conn = get_motherduck_connection()
    reservas_df = conn.sql("""
        SELECT *
        FROM reservas.main.reservas_abril
    """).df()
    
    # Converter colunas de data
    reservas_df['data_cad'] = pd.to_datetime(reservas_df['data_cad'])
    reservas_df['data_ultima_alteracao_situacao'] = pd.to_datetime(reservas_df['data_ultima_alteracao_situacao'])
    
    return reservas_df

# Título do aplicativo
st.title("🏢 Imobiliária")

# Carregar e processar dados
reservas_df = load_data()

# Sidebar para filtros
st.sidebar.header("Filtros")

# Filtro de data
data_inicio = st.sidebar.date_input(
    "Data Inicial",
    value=pd.Timestamp('2025-04-01'),
    min_value=min(reservas_df['data_cad'].dt.date),
    max_value=max(reservas_df['data_cad'].dt.date),
    key="data_inicio_filter"
)
data_fim = st.sidebar.date_input(
    "Data Final",
    value=max(reservas_df['data_cad'].dt.date),
    min_value=min(reservas_df['data_cad'].dt.date),
    max_value=max(reservas_df['data_cad'].dt.date),
    key="data_fim_filter"
)

# Filtro de imobiliária ordenado por vendas totais
vendas_por_imobiliaria = reservas_df[reservas_df['situacao'] == 'Vendida'].groupby('imobiliaria')['idreserva'].count().reset_index()
vendas_por_imobiliaria.columns = ['imobiliaria', 'total_vendas']
vendas_por_imobiliaria = vendas_por_imobiliaria.sort_values('total_vendas', ascending=False)

# Obter lista ordenada de imobiliárias por vendas
imobiliarias = vendas_por_imobiliaria['imobiliaria'].tolist()

# Adicionar imobiliárias sem vendas no período ao final da lista
todas_imobiliarias = set(reservas_df['imobiliaria'].unique())
imobiliarias.extend([i for i in todas_imobiliarias if i not in imobiliarias])

# Preparar lista de opções com destaque para Prati e mostrar contagem de vendas
options = ["Todas"] + imobiliarias
formatted_options = [
    f"{opt} ({vendas_por_imobiliaria[vendas_por_imobiliaria['imobiliaria'] == opt]['total_vendas'].iloc[0] if opt in vendas_por_imobiliaria['imobiliaria'].values else 0})" 
    if opt != "Todas" else opt for opt in options
]
formatted_options = [
    f"💠 {opt}" if "PRATI EMPREENDIMENTOS" in str(opt).upper() else opt 
    for opt in formatted_options
]
option_to_display = dict(zip(options, formatted_options))
imobiliaria_selecionada = st.sidebar.selectbox(
    "Imobiliária", 
    options,
    format_func=lambda x: option_to_display[x],
    key="imobiliaria_filter"
)

# Filtro de empreendimento
empreendimentos = sorted(reservas_df['empreendimento'].unique())
empreendimento_selecionado = st.sidebar.selectbox("Empreendimento", ["Todos"] + list(empreendimentos), key="empreendimento_filter")

# Aplicar todos os filtros
mask = (reservas_df['data_cad'].dt.date >= data_inicio) & (reservas_df['data_cad'].dt.date <= data_fim)
df_filtrado = reservas_df[mask].copy()

if empreendimento_selecionado != "Todos":
    df_filtrado = df_filtrado[df_filtrado['empreendimento'] == empreendimento_selecionado]
if imobiliaria_selecionada != "Todas":
    df_filtrado = df_filtrado[df_filtrado['imobiliaria'] == imobiliaria_selecionada]

# Remover reservas canceladas e vendidas
df_sem_canceladas_vendidas = df_filtrado[~df_filtrado['situacao'].isin(['Cancelada', 'Vendida', 'Distrato'])]

# Métricas principais
col1, col2 = st.columns(2)

# Coluna da esquerda - Métricas totais
with col1:
    total_reservas = len(df_sem_canceladas_vendidas)
    valor_total = df_sem_canceladas_vendidas['valor_contrato'].sum()
    st.metric(label="Total de Reservas", value=int(total_reservas), help="Total de reservas ativas")
    st.metric(label="Valor Total", value=format_currency(valor_total))

# Coluna da direita - Métricas Prati
with col2:
    reservas_prati = df_sem_canceladas_vendidas[df_sem_canceladas_vendidas['imobiliaria'].str.strip().str.upper() == 'PRATI EMPREENDIMENTOS']
    total_prati = len(reservas_prati)
    valor_prati = reservas_prati['valor_contrato'].sum()
    st.metric(label="Reservas Prati", value=int(total_prati), help="Total de reservas da Prati")
    st.metric(label="Valor Prati", value=format_currency(valor_prati))

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
        
    # Pega a data da última alteração
    data_ultima_alteracao = pd.to_datetime(row['data_ultima_alteracao_situacao'])
    
    # Calcula a diferença entre agora e a última alteração em dias
    dias_decorridos = (datetime.now() - data_ultima_alteracao).days
    
    # Verifica se o tempo desde a última alteração excede o limite
    return dias_decorridos >= dias_limite

# Verificar reservas fora do prazo
df_sem_canceladas_vendidas['fora_do_prazo'] = df_sem_canceladas_vendidas.apply(check_time_limit, axis=1)
df_sem_canceladas_vendidas['dias_na_situacao'] = (datetime.now() - df_sem_canceladas_vendidas['data_ultima_alteracao_situacao']).dt.days

analise_imobiliaria = df_sem_canceladas_vendidas.groupby('imobiliaria').agg({
    'idreserva': 'count',
    'fora_do_prazo': 'sum',
    'valor_contrato': 'sum',
    'dias_na_situacao': 'mean'
}).reset_index()

analise_imobiliaria.columns = ['Imobiliária', 'Total Reservas', 'Fora do Prazo', 'Valor Total', 'Média de Dias']
analise_imobiliaria['Média de Dias'] = analise_imobiliaria['Média de Dias'].round(1)
analise_imobiliaria['Valor Total'] = analise_imobiliaria['Valor Total'].apply(format_currency)

# Análise comparativa Prati vs Outras Imobiliárias
st.subheader("Comparativo Prati vs Outras Imobiliárias")

# Definir ordem do funil de vendas
ordem_situacoes = [
    'Reserva (7)',
    'Crédito (CEF) (3)',
    'Negociação (5)',
    'Mútuo',
    'Análise Diretoria',
    'Contrato - Elaboração',
    'Contrato - Assinatura',
    'Vendida',
    'Distrato'
]

# Separar dados Prati e outras imobiliárias
df_prati = df_sem_canceladas_vendidas[df_sem_canceladas_vendidas['imobiliaria'].str.strip().str.upper() == 'PRATI EMPREENDIMENTOS']
df_outras = df_sem_canceladas_vendidas[df_sem_canceladas_vendidas['imobiliaria'].str.strip().str.upper() != 'PRATI EMPREENDIMENTOS']

# Análise por situação para cada grupo
analise_situacao_prati = df_prati.groupby('situacao')['idreserva'].count().reset_index()
analise_situacao_outras = df_outras.groupby('situacao')['idreserva'].count().reset_index()

# Renomear colunas
analise_situacao_prati.columns = ['Situação', 'Prati']
analise_situacao_outras.columns = ['Situação', 'Outras']

# Mesclar os dataframes
analise_comparativa = pd.merge(analise_situacao_prati, analise_situacao_outras, on='Situação', how='outer').fillna(0)
analise_comparativa = analise_comparativa.astype({'Prati': int, 'Outras': int})

# Criar mapeamento para ordem
ordem_mapping = {situacao: idx for idx, situacao in enumerate(ordem_situacoes)}

# Adicionar coluna de ordem e ordenar
analise_comparativa['ordem'] = analise_comparativa['Situação'].map(ordem_mapping)
analise_comparativa = analise_comparativa.sort_values('ordem').drop('ordem', axis=1)

# Exibir tabela comparativa
st.table(analise_comparativa)

st.divider()

# Análise por Imobiliária
st.subheader("Análise por Imobiliária")

# Exibir tabela de análise por imobiliária
st.table(analise_imobiliaria)

st.divider()

# Criar duas colunas para os gráficos
col_valor, col_qtd = st.columns(2)



with col_valor:
    st.subheader("Distribuição de Valores por Imobiliária")
    # Dados para o gráfico de valores
    chart_data_valor = df_sem_canceladas_vendidas.groupby('imobiliaria')['valor_contrato'].sum().reset_index()
    chart_data_valor.columns = ['Imobiliária', 'Valor']
    chart_data_valor = chart_data_valor.sort_values('Valor', ascending=False)
    chart_data_valor['Valor_Formatado'] = chart_data_valor['Valor'].apply(format_currency)

    # Criar gráfico de valores com Plotly
    fig_valor = px.bar(chart_data_valor, 
                x='Valor', 
                y='Imobiliária',
                orientation='h',
                text='Valor_Formatado')    # Customizar o layout do gráfico de valores
    fig_valor.update_layout(
        height=600,
        margin=dict(l=20, r=150, t=30, b=20),  # Aumentar margem direita para os valores
        xaxis_title="Valor Total em R$",
        yaxis_title="",
        yaxis={
            'categoryorder':'total ascending',
            'tickfont': {'size': 10}  # Reduzir tamanho da fonte dos nomes
        },
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False
    )

    # Customizar as barras do gráfico de valores
    fig_valor.update_traces(
        textposition='outside',
        marker_color='#1f77b4',
        textfont=dict(size=11),  # Tamanho da fonte dos valores
        cliponaxis=False  # Evitar que o texto seja cortado
    )

    # Exibir o gráfico de valores
    st.plotly_chart(fig_valor, use_container_width=True)

with col_qtd:
    st.subheader("Distribuição de Reservas por Imobiliária")
    # Dados para o gráfico de quantidades
    chart_data_qtd = df_sem_canceladas_vendidas.groupby('imobiliaria')['idreserva'].count().reset_index()
    chart_data_qtd.columns = ['Imobiliária', 'Quantidade']
    chart_data_qtd = chart_data_qtd.sort_values('Quantidade', ascending=False)

    # Criar gráfico de quantidades com Plotly
    fig_qtd = px.bar(chart_data_qtd, 
                x='Quantidade', 
                y='Imobiliária',
                orientation='h',
                text='Quantidade')    # Customizar o layout do gráfico de quantidades
    fig_qtd.update_layout(
        height=600,
        margin=dict(l=20, r=150, t=30, b=20),  # Aumentar margem direita para os números
        xaxis_title="Quantidade de Reservas",
        yaxis_title="",
        yaxis={
            'categoryorder':'total ascending',
            'tickfont': {'size': 10}  # Reduzir tamanho da fonte dos nomes
        },
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False
    )

    # Customizar as barras do gráfico de quantidades
    fig_qtd.update_traces(
        textposition='outside',
        marker_color='#2ca02c',  # Cor verde para diferenciar do gráfico de valores
        textfont=dict(size=11),  # Tamanho da fonte dos valores
        cliponaxis=False  # Evitar que o texto seja cortado
    )

    # Exibir o gráfico de quantidades
    st.plotly_chart(fig_qtd, use_container_width=True)
