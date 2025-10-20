import streamlit as st
import os

# Função para obter o caminho absoluto da logo
def get_logo_path():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, "logo.png")

# Configuração da página
st.set_page_config(page_title="Relatório de Reservas", layout="wide")

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

# def hide_sidebar():
#     st.markdown("""
#     <style>
#         [data-testid="stSidebar"] {
#             display: none;
#         }
#         .stTextInput > div > div > input {
#             width: 200px !important;
#         }
#         .small-font {
#             font-size: 14px !important;
#             font-weight: normal !important;
#             text-align: center !important;
#         }
#         div[data-testid="stImage"] {
#             display: flex;
#             justify-content: center;
#         }
#         div.stButton > button {
#             width: 200px;
#             margin: 0 auto;
#             display: block;
#         }
#         div[data-testid="column"] {
#             display: flex;
#             flex-direction: column;
#             align-items: center;
#             justify-content: center;
#         }
#     </style>
#     """, unsafe_allow_html=True)

# # Função para verificar senha
# def check_password():
#     """Returns `True` if the user had the correct password."""
    
#     if "password_correct" not in st.session_state:
#         # First run, hide sidebar and show password input
#         hide_sidebar()
        
#         col1, col2, col3 = st.columns([1, 1, 1])
#         with col2:
#             # Logo centralizada usando arquivo local
#             st.image(get_logo_path(), width=400)
#             st.markdown("<br>", unsafe_allow_html=True)
            
#             # Campo de senha com label menor e centralizado
#             st.markdown('<p class="small-font">Por favor, digite a senha para acessar o dashboard:</p>', unsafe_allow_html=True)
#             password = st.text_input(
#                 "",
#                 type="password",
#                 key="password",
#                 label_visibility="collapsed"
#             )
            
#             # Botão de entrar
#             if st.button("Entrar"):
#                 if password == "prati2025":
#                     st.session_state["password_correct"] = True
#                     st.rerun()
#                 else:
#                     st.error("😕 Senha incorreta")
#         return False
    
#     return st.session_state.get("password_correct", False)

# # Verifica a senha antes de mostrar qualquer conteúdo
# if not check_password():
#     st.stop()  # Não mostra nada além deste ponto se a senha estiver errada

# # Se chegou aqui, a senha está correta
# Título do aplicativo
st.title("📊 Relatório De Reservas")

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
    data_ultima_alteracao = pd.to_datetime(row['data_ultima_alteracao_situacao'])
    
    # Calcula a diferença entre agora e a última alteração em dias
    dias_decorridos = (datetime.now() - data_ultima_alteracao).days
    
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

# Aplicar filtros
mask = (reservas_df['data_cad'].dt.date >= data_inicio) & (reservas_df['data_cad'].dt.date <= data_fim)
if empreendimento_selecionado != "Todos":
    mask = mask & (reservas_df['empreendimento'] == empreendimento_selecionado)
if situacao_selecionada != "Todas":
    mask = mask & (reservas_df['situacao'] == situacao_selecionada)

df_filtrado = reservas_df[mask]

# Métricas principais
df_sem_canceladas_vendidas = df_filtrado[~df_filtrado['situacao'].isin(['Cancelada', 'Vendida', 'Distrato'])]

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

# Contar reservas por situação do df_filtrado
quantidade_por_situacao = df_filtrado[~df_filtrado['situacao'].isin(['Cancelada', 'Distrato', 'Vendida'])]['situacao'].value_counts().reset_index()
quantidade_por_situacao.columns = ['Situação', 'Quantidade']

# Criar mapeamento para ordem
ordem_mapping = {situacao: idx for idx, situacao in enumerate(ordem_situacoes)}
quantidade_por_situacao['ordem'] = quantidade_por_situacao['Situação'].map(ordem_mapping)
quantidade_por_situacao = quantidade_por_situacao.sort_values('ordem').drop('ordem', axis=1)

