import streamlit as st
import pandas as pd
from datetime import datetime
import re
import requests
import locale
import duckdb
import os
import sys
from pathlib import Path

# Adicionar o diretório pai ao path para importar auth
sys.path.append(str(Path(__file__).parent.parent))

# Importar sistema de autenticação avançado
try:
    from advanced_auth import require_auth, require_page_access
    
    # Proteger com autenticação
    require_auth()
    
    # Proteger acesso à página específica
    require_page_access("motivo_fora_prazo")
except ImportError as e:
    st.error(f"Erro ao importar sistema de autenticação: {e}")
    st.stop()

from utils import display_navigation

# Display navigation bar (includes logo)
display_navigation()

# Store current page in session state
st.session_state['current_page'] = __file__

st.set_page_config(page_title="Motivo Fora do Prazo", page_icon="📅", layout="wide")

# Dicionário de mapeamento de IDs de usuários para nomes
USER_ID_TO_NAME = {
    "52": "Gustavo Sordi (Gestor)",
    "69": "Giovana Ramos Fiorentini (Gestor)",
    "80": "José Aquino (Gestor)",
    "97": "Italo Peres (Gestor)",
    "91": "Luana Casarin (Gestor)",
    "100": "Vitoria Almeida (Gestor)",
    "114": "Camila Novaes (Gestor)",
    "125": "Lucas Mateus Follmann (Gestor)",
    "126": "Fernanda Tomio (Gestor)",
    "128": "Adriana Casarin (Gestor)",
    "129": "Djonathan Souza (Analista)",
    "157": "Marciane Ross (Corretor)",
    "240": "Alana Konzen (Corretor)",
    "282": "Gabriela Vettorello (Corretor)",
    "4": "Juliane Zwick (Correspondente)",
    "5": "Carine Kaiser (Correspondente)",
    "9": "Luciano Santiago (Correspondente)",
    "11": "Vanessa Gonzaga (Correspondente)",
    "12": "Gustavo Grabski (Correspondente)",
    "16": "Fabio Weinman (Correspondente)",
    "141": "Allana Heloyza Dias de Oliveira (Gestor)",
    "142": "EDUARDA VITORIA COUTINHO GALLO - Duda (Gestor)",
    "135": "Lavínia Gabrielly Fetsch - Lavínia (Gestor)",
    "407": "VINICIUS HENRIQUE CZERNIEJ (Corretor)",
}

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

# Carregar token do MotherDuck de forma segura
MOTHERDUCK_TOKEN = st.secrets.get("MOTHERDUCK_TOKEN", os.getenv("MOTHERDUCK_TOKEN", ""))
if not MOTHERDUCK_TOKEN:
    st.error("Token do MotherDuck não configurado. Verifique as configurações de secrets.")
    st.stop()

# Título do aplicativo
st.title("📅 Análise de Reservas Fora do Prazo")

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

# Carregando os dados
@st.cache_data
def load_data():
    conn = duckdb.connect(f"md:reservas?token={MOTHERDUCK_TOKEN}")
    reservas_df = conn.sql("""
        SELECT *
        FROM reservas.main.reservas_abril
    """).df()
    
    # Converter colunas de data
    reservas_df['data_cad'] = pd.to_datetime(reservas_df['data_cad'])
    reservas_df['data_ultima_alteracao_situacao'] = pd.to_datetime(reservas_df['data_ultima_alteracao_situacao'])
    
    conn.close()
    return reservas_df

reservas_df = load_data()

# Sidebar para filtros
st.sidebar.header("Filtros")

# Filtro de data
data_inicio = st.sidebar.date_input(
    "Data Inicial",
    value=pd.Timestamp('2025-01-01'),  # Data padrão definida para 01/01/2025
    min_value=min(reservas_df['data_cad'].dt.date),
    max_value=max(reservas_df['data_cad'].dt.date)
)
data_fim = st.sidebar.date_input(
    "Data Final",
    value=max(reservas_df['data_cad'].dt.date),
    min_value=min(reservas_df['data_cad'].dt.date),
    max_value=max(reservas_df['data_cad'].dt.date)
)

# Filtro de empreendimento
empreendimentos = sorted(reservas_df['empreendimento'].unique())
empreendimento_selecionado = st.sidebar.selectbox("Empreendimento", ["Todos"] + list(empreendimentos))

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
    f"💠 {opt} ({vendas_por_imobiliaria[vendas_por_imobiliaria['imobiliaria'] == opt]['total_vendas'].iloc[0] if opt in vendas_por_imobiliaria['imobiliaria'].values else 0})"
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
    format_func=lambda x: option_to_display[x]
)

# Filtro de situação
situacoes = sorted(reservas_df[~reservas_df['situacao'].isin(['Vendida', 'Distrato', 'Cancelada'])]['situacao'].unique())
situacao_selecionada = st.sidebar.selectbox("Situação", ["Todas"] + list(situacoes))

