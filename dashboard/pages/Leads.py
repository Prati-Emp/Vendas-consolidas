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

st.set_page_config(page_title="Leads - Funil de Vendas", page_icon="📊", layout="wide")

st.title("📊 Funil de Leads (Versão Antiga)")

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
        data_consolidada,
        Referencia_data as referencia_data,
        Situacao as situacao_nome,
        Imobiliaria as imobiliaria,
        COALESCE(NULLIF(TRIM(Corretor_consolidado), ''), '—') AS corretor_consolidado,
        COALESCE(NULLIF(TRIM(Midia_consolidada), ''), '—') AS midia_consolidada,
        nome_situacao_anterior_lead,
        gestor,
        empreendimento_ultimo,
        status_em_atendimento,
        status_visita_realizada,
        status_reserva,
        status_venda_realizada,
        motivo_cancelamento_consolidada
    FROM cv_leads
    ORDER BY data_consolidada DESC
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

# Date filters stacked vertically (using data_consolidada)
data_inicio = st.sidebar.date_input("Data Inicial", value=datetime(2022, 4, 13).date())
data_fim = st.sidebar.date_input("Data Final", value=datetime.now().date())

# Empreendimento filter
empreendimentos = sorted(leads_df['empreendimento_ultimo'].dropna().unique())
selected_empreendimento = st.sidebar.selectbox("Empreendimento de Interesse", ["Todos"] + list(empreendimentos))

# Mídia filter (baseado em midia_consolidada)
if 'midia_consolidada' in leads_df.columns:
    # Primeiro aplicar filtros de data para obter mídias disponíveis no período
    leads_periodo = leads_df[
        (leads_df['data_consolidada'].dt.date >= data_inicio) &
        (leads_df['data_consolidada'].dt.date <= data_fim)
    ]
    midias = sorted(leads_periodo.get('midia_consolidada', pd.Series(dtype=str)).dropna().unique())
else:
    midias = []
selected_midias = st.sidebar.multiselect("Mídia", midias, default=[], help="Baseada na última movimentação de mídia registrada")

# Corretor filter (opcional, múltipla escolha) - apenas corretores com leads no período
if 'corretor_consolidado' in leads_df.columns:
    # Primeiro aplicar filtros de data para obter corretores disponíveis no período
    leads_periodo = leads_df[
        (leads_df['data_consolidada'].dt.date >= data_inicio) &
        (leads_df['data_consolidada'].dt.date <= data_fim)
    ]
    corretores = sorted(leads_periodo.get('corretor_consolidado', pd.Series(dtype=str)).dropna().unique())
    
    # Lista de corretores a serem ocultados do filtro
    corretores_ocultos = [
        "ODAIR DIAS DOS SANTOS",
        "Sabrina M. da Silva dos Santos",
        "Alex Anderson Fritzen da Silva",
        "DAIANA PINHEIRO FÜHR",
        "GRAZIELE GODOI",
        "ROSANGELA CRISTINA BEVILAQUA",
        "Alan Rafael Giombelli",
        "Marcos Roberto ferla",
        "JULIANO RAFAEL SIMON",
        "HYORRANA LOPES",
        "Sabrina maria da silva dos santos",
        "VANESSA CARDOSO NAZARIN"
    ]
    
    # Remover corretores da lista de seleção
    corretores = [c for c in corretores if c not in corretores_ocultos]
else:
    corretores = []
selected_corretores = st.sidebar.multiselect("Corretor", corretores, default=[], help="Consolida corretor + corretor_ultimo")

# =============================================================================
# FILTROS PARA LEADS NOVO (NOVO FUNIL)
# =============================================================================
st.sidebar.markdown("---")
st.sidebar.header("Filtros - Leads Novo")

# Filtros de data para o novo funil
data_inicio_novo = st.sidebar.date_input(
    "Data Inicial (Leads Novo)", 
    value=datetime(2025, 10, 22).date(),
    min_value=datetime(2025, 10, 22).date(),
    max_value=datetime.now().date(),
    help="Data inicial (mínimo: 22/10/2025, máximo: hoje)"
)

data_fim_novo = st.sidebar.date_input(
    "Data Final (Leads Novo)", 
    value=datetime.now().date(),
    min_value=data_inicio_novo,
    max_value=datetime.now().date(),
    help="Data final (máximo: hoje)"
)

