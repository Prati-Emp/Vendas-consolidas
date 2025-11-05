import streamlit as st
import pandas as pd
from datetime import datetime, date
import sys
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
from dateutil.relativedelta import relativedelta
import time
import re

# Garantir que os módulos compartilhados possam ser importados quando o app for executado diretamente
sys.path.append(str(Path(__file__).resolve().parent.parent))

from advanced_auth import require_auth, get_current_user
from utils import display_navigation
from utils.md_conn import get_md_connection, get_metas_data
from utils.formatters import format_compact_currency, format_currency


st.set_page_config(page_title="TV Comercial", layout="wide")


require_auth()
# display_navigation()  # Removido conforme solicitado - não mostrar barra de navegação
st.session_state['current_page'] = __file__


# Bloqueio de acesso: somente o usuário Odair pode ver esta página
current_user = get_current_user() or {}
email = (current_user.get('email') or "").lower()
if email not in {"odair.santos@grupoprati.com"}:
    st.warning("⚠️ Você não tem permissão para acessar a TV Comercial.")
    st.stop()

# ============================================================================
# CONFIGURAÇÕES DO CARROSSEL - SEM JAVASCRIPT, SEM RELOAD, APENAS PYTHON
# ============================================================================
CAROUSEL_SECTIONS = 5  # Número de seções/blocos (Velocímetro+Termômetro, Reservas, Leads Ativos, Distribuição por Mídia, Cancelamentos)
CAROUSEL_INTERVAL = 5  # Segundos por seção

# Inicializar estado do carrossel
if 'carousel_index' not in st.session_state:
    st.session_state.carousel_index = 0
if 'carousel_last_update' not in st.session_state:
    st.session_state.carousel_last_update = time.time()

# Verificar se precisa avançar (baseado em tempo decorrido)
current_time = time.time()
elapsed = current_time - st.session_state.carousel_last_update

# Se passou o intervalo, avança para próxima seção
if elapsed >= CAROUSEL_INTERVAL:
    st.session_state.carousel_index = (st.session_state.carousel_index + 1) % CAROUSEL_SECTIONS
    st.session_state.carousel_last_update = current_time
    # Forçar rerun para mostrar nova seção (preserva sessão)
    st.rerun()

# Título e informações removidos para liberar espaço na apresentação

# Placeholder principal que será atualizado com o conteúdo do bloco atual
carousel_placeholder = st.empty()

