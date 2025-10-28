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
try:
    from advanced_auth import require_auth, require_page_access
    
    # Proteger com autenticação
    require_auth()
    
    # Proteger acesso à página específica
    require_page_access("leads")
except ImportError as e:
    st.error(f"Erro ao importar sistema de autenticação: {e}")
    st.stop()

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


@st.cache_data(show_spinner=False)
def load_tempo_por_situacao_data(
    data_inicio_str: str,
    data_fim_str: str,
    imobiliarias_filter: tuple,
    corretores_filter: tuple,
    empreendimento_filter: str,
):
    """Carrega tempos de workflow consolidados do MotherDuck aplicando os filtros principais."""
    con = duckdb.connect(f"md:?motherduck_token={MOTHERDUCK_TOKEN}")

    filtros_sql = [
        "tempo IS NOT NULL",
        "Data_cad IS NOT NULL",
        "CAST(Data_cad AS DATE) >= CAST(? AS DATE)",
        "CAST(Data_cad AS DATE) <= CAST(? AS DATE)"
    ]

    params = [data_inicio_str, data_fim_str]

    if corretores_filter:
        placeholders = ",".join(["?" for _ in corretores_filter])
        filtros_sql.append("COALESCE(NULLIF(TRIM(corretor_consolidado), ''), '—') IN (" + placeholders + ")")
        params.extend(corretores_filter)

    if imobiliarias_filter:
        placeholders = ",".join(["?" for _ in imobiliarias_filter])
        filtros_sql.append("COALESCE(NULLIF(TRIM(imobiliaria), ''), '—') IN (" + placeholders + ")")
        params.extend(imobiliarias_filter)

    if empreendimento_filter and empreendimento_filter != "Todos":
        filtros_sql.append("COALESCE(NULLIF(TRIM(empreendimento_primeiro), ''), '—') = ?")
        params.append(empreendimento_filter)

    where_clause = " AND ".join(filtros_sql)

    query = f"""
        SELECT 
            COALESCE(NULLIF(TRIM(corretor_consolidado), ''), '—') AS corretor_consolidado,
            COALESCE(NULLIF(TRIM(situacao), ''), '—') AS situacao,
            tempo,
            CAST(Data_cad AS DATE) AS data_cad,
            COALESCE(NULLIF(TRIM(imobiliaria), ''), '—') AS imobiliaria,
            COALESCE(NULLIF(TRIM(empreendimento_primeiro), ''), '—') AS empreendimento_primeiro
        FROM informacoes_consolidadas.cv_leads_workflow_consolidado
        WHERE {where_clause}
    """

    df = con.execute(query, params).df()
    con.close()
    return df


def formatar_tempo_minutos(minutos):
    """Converte minutos em representação legível (dias, horas, minutos)."""
    if minutos is None or pd.isna(minutos):
        return "-"

    try:
        minutos_float = float(minutos)
    except (TypeError, ValueError):
        return "-"

    if minutos_float < 1:
        return "< 1 min"

    minutos_int = int(round(minutos_float))
    dias = minutos_int // (24 * 60)
    horas = (minutos_int % (24 * 60)) // 60
    minutos_restantes = minutos_int % 60

    partes = []

    if dias > 0:
        partes.append(f"{dias} dia{'s' if dias != 1 else ''}")

    if horas > 0:
        partes.append(f"{horas} h")

    if dias == 0 and horas == 0 and minutos_restantes > 0:
        partes.append(f"{minutos_restantes} min")
    elif minutos_restantes > 0 and (dias > 0 or horas > 0):
        partes.append(f"{minutos_restantes} min")

    if not partes:
        partes.append("0 min")

    return " ".join(partes)

if leads_df.empty:
    st.warning("Nenhum dado retornado do Mother Duck.")
    st.stop()