# Apply filters using data_consolidada
filtered_df = leads_df[
    (leads_df['data_consolidada'].dt.date >= data_inicio) &
    (leads_df['data_consolidada'].dt.date <= data_fim)
].copy()

if selected_empreendimento != "Todos":
    filtered_df = filtered_df[filtered_df['empreendimento_ultimo'] == selected_empreendimento]

# Aplicar filtro de mídia, quando houver seleção
if 'midia_consolidada' in filtered_df.columns and len(selected_midias) > 0:
    filtered_df = filtered_df[filtered_df['midia_consolidada'].isin(selected_midias)]

# Aplicar filtro de corretor, quando houver seleção
if 'corretor_consolidado' in filtered_df.columns and len(selected_corretores) > 0:
    filtered_df = filtered_df[filtered_df['corretor_consolidado'].isin(selected_corretores)]

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

# Cards do funil antigo
st.markdown("---")
col1, col2, col3, col4, col5 = st.columns(5)

tooltip_texts = {
    "Leads": "Total de leads em todas as situações.",
    "Em atendimento": "Leads nas situações relacionadas a atendimento.",
    "Visita Realizada": "Leads que realizaram visita.",
    "Com reserva": "Leads com reserva confirmada.",
    "Venda realizada": "Leads que resultaram em venda."
}

col1.metric(label="Leads", value=etapa_counts[0], help=tooltip_texts['Leads'])
col2.metric(label="Em atendimento", value=etapa_counts[1], help=tooltip_texts['Em atendimento'])
col3.metric(label="Visita Realizada", value=etapa_counts[2], help=tooltip_texts['Visita Realizada'])
col4.metric(label="Com reserva", value=etapa_counts[3], help=tooltip_texts['Com reserva'])
col5.metric(label="Venda realizada", value=etapa_counts[4], help=tooltip_texts['Venda realizada'])

# =============================================================================
# NOVO FUNIL - VERSÃO COM COLUNAS DE STATUS
# =============================================================================
st.markdown("---")
st.markdown("## 📊 Funil de Leads (Versão Nova)")

# Filtros específicos para o novo funil (movidos para sidebar)
# Será implementado na sidebar

# Aplicar filtros específicos para o novo funil
filtered_df_novo = leads_df[
    (leads_df['data_consolidada'].dt.date >= data_inicio_novo) &
    (leads_df['data_consolidada'].dt.date <= data_fim_novo)
].copy()

# Aplicar outros filtros (empreendimento, mídia, corretor) se selecionados
if selected_empreendimento != "Todos":
    filtered_df_novo = filtered_df_novo[filtered_df_novo['empreendimento_ultimo'] == selected_empreendimento]

if selected_midias:
    filtered_df_novo = filtered_df_novo[filtered_df_novo['midia_consolidada'].isin(selected_midias)]

if selected_corretores:
    filtered_df_novo = filtered_df_novo[filtered_df_novo['corretor_consolidado'].isin(selected_corretores)]

# Funil baseado nas novas colunas de status
def render_novo_funil_status():
    # Contar leads por status usando as novas colunas (com filtros específicos)
    total_leads = len(filtered_df_novo)
    
    
    # Contar por status usando as colunas específicas (buscar por "sim" em qualquer variação)
    em_atendimento = len(filtered_df_novo[filtered_df_novo.get('status_em_atendimento', '').str.lower() == 'sim'])
    visita_realizada = len(filtered_df_novo[filtered_df_novo.get('status_visita_realizada', '').str.lower() == 'sim'])
    com_reserva = len(filtered_df_novo[filtered_df_novo.get('status_reserva', '').str.lower() == 'sim'])
    venda_realizada = len(filtered_df_novo[filtered_df_novo.get('status_venda_realizada', '').str.lower() == 'sim'])
    
    # Criar dados para o funil
    funil_etapas_novo = ["Leads", "Em atendimento", "Visita realizada", "Com reserva", "Venda realizada"]
    etapa_counts_novo = [total_leads, em_atendimento, visita_realizada, com_reserva, venda_realizada]
    
    # Criar gráfico de funil
    fig_novo = go.Figure(go.Funnel(
        y=funil_etapas_novo,
        x=etapa_counts_novo,
        textinfo="value+percent initial"
    ))
    
    # Adicionar título e formatação
    fig_novo.update_layout(
        title="Funil de Leads (Baseado em Status)",
        font=dict(size=12),
        margin=dict(l=0, r=0, t=40, b=0)
    )
    
    st.plotly_chart(fig_novo, use_container_width=True)
    
    # Cards de resumo
    st.markdown("---")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    tooltip_texts_novo = {
        "Leads": "Total de leads em todas as situações (mesmo cálculo atual).",
        "Em atendimento": "Leads com status_em_atendimento = 'sim'.",
        "Visita realizada": "Leads com status_visita_realizada = 'sim'.",
        "Com reserva": "Leads com status_reserva = 'sim'.",
        "Venda realizada": "Leads com status_venda_realizada = 'sim'."
    }
    
    col1.metric(label="Leads", value=total_leads, help=tooltip_texts_novo['Leads'])
    col2.metric(label="Em atendimento", value=em_atendimento, help=tooltip_texts_novo['Em atendimento'])
    col3.metric(label="Visita realizada", value=visita_realizada, help=tooltip_texts_novo['Visita realizada'])
    col4.metric(label="Com reserva", value=com_reserva, help=tooltip_texts_novo['Com reserva'])
    col5.metric(label="Venda realizada", value=venda_realizada, help=tooltip_texts_novo['Venda realizada'])