st.markdown(
    """
    <style>
        .stApp {
            background: radial-gradient(circle at 20% 20%, #1f2937 0%, #0f172a 45%, #060c1a 100%) !important;
            color: #f8fafc;
        }
        .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
        .stApp p, .stApp span, .stApp label, .stApp div, .stApp li {
            color: inherit;
        }
        .block-container {
            padding-top: 0 !important;
            padding-bottom: 0.75rem !important;
        }
        .tv-header {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 1.28rem;
            font-weight: 700;
            letter-spacing: 0.02em;
            margin: 0;
        }
        .tv-header-icon {
            font-size: 1.2rem;
            line-height: 1;
        }
        .tv-header-text {
            font-size: 1.08rem;
            font-weight: 600;
        }
        .tv-timestamp {
            font-size: 0.82rem;
            color: rgba(226, 232, 240, 0.75);
            margin: 0.05rem 0 0.35rem;
        }
        [data-testid="stHeader"] {
            background-color: transparent;
        }
        div[data-testid="stSidebar"] {
            background: rgba(8, 11, 23, 0.92);
        }
        div[data-testid="stSidebar"] * {
            color: #f8fafc !important;
        }
        .nav-container .stButton > button {
            background: rgba(15, 23, 42, 0.35);
            border: 1px solid rgba(148, 163, 184, 0.45);
            color: #f8fafc;
            backdrop-filter: blur(6px);
        }
        .nav-container .stButton > button:hover {
            background: rgba(59, 130, 246, 0.35);
            border-color: rgba(59, 130, 246, 0.75);
        }
        .tv-carousel-section {
            animation: fadeIn 0.8s ease-in-out;
            padding-bottom: 0 !important;
            margin-bottom: 0 !important;
        }
        .tv-carousel-section--reservas {
            padding-top: 4px;
        }
        .tv-carousel-section--reservas .tv-kpi-card {
            min-height: 150px;
            padding: 22px 20px;
        }
        .tv-carousel-section--reservas .tv-kpi-title-main {
            font-size: 0.95rem;
        }
        .tv-carousel-section--reservas .tv-kpi-value {
            font-size: 2.3rem;
        }
        .tv-carousel-section--reservas .tv-kpi-subtitle {
            font-size: 0.9rem;
        }
        .tv-carousel-section--split {
            padding-top: 2px;
        }
        .tv-carousel-section--split .tv-split-column {
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
        }
        .tv-carousel-section--split h3 {
            margin: 0 0 0.35rem;
            font-size: 0.9rem;
            font-weight: 600;
        }
        .tv-carousel-section--split .tv-kpi-card {
            min-height: 26px !important;
            padding: 3px 5px !important;
            margin-bottom: 2px !important;
            border-radius: 8px;
            box-shadow: 0 3px 8px rgba(0, 0, 0, 0.12);
            justify-content: flex-start;
            gap: 2px;
        }
        .tv-carousel-section--split .tv-kpi-card.tv-kpi-card--compact {
            min-height: 22px !important;
            padding: 2px 4px !important;
            margin-bottom: 1px !important;
        }
        .tv-carousel-section--split .tv-kpi-title-main {
            font-size: 0.6rem !important;
            line-height: 1.1;
        }
        .tv-carousel-section--split .tv-kpi-title {
            gap: 0px !important;
            margin-bottom: 0px !important;
        }
        .tv-carousel-section--split .tv-kpi-title-tag {
            font-size: 0.48rem !important;
            padding: 0px 3px !important;
        }
        .tv-carousel-section--split .tv-kpi-value {
            font-size: 1.0rem !important;
            margin-bottom: 0px !important;
            line-height: 1.1;
        }
        .tv-carousel-section--split .tv-kpi-subtitle {
            font-size: 0.54rem !important;
            line-height: 1.1;
        }
        .tv-carousel-section .tv-kpi-card.tv-kpi-card--compact {
            height: 85px !important;
            min-height: 85px !important;
            max-height: 85px !important;
            padding: 10px 12px !important;
            margin-bottom: 10px !important;
            display: flex !important;
            flex-direction: column !important;
            justify-content: space-between !important;
            align-items: center !important;
        }
        .tv-carousel-section .tv-kpi-card.tv-kpi-card--compact .tv-kpi-title {
            width: 100%;
            margin-bottom: 4px;
        }
        .tv-carousel-section .tv-kpi-card.tv-kpi-card--compact .tv-kpi-title-main {
            font-size: 0.72rem !important;
            line-height: 1.2;
        }
        .tv-carousel-section .tv-kpi-card.tv-kpi-card--compact .tv-kpi-title-tag {
            font-size: 0.58rem !important;
            padding: 2px 6px !important;
            margin-top: 2px;
        }
        .tv-carousel-section .tv-kpi-card.tv-kpi-card--compact .tv-kpi-value {
            font-size: 1.4rem !important;
            margin-bottom: 4px;
            line-height: 1.2;
        }
        .tv-carousel-section .tv-kpi-card.tv-kpi-card--compact .tv-kpi-subtitle {
            font-size: 0.68rem !important;
            line-height: 1.2;
            text-align: center;
        }
        .tv-carousel-section [data-testid="column"] {
            display: flex;
            flex-direction: column;
        }
        .tv-carousel-section [data-testid="column"] > div {
            display: flex;
            flex-direction: column;
        }
        /* CSS para o novo layout do bloco 0 (60/40 com cards dentro de cada coluna) */
        .tv-bloco-0-layout {
            width: 100%;
            max-width: 100%;
            padding-bottom: 0 !important;
            margin-bottom: 0 !important;
        }
        .tv-bloco-0-layout > div[data-testid="column-container"] {
            gap: 20px !important;
        }
        .tv-bloco-0-layout [data-testid="column"] {
            display: flex;
            flex-direction: column;
            gap: 0;
        }
        .tv-bloco-0-coluna {
            width: 100%;
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: flex-start;
            margin-bottom: 0 !important;
            padding-bottom: 0 !important;
        }
        /* Garantir que os gráficos ocupem o espaço necessário */
        .tv-bloco-0-coluna > div:first-of-type {
            flex-shrink: 0;
        }
        .tv-bloco-0-cards-wrapper {
            width: 100%;
            margin-top: 0;
            margin-bottom: 0 !important;
            flex-shrink: 0;
        }
        /* Garantir que os cards comecem na mesma linha horizontal usando flexbox */
        .tv-bloco-0-layout [data-testid="column"] {
            display: flex;
            flex-direction: column;
            justify-content: flex-start;
            align-items: stretch;
            margin-bottom: 0 !important;
            padding-bottom: 0 !important;
        }
        .tv-bloco-0-cards-wrapper > div[data-testid="column-container"] {
            gap: 20px !important;
        }
        .tv-bloco-0-cards-wrapper [data-testid="column"] {
            display: flex;
            flex-direction: column;
            flex: 1;
            min-width: 0;
        }
        .tv-bloco-0-cards-wrapper [data-testid="column"] > div {
            width: 100%;
            height: 100%;
            display: flex;
            flex-direction: column;
        }
        /* Cards do velocímetro - altura ~180px */
        .tv-bloco-0-cards-velocimetro .tv-kpi-card.tv-kpi-card--compact {
            height: 180px !important;
            min-height: 180px !important;
            max-height: 180px !important;
            padding: 12px 14px !important;
            margin-bottom: 0 !important;
            width: 100%;
            box-sizing: border-box;
            display: flex !important;
            flex-direction: column !important;
            justify-content: space-between !important;
            align-items: center !important;
        }
        .tv-bloco-0-cards-velocimetro .tv-kpi-card.tv-kpi-card--compact .tv-kpi-title {
            width: 100%;
            margin-bottom: 6px;
            text-align: center;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-wrap: wrap;
            gap: 5px;
        }
        .tv-bloco-0-cards-velocimetro .tv-kpi-card.tv-kpi-card--compact .tv-kpi-title-main {
            font-size: 0.125rem !important; /* 2px */
            line-height: 1.2;
            font-weight: 600;
        }
        .tv-bloco-0-cards-velocimetro .tv-kpi-card.tv-kpi-card--compact .tv-kpi-value {
            font-size: 0.275rem !important; /* 4.4px */
            margin-bottom: 6px;
            line-height: 1.3;
            font-weight: 700;
            text-align: center;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .tv-bloco-0-cards-velocimetro .tv-kpi-card.tv-kpi-card--compact .tv-kpi-subtitle {
            font-size: 0.1375rem !important; /* 2.2px */
            line-height: 1.2;
            text-align: center;
        }
        .tv-bloco-0-cards-velocimetro .tv-kpi-card.tv-kpi-card--compact .tv-kpi-title-tag {
            font-size: 0.0875rem !important; /* 1.4px */
            padding: 2px 4px !important;
            margin-left: 4px;
        }
        /* Cards do termômetro - altura ~160px */
        .tv-bloco-0-cards-termometro .tv-kpi-card.tv-kpi-card--compact {
            height: 160px !important;
            min-height: 160px !important;
            max-height: 160px !important;
            padding: 10px 12px !important;
            margin-bottom: 0 !important;
            width: 100%;
            box-sizing: border-box;
            display: flex !important;
            flex-direction: column !important;
            justify-content: space-between !important;
            align-items: center !important;
        }
        .tv-bloco-0-cards-termometro .tv-kpi-card.tv-kpi-card--compact .tv-kpi-title {
            width: 100%;
            margin-bottom: 6px;
            text-align: center;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-wrap: wrap;
            gap: 5px;
        }
        .tv-bloco-0-cards-termometro .tv-kpi-card.tv-kpi-card--compact .tv-kpi-title-main {
            font-size: 0.125rem !important; /* 2px */
            line-height: 1.2;
            font-weight: 600;
        }
        .tv-bloco-0-cards-termometro .tv-kpi-card.tv-kpi-card--compact .tv-kpi-value {
            font-size: 0.275rem !important; /* 4.4px */
            margin-bottom: 6px;
            line-height: 1.3;
            font-weight: 700;
            text-align: center;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .tv-bloco-0-cards-termometro .tv-kpi-card.tv-kpi-card--compact .tv-kpi-subtitle {
            font-size: 0.1375rem !important; /* 2.2px */
            line-height: 1.2;
            text-align: center;
        }
        .tv-bloco-0-cards-termometro .tv-kpi-card.tv-kpi-card--compact .tv-kpi-title-tag {
            font-size: 0.0875rem !important; /* 1.4px */
            padding: 2px 4px !important;
            margin-left: 4px;
        }
        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        .tv-carousel-hidden {
            display: none;
        }
        /* Ocultar sidebar e header para modo TV */
        .tv-mode div[data-testid="stSidebar"] {
            display: none !important;
        }
        .tv-mode [data-testid="stHeader"] {
            display: none !important;
        }
        .tv-mode .stDeployButton {
            display: none !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)


CONVERSAO_SITUACOES = {situacao.lower() for situacao in ["Distrato", "Mútuo", "Vendida"]}
CONVERSAO_SITUACOES_EXCLUIDAS = {situacao.lower() for situacao in ["Vencida"]}
SITUACOES_RESERVAS_EXCLUIDAS = {situacao.lower() for situacao in ["Mútuo", "Vencida"]}
TERMOMETRO_SITUACOES_INATIVAS = {situacao.lower() for situacao in ["Cancelada", "Vendida", "Distrato"]}
TERMOMETRO_DATA_INICIO = date(2025, 1, 1)

MESES_COLUNAS_2025 = {
    1: "meta_janeiro",
    2: "meta_fevereiro",
    3: "meta_marco",
    4: "meta_abril",
    5: "meta_maio",
    6: "meta_junho",
    7: "meta_julho",
    8: "meta_agosto",
    9: "meta_setembro",
    10: "meta_outubro",
    11: "meta_novembro",
    12: "meta_dezembro",
}

MESES_NOME_PT = {
    1: "janeiro",
    2: "fevereiro",
    3: "março",
    4: "abril",
    5: "maio",
    6: "junho",
    7: "julho",
    8: "agosto",
    9: "setembro",
    10: "outubro",
    11: "novembro",
    12: "dezembro",
}


LEADS_CORRETORES_REMOVIDOS = {
    "ODAIR DIAS DOS SANTOS",
    "SABRINA M. DA SILVA DOS SANTOS",
    "ALEX ANDERSON FRITZEN DA SILVA",
    "DAIANA PINHEIRO FÜHR",
    "GRAZIELE GODOI",
    "ROSANGELA CRISTINA BEVILAQUA",
    "ALAN RAFAEL GIOMBELLI",
    "MARCOS ROBERTO FERLA",
    "JULIANO RAFAEL SIMON",
    "HYORRANA LOPES",
    "SABRINA MARIA DA SILVA DOS SANTOS",
    "VANESSA CARDOSO NAZARIN",
    "ANTONY EDUARDO BIANCHINI GOUVEA",
    "TAYNÁ STURM",
    "RAYSSA NIELSEN",
    "ITALO CARLOS FERNANDES PERES",
    "MICHEL VASCONCELOS",
    "JOSE CARLOS DA SILVA",
    "SUELLEN SALOME GUIMARÃES MORO",
    "ANGELA MARIA ROCHA CENEDESE",
    "HENRIQUE MARTINS SPECK",
    "LAYANE OLIVEIRA DE SOUZA",
    "RODRIGO WRASSE",
    "NOELI KREIBICH",
    "JOSIBEL ALESSANDRA PALMEIRA",
    "TAMIRIS TEIXEIRA DE ANDRADE LUDVIG"
}

LEADS_FUNIL_MAP = {
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

LEADS_FUNIL_ETAPAS = [
    "Leads",
    "Em atendimento",
    "Visita realizada",
    "Com reserva"
]

# Mapeamento de índices hierárquicos das reservas (baseado na coluna índice 1-11)
# Situações "Mútuo" e "Vendida" não aparecem no dataset, mas mantemos a hierarquia
RESERVAS_SITUACAO_INDICES = {
    "Reserva": 1,
    "Reserva (7)": 1,
    "Crédito (CEF)": 2,
    "Crédito (CEF) (3)": 2,
    "Crédito reprovado (CEF)": 3,
    "Negociação": 4,
    "Negociação (5)": 4,
    "Mútuo": 5,
    "Análise de proposta (Diretoria)": 6,
    "Análise de proposta (Diretoria) (1)": 6,
    "Análise Diretoria": 6,
    "Análise Diretoria (Diretoria)": 6,
    "Crédito (Interno)": 7,
    "Crédito (Interno) (2)": 7,
    "Contrato - Elaboração": 8,
    "Contrato - Elaboração (2)": 8,
    "Contrato - Assinatura": 9,
    "Contrato - Assinatura (5)": 9,
    "Contrato Assinado": 10,
    "Contrato Assinado (1)": 10,
    "Sienge": 11,
    "Vendia": 12,
    "Vendida": 12,
}

# Lista de ordem para compatibilidade com código existente
RESERVAS_SITUACAO_ORDEM = sorted(RESERVAS_SITUACAO_INDICES.keys(), key=lambda x: RESERVAS_SITUACAO_INDICES[x])


def format_int_value(value: float | int) -> str:
    try:
        return f"{int(round(value)):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "0"


def map_lead_stage(prev_situacao: str | None, curr_situacao: str | None) -> str:
    curr_key = str(curr_situacao).strip().lower() if curr_situacao and pd.notna(curr_situacao) else None
    if curr_key == "descartado":
        if not prev_situacao or pd.isna(prev_situacao):
            return "Leads"
        prev_key = str(prev_situacao).strip().lower()
        return LEADS_FUNIL_MAP.get(prev_key, "Leads")
    if curr_key is None:
        return "Leads"
    return LEADS_FUNIL_MAP.get(curr_key, "Leads")


def apply_dark_theme(fig: go.Figure, margin_top: int = 60) -> go.Figure:
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#f8fafc",
        margin=dict(t=margin_top, b=40, l=0, r=0)
    )
    return fig


def normalize_reserva_label(label: str | None) -> str:
    if not isinstance(label, str):
        return ""
    return label.split(" (")[0].strip()


def get_reserva_indice(situacao: str | None) -> int:
    """
    Busca o índice de uma situação de reserva no dicionário.
    Tenta primeiro o nome exato, depois normaliza removendo números entre parênteses no final.
    """
    if not situacao or pd.isna(situacao):
        return 999
    
    situacao_str = str(situacao).strip()
    
    # Tentar busca exata primeiro
    if situacao_str in RESERVAS_SITUACAO_INDICES:
        return RESERVAS_SITUACAO_INDICES[situacao_str]
    
    # Normalizar removendo números entre parênteses no final
    # Remove múltiplos "(número)" no final (ex: "Crédito (CEF) (3)" -> "Crédito (CEF)")
    situacao_normalizada = re.sub(r'\s*\(\d+\)\s*$', '', situacao_str).strip()
    # Tenta novamente para remover múltiplos níveis
    while situacao_normalizada != re.sub(r'\s*\(\d+\)\s*$', '', situacao_normalizada).strip():
        situacao_normalizada = re.sub(r'\s*\(\d+\)\s*$', '', situacao_normalizada).strip()
    
    # Tentar busca normalizada
    if situacao_normalizada in RESERVAS_SITUACAO_INDICES:
        return RESERVAS_SITUACAO_INDICES[situacao_normalizada]
    
    # Tentar correspondência parcial: verificar se a situação normalizada corresponde
    # ao início de alguma chave do dicionário ou vice-versa
    for key in RESERVAS_SITUACAO_INDICES.keys():
        # Correspondência exata após normalização
        key_normalizada = re.sub(r'\s*\(\d+\)\s*$', '', key).strip()
        while key_normalizada != re.sub(r'\s*\(\d+\)\s*$', '', key_normalizada).strip():
            key_normalizada = re.sub(r'\s*\(\d+\)\s*$', '', key_normalizada).strip()
        
        if situacao_normalizada == key_normalizada:
            return RESERVAS_SITUACAO_INDICES[key]
        
        # Correspondência de início: se uma começa com a outra
        if situacao_normalizada.startswith(key_normalizada) or key_normalizada.startswith(situacao_normalizada):
            # Verificar se não é apenas uma substring acidental
            if len(situacao_normalizada) > 3 and len(key_normalizada) > 3:
                return RESERVAS_SITUACAO_INDICES[key]
    
    return 999


@st.cache_data(ttl=300)
def load_reservas_tv() -> pd.DataFrame:
    conn = get_md_connection()
    sql = """
        SELECT
            data_cad::DATE AS data_cad,
            data_venda::DATE AS data_venda,
            situacao,
            valor_contrato,
            COALESCE(NULLIF(TRIM(imobiliaria), ''), '—') AS imobiliaria
        FROM reservas.main.reservas_abril
        WHERE data_cad IS NOT NULL
    """
    return conn.run_query(sql)


@st.cache_data(ttl=300)
def load_vendas_house_overview(inicio: str, fim: str) -> pd.DataFrame:
    conn = get_md_connection()
    sql = """
        SELECT
            CASE
                WHEN POSITION('PRATI' IN UPPER(COALESCE(NULLIF(TRIM(imobiliaria), ''), '—'))) > 0 THEN 'Venda Interna (Prati)'
                ELSE 'Venda Externa (Imobiliárias)'
            END AS origem,
            COUNT(*) AS quantidade,
            SUM(value) AS valor_total,
            AVG(value) AS ticket_medio
        FROM informacoes_consolidadas.sienge_vendas_consolidadas
        WHERE value IS NOT NULL
          AND contractDate >= CAST(? AS DATE)
          AND contractDate <= CAST(? AS DATE)
        GROUP BY 1
    """
    return conn.run_query(sql, [inicio, fim])


@st.cache_data(ttl=300)
def load_vpl_geral(inicio: str, fim: str) -> pd.DataFrame:
    conn = get_md_connection()
    sql = """
        SELECT
            SUM(COALESCE(vpl_reserva, 0)) AS total_vpl_reserva,
            SUM(COALESCE(vpl_tabela, 0)) AS total_vpl_tabela
        FROM informacoes_consolidadas.sienge_vendas_consolidadas
        WHERE contractDate >= CAST(? AS DATE)
          AND contractDate <= CAST(? AS DATE)
          AND COALESCE(vpl_reserva, 0) <> 0
          AND COALESCE(vpl_tabela, 0) <> 0
    """
    return conn.run_query(sql, [inicio, fim])


@st.cache_data(ttl=300)
def load_leads_tv() -> pd.DataFrame:
    conn = get_md_connection()
    sql = """
        SELECT 
            Idlead AS idlead,
            CAST(data_cad AS DATE) AS data_cad,
            CAST(data_consolidada AS DATE) AS data_consolidada,
            COALESCE(NULLIF(TRIM(Situacao), ''), '—') AS situacao_nome,
            COALESCE(NULLIF(TRIM(nome_situacao_anterior_lead), ''), '—') AS nome_situacao_anterior_lead,
            COALESCE(NULLIF(TRIM(corretor_consolidado), ''), '—') AS corretor_consolidado,
            COALESCE(NULLIF(TRIM(midia_consolidada), ''), '—') AS midia_consolidada,
            COALESCE(NULLIF(TRIM(motivo_cancelamento_consolidada), ''), '') AS motivo_cancelamento_consolidada
        FROM reservas.main.cv_leads
        WHERE data_consolidada IS NOT NULL
    """
    try:
        return conn.run_query(sql)
    except Exception:
        sql_alt = sql.replace("reservas.main.cv_leads", "reservas.cv_leads")
        return conn.run_query(sql_alt)


@st.cache_data(ttl=300)
def load_vendas_mes(inicio: str, fim: str) -> float:
    conn = get_md_connection()
    sql = """
        SELECT COALESCE(SUM(value), 0) AS total_vendas
        FROM informacoes_consolidadas.sienge_vendas_consolidadas
        WHERE value IS NOT NULL
          AND contractDate >= CAST(? AS DATE)
          AND contractDate < CAST(? AS DATE)
    """
    df = conn.run_query(sql, [inicio, fim])
    if df.empty:
        return 0.0
    return float(df.loc[0, "total_vendas"] or 0.0)


@st.cache_data(ttl=300)
def load_metas() -> pd.DataFrame:
    return get_metas_data()


reservas_df = load_reservas_tv()

if reservas_df.empty:
    st.error("Não encontramos dados de reservas para exibir neste painel.")
    st.stop()


reservas_df['data_cad'] = pd.to_datetime(reservas_df['data_cad'], errors='coerce')
reservas_df['data_venda'] = pd.to_datetime(reservas_df.get('data_venda'), errors='coerce')
reservas_df['situacao'] = reservas_df['situacao'].astype(str).str.strip()
reservas_df['situacao_normalizada'] = reservas_df['situacao'].str.lower()
reservas_df['valor_contrato'] = pd.to_numeric(
    reservas_df.get('valor_contrato', pd.Series(dtype=float)),
    errors='coerce'
).fillna(0.0)
reservas_df['imobiliaria'] = reservas_df.get('imobiliaria', pd.Series(index=reservas_df.index, dtype=str)).fillna('—').astype(str).str.strip()
reservas_df['imobiliaria_normalizada'] = reservas_df['imobiliaria'].str.upper()


data_final_analise = datetime.now().date()
mask_periodo = (
    reservas_df['data_cad'].dt.date >= TERMOMETRO_DATA_INICIO
) & (
    reservas_df['data_cad'].dt.date <= data_final_analise
) & (
    ~reservas_df['situacao_normalizada'].isin(SITUACOES_RESERVAS_EXCLUIDAS)
)

reservas_base_df = reservas_df[mask_periodo].copy()

reservas_ativas_df = reservas_base_df[
    ~reservas_base_df['situacao_normalizada'].isin(TERMOMETRO_SITUACOES_INATIVAS)
].copy()


reservas_atuais_total = len(reservas_ativas_df)
valor_total_reservas = float(reservas_ativas_df['valor_contrato'].sum())

seis_meses_atras = data_final_analise - relativedelta(months=6)
reservas_6m_df = reservas_df[
    (reservas_df['data_cad'].dt.date >= seis_meses_atras)
    & (reservas_df['data_cad'].dt.date <= data_final_analise)
    & (~reservas_df['situacao_normalizada'].isin(CONVERSAO_SITUACOES_EXCLUIDAS))
].copy()


def calcular_conversao(df: pd.DataFrame) -> tuple[int, int, float]:
    total = len(df)
    convertidas = df['situacao_normalizada'].isin(CONVERSAO_SITUACOES).sum()
    taxa = (convertidas / total * 100) if total > 0 else 0.0
    return total, convertidas, taxa


# Calcular taxa de conversão geral usando últimos 6 meses
total_reservas_6m, reservas_convertidas_6m, taxa_conversao_geral = calcular_conversao(reservas_6m_df)
# Converter de percentual para decimal (função retorna em %)
taxa_conversao_geral = taxa_conversao_geral / 100


def calcular_tempo_medio_conversao(df: pd.DataFrame) -> tuple[float | None, int]:
    if df.empty or 'data_venda' not in df.columns:
        return None, 0

    mask_convertidas = (
        df['situacao_normalizada'].isin(CONVERSAO_SITUACOES)
        & df['data_venda'].notna()
        & df['data_cad'].notna()
    )

    convertidas_df = df.loc[mask_convertidas].copy()

    if convertidas_df.empty:
        return None, 0

    convertidas_df['dias_para_conversao'] = (
        convertidas_df['data_venda'] - convertidas_df['data_cad']
    ).dt.days

    convertidas_df = convertidas_df[convertidas_df['dias_para_conversao'] >= 0]

    if convertidas_df.empty:
        return None, 0

    tempo_medio = float(convertidas_df['dias_para_conversao'].mean())
    quantidade_base = int(convertidas_df.shape[0])

    return tempo_medio, quantidade_base


mask_prati = reservas_6m_df['imobiliaria_normalizada'].str.contains('PRATI', na=False)
reservas_prati_6m = reservas_6m_df[mask_prati]
reservas_outras_6m = reservas_6m_df[~mask_prati]

total_prati, convertidas_prati, taxa_prati = calcular_conversao(reservas_prati_6m)
total_outras, convertidas_outras, taxa_outras = calcular_conversao(reservas_outras_6m)

tempo_medio_prati_dias, tempo_medio_prati_base = calcular_tempo_medio_conversao(reservas_prati_6m)
tempo_medio_outras_dias, tempo_medio_outras_base = calcular_tempo_medio_conversao(reservas_outras_6m)

potencial_vendas_valor = valor_total_reservas * taxa_conversao_geral


coluna_meta_atual = MESES_COLUNAS_2025.get(datetime.now().month)
meta_total = 0.0

metas_df = load_metas()
if coluna_meta_atual and coluna_meta_atual in metas_df.columns:
    serie_meta = metas_df[coluna_meta_atual].astype(str)
    serie_meta = serie_meta.str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
    meta_total = float(pd.to_numeric(serie_meta, errors='coerce').fillna(0.0).sum())


inicio_mes_atual = datetime(datetime.now().year, datetime.now().month, 1)
inicio_proximo_mes = (pd.Timestamp(inicio_mes_atual) + pd.DateOffset(months=1)).to_pydatetime()

vendas_realizadas_valor = load_vendas_mes(
    inicio_mes_atual.strftime('%Y-%m-%d'),
    inicio_proximo_mes.strftime('%Y-%m-%d')
)


falta_para_meta_valor = max(meta_total - vendas_realizadas_valor, 0.0) if meta_total > 0 else 0.0
atingimento_percent = (vendas_realizadas_valor / meta_total * 100) if meta_total > 0 else 0.0
cobertura_percent = (potencial_vendas_valor / meta_total * 100) if meta_total > 0 else 0.0


if meta_total <= 0:
    status = "Sem meta cadastrada"
    interpretacao = "Não encontramos metas para o mês atual."
    acao = "Atualize os dados de metas ou verifique o cadastro do mês corrente."
    status_color = "#95a5a6"
elif cobertura_percent < 70:
    status = "Frio"
    interpretacao = "Reservas insuficientes para atingir a meta."
    acao = "Intensifique a prospecção e aumente o volume de reservas."
    status_color = "#1E90FF"
elif cobertura_percent <= 100:
    status = "Morno"
    interpretacao = "Em linha, mas ainda exige atenção."
    acao = "Foque em qualificação e follow-ups."
    status_color = "#f1c40f"
else:
    status = "Quente"
    interpretacao = "Carteira suficiente para atingir a meta."
    acao = "Mantenha o ritmo e priorize o fechamento."
    status_color = "#FF5722"


mes_referencia = MESES_NOME_PT.get(datetime.now().month, "mês atual")
mes_referencia_curto = mes_referencia.capitalize() if mes_referencia else "Mês atual"


periodo_inicio_str = TERMOMETRO_DATA_INICIO.strftime('%Y-%m-%d')
periodo_fim_str = data_final_analise.strftime('%Y-%m-%d')


house_raw_df = load_vendas_house_overview(periodo_inicio_str, periodo_fim_str)
house_data_available = False
house_df = pd.DataFrame()
total_valor_house = 0.0
valor_prati = 0.0
quantidade_prati = 0
taxa_house_percent = 0.0
ticket_prati = 0.0

if not house_raw_df.empty and house_raw_df['valor_total'].fillna(0).sum() > 0:
    house_df = house_raw_df.fillna({'quantidade': 0, 'valor_total': 0.0, 'ticket_medio': 0.0}).copy()
    total_valor_house = float(house_df['valor_total'].sum())
    valor_prati = float(house_df.loc[house_df['origem'] == 'Venda Interna (Prati)', 'valor_total'].sum())
    quantidade_prati = int(house_df.loc[house_df['origem'] == 'Venda Interna (Prati)', 'quantidade'].sum())
    taxa_house_percent = (valor_prati / total_valor_house * 100) if total_valor_house > 0 else 0.0
    ticket_prati = (valor_prati / quantidade_prati) if quantidade_prati > 0 else 0.0
    house_data_available = True


vpl_df = load_vpl_geral(periodo_inicio_str, periodo_fim_str)
vpl_data_available = False
total_vpl_reserva = 0.0
total_vpl_tabela = 0.0
vpl_percent = 0.0

if not vpl_df.empty:
    vpl_row = vpl_df.iloc[0]
    total_vpl_reserva = float(vpl_row.get('total_vpl_reserva', 0.0) or 0.0)
    total_vpl_tabela = float(vpl_row.get('total_vpl_tabela', 0.0) or 0.0)
    vpl_percent = ((total_vpl_reserva / total_vpl_tabela) - 1) * 100 if total_vpl_tabela > 0 else 0.0
    vpl_data_available = True


st.markdown(
    """
    <style>
        .tv-kpi-card {
            background: linear-gradient(135deg, rgba(255,255,255,0.12), rgba(255,255,255,0.04));
            border-radius: 18px;
            padding: 28px 24px;
            text-align: center;
            margin-bottom: 16px;
            box-shadow: 0 12px 24px rgba(0, 0, 0, 0.25);
            min-height: 170px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            align-items: center;
        }
        .tv-kpi-title {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 8px;
            margin-bottom: 18px;
            text-transform: uppercase;
        }
        .tv-kpi-title-main {
            font-size: 1.0rem;
            font-weight: 600;
            letter-spacing: 0.04em;
            color: rgba(255, 255, 255, 0.80);
        }
        .tv-kpi-title-tag {
            padding: 4px 12px;
            border-radius: 999px;
            font-size: 0.75rem;
            letter-spacing: 0.14em;
            background: rgba(15, 23, 42, 0.55);
            color: rgba(255, 255, 255, 0.75);
        }
        .tv-kpi-title-tag--empty {
            visibility: hidden;
        }
        .tv-kpi-value {
            font-size: 2.8rem;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 12px;
        }
        .tv-kpi-subtitle {
            font-size: 0.95rem;
            color: rgba(255, 255, 255, 0.68);
            font-weight: 500;
        }
        .tv-kpi-card--compact .tv-kpi-title {
            gap: 6px;
            margin-bottom: 8px;
        }
        .tv-kpi-card--compact .tv-kpi-value {
            margin-bottom: 10px;
        }
        .tv-status-badge {
            display: inline-flex;
            align-items: center;
            gap: 12px;
            padding: 12px 26px;
            border-radius: 999px;
            font-weight: 600;
            font-size: 1.2rem;
            color: #0b0b0b;
            margin: 12px 0 24px;
            box-shadow: 0 12px 24px rgba(0, 0, 0, 0.25);
        }
        .tv-status-context {
            font-size: 1.05rem;
            color: rgba(255, 255, 255, 0.78);
            margin-bottom: 6px;
        }
        .tv-midia-table {
            width: 100%;
            margin: 20px 0 14px;
            border-radius: 22px;
            background: linear-gradient(158deg, rgba(12, 23, 45, 0.96), rgba(6, 12, 26, 0.98));
            border: 1px solid rgba(88, 112, 164, 0.32);
            box-shadow: 0 22px 48px rgba(2, 10, 25, 0.38);
            overflow: hidden;
        }
        .tv-midia-table table {
            width: 100%;
            border-collapse: collapse;
            font-family: 'Manrope', sans-serif;
            color: rgba(236, 241, 250, 0.94);
            font-size: 1.05rem;
            letter-spacing: 0.015em;
        }
        .tv-midia-table thead tr {
            background: rgba(24, 34, 54, 0.94);
        }
        .tv-midia-table thead th {
            padding: 18px 22px;
            text-transform: uppercase;
            font-weight: 700;
            font-size: 1.14rem;
            letter-spacing: 0.08em;
            border-bottom: 1px solid rgba(148, 163, 184, 0.32);
            text-align: right;
        }
        .tv-midia-table thead th:first-child {
            text-align: left;
        }
        .tv-midia-table tbody td {
            padding: 18px 22px;
            border-bottom: 1px solid rgba(71, 85, 105, 0.24);
            text-align: right;
            font-weight: 500;
            color: rgba(236, 241, 250, 0.88);
            transition: background 0.22s ease, color 0.22s ease;
        }
        .tv-midia-table tbody td:first-child {
            text-align: left;
            font-weight: 600;
        }
        .tv-midia-table tbody tr:nth-child(odd) td {
            background: rgba(18, 26, 45, 0.78);
        }
        .tv-midia-table tbody tr:nth-child(even) td {
            background: rgba(11, 19, 33, 0.82);
        }
        .tv-midia-table tbody tr:last-child td {
            border-bottom: none;
        }
        .tv-midia-table tbody tr:hover td {
            background: rgba(59, 130, 246, 0.24);
            color: rgba(248, 250, 252, 0.95);
        }
    </style>
    """,
    unsafe_allow_html=True
)


def render_kpi(coluna, titulo: str, valor: str, subtitulo: str | None = None, tag: str | None = None, valor_color: str | None = None, compact: bool = False):
    tag_html = f'<span class="tv-kpi-title-tag">{tag}</span>' if tag else '<span class="tv-kpi-title-tag tv-kpi-title-tag--empty">—</span>'
    titulo_html = f"<span class='tv-kpi-title-main'>{titulo}</span>{tag_html}"
    valor_style = f" style='color:{valor_color};'" if valor_color else ""
    card_class = "tv-kpi-card tv-kpi-card--compact" if compact else "tv-kpi-card"
    coluna.markdown(
        f"""
        <div class=\"{card_class}\">
            <div class=\"tv-kpi-title\">{titulo_html}</div>
            <div class=\"tv-kpi-value\"{valor_style}>{valor}</div>
            {f'<div class=\"tv-kpi-subtitle\">{subtitulo}</div>' if subtitulo else ''}
        </div>
        """,
        unsafe_allow_html=True
    )


def render_velocimetro_metas(meta_valor: float, vendas_valor: float, atingimento_percent: float, mes_referencia: str):
    """Renderiza um velocímetro com os 3 KPIs principais de metas"""
    # Barra sempre verde
    cor_barra = '#22c55e'  # Sempre verde
    
    # Cor do valor de vendas: verde se >= 100%, vermelho caso contrário
    cor_vendas = '#22c55e' if atingimento_percent >= 100 else '#ef4444'
    
    # Formatar valor de vendas realizado para o centro
    vendas_formatada = format_compact_currency(vendas_valor) if vendas_valor > 0 else "—"
    
    fig = go.Figure(go.Indicator(
        mode = "gauge",
        value = atingimento_percent,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "", 'font': {'size': 22, 'color': '#f8fafc', 'family': 'Manrope, sans-serif'}},
        gauge = {
            'axis': {'range': [None, 150], 'tickwidth': 2, 'tickcolor': '#f8fafc', 'tickfont': {'size': 12, 'color': '#f8fafc'}},
            'bar': {'color': cor_barra, 'thickness': 1.0, 'line': {'width': 0}},
            'bgcolor': "rgba(15, 23, 42, 0.3)",
            'borderwidth': 2,
            'bordercolor': "rgba(148, 163, 184, 0.5)",
            'steps': [
                {'range': [0, 70], 'color': 'rgba(30, 144, 255, 0.3)'},  # Azul mais transparente
                {'range': [70, 100], 'color': 'rgba(241, 196, 15, 0.3)'},  # Amarelo mais transparente
                {'range': [100, 150], 'color': 'rgba(255, 87, 34, 0.3)'}  # Laranja mais transparente
            ],
            'threshold': {
                'line': {'color': "rgba(255, 255, 255, 0.9)", 'width': 5},
                'thickness': 0.75,
                'value': 100
            }
        }
    ))
    
    # Formatar valor da meta
    meta_formatada = format_compact_currency(meta_valor) if meta_valor > 0 else "—"
    
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#f8fafc", family='Manrope, sans-serif'),
        height=200,
        margin=dict(t=5, b=30, l=30, r=30),
        autosize=False,
        annotations=[
            dict(
                text=f"Meta: {meta_formatada}",
                x=0.98,
                y=0.95,
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(size=14, color='rgba(248, 250, 252, 0.9)', family='Manrope, sans-serif'),
                align="right"
            ),
            dict(
                text=f"%Realiz: <b>{atingimento_percent:.1f}%</b>",
                x=0.98,
                y=0.88,
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(size=14, color=cor_vendas, family='Manrope, sans-serif'),
                align="right"
            ),
            dict(
                text=vendas_formatada,
                x=0.5,
                y=0.08,
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(size=48, color='#f8fafc', family='Manrope, sans-serif'),
                align="center"
            )
        ]
    )
    
    return fig


def render_midia_table_html(dataframe: pd.DataFrame):
    if dataframe.empty:
        return

    header_cells = ''.join(f"<th>{col}</th>" for col in dataframe.columns)
    body_rows = []
    for _, row in dataframe.iterrows():
        cells = ''.join(f"<td>{row[col]}</td>" for col in dataframe.columns)
        body_rows.append(f"<tr>{cells}</tr>")

    table_html = f"""
        <div class="tv-midia-table">
            <table>
                <thead><tr>{header_cells}</tr></thead>
                <tbody>{''.join(body_rows)}</tbody>
            </table>
        </div>
    """

    st.markdown(table_html, unsafe_allow_html=True)


# ============================================================================
# FUNÇÕES DE RENDERIZAÇÃO DOS BLOCOS DO CARROSSEL
# ============================================================================

def render_bloco_0():
    """Bloco 0: Velocímetro de Metas + Termômetro de Vendas"""
    st.markdown('<div class="tv-carousel-section tv-bloco-0-layout">', unsafe_allow_html=True)
    
    # Layout principal: 40% (velocímetro) e 60% (cards)
    col_principal_esq, col_principal_dir = st.columns([0.4, 0.6], gap="large")
    
    # Preparar dados dos cards
    mes_tag = mes_referencia_curto.upper()
    ano_tag = str(TERMOMETRO_DATA_INICIO.year)
    
    falta_color = None
    if meta_total > 0:
        falta_color = "#22c55e" if falta_para_meta_valor == 0 else "#ef4444"

    taxa_house_color = None
    if house_data_available:
        taxa_house_color = "#22c55e" if taxa_house_percent >= 30 else "#ef4444"

    vpl_color = None
    if vpl_data_available:
        if vpl_percent > 0:
            vpl_color = "#22c55e"
        elif vpl_percent < 0:
            vpl_color = "#ef4444"
    
    # COLUNA ESQUERDA (40%): Velocímetro
    with col_principal_esq:
        st.markdown('<div class="tv-bloco-0-coluna">', unsafe_allow_html=True)
        
        # Título e Velocímetro
        st.markdown("<h3 style='margin: 0 0 0; text-align: center; font-size: 1.2rem;'>🎯 Velocímetro de Vendas</h3>", unsafe_allow_html=True)
        fig_velocimetro = render_velocimetro_metas(meta_total, vendas_realizadas_valor, atingimento_percent, mes_referencia_curto.capitalize())
        st.plotly_chart(fig_velocimetro, use_container_width=True)
        
        # Tag do mês formatado como nos cards
        st.markdown(
            f"<div style='text-align: center; margin-top: -45px;'><span style='display: inline-block; padding: 4px 12px; border-radius: 999px; background: rgba(15, 23, 42, 0.55); color: rgba(255, 255, 255, 0.75); font-size: 11px; font-family: Manrope, sans-serif; letter-spacing: 0.14em;'>{mes_referencia_curto.upper()}</span></div>",
            unsafe_allow_html=True
        )
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # COLUNA DIREITA (60%): Cards de vendas
    with col_principal_dir:
        st.markdown('<div class="tv-bloco-0-coluna">', unsafe_allow_html=True)
        
        # 3 cards de vendas lado a lado
        st.markdown('<div class="tv-bloco-0-cards-wrapper tv-bloco-0-cards-velocimetro">', unsafe_allow_html=True)
        cards_vendas = st.columns(3, gap="small")
        render_kpi(cards_vendas[0], "Falta para Meta", format_compact_currency(falta_para_meta_valor) if meta_total > 0 else "—", "Gap remanescente", tag=mes_tag, valor_color=falta_color, compact=True)
        render_kpi(cards_vendas[1], "🏠 Taxa House (valor)", f"{taxa_house_percent:.1f}%" if house_data_available else "—", "Meta: 30% vendas internas", tag=ano_tag, valor_color=taxa_house_color, compact=True)
        render_kpi(cards_vendas[2], "Porcentagem VPL Geral", f"{vpl_percent:.2f}%" if vpl_data_available else "—", "Meta: VPL Positivo", tag=ano_tag, valor_color=vpl_color, compact=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Remover espaçamento padrão do Streamlit após as colunas
    st.markdown('<style>div[data-testid="column-container"]:last-child { margin-bottom: 0 !important; }</style>', unsafe_allow_html=True)
    
    # Termômetro ocupando toda a largura da página (fora das colunas principais)
    escala_max = 150
    indicador_percentual = max(0.0, min(cobertura_percent, escala_max))
    indicador_posicao = indicador_percentual / escala_max * 100
    largura_preenchida = min(max(cobertura_percent / escala_max, 0.0), 1.0) * 100

    barra_escala_html = f"""
    <div style='margin-top:-20px; position:relative; padding-top:0px; height:300px; display:flex; flex-direction:column; justify-content:flex-start; align-items:flex-start; width:100%; padding-left: 5%;'>
      <h3 style='margin: 0 0 4.5rem; text-align: left; font-size: 1.4rem; width: 90%; white-space: nowrap;'>🌡️ Termômetro de Vendas</h3>
      <div style='position:relative; margin-bottom:8px; width:90%; max-width:90%;'>
        <div style='position:absolute; bottom:0; left:{indicador_posicao}%; transform:translateX(-50%); display:flex; flex-direction:column; align-items:center; z-index:10;'>
          <div style='font-size:0.85rem;font-weight:700;color:{status_color};margin-bottom:2px;background:rgba(11,11,11,0.85);padding:3px 12px;border-radius:999px;'>{cobertura_percent:.1f}%</div>
          <div style='width:0;height:0;border-left:12px solid transparent;border-right:12px solid transparent;border-bottom:16px solid {status_color};'></div>
        </div>
      </div>
      <div style='position:relative; border-radius:14px; overflow:hidden; height:60px; box-shadow:0 0 16px rgba(0,0,0,0.35); max-width:90%; width:90%;'>
        <div style='display:flex; height:100%; font-size:1.05rem; width:100%;'>
          <div style='flex:70; max-width:70%; background:#1E90FF; color:#ffffff; display:flex; flex-direction:column; align-items:center; justify-content:center; font-weight:600; opacity:{1 if cobertura_percent >= 0 else 0.25};'>
            Frio
            <span style="font-weight:400;font-size:0.85rem;opacity:0.85;">&lt; 70%</span>
          </div>
          <div style='flex:30; max-width:30%; background:#f1c40f; color:#0b0b0b; display:flex; flex-direction:column; align-items:center; justify-content:center; font-weight:700; opacity:{1 if cobertura_percent >= 70 else 0.3};'>
            Morno
            <span style="font-weight:500;font-size:0.85rem;opacity:0.85;">70% – 100%</span>
          </div>
          <div style='flex:50; max-width:50%; background:#FF5722; color:#ffffff; display:flex; flex-direction:column; align-items:center; justify-content:center; font-weight:600; opacity:{1 if cobertura_percent >= 100 else 0.3};'>
            Quente
            <span style="font-weight:400;font-size:0.85rem;opacity:0.85;">&gt; 100%</span>
          </div>
        </div>
        <div style='position:absolute; top:0; bottom:0; left:0; width:{largura_preenchida}%; background:rgba(255,255,255,0.15); mix-blend-mode:screen;'></div>
        <div style='position:absolute; top:0; bottom:0; left:{indicador_posicao}%; transform:translateX(-50%); width:7px; background:#ffffff; box-shadow:0 0 10px rgba(0,0,0,0.55); border-radius:999px;'></div>
      </div>
    </div>
    """

    st.markdown(barra_escala_html, unsafe_allow_html=True)
    
    # Cards abaixo ocupando toda a largura da página (fora das colunas)
    st.markdown('<div style="margin-top: 20px;">', unsafe_allow_html=True)
    
    # Lógica de cor para "Potencial de Vendas"
    potencial_color = None
    if meta_total > 0:
        if potencial_vendas_valor < meta_total and vendas_realizadas_valor < meta_total:
            potencial_color = "#ef4444"  # Vermelho
        else:
            potencial_color = "#22c55e"  # Verde
    
    # 4 cards ocupando toda a largura
    st.markdown('<div class="tv-bloco-0-cards-wrapper tv-bloco-0-cards-termometro">', unsafe_allow_html=True)
    cards_dir = st.columns([0.25, 0.25, 0.25, 0.25], gap="small")
    tag_6m = "6 MESES"
    render_kpi(cards_dir[0], "Taxa de Conversão Geral", f"{taxa_conversao_geral * 100:.1f}%", f"{format_int_value(reservas_convertidas_6m)}/{format_int_value(total_reservas_6m)}", tag=tag_6m, compact=True)
    render_kpi(cards_dir[1], "Reservas Atuais", f"{reservas_atuais_total}", "Reservas ativas no pipeline", compact=True)
    render_kpi(cards_dir[2], "Potencial de Vendas", format_compact_currency(potencial_vendas_valor), "Reservas x taxa de conversão", valor_color=potencial_color, compact=True)
    render_kpi(cards_dir[3], "Cobertura da Meta", f"{cobertura_percent:.1f}%", "Potencial versus meta", tag=status.upper(), valor_color=status_color, compact=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)  # Fecha tv-carousel-section

def render_bloco_1():
    """Bloco 1: KPIs Adicionais (cards movidos)"""
    st.markdown('<div class="tv-carousel-section">', unsafe_allow_html=True)
    st.markdown("## 📊 Indicadores Adicionais")
    
    linha_um = st.columns(3)
    mes_tag = mes_referencia_curto.upper()
    ano_tag = str(TERMOMETRO_DATA_INICIO.year)
    
    falta_color = None
    if meta_total > 0:
        falta_color = "#22c55e" if falta_para_meta_valor == 0 else "#ef4444"

    taxa_house_color = None
    if house_data_available:
        taxa_house_color = "#22c55e" if taxa_house_percent >= 30 else "#ef4444"

    vpl_color = None
    if vpl_data_available:
        if vpl_percent > 0:
            vpl_color = "#22c55e"
        elif vpl_percent < 0:
            vpl_color = "#ef4444"

    render_kpi(linha_um[0], "Falta para Meta", format_compact_currency(falta_para_meta_valor) if meta_total > 0 else "—", "Gap remanescente", tag=mes_tag, valor_color=falta_color, compact=True)
    render_kpi(linha_um[1], "🏠 Taxa House (valor)", f"{taxa_house_percent:.1f}%" if house_data_available else "—", "Meta: 30% vendas internas", tag=ano_tag, valor_color=taxa_house_color, compact=True)
    render_kpi(linha_um[2], "Porcentagem VPL Geral", f"{vpl_percent:.2f}%" if vpl_data_available else "—", "Meta: VPL Positivo", tag=ano_tag, valor_color=vpl_color, compact=True)
    
    st.markdown("---")
    
    linha_termometro = st.columns(4)
    tag_6m = "6 MESES"
    render_kpi(linha_termometro[0], "Taxa de Conversão Geral", f"{taxa_conversao_geral * 100:.1f}%", f"{format_int_value(reservas_convertidas_6m)}/{format_int_value(total_reservas_6m)}", tag=tag_6m)
    render_kpi(linha_termometro[1], "Reservas Atuais", f"{reservas_atuais_total}", "Reservas ativas no pipeline")
    render_kpi(linha_termometro[2], "Potencial de Vendas", format_compact_currency(potencial_vendas_valor), "Reservas x taxa de conversão")
    render_kpi(linha_termometro[3], "Cobertura da Meta", f"{cobertura_percent:.1f}%", "Potencial versus meta")
    
    st.markdown('</div>', unsafe_allow_html=True)


def render_bloco_reservas():
    """Bloco Reservas: Reservas - Situação Atual"""
    st.markdown('<div class="tv-carousel-section">', unsafe_allow_html=True)
    st.markdown("## 🧾 Reservas - Situação Atual")

    reservas_status_df = reservas_ativas_df.copy()

    if reservas_status_df.empty:
        st.info("Sem reservas ativas para exibir no momento.")
    else:
        reservas_status_df['situacao'] = reservas_status_df['situacao'].astype(str).str.strip()

        status_counts = (
            reservas_status_df.groupby('situacao', dropna=False)
            .agg(
                Quantidade=('situacao', 'size'),
                Valor=('valor_contrato', 'sum')
            )
            .reset_index()
        )
        status_counts = status_counts.rename(columns={'situacao': 'Situacao'})

        if status_counts.empty:
            st.info("Nenhuma situação ativa encontrada no período.")
        else:
            status_counts['SituacaoNormalizada'] = status_counts['Situacao'].apply(normalize_reserva_label)
            status_counts['Indice'] = status_counts['Situacao'].apply(get_reserva_indice)
            # Ordenar por índice (crescente) e depois por situação (alfabética)
            status_counts = status_counts.sort_values(['Indice', 'Situacao'], ascending=[True, True]).reset_index(drop=True)

            total_reservas_status = int(status_counts['Quantidade'].sum())
            status_counts['Percentual'] = status_counts['Quantidade'].apply(
                lambda v: round(v / total_reservas_status * 100, 1) if total_reservas_status > 0 else 0.0
            )
            status_counts['Valor'] = status_counts['Valor'].fillna(0.0)
            status_counts['ValorFormatado'] = status_counts['Valor'].apply(format_compact_currency)
            status_counts['QuantidadeFormatada'] = status_counts['Quantidade'].apply(format_int_value)

            # Ordem esperada: índice 1 no topo
            # No Plotly com gráfico horizontal, precisamos garantir que a ordem seja respeitada
            # Criar uma coluna de ordem para garantir a ordenação correta
            ordem_dict = {situacao: idx for idx, situacao in enumerate(status_counts['Situacao'].tolist())}
            status_counts['_ordem_plot'] = status_counts['Situacao'].map(ordem_dict)
            
            # Ordem para o categoryarray: índice 1 deve aparecer no topo
            # No Plotly com gráfico horizontal, a primeira entrada do array aparece no topo
            # Como ordenamos por índice crescente (1 primeiro), precisamos inverter para o topo
            ordem_situacoes = status_counts['Situacao'].tolist()
            ordem_plotly = list(reversed(ordem_situacoes))  # Inverter para índice 1 no topo

            paleta_reservas = ['#16295f', '#1e3a8a', '#2563eb', '#3b82f6', '#60a5fa', '#7c3aed', '#a855f7']
            color_map = {
                situacao: paleta_reservas[i % len(paleta_reservas)]
                for i, situacao in enumerate(status_counts['Situacao'].tolist())
            }

            fig_reserva_status = px.bar(
                status_counts,
                x='Quantidade',
                y='Situacao',
                orientation='h',
                text='ValorFormatado',
                custom_data=['QuantidadeFormatada', 'ValorFormatado'],
                color='Situacao',
                color_discrete_map=color_map,
                title='Distribuição de Reservas por Situação'
            )
            fig_reserva_status = apply_dark_theme(fig_reserva_status, margin_top=35)
            fig_reserva_status.update_layout(
                height=520,
                margin=dict(t=35, b=20, l=10, r=10),
                showlegend=False,
                title=dict(
                    text='Distribuição de Reservas por Situação',
                    x=0,
                    xanchor='left',
                    font=dict(size=18, color='#f8fafc', family='Manrope, sans-serif')
                ),
                yaxis=dict(
                    categoryorder='array',
                    categoryarray=ordem_plotly,
                    title='',
                    tickfont=dict(size=14, color='rgba(248,250,252,0.88)', family='Manrope, sans-serif')
                ),
                xaxis=dict(
                    showticklabels=False,
                    showgrid=False,
                    zeroline=False,
                    title=''
                ),
                bargap=0.25
            )
            max_quantidade = status_counts['Quantidade'].max() if not status_counts.empty else 0
            offset_anotacao = max(max_quantidade * 0.012, 0.3)
            fig_reserva_status.update_traces(
                texttemplate='<b>%{text}</b>',
                textposition='inside',
                insidetextanchor='middle',
                textfont=dict(color='#f8fafc', size=16, family='Manrope, sans-serif'),
                hovertemplate='<b>%{y}</b><br>Quantidade: %{customdata[0]}<br>Valor: %{text}<extra></extra>'
            )
            for _, linha in status_counts.iterrows():
                fig_reserva_status.add_annotation(
                    x=float(linha['Quantidade']) + offset_anotacao,
                    y=linha['Situacao'],
                    text=linha['QuantidadeFormatada'],
                    showarrow=False,
                    font=dict(size=13, color='#f8fafc', family='Manrope, sans-serif'),
                    xanchor='left',
                    bgcolor='rgba(15,23,42,0.82)',
                    bordercolor='rgba(148, 163, 184, 0.45)',
                    borderwidth=1,
                    borderpad=5
                )
            st.plotly_chart(fig_reserva_status, use_container_width=True)

            linha_cards = st.columns(4)
            tag_6m = "6 MESES"

            valor_conversao_prati = f"{taxa_prati:.1f}%" if total_prati > 0 else "—"
            sub_prati = (
                f"{format_int_value(convertidas_prati)}/{format_int_value(total_prati)}"
                if total_prati > 0 else "Sem registros no período"
            )

            valor_conversao_outras = f"{taxa_outras:.1f}%" if total_outras > 0 else "—"
            sub_outras = (
                f"{format_int_value(convertidas_outras)}/{format_int_value(total_outras)}"
                if total_outras > 0 else "Sem registros no período"
            )

            tempo_prati_display = f"{tempo_medio_prati_dias:.1f} dias" if tempo_medio_prati_dias is not None else "—"
            sub_tempo_prati = (
                f"Base: {format_int_value(tempo_medio_prati_base)} conv."
                if tempo_medio_prati_base > 0 else "Sem conversões com data de venda"
            )

            tempo_outras_display = f"{tempo_medio_outras_dias:.1f} dias" if tempo_medio_outras_dias is not None else "—"
            sub_tempo_outras = (
                f"Base: {format_int_value(tempo_medio_outras_base)} conv."
                if tempo_medio_outras_base > 0 else "Sem conversões com data de venda"
            )

            render_kpi(
                linha_cards[0],
                "Conversão Prati",
                valor_conversao_prati,
                sub_prati,
                tag=tag_6m,
                compact=True
            )
            render_kpi(
                linha_cards[1],
                "Conversão Outras Imobiliárias",
                valor_conversao_outras,
                sub_outras,
                tag=tag_6m,
                compact=True
            )
            render_kpi(
                linha_cards[2],
                "Tempo Médio Conversão Prati",
                tempo_prati_display,
                sub_tempo_prati,
                tag=tag_6m,
                compact=True
            )
            render_kpi(
                linha_cards[3],
                "Tempo Médio Conversão Outras",
                tempo_outras_display,
                sub_tempo_outras,
                tag=tag_6m,
                compact=True
            )
    st.markdown('</div>', unsafe_allow_html=True)


def render_bloco_2():
    """Bloco 2: Leads Ativos (gráfico e card)"""
    st.markdown('<div class="tv-carousel-section">', unsafe_allow_html=True)
    st.markdown("## 📈 Leads Ativos")

    leads_base_df = load_leads_tv()

    if leads_base_df.empty:
        st.info("Não foi possível carregar dados de leads para o período analisado.")
    else:
        leads_tv_df = leads_base_df.copy()
        leads_tv_df['data_consolidada'] = pd.to_datetime(leads_tv_df['data_consolidada'], errors='coerce')
        leads_tv_df = leads_tv_df[leads_tv_df['data_consolidada'].notna()]
        leads_tv_df = leads_tv_df[
            (leads_tv_df['data_consolidada'].dt.date >= TERMOMETRO_DATA_INICIO) &
            (leads_tv_df['data_consolidada'].dt.date <= data_final_analise)
        ].copy()

        if leads_tv_df.empty:
            st.info("Sem leads no período de análise selecionado.")
        else:
            leads_tv_df['corretor_consolidado'] = leads_tv_df['corretor_consolidado'].fillna('—')
            leads_tv_df = leads_tv_df[~leads_tv_df['corretor_consolidado'].str.upper().isin(LEADS_CORRETORES_REMOVIDOS)]

            leads_tv_df['funil_etapa'] = leads_tv_df.apply(
                lambda row: map_lead_stage(row['nome_situacao_anterior_lead'], row['situacao_nome']), axis=1
            )

            situacoes_excluidas = {"descartado", "em pré-cadastro", "venda realizada", "vencido"}
            leads_tv_df['situacao_normalizada'] = leads_tv_df['situacao_nome'].str.lower().str.strip()
            leads_ativos_df = leads_tv_df[~leads_tv_df['situacao_normalizada'].isin(situacoes_excluidas)].copy()

            total_leads_ativos = int(leads_ativos_df.shape[0])

            if total_leads_ativos == 0:
                st.info("Sem leads ativos no período de análise selecionado.")
            else:
                funil_etapas_ativos = LEADS_FUNIL_ETAPAS
                etapa_counts = [
                    int((leads_ativos_df['funil_etapa'] == etapa).sum())
                    for etapa in funil_etapas_ativos
                ]
                percentuais = [
                    (valor / total_leads_ativos * 100) if total_leads_ativos > 0 else 0.0
                    for valor in etapa_counts
                ]
                max_valor = max(etapa_counts) if etapa_counts else 0
                offset_anotacao = max(max_valor * 0.015, 3)
                textos_percentual = [f"{percentual:.1f}%" for percentual in percentuais]

                fig_leads = go.Figure()
                fig_leads.add_trace(go.Bar(
                    y=funil_etapas_ativos,
                    x=etapa_counts,
                    orientation='h',
                    text=textos_percentual,
                    texttemplate='<b>%{text}</b>',
                    textposition='inside',
                    insidetextanchor='middle',
                    textfont=dict(color='#f8fafc', size=17, family='Manrope, sans-serif'),
                    marker=dict(
                        color=['#60a5fa', '#3b82f6', '#2563eb', '#7c3aed'],
                        line=dict(width=0)
                    ),
                    customdata=percentuais,
                    hovertemplate="<b>%{y}</b><br>Quantidade: %{x:,}<br>Participação: %{customdata:.1f}%<extra></extra>",
                    cliponaxis=False
                ))

                for etapa, valor in zip(funil_etapas_ativos, etapa_counts):
                    fig_leads.add_annotation(
                        x=valor + offset_anotacao,
                        y=etapa,
                        text=format_int_value(valor),
                        showarrow=False,
                        font=dict(size=15, color='#f8fafc', family='Manrope, sans-serif'),
                        xanchor='left',
                        bgcolor='rgba(15,23,42,0.78)',
                        bordercolor='rgba(148,163,184,0.45)',
                        borderwidth=1,
                        borderpad=5
                    )

                range_max = max_valor + offset_anotacao * 3 if max_valor else 1
                fig_leads.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#f8fafc"),
                    height=480,
                    margin=dict(t=35, b=18, l=135, r=40),
                    showlegend=False,
                    xaxis=dict(
                        showgrid=False,
                        zeroline=False,
                        showticklabels=False,
                        range=[0, range_max]
                    ),
                    yaxis=dict(
                        showgrid=False,
                        tickfont=dict(size=15, color='rgba(248,250,252,0.88)', family='Manrope, sans-serif'),
                        categoryorder='array',
                        categoryarray=list(reversed(funil_etapas_ativos))
                    ),
                    hoverlabel=dict(bgcolor='rgba(15,23,42,0.92)', font_size=13, font_family='Manrope, sans-serif')
                )
                st.plotly_chart(fig_leads, use_container_width=True)

                # Espaçamento para mover texto para baixo (reduzido para ficar um pouco mais para cima)
                st.markdown('<br><br><br><br><br>', unsafe_allow_html=True)

                # Mostrar total de leads ativos em formato de texto (duas linhas)
                st.caption(f"Total Leads Ativos: {format_int_value(total_leads_ativos)}")
                st.caption(f"Período analisado: {TERMOMETRO_DATA_INICIO.strftime('%d/%m/%Y')} até {data_final_analise.strftime('%d/%m/%Y')}")
    
    st.markdown('</div>', unsafe_allow_html=True)


def render_bloco_cancelamentos():
    """Bloco Cancelamentos: Cancelamentos por Motivo"""
    st.markdown('<div class="tv-carousel-section">', unsafe_allow_html=True)
    st.markdown("## ❌ Cancelamentos por Motivo")
    
    leads_base_df = load_leads_tv()
    
    if leads_base_df.empty:
        st.info("Não foi possível carregar dados de leads para análise de cancelamentos.")
    else:
        leads_tv_df = leads_base_df.copy()
        leads_tv_df['data_consolidada'] = pd.to_datetime(leads_tv_df['data_consolidada'], errors='coerce')
        leads_tv_df = leads_tv_df[leads_tv_df['data_consolidada'].notna()]
        leads_tv_df = leads_tv_df[
            (leads_tv_df['data_consolidada'].dt.date >= TERMOMETRO_DATA_INICIO) &
            (leads_tv_df['data_consolidada'].dt.date <= data_final_analise)
        ].copy()
        
        if leads_tv_df.empty:
            st.info("Sem dados de leads para análise de cancelamentos.")
        else:
            # Filtrar apenas cancelamentos (onde há motivo de cancelamento)
            cancelamentos_df = leads_tv_df[
                (leads_tv_df['motivo_cancelamento_consolidada'].notna()) &
                (leads_tv_df['motivo_cancelamento_consolidada'] != '') &
                (leads_tv_df['motivo_cancelamento_consolidada'].str.strip() != '')
            ].copy()
            
            if cancelamentos_df.empty:
                st.info("Nenhum cancelamento encontrado no período selecionado.")
            else:
                # Contar cancelamentos por motivo
                motivo_counts = (
                    cancelamentos_df.groupby('motivo_cancelamento_consolidada')
                    .size()
                    .reset_index(name='Quantidade')
                    .sort_values('Quantidade', ascending=False)
                )
                motivo_counts = motivo_counts.rename(columns={'motivo_cancelamento_consolidada': 'Motivo'})
                
                total_cancelamentos = int(motivo_counts['Quantidade'].sum())
                motivo_counts['Percentual'] = motivo_counts['Quantidade'].apply(
                    lambda v: round(v / total_cancelamentos * 100, 1) if total_cancelamentos > 0 else 0.0
                )
                motivo_counts['QuantidadeFormatada'] = motivo_counts['Quantidade'].apply(format_int_value)
                
                # Criar gráfico usando go.Figure (mais simples e confiável)
                paleta_cancelamentos = ['#ef4444', '#f87171', '#fca5a5', '#dc2626', '#b91c1c', '#991b1b', '#7f1d1d']
                max_valor = motivo_counts['Quantidade'].max() if not motivo_counts.empty else 0
                offset_anotacao = max(max_valor * 0.015, 3)
                
                fig_cancelamentos = go.Figure()
                fig_cancelamentos.add_trace(go.Bar(
                    y=motivo_counts['Motivo'].tolist(),
                    x=motivo_counts['Quantidade'].tolist(),
                    orientation='h',
                    text=motivo_counts['Percentual'].apply(lambda x: f"{x:.1f}%").tolist(),
                    texttemplate='<b>%{text}</b>',
                    textposition='inside',
                    insidetextanchor='middle',
                    textfont=dict(color='#f8fafc', size=16, family='Manrope, sans-serif'),
                    marker=dict(
                        color=[paleta_cancelamentos[i % len(paleta_cancelamentos)] for i in range(len(motivo_counts))],
                        line=dict(width=0)
                    ),
                    customdata=motivo_counts['QuantidadeFormatada'].tolist(),
                    hovertemplate="<b>%{y}</b><br>Quantidade: %{customdata}<br>Percentual: %{text}<extra></extra>",
                    cliponaxis=False
                ))
                
                # Adicionar anotações com quantidade
                for _, linha in motivo_counts.iterrows():
                    fig_cancelamentos.add_annotation(
                        x=float(linha['Quantidade']) + offset_anotacao,
                        y=linha['Motivo'],
                        text=linha['QuantidadeFormatada'],
                        showarrow=False,
                        font=dict(size=14, color='#f8fafc', family='Manrope, sans-serif'),
                        xanchor='left',
                        bgcolor='rgba(15,23,42,0.82)',
                        bordercolor='rgba(148, 163, 184, 0.45)',
                        borderwidth=1,
                        borderpad=5
                    )
                
                range_max = max_valor + offset_anotacao * 3 if max_valor else 1
                fig_cancelamentos.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#f8fafc"),
                    height=700,
                    margin=dict(t=35, b=20, l=10, r=40),
                    showlegend=False,
                    xaxis=dict(
                        showgrid=False,
                        zeroline=False,
                        showticklabels=False,
                        range=[0, range_max]
                    ),
                    yaxis=dict(
                        showgrid=False,
                        tickfont=dict(size=14, color='rgba(248,250,252,0.88)', family='Manrope, sans-serif'),
                        categoryorder='total ascending'
                    ),
                    hoverlabel=dict(bgcolor='rgba(15,23,42,0.92)', font_size=13, font_family='Manrope, sans-serif')
                )
                st.plotly_chart(fig_cancelamentos, use_container_width=True)
                
                # Mostrar total de cancelamentos em formato de texto (duas linhas)
                st.caption(f"Total Cancelamentos: {format_int_value(total_cancelamentos)}")
                st.caption(f"Período analisado: {TERMOMETRO_DATA_INICIO.strftime('%d/%m/%Y')} até {data_final_analise.strftime('%d/%m/%Y')}")
    
    st.markdown('</div>', unsafe_allow_html=True)


# ============================================================================
# LÓGICA DE RENDERIZAÇÃO DO CARROSSEL - SEM JAVASCRIPT, APENAS PYTHON
# ============================================================================

# Dicionário mapeando índice para função de renderização
RENDER_FUNCTIONS = {
    0: render_bloco_0,
    1: render_bloco_reservas,
    2: render_bloco_2,
    4: render_bloco_cancelamentos,
    # Bloco 3 (Mídia) ainda está inline no código
}

# Renderizar o bloco atual dentro do placeholder baseado no índice
with carousel_placeholder.container():
    current_index = st.session_state.carousel_index
    
    if current_index == 0:
        render_bloco_0()
    elif current_index == 1:
        render_bloco_reservas()
    elif current_index == 2:
        render_bloco_2()
    elif current_index == 3:
        # Bloco 3: Distribuição por Mídia
        st.markdown('<div class="tv-carousel-section">', unsafe_allow_html=True)
        st.markdown("## 📣 Distribuição por Mídia")

        leads_base_df = load_leads_tv()

        if leads_base_df.empty:
            st.info("Não foi possível carregar dados de mídia para o período de análise.")
        else:
            leads_tv_df = leads_base_df.copy()
            leads_tv_df['data_consolidada'] = pd.to_datetime(leads_tv_df['data_consolidada'], errors='coerce')
            leads_tv_df = leads_tv_df[leads_tv_df['data_consolidada'].notna()]
            leads_tv_df = leads_tv_df[
                (leads_tv_df['data_consolidada'].dt.date >= TERMOMETRO_DATA_INICIO) &
                (leads_tv_df['data_consolidada'].dt.date <= data_final_analise)
            ].copy()

            if leads_tv_df.empty:
                st.info("Sem dados de mídia para o período de análise selecionado.")
            else:
                leads_tv_df['midia_consolidada'] = leads_tv_df['midia_consolidada'].fillna('Outros').astype(str).str.strip()
                leads_tv_df['situacao_normalizada'] = leads_tv_df['situacao_nome'].astype(str).str.lower().str.strip()

                midia_resumo = (
                    leads_tv_df.groupby('midia_consolidada')
                    .agg(
                        total_leads=('idlead', 'count'),
                        vendas=('situacao_normalizada', lambda x: (x == 'venda realizada').sum())
                    )
                    .reset_index()
                )

                if midia_resumo.empty:
                    st.info("Sem dados de mídia para exibir.")
                else:
                    total_leads_midia = midia_resumo['total_leads'].sum()
                    midia_resumo['percent_leads'] = (
                        midia_resumo['total_leads'] / total_leads_midia * 100
                    ).round(1) if total_leads_midia > 0 else 0.0

                    midia_resumo['percent_conversao'] = midia_resumo.apply(
                        lambda row: round((row['vendas'] / row['total_leads'] * 100), 1) if row['total_leads'] > 0 else 0.0,
                        axis=1
                    )

                    midia_resumo = midia_resumo.sort_values('total_leads', ascending=False)

                    midia_display = midia_resumo.copy()
                    midia_display['Mídia'] = midia_display['midia_consolidada']
                    midia_display['Total Leads'] = midia_display['total_leads'].apply(format_int_value)
                    midia_display['Vendas Realizadas'] = midia_display['vendas'].apply(format_int_value)
                    midia_display['% Leads'] = midia_display['percent_leads'].map(lambda v: f"{v:.1f}%")
                    midia_display['% Conversão'] = midia_display['percent_conversao'].map(lambda v: f"{v:.1f}%")
                    midia_display = midia_display[['Mídia', 'Total Leads', 'Vendas Realizadas', '% Leads', '% Conversão']]

                    render_midia_table_html(midia_display)

                    total_leads_exibidos = format_int_value(int(total_leads_midia))
                    st.caption(
                        f"Base consolidada de {TERMOMETRO_DATA_INICIO.strftime('%d/%m/%Y')} até {data_final_analise.strftime('%d/%m/%Y')} · Leads contabilizados: {total_leads_exibidos}"
                    )
        st.markdown('</div>', unsafe_allow_html=True)
    elif current_index == 4:
        render_bloco_cancelamentos()


# ============================================================================
# LOOP DE AUTO-AVANÇO DO CARROSSEL (SOMENTE PYTHON)
# ============================================================================
tempo_restante_segundos = max(0.0, CAROUSEL_INTERVAL - (time.time() - st.session_state.carousel_last_update))
if tempo_restante_segundos > 0:
    time.sleep(tempo_restante_segundos)

st.session_state.carousel_index = (st.session_state.carousel_index + 1) % CAROUSEL_SECTIONS
st.session_state.carousel_last_update = time.time()
st.rerun()