# Verificar fora do prazo diretamente na tabela de reservas
df_sem_canceladas_vendidas = df_filtrado[~df_filtrado['situacao'].isin(['Cancelada', 'Vendida'])]
df_sem_canceladas_vendidas['tempo_excedido'] = df_sem_canceladas_vendidas.apply(check_time_limit, axis=1)
df_sem_canceladas_vendidas['dias_na_situacao'] = (datetime.now() - df_sem_canceladas_vendidas['data_ultima_alteracao_situacao']).dt.days

# Calcular tempo médio por situação
tempo_medio = df_sem_canceladas_vendidas.groupby('situacao')['dias_na_situacao'].mean().round(0).astype(int).reset_index()
tempo_medio.columns = ['Situação', 'Tempo Médio']

# Contar fora do prazo por situação
fora_prazo_por_situacao = df_sem_canceladas_vendidas[df_sem_canceladas_vendidas['tempo_excedido']].groupby('situacao')['tempo_excedido'].count().reset_index()
fora_prazo_por_situacao.columns = ['Situação', 'Fora do Prazo']

# Juntar as informações
reservas_por_situacao = pd.merge(quantidade_por_situacao, fora_prazo_por_situacao, on='Situação', how='left')
reservas_por_situacao = pd.merge(reservas_por_situacao, tempo_medio, on='Situação', how='left')
reservas_por_situacao['Fora do Prazo'] = reservas_por_situacao['Fora do Prazo'].fillna(0).astype(int)
reservas_por_situacao['Tempo Médio'] = reservas_por_situacao['Tempo Médio'].fillna(0).astype(int)

# Garantir que "Fora do Prazo" não seja maior que "Quantidade"
reservas_por_situacao['Fora do Prazo'] = reservas_por_situacao.apply(
    lambda row: min(row['Fora do Prazo'], row['Quantidade']), 
    axis=1
)

# Calcular "Dentro do Prazo"
reservas_por_situacao['Dentro do Prazo'] = reservas_por_situacao['Quantidade'] - reservas_por_situacao['Fora do Prazo']


# Reordenar as colunas mantendo os nomes originais exatos
reservas_por_situacao = reservas_por_situacao[['Situação', 'Quantidade', 'Fora do Prazo', 'Tempo Médio', 'Dentro do Prazo']]

# Adicionar linha de totais
totais = pd.DataFrame([{
    'Situação': 'Total',
    'Quantidade': reservas_por_situacao['Quantidade'].sum(),
    'Fora do Prazo': reservas_por_situacao['Fora do Prazo'].sum(),
    'Tempo Médio': round(reservas_por_situacao['Tempo Médio'].mean()),
    'Dentro do Prazo': reservas_por_situacao['Dentro do Prazo'].sum()
}])

reservas_por_situacao = pd.concat([reservas_por_situacao, totais], ignore_index=True)

st.table(reservas_por_situacao)

st.divider()

# Reservas por Empreendimento
st.subheader("Reservas Por Empreendimento")

# Contar reservas por empreendimento
quantidade_por_empreendimento = df_filtrado[~df_filtrado['situacao'].isin(['Cancelada', 'Vendida'])]['empreendimento'].value_counts().reset_index()
quantidade_por_empreendimento.columns = ['Empreendimento', 'Quantidade']

# Contar fora do prazo por empreendimento
fora_prazo_por_empreendimento = df_sem_canceladas_vendidas[df_sem_canceladas_vendidas['tempo_excedido']].groupby('empreendimento')['tempo_excedido'].count().reset_index()
fora_prazo_por_empreendimento.columns = ['Empreendimento', 'Fora do Prazo']

# Calcular tempo médio por empreendimento
tempo_medio_empreendimento = df_sem_canceladas_vendidas.groupby('empreendimento')['dias_na_situacao'].mean().round(0).astype(int).reset_index()
tempo_medio_empreendimento.columns = ['Empreendimento', 'Tempo Médio']