# Mostrar informações do período selecionado
st.info(f"📊 **Período de Análise**: {data_inicio_novo.strftime('%d/%m/%Y')} a {data_fim_novo.strftime('%d/%m/%Y')} | **Total de Leads**: {len(filtered_df_novo):,}")

# Renderizar o novo funil
render_novo_funil_status()


# =============================================================================
# ANÁLISE DE FUNIL - DISTRIBUIÇÕES POR CORRETOR E MÍDIA (FUNIL ANTIGO)
# =============================================================================
st.markdown("---")
st.subheader("Análise de Funil — Distribuições por Corretor e Mídia")

# Garantir colunas necessárias
for col in ["corretor_consolidado", "midia_consolidada"]:
    if col not in filtered_df.columns:
        filtered_df[col] = '—'

base_df = filtered_df.copy()

# Tabela por Corretor (todos os leads filtrados)
st.markdown("**Por Corretor**", help="Coluna corretor: Consolida corretor + corretor_ultimo")

if base_df.empty:
    st.info("Sem leads no topo do funil para o filtro atual.")
else:
    por_corretor = (
        base_df.groupby("corretor_consolidado")["idlead"].count().reset_index(name="Leads")
        .sort_values("Leads", ascending=False)
    )
    # Renomear coluna para "corretor"
    por_corretor = por_corretor.rename(columns={"corretor_consolidado": "corretor"})
    
    # Ocultar informações do corretor "Odair Dias dos Santos"
    por_corretor = por_corretor[por_corretor["corretor"] != "ODAIR DIAS DOS SANTOS"]
    
    # Adicionar colunas de situação/etapa
    for corretor in por_corretor["corretor"]:
        mask = base_df["corretor_consolidado"] == corretor
        
        # Venda realizada
        venda_realizada = base_df[mask & (base_df["funil_etapa"] == "Venda realizada")]["idlead"].count()
        por_corretor.loc[por_corretor["corretor"] == corretor, "Venda realizada"] = venda_realizada
        
        # Visita realizada (cumulativo - igual ao funil)
        visita_realizada = base_df[mask & (base_df["funil_etapa"] == "Visita realizada")]["idlead"].count() + \
                          base_df[mask & (base_df["funil_etapa"] == "Com reserva")]["idlead"].count() + \
                          base_df[mask & (base_df["funil_etapa"] == "Venda realizada")]["idlead"].count()
        por_corretor.loc[por_corretor["corretor"] == corretor, "Visita realizada"] = visita_realizada
    
    total_topo = max(int(por_corretor["Leads"].sum()), 1)
    por_corretor["% Leads"] = (por_corretor["Leads"] / total_topo * 100).round(1)
    
    # Calcular taxa de conversão (Venda realizada / Total Leads)
    por_corretor["% Conversão vendas"] = (por_corretor["Venda realizada"] / por_corretor["Leads"] * 100).round(1)
    
    # Calcular taxa de conversão para visitas (Visita realizada / Total Leads)
    por_corretor["% Conversão visitas"] = (por_corretor["Visita realizada"] / por_corretor["Leads"] * 100).round(1)
    
    # Ordenar por taxa de conversão (maior para menor) e usar como índice para ordenação
    por_corretor = por_corretor.sort_values("% Conversão vendas", ascending=False)
    por_corretor = por_corretor.reset_index(drop=True)
    por_corretor.index = por_corretor.index + 1  # Começar do 1 em vez de 0
    
    # Formatar colunas de percentual para exibição
    por_corretor_display = por_corretor.copy()
    por_corretor_display["% Leads"] = por_corretor_display["% Leads"].astype(str) + "%"
    por_corretor_display["% Conversão vendas"] = por_corretor_display["% Conversão vendas"].astype(str) + "%"
    por_corretor_display["% Conversão visitas"] = por_corretor_display["% Conversão visitas"].astype(str) + "%"
    
    # Adicionar tooltip explicativo
    st.markdown("💡 **Dica**: A primeira coluna (índice) ordena automaticamente pela taxa de conversão de vendas do maior para o menor.")
    
    st.dataframe(por_corretor_display, use_container_width=True)

