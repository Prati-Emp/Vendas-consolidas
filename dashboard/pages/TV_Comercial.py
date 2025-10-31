import streamlit as st
import pandas as pd
from datetime import datetime, date
import sys
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go

# Garantir que os módulos compartilhados possam ser importados quando o app for executado diretamente
sys.path.append(str(Path(__file__).resolve().parent.parent))

from advanced_auth import require_auth, get_current_user
from utils import display_navigation
from utils.md_conn import get_md_connection, get_metas_data
from utils.formatters import format_compact_currency, format_currency


st.set_page_config(page_title="TV Comercial", layout="wide")


require_auth()
display_navigation()
st.session_state['current_page'] = __file__


st.title("📺 TV Comercial")
st.caption(f"Atualização realizada em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

# Bloqueio de acesso: somente o usuário Odair pode ver esta página
current_user = get_current_user() or {}
email = (current_user.get('email') or "").lower()
if email not in {"odair.santos@grupoprati.com"}:
    st.warning("⚠️ Você não tem permissão para acessar a TV Comercial.")
    st.stop()

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
    </style>
    """,
    unsafe_allow_html=True
)


CONVERSAO_SITUACOES = {situacao.lower() for situacao in ["Distrato", "Mútuo", "Vendida"]}
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
    "Com reserva",
    "Venda realizada"
]

RESERVAS_SITUACAO_ORDEM = [
    "Reserva",
    "Crédito (CEF)",
    "Negociação",
    "Análise Diretoria",
    "Contrato - Elaboração",
    "Contrato - Assinatura"
]


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


@st.cache_data(ttl=300)
def load_reservas_tv() -> pd.DataFrame:
    conn = get_md_connection()
    sql = """
        SELECT
            data_cad::DATE AS data_cad,
            situacao,
            valor_contrato
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
reservas_df['situacao'] = reservas_df['situacao'].astype(str).str.strip()
reservas_df['situacao_normalizada'] = reservas_df['situacao'].str.lower()
reservas_df['valor_contrato'] = pd.to_numeric(
    reservas_df.get('valor_contrato', pd.Series(dtype=float)),
    errors='coerce'
).fillna(0.0)


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

total_reservas_periodo = len(reservas_base_df)
reservas_convertidas_total = reservas_base_df['situacao_normalizada'].isin(CONVERSAO_SITUACOES).sum()
taxa_conversao_geral = (
    reservas_convertidas_total / total_reservas_periodo
) if total_reservas_periodo > 0 else 0.0

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
        }
        .tv-kpi-title {
            font-size: 1.0rem;
            font-weight: 600;
            color: rgba(255, 255, 255, 0.80);
            margin-bottom: 18px;
            letter-spacing: 0.04em;
            text-transform: uppercase;
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
    </style>
    """,
    unsafe_allow_html=True
)


def render_kpi(coluna, titulo: str, valor: str, subtitulo: str | None = None):
    coluna.markdown(
        f"""
        <div class=\"tv-kpi-card\">
            <div class=\"tv-kpi-title\">{titulo}</div>
            <div class=\"tv-kpi-value\">{valor}</div>
            {f'<div class=\"tv-kpi-subtitle\">{subtitulo}</div>' if subtitulo else ''}
        </div>
        """,
        unsafe_allow_html=True
    )


linha_um = st.columns(4)
render_kpi(linha_um[0], f"Meta de Vendas ({mes_referencia_curto})", format_compact_currency(meta_total) if meta_total > 0 else "—", "Objetivo mensal consolidado")
render_kpi(linha_um[1], f"Vendas Realizadas ({mes_referencia_curto})", format_compact_currency(vendas_realizadas_valor) if vendas_realizadas_valor > 0 else "R$ 0", "Vendas concluídas do mês")
render_kpi(linha_um[2], "Atingimento da Meta", f"{atingimento_percent:.1f}%", "Vendas / Meta do mês")
render_kpi(linha_um[3], "Falta para Meta", format_compact_currency(falta_para_meta_valor) if meta_total > 0 else "—", "Gap remanescente")

# Seção do termômetro
st.subheader("🌡️ Termômetro de Vendas")

st.markdown(
    f"<div class='tv-status-badge' style='background:{status_color}; color:{'#ffffff' if status in {'Frio', 'Quente'} else '#0b0b0b'};'>"
    f"<span>Status atual:</span><strong>{status}</strong></div>",
    unsafe_allow_html=True
)

st.markdown(f"<div class='tv-status-context'><strong>Interpretação:</strong> {interpretacao}</div>", unsafe_allow_html=True)
st.markdown(f"<div class='tv-status-context'><strong>Ação sugerida:</strong> {acao}</div>", unsafe_allow_html=True)


escala_max = 150
indicador_percentual = max(0.0, min(cobertura_percent, escala_max))
indicador_posicao = indicador_percentual / escala_max * 100
largura_preenchida = min(max(cobertura_percent / escala_max, 0.0), 1.0) * 100

barra_escala_html = f"""
<div style='margin-top:1.25rem; position:relative; padding-top:42px;'>
  <div style='position:absolute; top:0; left:{indicador_posicao}%; transform:translateX(-50%); display:flex; flex-direction:column; align-items:center;'>
    <div style='font-size:0.9rem;font-weight:700;color:{status_color};margin-bottom:8px;background:rgba(11,11,11,0.85);padding:4px 14px;border-radius:999px;'>{cobertura_percent:.1f}%</div>
    <div style='width:0;height:0;border-left:14px solid transparent;border-right:14px solid transparent;border-bottom:18px solid {status_color};'></div>
  </div>
  <div style='position:relative; border-radius:16px; overflow:hidden; height:68px; box-shadow:0 0 18px rgba(0,0,0,0.35);'>
    <div style='display:flex; height:100%; font-size:1.05rem;'>
      <div style='flex:70; background:#1E90FF; color:#ffffff; display:flex; flex-direction:column; align-items:center; justify-content:center; font-weight:600; opacity:{1 if cobertura_percent >= 0 else 0.25};'>
        Frio
        <span style="font-weight:400;font-size:0.85rem;opacity:0.85;">&lt; 70%</span>
      </div>
      <div style='flex:30; background:#f1c40f; color:#0b0b0b; display:flex; flex-direction:column; align-items:center; justify-content:center; font-weight:700; opacity:{1 if cobertura_percent >= 70 else 0.3};'>
        Morno
        <span style="font-weight:500;font-size:0.85rem;opacity:0.85;">70% – 100%</span>
      </div>
      <div style='flex:50; background:#FF5722; color:#ffffff; display:flex; flex-direction:column; align-items:center; justify-content:center; font-weight:600; opacity:{1 if cobertura_percent >= 100 else 0.3};'>
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


st.markdown(
    f"<div style='margin-top:18px; font-size:0.95rem; color:rgba(255,255,255,0.65);'>Base analisada de {TERMOMETRO_DATA_INICIO.strftime('%d/%m/%Y')} até {data_final_analise.strftime('%d/%m/%Y')} · Atualize a página para forçar nova leitura.</div>",
    unsafe_allow_html=True
)

linha_termometro = st.columns(4)
render_kpi(linha_termometro[0], "Taxa de Conversão Geral", f"{taxa_conversao_geral * 100:.1f}%", "Reservas que viram vendas")
render_kpi(linha_termometro[1], "Reservas Atuais", f"{reservas_atuais_total}", "Reservas ativas no pipeline")
render_kpi(linha_termometro[2], "Potencial de Vendas", format_compact_currency(potencial_vendas_valor), "Reservas x taxa de conversão")
render_kpi(linha_termometro[3], "Cobertura da Meta", f"{cobertura_percent:.1f}%", "Potencial versus meta")


periodo_inicio_str = TERMOMETRO_DATA_INICIO.strftime('%Y-%m-%d')
periodo_fim_str = data_final_analise.strftime('%Y-%m-%d')


st.markdown("---")
st.markdown("## 🏠 Análise Vendas House")

house_raw_df = load_vendas_house_overview(periodo_inicio_str, periodo_fim_str)

if house_raw_df.empty or house_raw_df['valor_total'].fillna(0).sum() == 0:
    st.info("Sem dados de vendas suficientes para exibir a análise House x Imobiliárias no período selecionado.")
else:
    house_df = house_raw_df.fillna({'quantidade': 0, 'valor_total': 0.0, 'ticket_medio': 0.0}).copy()
    total_valor_house = float(house_df['valor_total'].sum())
    valor_prati = float(house_df.loc[house_df['origem'] == 'Venda Interna (Prati)', 'valor_total'].sum())
    quantidade_prati = int(house_df.loc[house_df['origem'] == 'Venda Interna (Prati)', 'quantidade'].sum())
    taxa_house_percent = (valor_prati / total_valor_house * 100) if total_valor_house > 0 else 0.0
    ticket_prati = (valor_prati / quantidade_prati) if quantidade_prati > 0 else 0.0

    house_kpi_cols = st.columns(3)
    render_kpi(house_kpi_cols[0], "Taxa House (valor)", f"{taxa_house_percent:.1f}%", "Participação das vendas Prati")
    render_kpi(house_kpi_cols[1], "Valor Prati", format_compact_currency(valor_prati) if valor_prati > 0 else "R$ 0", "Vendas internas jan/25 até hoje")
    render_kpi(house_kpi_cols[2], "Ticket Médio Prati", format_currency(ticket_prati) if ticket_prati > 0 else "—")

    fig_house = px.pie(
        house_df,
        values='valor_total',
        names='origem',
        hole=0.45,
        color='origem',
        color_discrete_map={
            'Venda Interna (Prati)': '#38bdf8',
            'Venda Externa (Imobiliárias)': '#6366f1'
        },
        title='Participação por origem (valor)'
    )
    fig_house = apply_dark_theme(fig_house, margin_top=50)
    st.plotly_chart(fig_house, use_container_width=True)


st.markdown("---")
st.markdown("## 💰 VPL Geral")

vpl_df = load_vpl_geral(periodo_inicio_str, periodo_fim_str)

if vpl_df.empty:
    st.info("Sem dados de VPL disponíveis para o período analisado.")
else:
    vpl_row = vpl_df.iloc[0]
    total_vpl_reserva = float(vpl_row.get('total_vpl_reserva', 0.0) or 0.0)
    total_vpl_tabela = float(vpl_row.get('total_vpl_tabela', 0.0) or 0.0)
    vpl_percent = ((total_vpl_reserva / total_vpl_tabela) - 1) * 100 if total_vpl_tabela > 0 else 0.0
    vpl_gap = total_vpl_reserva - total_vpl_tabela

    vpl_cols = st.columns(4)
    render_kpi(vpl_cols[0], "VPL Reserva", format_compact_currency(total_vpl_reserva), "Reservas cadastradas")
    render_kpi(vpl_cols[1], "VPL Tabela", format_compact_currency(total_vpl_tabela), "Tabela oficial")
    render_kpi(vpl_cols[2], "% VPL", f"{vpl_percent:.2f}%", "VPL Geral")
    render_kpi(vpl_cols[3], "Gap VPL", format_compact_currency(vpl_gap), "Reserva - Tabela")


st.markdown("---")
st.markdown("## 📈 Leads - Indicadores Essenciais")

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

        funil_initial_counts = {
            etapa: int((leads_tv_df['funil_etapa'] == etapa).sum())
            for etapa in LEADS_FUNIL_ETAPAS
        }

        total_leads_funil = int(len(leads_tv_df))

        if total_leads_funil == 0:
            st.info("Sem leads ativos no funil para o período considerado.")
        else:
            etapa_counts = []
            for etapa in LEADS_FUNIL_ETAPAS:
                if etapa == "Leads":
                    etapa_counts.append(total_leads_funil)
                elif etapa == "Em atendimento":
                    etapa_counts.append(
                        funil_initial_counts.get("Em atendimento", 0)
                        + funil_initial_counts.get("Visita realizada", 0)
                        + funil_initial_counts.get("Com reserva", 0)
                        + funil_initial_counts.get("Venda realizada", 0)
                    )
                elif etapa == "Visita realizada":
                    etapa_counts.append(
                        funil_initial_counts.get("Visita realizada", 0)
                        + funil_initial_counts.get("Com reserva", 0)
                        + funil_initial_counts.get("Venda realizada", 0)
                    )
                elif etapa == "Com reserva":
                    etapa_counts.append(
                        funil_initial_counts.get("Com reserva", 0)
                        + funil_initial_counts.get("Venda realizada", 0)
                    )
                else:
                    etapa_counts.append(funil_initial_counts.get(etapa, 0))

            funil_fig = go.Figure(go.Funnel(
                y=LEADS_FUNIL_ETAPAS,
                x=etapa_counts,
                textinfo="value+percent initial",
                marker=dict(color=['#60a5fa', '#3b82f6', '#2563eb', '#7c3aed', '#f59e0b'])
            ))
            funil_fig = apply_dark_theme(funil_fig)
            st.plotly_chart(funil_fig, use_container_width=True)

            funil_cols = st.columns(len(LEADS_FUNIL_ETAPAS))
            for col, etapa, valor in zip(funil_cols, LEADS_FUNIL_ETAPAS, etapa_counts):
                percentual = (valor / total_leads_funil * 100) if total_leads_funil > 0 else 0.0
                render_kpi(col, etapa, format_int_value(valor), f"{percentual:.1f}% do total")

            st.caption(
                f"Base de leads analisada de {TERMOMETRO_DATA_INICIO.strftime('%d/%m/%Y')} até {data_final_analise.strftime('%d/%m/%Y')} · Total: {format_int_value(total_leads_funil)}"
            )

            # Cancelamentos por motivo
            st.markdown("### ❌ Cancelamentos por Motivo")
            cancelamentos_df = leads_tv_df[
                leads_tv_df['motivo_cancelamento_consolidada'].notna()
                & (leads_tv_df['motivo_cancelamento_consolidada'].str.strip() != '')
            ].copy()

            if cancelamentos_df.empty:
                st.info("Nenhum cancelamento registrado no período.")
            else:
                cancelamentos_resumo = (
                    cancelamentos_df.groupby('motivo_cancelamento_consolidada')['idlead']
                    .count()
                    .reset_index(name='Quantidade')
                    .sort_values('Quantidade', ascending=False)
                )

                fig_cancel = px.bar(
                    cancelamentos_resumo.head(10),
                    x='Quantidade',
                    y='motivo_cancelamento_consolidada',
                    orientation='h',
                    color='Quantidade',
                    color_continuous_scale='Blues',
                    title='Top 10 motivos de cancelamento'
                )
                fig_cancel = apply_dark_theme(fig_cancel, margin_top=40)
                fig_cancel.update_yaxes(title="", autorange="reversed")
                fig_cancel.update_traces(texttemplate='%{x}', textposition='outside')
                fig_cancel.update_layout(coloraxis_showscale=False)
                st.plotly_chart(fig_cancel, use_container_width=True)

            # Por mídia
            st.markdown("### 📣 Distribuição por Mídia")
            midia_resumo = (
                leads_tv_df.groupby('midia_consolidada')
                .agg(
                    total_leads=('idlead', 'count'),
                    vendas=('funil_etapa', lambda x: (x == 'Venda realizada').sum())
                )
                .reset_index()
            )

            if midia_resumo.empty:
                st.info("Sem dados de mídia para exibir.")
            else:
                total_leads_midia = midia_resumo['total_leads'].sum()
                if total_leads_midia > 0:
                    midia_resumo['percent_leads'] = (midia_resumo['total_leads'] / total_leads_midia * 100).round(1)
                else:
                    midia_resumo['percent_leads'] = 0.0
                midia_resumo['percent_conversao'] = midia_resumo.apply(
                    lambda row: round((row['vendas'] / row['total_leads'] * 100), 1) if row['total_leads'] > 0 else 0.0, axis=1
                )
                midia_resumo = midia_resumo.sort_values('total_leads', ascending=False)

                midia_display = midia_resumo.copy()
                midia_display['Mídia'] = midia_display['midia_consolidada']
                midia_display['Total Leads'] = midia_display['total_leads'].apply(format_int_value)
                midia_display['Vendas Realizadas'] = midia_display['vendas'].apply(format_int_value)
                midia_display['% Leads'] = midia_display['percent_leads'].map(lambda v: f"{v:.1f}%")
                midia_display['% Conversão'] = midia_display['percent_conversao'].map(lambda v: f"{v:.1f}%")
                midia_display = midia_display[['Mídia', 'Total Leads', 'Vendas Realizadas', '% Leads', '% Conversão']]

                st.dataframe(midia_display, use_container_width=True, hide_index=True)


st.markdown("---")
st.markdown("## 🧾 Reservas - Situação Atual")

reservas_status_df = reservas_ativas_df.copy()

if reservas_status_df.empty:
    st.info("Sem reservas ativas para exibir no momento.")
else:
    reservas_status_df['situacao'] = reservas_status_df['situacao'].astype(str).str.strip()

    status_counts = (
        reservas_status_df.groupby('situacao', dropna=False)
        .size()
        .reset_index(name='Quantidade')
    )
    status_counts = status_counts.rename(columns={'situacao': 'Situacao'})

    if status_counts.empty:
        st.info("Nenhuma situação ativa encontrada no período.")
    else:
        status_counts['SituacaoNormalizada'] = status_counts['Situacao'].apply(normalize_reserva_label)
        status_counts['Indice'] = status_counts['SituacaoNormalizada'].apply(
            lambda s: RESERVAS_SITUACAO_ORDEM.index(s)
            if s in RESERVAS_SITUACAO_ORDEM else len(RESERVAS_SITUACAO_ORDEM)
        )
        status_counts = status_counts.sort_values(['Indice', 'Situacao']).reset_index(drop=True)

        total_reservas_status = int(status_counts['Quantidade'].sum())
        status_counts['Percentual'] = status_counts['Quantidade'].apply(
            lambda v: round(v / total_reservas_status * 100, 1) if total_reservas_status > 0 else 0.0
        )

        fig_reserva_status = px.bar(
            status_counts,
            x='Quantidade',
            y='Situacao',
            orientation='h',
            text='Quantidade',
            color='Quantidade',
            color_continuous_scale='Blues',
            title='Distribuição de Reservas por Situação'
        )
        fig_reserva_status.update_layout(yaxis=dict(categoryorder='array', categoryarray=status_counts['Situacao'].tolist()[::-1]))
        fig_reserva_status = apply_dark_theme(fig_reserva_status, margin_top=60)
        fig_reserva_status.update_traces(texttemplate='%{text}', textposition='outside')
        fig_reserva_status.update_layout(coloraxis_showscale=False)
        fig_reserva_status.update_yaxes(title="Situação")
        st.plotly_chart(fig_reserva_status, use_container_width=True)

        reservas_display = status_counts[['Situacao', 'Quantidade', 'Percentual']].copy()
        reservas_display = reservas_display.rename(columns={'Situacao': 'Situação'})
        reservas_display['Reservas'] = reservas_display['Quantidade'].apply(format_int_value)
        reservas_display['%'] = reservas_display['Percentual'].map(lambda v: f"{v:.1f}%")
        reservas_display = reservas_display[['Situação', 'Reservas', '%']]

        st.dataframe(reservas_display, use_container_width=True, hide_index=True)
        st.caption(f"Total de reservas ativas consideradas: {format_int_value(total_reservas_status)}")