# Juntar as informações
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
    'Tempo Médio': round(reservas_por_empreendimento['Tempo Médio'].mean()),
    'Dentro do Prazo': reservas_por_empreendimento['Dentro do Prazo'].sum()
}])

reservas_por_empreendimento = pd.concat([reservas_por_empreendimento, totais_empreendimento], ignore_index=True)

st.table(reservas_por_empreendimento)

st.divider()

# Tabela detalhada
st.subheader("Lista De Reservas")

# Calcular o tempo na situação atual
df_sem_canceladas_vendidas['tempo_na_situacao'] = (datetime.now() - pd.to_datetime(df_sem_canceladas_vendidas['data_ultima_alteracao_situacao'])).dt.days

# Verificar quais reservas estão fora do prazo
df_sem_canceladas_vendidas['fora_do_prazo'] = df_sem_canceladas_vendidas.apply(check_time_limit, axis=1)

# Função para estilizar o DataFrame
def highlight_fora_prazo(s):
    return ['color: red' if df_sem_canceladas_vendidas['fora_do_prazo'].iloc[i] else '' for i in range(len(s))]

# Preparar e exibir o DataFrame com estilo
colunas_exibir = ['idreserva', 'cliente', 'empreendimento', 'situacao', 
                'tempo_na_situacao', 'valor_contrato', 'imobiliaria']

# Formatar o valor do contrato antes de exibir
df_exibir = df_sem_canceladas_vendidas[colunas_exibir].copy()
df_exibir['valor_contrato'] = df_exibir['valor_contrato'].apply(format_currency)

# Renomear as colunas para title case
df_exibir.columns = ['Id Reserva', 'Cliente', 'Empreendimento', 'Situação', 
                   'Tempo Na Situação', 'Valor Contrato', 'Imobiliária']

st.dataframe(
    df_exibir.style.apply(highlight_fora_prazo, axis=0),
    use_container_width=True
)

st.divider()

# Análise de workflow
st.subheader("Análise De Workflow")

# Definir ordem do funil de vendas
ordem_situacoes = [
    'Reserva (7)',
    'Crédito (CEF) (3)',
    'Negociação (5)',
    'Mútuo',
    'Análise Diretoria',
    'Contrato - Elaboração',
    'Contrato - Assinatura',
   # 'Vendida',
    # 'Distrato'
]

# Criar DataFrame com a ordem correta
workflow_agregado = df_filtrado.groupby('situacao')['idreserva'].count().reset_index()
workflow_agregado.columns = ['situacao', 'quantidade']

# Criar mapeamento para ordem
ordem_mapping = {situacao: idx for idx, situacao in enumerate(ordem_situacoes)}
workflow_agregado['ordem'] = workflow_agregado['situacao'].map(ordem_mapping)

# Remover situações que não estão no mapeamento ou têm quantidade zero
workflow_agregado = workflow_agregado.dropna(subset=['ordem'])  # Remove situações que não estão no mapeamento
workflow_agregado = workflow_agregado[workflow_agregado['quantidade'] > 0]  # Remove situações com quantidade zero
workflow_agregado = workflow_agregado.sort_values('ordem').drop('ordem', axis=1)

# Criar gráfico com plotly express
import plotly.express as px

fig = px.bar(workflow_agregado, 
             x='situacao', 
             y='quantidade',
             text='quantidade',
             labels={'situacao': 'Situação', 'quantidade': 'Quantidade'},
             title='Análise do Funil de Vendas')

fig.update_layout(
    xaxis_title="Situação",
    yaxis_title="Quantidade",
    showlegend=False
)

st.plotly_chart(fig, use_container_width=True)

# Exibir tabela com os dados
st.write("Detalhamento por Situação:")
workflow_agregado.columns = ['Situação', 'Quantidade']
st.table(workflow_agregado)