# =============================================================================
# TABELA DE CANCELAMENTOS POR CORRETOR
# =============================================================================
st.markdown("---")
st.markdown("**Cancelamentos por Corretor**", help="Análise de motivos de cancelamento por corretor")

if base_df.empty:
    st.info("Sem leads no topo do funil para o filtro atual.")
else:
    # Filtrar apenas leads com cancelamentos
    leads_cancelados = base_df[base_df['motivo_cancelamento_consolidada'].notna() & 
                              (base_df['motivo_cancelamento_consolidada'] != '')].copy()
    
    if leads_cancelados.empty:
        st.info("Nenhum cancelamento encontrado para o período selecionado.")
    else:
        # Análise por corretor
        cancelamentos_por_corretor = leads_cancelados.groupby('corretor_consolidado').agg({
            'idlead': 'count',
            'motivo_cancelamento_consolidada': lambda x: x.value_counts().to_dict()
        }).reset_index()
        
        cancelamentos_por_corretor.columns = ['Corretor', 'Total Cancelamentos', 'Motivos Detalhados']
        
        # Ocultar corretores da lista de exclusão
        corretores_ocultos = [
            "ODAIR DIAS DOS SANTOS",
            "Sabrina M. da Silva dos Santos",
            "Alex Anderson Fritzen da Silva",
            "DAIANA PINHEIRO FÜHR",
            "GRAZIELE GODOI",
            "ROSANGELA CRISTINA BEVILAQUA",
            "Alan Rafael Giombelli",
            "Marcos Roberto ferla",
            "JULIANO RAFAEL SIMON",
            "HYORRANA LOPES",
            "Sabrina maria da silva dos santos",
            "VANESSA CARDOSO NAZARIN"
        ]
        cancelamentos_por_corretor = cancelamentos_por_corretor[
            ~cancelamentos_por_corretor['Corretor'].isin(corretores_ocultos)
        ]
        
        # Ordenar por total de cancelamentos
        cancelamentos_por_corretor = cancelamentos_por_corretor.sort_values('Total Cancelamentos', ascending=False)
        cancelamentos_por_corretor = cancelamentos_por_corretor.reset_index(drop=True)
        cancelamentos_por_corretor.index = cancelamentos_por_corretor.index + 1
        
        # Mostrar tabela principal
        st.dataframe(cancelamentos_por_corretor[['Corretor', 'Total Cancelamentos']], use_container_width=True)
        
        # Seção expandível para detalhes
        st.markdown("---")
        with st.expander("📊 **Ver Detalhes dos Motivos de Cancelamento por Corretor**"):
            for idx, row in cancelamentos_por_corretor.iterrows():
                st.markdown(f"**{row['Corretor']}** - {row['Total Cancelamentos']} cancelamentos")
                
                # Criar tabela de motivos para este corretor
                motivos_df = pd.DataFrame(list(row['Motivos Detalhados'].items()), 
                                        columns=['Motivo', 'Quantidade'])
                motivos_df = motivos_df.sort_values('Quantidade', ascending=False)
                
                # Calcular percentual
                total = motivos_df['Quantidade'].sum()
                motivos_df['% do Total'] = (motivos_df['Quantidade'] / total * 100).round(1)
                motivos_df['% do Total'] = motivos_df['% do Total'].astype(str) + '%'
                
                st.dataframe(motivos_df, use_container_width=True)
                st.markdown("---")

st.markdown("---")

# Tabela por Mídia (todos os leads filtrados) - com mais espaço horizontal
st.markdown("**Por Mídia**", help="Coluna Mídia: Baseada na última movimentação de mídia registrada")

if base_df.empty:
    st.info("Sem leads no topo do funil para o filtro atual.")