# =============================================================================
# REMOÇÃO DE CORRETORES ESPECÍFICOS
# =============================================================================
# Lista de corretores a serem removidos completamente dos dados
corretores_removidos = [
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

# Remover leads desses corretores do conjunto de dados
leads_df = leads_df[~leads_df['corretor_consolidado'].isin(corretores_removidos)]

# Sidebar for filters
st.sidebar.header("Filtros")

# Date filters stacked vertically (using data_consolidada)
data_inicio = st.sidebar.date_input("Data Inicial", value=datetime(2022, 4, 13).date())
data_fim = st.sidebar.date_input("Data Final", value=datetime.now().date())

# Base de dados apenas com filtro de datas para reaproveitar nas opções adicionais
leads_periodo_base = leads_df[
    (leads_df['data_consolidada'].dt.date >= data_inicio) &
    (leads_df['data_consolidada'].dt.date <= data_fim)
]

# Empreendimento filter
empreendimentos = sorted(leads_df['empreendimento_ultimo'].dropna().unique())
selected_empreendimento = st.sidebar.selectbox("Empreendimento de Interesse", ["Todos"] + list(empreendimentos))

# Mídia filter (baseado em midia_consolidada)
if 'midia_consolidada' in leads_df.columns:
    midias = sorted(leads_periodo_base.get('midia_consolidada', pd.Series(dtype=str)).dropna().unique())
else:
    midias = []
selected_midias = st.sidebar.multiselect("Mídia", midias, default=[], help="Baseada na última movimentação de mídia registrada")

# Corretor filter (opcional, múltipla escolha) - apenas corretores com leads no período
if 'corretor_consolidado' in leads_df.columns:
    corretores = sorted(leads_periodo_base.get('corretor_consolidado', pd.Series(dtype=str)).dropna().unique())
    
    # Corretores já foram removidos dos dados, então não precisamos filtrar aqui
else:
    corretores = []
selected_corretores = st.sidebar.multiselect("Corretor", corretores, default=[], help="Consolida corretor + corretor_ultimo")

# Imobiliária filter (opcional, múltipla escolha)
if 'imobiliaria' in leads_df.columns:
    imobiliarias_series = leads_periodo_base.get('imobiliaria', pd.Series(dtype=str)).fillna('—').replace('', '—')
    imobiliarias = sorted(imobiliarias_series.unique().tolist())
else:
    imobiliarias = []
selected_imobiliarias = st.sidebar.multiselect(
    "Imobiliária",
    imobiliarias,
    default=[],
    help="Baseada na última movimentação registrada"
)

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

# Aplicar filtro de imobiliária, quando houver seleção
if 'imobiliaria' in filtered_df.columns and len(selected_imobiliarias) > 0:
    filtered_df = filtered_df[filtered_df['imobiliaria'].isin(selected_imobiliarias)]

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

if selected_imobiliarias:
    filtered_df_novo = filtered_df_novo[filtered_df_novo['imobiliaria'].isin(selected_imobiliarias)]

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
        
        # Total cancelamentos
        cancelamentos = base_df[mask & base_df['motivo_cancelamento_consolidada'].notna() & 
                               (base_df['motivo_cancelamento_consolidada'] != '')]["idlead"].count()
        por_corretor.loc[por_corretor["corretor"] == corretor, "Total Cancelamentos"] = cancelamentos
    
    total_topo = max(int(por_corretor["Leads"].sum()), 1)
    por_corretor["% Leads"] = (por_corretor["Leads"] / total_topo * 100).round(1)
    
    # Calcular taxa de conversão (Venda realizada / Total Leads)
    por_corretor["% Conversão vendas"] = (por_corretor["Venda realizada"] / por_corretor["Leads"] * 100).round(1)
    
    # Calcular taxa de cancelamento (Total Cancelamentos / Total Leads)
    por_corretor["% Cancelamento leads"] = (por_corretor["Total Cancelamentos"] / por_corretor["Leads"] * 100).round(1)
    
    # Ordenar por taxa de conversão (maior para menor) e usar como índice para ordenação
    por_corretor = por_corretor.sort_values("% Conversão vendas", ascending=False)
    por_corretor = por_corretor.reset_index(drop=True)
    por_corretor.index = por_corretor.index + 1  # Começar do 1 em vez de 0
    
    # Formatar colunas de percentual para exibição
    por_corretor_display = por_corretor.copy()
    por_corretor_display["% Leads"] = por_corretor_display["% Leads"].astype(str) + "%"
    por_corretor_display["% Conversão vendas"] = por_corretor_display["% Conversão vendas"].astype(str) + "%"
    por_corretor_display["% Cancelamento leads"] = por_corretor_display["% Cancelamento leads"].astype(str) + "%"
    
    # Adicionar tooltip explicativo
    st.markdown("💡 **Dica**: A primeira coluna (índice) ordena automaticamente pela taxa de conversão de vendas do maior para o menor.")
    
    st.dataframe(por_corretor_display, use_container_width=True)

# =============================================================================
# SEÇÃO EXPANDÍVEL PARA DETALHES DE CANCELAMENTOS
# =============================================================================
st.markdown("---")
with st.expander("📊 **Ver Detalhes dos Motivos de Cancelamento por Corretor**"):
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
        
        # Corretores já foram removidos dos dados, então não precisamos filtrar aqui
        
        # Ordenar por total de cancelamentos
        cancelamentos_por_corretor = cancelamentos_por_corretor.sort_values('Total Cancelamentos', ascending=False)
        
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
st.markdown("## 📊 Leads Ativos")

# Tooltip informativo sobre a seção Leads Ativos
st.info("ℹ️ **Importante**: Esta seção mostra a foto atual de todos os leads ativos. Os filtros de data da página principal não se aplicam aqui.")

# Tooltip por hover explicando o que é Lead e Lead Ativo
tooltip_text = (
    "Lead: Registro de um contato que entrou no funil comercial.\n"
    "Lead ativo: Lead que segue em acompanhamento (situações diferentes de Descartado, Em Pré-Cadastro, Venda Realizada ou Vencido)."
)
tooltip_text_html = tooltip_text.replace("\n", "&#10;")

st.markdown(
    f"""
    <div style='display:flex; align-items:center; gap:8px;'>
        <h3 style='margin:0;'>Leads Ativos</h3>
        <div title="{tooltip_text_html}" style='background-color:#1e1e1e;border:1px solid #404040;border-radius:50%;width:24px;height:24px;display:flex;align-items:center;justify-content:center;cursor:help;'>
            <span style='color:#ffffff;font-size:14px;font-weight:bold;'>i</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    **Lead:** Registro de um contato que iniciou relacionamento com a equipe comercial.

    **Lead ativo:** Lead que ainda está em acompanhamento porque sua situação atual é diferente de *Descartado*, *Em Pré-Cadastro*, *Venda Realizada* ou *Vencido*.
    """
)

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

# Calcular total de leads ativos ANTES de usar na tabela
total_ativos = int(filtered_ativos_df.shape[0])

# Gráfico de barras horizontais simples para funil de leads ativos
fig_barras = go.Figure()

# Preparar dados para texto dentro e fora das barras
text_inside = []  # Percentuais dentro das barras
text_outside = []  # Quantidades fora das barras

# Calcular percentuais em relação ao total de leads ativos
leads_base = total_ativos if total_ativos > 0 else 1

for i, etapa in enumerate(funil_etapas_ativos):
    quantidade = etapa_counts_ativos[i]
    
    # Percentual calculado em relação ao total de leads ativos
    percentual = (quantidade / leads_base * 100) if leads_base > 0 else 0
    
    # Texto dentro da barra (percentual)
    text_inside.append(f"{percentual:.1f}%")
    
    # Texto fora da barra (quantidade)
    text_outside.append(f"{quantidade}")

# Adicionar barras horizontais para cada etapa
fig_barras.add_trace(go.Bar(
    y=funil_etapas_ativos,
    x=etapa_counts_ativos,
    orientation='h',
    text=text_inside,  # Percentual dentro da barra
    textposition='inside',
    textfont=dict(color='white', size=12, family='Arial Black'),
    marker=dict(
        color='#4A90E2',  # Azul claro uniforme como na imagem
        line=dict(width=0)  # Sem bordas
    ),
    hovertemplate='<b>%{y}</b><br>Quantidade: %{x}<br>Percentual: %{customdata:.1f}%<extra></extra>',
    customdata=[(count / leads_base * 100) if leads_base > 0 else 0 for count in etapa_counts_ativos]
))

# Adicionar anotações com quantidades fora das barras
for i, etapa in enumerate(funil_etapas_ativos):
    quantidade = etapa_counts_ativos[i]
    
    fig_barras.add_annotation(
        x=quantidade + max(etapa_counts_ativos) * 0.02,  # Posicionar um pouco à direita da barra
        y=etapa,
        text=f"{quantidade}",
        showarrow=False,
        font=dict(size=12, color='white', family='Arial'),
        xref='x',
        yref='y'
    )

# Configurar layout do gráfico
fig_barras.update_layout(
    title="Leads Ativos",
    xaxis_title="Quantidade de Leads",
    yaxis_title="Etapas",
    showlegend=False,
    height=400,
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)',
    font=dict(color='white'),
    xaxis=dict(
        tickfont=dict(size=12),
        gridcolor='rgba(255,255,255,0.1)',
        showgrid=True,
        range=[0, max(etapa_counts_ativos) * 1.3]  # Expandir eixo X para acomodar texto externo
    ),
    yaxis=dict(
        tickfont=dict(size=12),
        gridcolor='rgba(255,255,255,0.1)',
        showgrid=False,
        categoryorder='array',
        categoryarray=funil_etapas_ativos[::-1]  # Inverter ordem para maior no topo
    ),
    margin=dict(l=100, r=100, t=50, b=50)  # Aumentar margem direita para texto externo
)