# Aplicar filtros
mask = (reservas_df['data_cad'].dt.date >= data_inicio) & (reservas_df['data_cad'].dt.date <= data_fim)
df_filtrado = reservas_df[mask].copy()

if empreendimento_selecionado != "Todos":
    df_filtrado = df_filtrado[df_filtrado['empreendimento'] == empreendimento_selecionado]
if imobiliaria_selecionada != "Todas":
    df_filtrado = df_filtrado[df_filtrado['imobiliaria'] == imobiliaria_selecionada]
if situacao_selecionada != "Todas":
    df_filtrado = df_filtrado[df_filtrado['situacao'] == situacao_selecionada]

# Remover reservas canceladas e vendidas
df_sem_canceladas_vendidas = df_filtrado[~df_filtrado['situacao'].isin(['Cancelada', 'Vendida'])]

# Verificar reservas fora do prazo
df_sem_canceladas_vendidas['fora_do_prazo'] = df_sem_canceladas_vendidas.apply(check_time_limit, axis=1)
df_sem_canceladas_vendidas['dias_na_situacao'] = (datetime.now() - df_sem_canceladas_vendidas['data_ultima_alteracao_situacao']).dt.days

# Métricas principais
col1, col2, col3 = st.columns(3)
with col1:
    total_fora_prazo = df_sem_canceladas_vendidas['fora_do_prazo'].sum()
    st.metric(label="Total Fora do Prazo", value=int(total_fora_prazo))
with col2:
    percentual_fora_prazo = (total_fora_prazo / len(df_sem_canceladas_vendidas)) * 100
    st.metric(label="Percentual Fora do Prazo", value=f"{percentual_fora_prazo:.1f}%")
with col3:
    valor_total_fora_prazo = df_sem_canceladas_vendidas[df_sem_canceladas_vendidas['fora_do_prazo']]['valor_contrato'].sum()
    st.metric(label="Valor Total Fora do Prazo", value=format_currency(valor_total_fora_prazo))

# Análise por situação
st.subheader("Análise por Situação")

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

# Calcular tempo médio para todas as reservas por situação
tempo_medio = df_sem_canceladas_vendidas.groupby('situacao')['dias_na_situacao'].mean().round(0).astype(int)

# Análise das reservas fora do prazo
analise_situacao = df_sem_canceladas_vendidas[df_sem_canceladas_vendidas['fora_do_prazo']].groupby('situacao').agg({
    'idreserva': 'count',
    'valor_contrato': 'sum'
}).reset_index()

# Adicionar tempo médio à análise
analise_situacao = analise_situacao.merge(
    tempo_medio.reset_index().rename(columns={'dias_na_situacao': 'Tempo Médio'}),
    on='situacao'
)

analise_situacao.columns = ['Situação', 'Quantidade', 'Valor Total', 'Tempo Médio']

# Criar mapeamento para ordem
ordem_mapping = {situacao: idx for idx, situacao in enumerate(ordem_situacoes)}
analise_situacao['ordem'] = analise_situacao['Situação'].map(ordem_mapping)
analise_situacao = analise_situacao.sort_values('ordem').drop('ordem', axis=1)

# Formatar valor total
analise_situacao['Valor Total'] = analise_situacao['Valor Total'].apply(format_currency)

st.table(analise_situacao)

st.divider()

# Análise por empreendimento
st.subheader("Análise por Empreendimento")

# Calcular tempo médio para todas as reservas por empreendimento
tempo_medio_emp = df_sem_canceladas_vendidas.groupby('empreendimento')['dias_na_situacao'].mean().round(0).astype(int)

# Análise das reservas fora do prazo por empreendimento
analise_empreendimento = df_sem_canceladas_vendidas[df_sem_canceladas_vendidas['fora_do_prazo']].groupby('empreendimento').agg({
    'idreserva': 'count',
    'valor_contrato': 'sum'
}).reset_index()

# Adicionar tempo médio à análise
analise_empreendimento = analise_empreendimento.merge(
    tempo_medio_emp.reset_index().rename(columns={'dias_na_situacao': 'Tempo Médio'}),
    on='empreendimento'
)

analise_empreendimento.columns = ['Empreendimento', 'Quantidade', 'Valor Total', 'Tempo Médio']
analise_empreendimento['Valor Total'] = analise_empreendimento['Valor Total'].apply(format_currency)

st.table(analise_empreendimento)