else:
    # Contar leads por mídia
    por_midia = base_df.groupby("midia_consolidada")["idlead"].count().reset_index()
    por_midia.columns = ["Mídia", "Total Leads"]
    
    # Adicionar colunas de situação/etapa
    for mídia in por_midia["Mídia"]:
        mask = base_df["midia_consolidada"] == mídia
        
        # Venda realizada
        venda_realizada = base_df[mask & (base_df["funil_etapa"] == "Venda realizada")]["idlead"].count()
        por_midia.loc[por_midia["Mídia"] == mídia, "Venda realizada"] = venda_realizada
    
    # Calcular percentuais
    total_topo_m = max(int(por_midia["Total Leads"].sum()), 1)
    por_midia["% Leads"] = (por_midia["Total Leads"] / total_topo_m * 100).round(1)
    
    # Calcular taxa de conversão (Venda realizada / Total Leads)
    por_midia["% Conversão vendas"] = (por_midia["Venda realizada"] / por_midia["Total Leads"] * 100).round(1)
    
    # Ordenar por taxa de conversão (maior para menor) e usar como índice para ordenação
    por_midia = por_midia.sort_values("% Conversão vendas", ascending=False)
    por_midia = por_midia.reset_index(drop=True)
    por_midia.index = por_midia.index + 1  # Começar do 1 em vez de 0
    
    # Formatar colunas de percentual para exibição
    por_midia_display = por_midia.copy()
    por_midia_display["% Leads"] = por_midia_display["% Leads"].astype(str) + "%"
    por_midia_display["% Conversão vendas"] = por_midia_display["% Conversão vendas"].astype(str) + "%"
    
    # Adicionar tooltip explicativo
    st.markdown("💡 **Dica**: A primeira coluna (índice) ordena automaticamente pela taxa de conversão de vendas do maior para o menor.")
    
    st.dataframe(por_midia_display, use_container_width=True)

st.markdown("---")
st.subheader("Leads detalhados")
# Exibir dados usando data_consolidada
display_columns = ["idlead", "situacao_nome", "nome_situacao_anterior_lead", "funil_etapa", "gestor", "imobiliaria", "empreendimento_ultimo", "data_consolidada"]
st.dataframe(
    filtered_df[display_columns].sort_values("data_consolidada", ascending=False),
    use_container_width=True
)


# =============================================================================
# SEÇÃO LEADS ATIVOS (não afetada pelos filtros da página principal)
# =============================================================================
st.markdown("---")
st.markdown("## 📊 Funil de Leads Ativos")

# Tooltip informativo sobre a seção Leads Ativos
st.info("ℹ️ **Importante**: Esta seção mostra a foto atual de todos os leads ativos. Os filtros de data da página principal não se aplicam aqui.")

# Carregar dados completos para leads ativos (sem filtros de data)
def get_leads_ativos_data():
    con = duckdb.connect(f"md:reservas?token={MOTHERDUCK_TOKEN}")
    query = """
    SELECT Idlead as idlead,
           Data_cad as data_cad,
           data_consolidada,
           Referencia_data as referencia_data,
           Situacao as situacao_nome,
           Imobiliaria as imobiliaria,
           nome_situacao_anterior_lead,
           gestor,
           empreendimento_ultimo
    FROM cv_leads
    ORDER BY data_consolidada DESC
    """
    df = con.execute(query).df()
    con.close()
    return df

# Sidebar para filtros específicos de Leads Ativos
st.sidebar.markdown("---")
st.sidebar.markdown("### Filtros - Leads Ativos")

# Imobiliaria filter para leads ativos
imobiliarias_ativos = sorted(leads_df['imobiliaria'].dropna().unique())
selected_imobiliaria_ativos = st.sidebar.selectbox("Imobiliária (Leads Ativos)", ["Todas"] + list(imobiliarias_ativos))

# Empreendimento filter para leads ativos
empreendimentos_ativos = sorted(leads_df['empreendimento_ultimo'].dropna().unique())
selected_empreendimento_ativos = st.sidebar.selectbox("Empreendimento (Leads Ativos)", ["Todos"] + list(empreendimentos_ativos))

# Carregar dados para leads ativos
leads_ativos_df = get_leads_ativos_data()

# Aplicar filtros específicos para leads ativos
filtered_ativos_df = leads_ativos_df.copy()

if selected_imobiliaria_ativos != "Todas":
    filtered_ativos_df = filtered_ativos_df[filtered_ativos_df['imobiliaria'] == selected_imobiliaria_ativos]