# Exibir gráfico
st.plotly_chart(fig_barras, use_container_width=True)

st.markdown("---")
# Cartão de total de leads ativos (todas as situações consideradas ativas)
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


# =============================================================================
# TEMPO MÉDIO POR SITUAÇÃO
# =============================================================================
st.markdown("---")
st.subheader("⏱️ Tempo por Situação")
st.write(
    "📌 **Como interpretar:** A tabela abaixo mostra o tempo médio (convertido de minutos para dias, horas e minutos) "
    "que cada corretor leva em cada situação do workflow consolidado."
)

tempo_situacao_df = load_tempo_por_situacao_data(
    data_inicio.strftime("%Y-%m-%d"),
    data_fim.strftime("%Y-%m-%d"),
    tuple(sorted(selected_imobiliarias)),
    tuple(sorted(selected_corretores)),
    selected_empreendimento,
)

if selected_imobiliarias:
    tempo_situacao_df = tempo_situacao_df[
        tempo_situacao_df["imobiliaria"].isin(selected_imobiliarias)
    ]

if selected_corretores:
    tempo_situacao_df = tempo_situacao_df[
        tempo_situacao_df["corretor_consolidado"].isin(selected_corretores)
    ]

if tempo_situacao_df.empty:
    st.info("Nenhuma informação de tempo encontrada para os filtros atuais.")