@st.cache_data
def get_reservation_messages(idreserva):
    """Busca as mensagens de uma reserva específica"""
    url = f"https://prati.cvcrm.com.br/api/v2/cv/reservas/{idreserva}/mensagens"
    headers = {
        "accept": "application/json",
        "email": "djonathan.souza@grupoprati.com",
        "token": "394f594bc6192c86d94f329355ae13ca0b78a2a9",
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        messages = response.json().get("dados", [])
        return messages
    except Exception as e:
        st.error(f"Erro ao buscar mensagens da reserva {idreserva}: {str(e)}")
        return []

st.divider()

# Lista detalhada de reservas fora do prazo em formato de cards
st.subheader("Cards de Reservas Fora do Prazo")
df_fora_prazo = df_sem_canceladas_vendidas[df_sem_canceladas_vendidas['fora_do_prazo']]

# Criar colunas para os cards (3 cards por linha)
for i in range(0, len(df_fora_prazo), 3):
    cols = st.columns([1, 1, 1])  # Equal width columns
    for j in range(3):
        if i + j < len(df_fora_prazo):
            row = df_fora_prazo.iloc[i + j]
            messages = get_reservation_messages(int(row['idreserva']))
            
            with cols[j]:
                st.markdown(f"""
                    <div style="
                        padding: 1.2rem;
                        border-radius: 10px;
                        border: 1px solid #e5e7eb;
                        margin: 0.5rem 0;
                        background-color: white;
                        color: black;
                        height: 100%;
                        box-shadow: 0 1px 3px rgba(0,0,0,0.12);
                    ">
                        <h4 style="color: #000000; margin-top: 0; margin-bottom: 1rem; font-weight: 600;">Reserva #{int(row['idreserva'])}</h4>
                        <p style="color: #000000; margin: 0.5rem 0;"><strong style="color: #000000; font-weight: 600;">Cliente:</strong> {row['cliente']}</p>
                        <p style="color: #000000; margin: 0.5rem 0;"><strong style="color: #000000; font-weight: 600;">Empreendimento:</strong> {row['empreendimento']}</p>
                        <p style="color: #000000; margin: 0.5rem 0;"><strong style="color: #000000; font-weight: 600;">Situação:</strong> {row['situacao']}</p>
                        <p style="color: #000000; margin: 0.5rem 0;"><strong style="color: #000000; font-weight: 600;">Dias na Situação:</strong> {row['dias_na_situacao']}</p>
                        <p style="color: #000000; margin: 0.5rem 0;"><strong style="color: #000000; font-weight: 600;">Valor:</strong> {format_currency(row['valor_contrato'])}</p>
                        <p style="color: #000000; margin: 0.5rem 0;"><strong style="color: #000000; font-weight: 600;">Imobiliária:</strong> {row['imobiliaria']}</p>
                    </div>
                """, unsafe_allow_html=True)
                
                if messages:
                    with st.expander("Ver Mensagens"):
                        for msg in messages:
                            # Try each user ID field in order
                            user_id = None
                            
                            # Check idusuario first
                            if msg.get('idusuario') is not None:
                                user_id = str(msg.get('idusuario'))
                            # Then check idusuarioImobiliaria
                            elif msg.get('idusuarioImobiliaria') is not None:
                                user_id = str(msg.get('idusuarioImobiliaria'))
                            # Then check idcorretor
                            elif msg.get('idcorretor') is not None:
                                user_id = str(msg.get('idcorretor'))
                            # Finally check idusuarioCorrespondente
                            elif msg.get('idusuarioCorrespondente') is not None:
                                user_id = str(msg.get('idusuarioCorrespondente'))
                            
                            # If we found a user ID, try to map it, otherwise use default name
                            if user_id and user_id in USER_ID_TO_NAME:
                                user_name = USER_ID_TO_NAME[user_id]
                            else:
                                user_name = msg.get('usuario_nome', 'N/A')
                              # Formatar a data
                            data_mensagem = msg.get('dataCad', 'N/A')
                            if data_mensagem != 'N/A':
                                try:
                                    # Converter a string para datetime e depois formatar
                                    data_formatada = datetime.strptime(data_mensagem, '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y')
                                except:
                                    data_formatada = data_mensagem
                            else:
                                data_formatada = data_mensagem

                            st.markdown(f"""
                                <div style="
                                    padding: 0.8rem;
                                    border-radius: 8px;
                                    border: 1px solid #e5e7eb;
                                    margin: 0.5rem 0;
                                    background-color: #f9fafb;
                                    color: #000000;
                                ">
                                    <p style="color: #000000; margin: 0.2rem 0;"><strong style="color: #000000;">Data:</strong> <span style="color: #000000;">{data_formatada}</span></p>
                                    <p style="color: #000000; margin: 0.2rem 0;"><strong style="color: #000000;">Usuário:</strong> <span style="color: #000000;">{user_name}</span></p>
                                    <p style="color: #000000; margin: 0.2rem 0;"><strong style="color: #000000;">Mensagem:</strong> <span style="color: #000000;">{msg.get('mensagem', 'N/A')}</span></p>
                                </div>
                            """, unsafe_allow_html=True)
                else:
                    with st.expander("Ver Mensagens"):
                        st.info("Não há mensagens para esta reserva.")