if selected_empreendimento_ativos != "Todos":
    filtered_ativos_df = filtered_ativos_df[filtered_ativos_df['empreendimento_ultimo'] == selected_empreendimento_ativos]

# Exclude converted leads: Descartado, Em Pré-Cadastro, Venda realizada, Vencido
exclude_situations = ['descartado', 'em pré-cadastro', 'venda realizada', 'vencido']
filtered_ativos_df = filtered_ativos_df[~filtered_ativos_df['situacao_nome'].str.lower().str.strip().isin(exclude_situations)]

# Mapeamento do funil para leads ativos
mapa_funil_ativos = {
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

def get_funil_etapa_ativos(prev_situacao, curr_situacao):
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
        return mapa_funil_ativos.get(prev_key, "Leads")
    
    # Para outras situações, usa mapeamento da atual
    if curr_key is None:
        return "Leads"
    return mapa_funil_ativos.get(curr_key, "Leads")

filtered_ativos_df["funil_etapa"] = filtered_ativos_df.apply(lambda row: get_funil_etapa_ativos(row['nome_situacao_anterior_lead'], row['situacao_nome']), axis=1)

funil_etapas_ativos = [
    "Leads",
    "Em atendimento",
    "Visita realizada",
    "Com reserva"
]

etapa_counts_ativos = [filtered_ativos_df[filtered_ativos_df["funil_etapa"] == etapa].shape[0] for etapa in funil_etapas_ativos]

# Calcular tempo ativo (dias desde a data consolidada até hoje)
filtered_ativos_df["data_consolidada"] = pd.to_datetime(filtered_ativos_df["data_consolidada"], errors="coerce")
now_ts = pd.Timestamp.now()
filtered_ativos_df["dias_ativo"] = (now_ts - filtered_ativos_df["data_consolidada"]).dt.days
# Formatar como "X dias" para exibição
filtered_ativos_df["tempo_ativo"] = filtered_ativos_df["dias_ativo"].apply(lambda d: f"{int(d)} dias" if pd.notna(d) else "-")

# Gráfico de funil para leads ativos
fig_ativos = go.Figure(go.Funnel(
    y=funil_etapas_ativos,
    x=etapa_counts_ativos,
    textinfo="value+percent initial"
))
st.plotly_chart(fig_ativos, use_container_width=True)

st.markdown("---")
# Cartão de total de leads ativos (todas as situações consideradas ativas)
total_ativos = int(filtered_ativos_df.shape[0])
col_total, col1, col2, col3, col4 = st.columns(5)

tooltip_texts_ativos = {
    "Total de leads ativos": "Soma de todas as situações ativas (exclui descartados, em pré-cadastro, venda realizada e vencido).",
    "Leads": "Total de leads na etapa inicial (excluindo descartados, em pré-cadastro, venda realizada e vencido).",
    "Em atendimento": "Leads nas situações relacionadas a atendimento (excluindo descartados, em pré-cadastro, venda realizada e vencido).",
    "Visita Realizada": "Leads que realizaram visita (excluindo descartados, em pré-cadastro, venda realizada e vencido).",
    "Com reserva": "Leads com reserva confirmada (excluindo descartados, em pré-cadastro, venda realizada e vencido)."
}

col_total.metric(label="Total de leads ativos", value=total_ativos, help=tooltip_texts_ativos['Total de leads ativos'])
col1.metric(label="Leads", value=etapa_counts_ativos[0], help=tooltip_texts_ativos['Leads'])
col2.metric(label="Em atendimento", value=etapa_counts_ativos[1], help=tooltip_texts_ativos['Em atendimento'])
col3.metric(label="Visita Realizada", value=etapa_counts_ativos[2], help=tooltip_texts_ativos['Visita Realizada'])
col4.metric(label="Com reserva", value=etapa_counts_ativos[3], help=tooltip_texts_ativos['Com reserva'])

st.markdown("---")
st.subheader("Leads ativos detalhados")
# Exibir dados de leads ativos usando data_consolidada
display_columns_ativos = ["idlead", "situacao_nome", "nome_situacao_anterior_lead", "funil_etapa", "gestor", "imobiliaria", "empreendimento_ultimo", "data_consolidada", "tempo_ativo"]
st.dataframe(
    filtered_ativos_df[display_columns_ativos].sort_values("data_consolidada", ascending=False),
    use_container_width=True
)