else:
    tempo_situacao_df["tempo"] = pd.to_numeric(tempo_situacao_df["tempo"], errors="coerce")
    tempo_situacao_df = tempo_situacao_df.dropna(subset=["tempo"])

    if tempo_situacao_df.empty:
        st.info("Nenhum tempo válido disponível após o tratamento dos dados.")
    else:
        tempo_agrupado = (
            tempo_situacao_df.groupby(["corretor_consolidado", "situacao"], dropna=False)["tempo"]
            .mean()
            .reset_index()
        )

        if tempo_agrupado.empty:
            st.info("Não há tempos médios calculados para exibir.")
        else:
            tempo_pivot = (
                tempo_agrupado.pivot_table(
                    index="corretor_consolidado",
                    columns="situacao",
                    values="tempo",
                    aggfunc="mean"
                )
            )

            tempo_pivot = tempo_pivot.sort_index()
            tempo_pivot = tempo_pivot.reindex(
                sorted(tempo_pivot.columns, key=lambda x: (x is None, str(x).lower())),
                axis=1
            )

            tempo_pivot_display = tempo_pivot.applymap(formatar_tempo_minutos).reset_index()
            tempo_pivot_display = tempo_pivot_display.rename(columns={"corretor_consolidado": "Corretor"})

            st.dataframe(tempo_pivot_display, use_container_width=True)
            st.caption(
                "Os tempos são médias calculadas a partir da coluna `tempo` da tabela "
                "informacoes_consolidadas.cv_leads_workflow_consolidado." 
                " Valores exibidos em dias, horas e minutos."
            )