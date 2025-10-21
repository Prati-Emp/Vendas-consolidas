import streamlit as st
import duckdb
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import os
import sys
from pathlib import Path

# Adicionar o diretório pai ao path para importar auth
sys.path.append(str(Path(__file__).parent.parent))

# Importar sistema de autenticação avançado
from advanced_auth import require_auth

# Proteger com autenticação
require_auth()

from utils import display_navigation

# Display navigation bar (includes logo)
display_navigation()

# Store current page in session state
st.session_state['current_page'] = __file__

st.set_page_config(page_title="Leads Ativos - Funil de Vendas", page_icon="📊", layout="wide")

st.title("📊 Funil de Leads Ativos")

MOTHERDUCK_TOKEN = st.secrets.get("MOTHERDUCK_TOKEN", os.getenv("MOTHERDUCK_TOKEN", ""))
if not MOTHERDUCK_TOKEN:
    st.error("Token do MotherDuck não configurado. Verifique as configurações de secrets.")
    st.stop()

# Load all data with broad date range for filtering
def get_all_leads_duckdb():
    con = duckdb.connect(f"md:reservas?token={MOTHERDUCK_TOKEN}")
    query = """
    SELECT Idlead as idlead,
           Data_cad as data_cad,
           Referencia_data as referencia_data,
           Situacao as situacao_nome,
           Imobiliaria as imobiliaria,
           nome_situacao_anterior_lead,
           gestor,
           empreendimento_ultimo
    FROM cv_leads
    ORDER BY data_cad DESC
    """
    df = con.execute(query).df()
    con.close()
    return df

@st.cache_data
def load_data():
    return get_all_leads_duckdb()

leads_df = load_data()

if leads_df.empty:
    st.warning("Nenhum dado retornado do Mother Duck.")
    st.stop()

# Sidebar for filters
st.sidebar.header("Filtros")

# Imobiliaria filter
imobiliarias = sorted(leads_df['imobiliaria'].dropna().unique())
selected_imobiliaria = st.sidebar.selectbox("Imobiliária", ["Todas"] + list(imobiliarias))

# Empreendimento filter
empreendimentos = sorted(leads_df['empreendimento_ultimo'].dropna().unique())
selected_empreendimento = st.sidebar.selectbox("Empreendimento de Interesse", ["Todos"] + list(empreendimentos))

# Apply filters
filtered_df = leads_df.copy()

if selected_imobiliaria != "Todas":
    filtered_df = filtered_df[filtered_df['imobiliaria'] == selected_imobiliaria]

if selected_empreendimento != "Todos":
    filtered_df = filtered_df[filtered_df['empreendimento_ultimo'] == selected_empreendimento]

# Exclude converted leads: Descartado, Em Pré-Cadastro, Venda realizada
exclude_situations = ['descartado', 'em pré-cadastro', 'venda realizada']
filtered_df = filtered_df[~filtered_df['situacao_nome'].str.lower().str.strip().isin(exclude_situations)]

# Mapeamento do funil baseado na tabela "de" (situação atual) -> "para" (etapa), com especial para "descartado" usando anterior
mapa_funil = {
    "aguardando atendimento": "Leads",
    "qualificação": "Leads",
    "descoberta": "Leads",
    "em atendimento": "Em atendimento",
    "atendimento futuro": "Em atendimento",
    "visita agendada": "Em atendimento",
    "visita realizada": "Visita realizada",
    "atendimento pos visita": "Visita realizada",
    "atendimento pós visita": "Visita realizada",
    "pre cadastro": "Com reserva",
    "pre cadastro pos visita": "Com reserva",
    "em pré-cadastro": "Com reserva",
    "com reserva": "Com reserva",
    "venda realizada": "Venda realizada"
}

def get_funil_etapa(prev_situacao, curr_situacao):
    # Normalizar entradas
    if pd.isna(curr_situacao):
        curr_key = None
    else:
        curr_key = str(curr_situacao).strip().lower()
    
    # Caso especial: "descartado" sempre usa etapa da situação anterior
    if curr_key == "descartado":
        if pd.isna(prev_situacao):
            return "Leads"
        prev_key = str(prev_situacao).strip().lower()
        return mapa_funil.get(prev_key, "Leads")
    
    # Para outras situações, usa mapeamento da atual
    if curr_key is None:
        return "Leads"
    return mapa_funil.get(curr_key, "Leads")

filtered_df["funil_etapa"] = filtered_df.apply(lambda row: get_funil_etapa(row['nome_situacao_anterior_lead'], row['situacao_nome']), axis=1)

funil_etapas = [
    "Leads",
    "Em atendimento",
    "Visita realizada",
    "Com reserva"
]

etapa_counts = [filtered_df[filtered_df["funil_etapa"] == etapa].shape[0] for etapa in funil_etapas]

# Calcular tempo ativo (dias desde a data de cadastro até hoje)
filtered_df["data_cad"] = pd.to_datetime(filtered_df["data_cad"], errors="coerce")
now_ts = pd.Timestamp.now()
filtered_df["dias_ativo"] = (now_ts - filtered_df["data_cad"]).dt.days
# Formatar como "X dias" para exibição
filtered_df["tempo_ativo"] = filtered_df["dias_ativo"].apply(lambda d: f"{int(d)} dias" if pd.notna(d) else "-")

fig = go.Figure(go.Funnel(
    y=funil_etapas,
    x=etapa_counts,
    textinfo="value+percent initial"
))
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
# Cartão de total de leads ativos (todas as situações consideradas ativas)
total_ativos = int(filtered_df.shape[0])
col_total, col1, col2, col3, col4 = st.columns(5)

tooltip_texts = {
    "Total de leads ativos": "Soma de todas as situações ativas (exclui descartados, em pré-cadastro e venda realizada).",
    "Leads": "Total de leads na etapa inicial (excluindo descartados, em pré-cadastro e venda realizada).",
    "Em atendimento": "Leads nas situações relacionadas a atendimento (excluindo descartados, em pré-cadastro e venda realizada).",
    "Visita Realizada": "Leads que realizaram visita (excluindo descartados, em pré-cadastro e venda realizada).",
    "Com reserva": "Leads com reserva confirmada (excluindo descartados, em pré-cadastro e venda realizada)."
}

col_total.metric(label="Total de leads ativos", value=total_ativos, help=tooltip_texts['Total de leads ativos'])
col1.metric(label="Leads", value=etapa_counts[0], help=tooltip_texts['Leads'])
col2.metric(label="Em atendimento", value=etapa_counts[1], help=tooltip_texts['Em atendimento'])
col3.metric(label="Visita Realizada", value=etapa_counts[2], help=tooltip_texts['Visita Realizada'])
col4.metric(label="Com reserva", value=etapa_counts[3], help=tooltip_texts['Com reserva'])

st.markdown("---")
st.subheader("Leads ativos detalhados")
display_columns = ["idlead", "situacao_nome", "nome_situacao_anterior_lead", "funil_etapa", "gestor", "imobiliaria", "empreendimento_ultimo", "data_cad", "tempo_ativo"]
st.dataframe(
    filtered_df[display_columns].sort_values("data_cad", ascending=False),
    use_container_width=True
)
