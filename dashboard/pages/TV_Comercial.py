import streamlit as st
import pandas as pd
from datetime import datetime, date

from advanced_auth import require_auth
from utils import display_navigation
from utils.md_conn import get_md_connection, get_metas_data
from utils.formatters import format_compact_currency


st.set_page_config(page_title="TV Comercial", layout="wide")


require_auth()
display_navigation()
st.session_state['current_page'] = __file__


st.title("📺 TV Comercial")
st.caption(f"Atualização realizada em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")


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
render_kpi(linha_um[1], "Taxa de Conversão Geral", f"{taxa_conversao_geral * 100:.1f}%", "Reservas que viram vendas")
render_kpi(linha_um[2], "Reservas Atuais", f"{reservas_atuais_total}", "Reservas ativas no pipeline")
render_kpi(linha_um[3], "Potencial de Vendas", format_compact_currency(potencial_vendas_valor), "Reservas x taxa de conversão")

linha_dois = st.columns(4)
render_kpi(linha_dois[0], "Cobertura da Meta", f"{cobertura_percent:.1f}%", "Potencial versus meta")
render_kpi(linha_dois[1], f"Vendas Realizadas ({mes_referencia_curto})", format_compact_currency(vendas_realizadas_valor) if vendas_realizadas_valor > 0 else "R$ 0", "Vendas concluídas do mês")
render_kpi(linha_dois[2], "Atingimento da Meta", f"{atingimento_percent:.1f}%", "Vendas / Meta do mês")
render_kpi(linha_dois[3], "Falta para Meta", format_compact_currency(falta_para_meta_valor) if meta_total > 0 else "—", "Gap remanescente")

st.markdown(
    f"<div class='tv-status-badge' style='background:{status_color}; color:{'#ffffff' if status in {'Frio', 'Quente'} else '#0b0b0b'};'>"
    f"<span>Status atual:</span><strong>{status}</strong></div>",
    unsafe_allow_html=True
)

st.markdown(f"<div class='tv-status-context'><strong>Interpretação:</strong> {interpretacao}</div>", unsafe_allow_html=True)
st.markdown(f"<div class='tv-status-context'><strong>Ação sugerida:</strong> {acao}</div>", unsafe_allow_html=True)


st.markdown(
    f"<div style='margin-top:18px; font-size:0.95rem; color:rgba(255,255,255,0.65);'>Base analisada de {TERMOMETRO_DATA_INICIO.strftime('%d/%m/%Y')} até {data_final_analise.strftime('%d/%m/%Y')} · Atualize a página para forçar nova leitura.</div>",
    unsafe_allow_html=True
)
