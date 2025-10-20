import streamlit as st
import duckdb
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import os

from utils import display_navigation

# Display navigation bar (includes logo)
display_navigation()

# Store current page in session state
st.session_state['current_page'] = __file__

st.set_page_config(page_title="Leads - Funil de Vendas", page_icon="📊", layout="wide")

st.title("📊 Funil de Leads")

# Carregar token do MotherDuck de forma segura
MOTHERDUCK_TOKEN = st.secrets.get("MOTHERDUCK_TOKEN", os.getenv("MOTHERDUCK_TOKEN", ""))
if not MOTHERDUCK_TOKEN:
    st.error("Token do MotherDuck não configurado. Verifique as configurações de secrets.")
    st.stop()

# Load all data with broad date range for filtering
def get_all_leads_duckdb():
    con = duckdb.connect(f"md:reservas?token={MOTHERDUCK_TOKEN}")
    query = """
    SELECT 
        Idlead as idlead,
        Data_cad as data_cad,
        Referencia_data as referencia_data,
        Situacao as situacao_nome,
        Imobiliaria as imobiliaria,
        COALESCE(NULLIF(TRIM(Corretor), ''), '—') AS corretor,
        COALESCE(NULLIF(TRIM(Midia_original), ''), '—') AS midia_original,
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

# Date filters stacked vertically (using data_cad)
data_inicio = st.sidebar.date_input("Data Inicial", value=datetime(2022, 4, 13).date())
data_fim = st.sidebar.date_input("Data Final", value=datetime.now().date())

# Empreendimento filter
empreendimentos = sorted(leads_df['empreendimento_ultimo'].dropna().unique())
selected_empreendimento = st.sidebar.selectbox("Empreendimento de Interesse", ["Todos"] + list(empreendimentos))

# Mídia filter (baseado em midia_original)
if 'midia_original' in leads_df.columns:
    # Primeiro aplicar filtros de data para obter mídias disponíveis no período
    leads_periodo = leads_df[
        (leads_df['data_cad'].dt.date >= data_inicio) &
        (leads_df['data_cad'].dt.date <= data_fim)
    ]
    midias = sorted(leads_periodo.get('midia_original', pd.Series(dtype=str)).dropna().unique())
else:
    midias = []
selected_midias = st.sidebar.multiselect("Mídia", midias, default=[])

# Corretor filter (opcional, múltipla escolha) - apenas corretores com leads no período
if 'corretor' in leads_df.columns:
    # Primeiro aplicar filtros de data para obter corretores disponíveis no período
    leads_periodo = leads_df[
        (leads_df['data_cad'].dt.date >= data_inicio) &
        (leads_df['data_cad'].dt.date <= data_fim)
    ]
    corretores = sorted(leads_periodo.get('corretor', pd.Series(dtype=str)).dropna().unique())
else:
    corretores = []
selected_corretores = st.sidebar.multiselect("Corretor", corretores, default=[])

# Apply filters using data_cad
filtered_df = leads_df[
    (leads_df['data_cad'].dt.date >= data_inicio) &
    (leads_df['data_cad'].dt.date <= data_fim)
].copy()

if selected_empreendimento != "Todos":
    filtered_df = filtered_df[filtered_df['empreendimento_ultimo'] == selected_empreendimento]

# Aplicar filtro de mídia, quando houver seleção
if 'midia_original' in filtered_df.columns and len(selected_midias) > 0:
    filtered_df = filtered_df[filtered_df['midia_original'].isin(selected_midias)]

# Aplicar filtro de corretor, quando houver seleção
if 'corretor' in filtered_df.columns and len(selected_corretores) > 0:
    filtered_df = filtered_df[filtered_df['corretor'].isin(selected_corretores)]

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
    "Com reserva",
    "Venda realizada"
]

# Calcular as contagens iniciais para cada etapa
initial_etapa_counts = {etapa: filtered_df[filtered_df["funil_etapa"] == etapa].shape[0] for etapa in funil_etapas}

etapa_counts = []
total_leads_remaining = filtered_df.shape[0]

for i, etapa in enumerate(funil_etapas):
    current_stage_count = initial_etapa_counts.get(etapa, 0)
    
    if i == 0: # Leads totais
        etapa_counts.append(total_leads_remaining)
    elif etapa == "Em atendimento":
        cumulative_em_atendimento = initial_etapa_counts.get("Em atendimento", 0) + \
                                    initial_etapa_counts.get("Visita realizada", 0) + \
                                    initial_etapa_counts.get("Com reserva", 0) + \
                                    initial_etapa_counts.get("Venda realizada", 0)
        etapa_counts.append(cumulative_em_atendimento)
    elif etapa == "Visita realizada":
        cumulative_visita_realizada = initial_etapa_counts.get("Visita realizada", 0) + \
                                      initial_etapa_counts.get("Com reserva", 0) + \
                                      initial_etapa_counts.get("Venda realizada", 0)
        etapa_counts.append(cumulative_visita_realizada)
    elif etapa == "Com reserva":
        cumulative_com_reserva = initial_etapa_counts.get("Com reserva", 0) + \
                                 initial_etapa_counts.get("Venda realizada", 0)
        etapa_counts.append(cumulative_com_reserva)
    else:
        etapa_counts.append(current_stage_count)

fig = go.Figure(go.Funnel(
    y=funil_etapas,
    x=etapa_counts,
    textinfo="value+percent initial"
))
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
col1, col2, col3, col4, col5 = st.columns(5)

tooltip_texts = {
    "Leads": "Total de leads em todas as situações.",
    "Em atendimento": "Leads nas situações relacionadas a atendimento.",
    "Visita Realizada": "Leads que realizaram visita.",
    "Com reserva": "Leads com reserva confirmada.",
    "Venda realizada": "Leads que resultaram em venda."
}

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric(label="Leads", value=etapa_counts[0], help=tooltip_texts['Leads'])
col2.metric(label="Em atendimento", value=etapa_counts[1], help=tooltip_texts['Em atendimento'])
col3.metric(label="Visita Realizada", value=etapa_counts[2], help=tooltip_texts['Visita Realizada'])
col4.metric(label="Com reserva", value=etapa_counts[3], help=tooltip_texts['Com reserva'])
col5.metric(label="Venda realizada", value=etapa_counts[4], help=tooltip_texts['Venda realizada'])

st.markdown("---")
st.subheader("Análise de Funil — Distribuições por Corretor e Mídia")

# Garantir colunas necessárias
for col in ["corretor", "midia_original"]:
    if col not in filtered_df.columns:
        filtered_df[col] = '—'

base_df = filtered_df.copy()

col_a, col_b = st.columns(2)

# Tabela por Corretor (todos os leads filtrados)
with col_a:
    st.markdown("**Por Corretor**")
    if base_df.empty:
        st.info("Sem leads no topo do funil para o filtro atual.")
    else:
        por_corretor = (
            base_df.groupby("corretor")["idlead"].count().reset_index(name="Leads")
            .sort_values("Leads", ascending=False)
        )
        total_topo = max(int(por_corretor["Leads"].sum()), 1)
        por_corretor["%"] = (por_corretor["Leads"] / total_topo * 100).round(1)
        por_corretor["%"] = por_corretor["%"].astype(str) + "%"
        st.dataframe(por_corretor, use_container_width=True)

# Tabela por Mídia (todos os leads filtrados)
with col_b:
    st.markdown("**Por Mídia**")
    if base_df.empty:
        st.info("Sem leads no topo do funil para o filtro atual.")
    else:
        # Contar leads por mídia
        por_midia = base_df.groupby("midia_original")["idlead"].count().reset_index()
        por_midia.columns = ["Mídia", "Total Leads"]
        
        # Adicionar colunas de situação/etapa
        for mídia in por_midia["Mídia"]:
            mask = base_df["midia_original"] == mídia
            
            # Em atendimento
            em_atendimento = base_df[mask & (base_df["situacao_nome"] == "aguardando atendimento")]["idlead"].count()
            por_midia.loc[por_midia["Mídia"] == mídia, "Em atendimento"] = em_atendimento
            
            # Visita Realizada
            visita_realizada = base_df[mask & (base_df["funil_etapa"] == "Visita Realizada")]["idlead"].count()
            por_midia.loc[por_midia["Mídia"] == mídia, "Visita Realizada"] = visita_realizada
            
            # Com reserva
            com_reserva = base_df[mask & (base_df["funil_etapa"] == "Com reserva")]["idlead"].count()
            por_midia.loc[por_midia["Mídia"] == mídia, "Com reserva"] = com_reserva
            
            # Venda realizada
            venda_realizada = base_df[mask & (base_df["funil_etapa"] == "Venda realizada")]["idlead"].count()
            por_midia.loc[por_midia["Mídia"] == mídia, "Venda realizada"] = venda_realizada
        
        # Calcular percentuais
        total_topo_m = max(int(por_midia["Total Leads"].sum()), 1)
        por_midia["% Total"] = (por_midia["Total Leads"] / total_topo_m * 100).round(1)
        por_midia["% Total"] = por_midia["% Total"].astype(str) + "%"
        
        # Ordenar por total de leads
        por_midia = por_midia.sort_values("Total Leads", ascending=False)
        
        st.dataframe(por_midia, use_container_width=True)

st.markdown("---")
st.subheader("Leads detalhados")
display_columns = ["idlead", "situacao_nome", "nome_situacao_anterior_lead", "funil_etapa", "gestor", "imobiliaria", "empreendimento_ultimo", "data_cad"]
st.dataframe(
    filtered_df[display_columns].sort_values("data_cad", ascending=False),
    use_container_width=True
)