import streamlit as st
import pandas as pd
from datetime import datetime, date
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from advanced_auth import require_auth, get_current_user
from utils.md_conn import get_md_connection
from utils.formatters import format_int


st.set_page_config(page_title="Distribuição por Mídia", layout="wide")


require_auth()
st.session_state['current_page'] = __file__


current_user = get_current_user() or {}
email = (current_user.get('email') or "").lower()
if email not in {"odair.santos@grupoprati.com"}:
    st.warning("⚠️ Você não tem permissão para acessar esta página.")
    st.stop()


st.markdown(
    """
    <style>
        .tv-midia-table {
            margin-top: 12px;
            background: linear-gradient(145deg, rgba(16,24,48,0.92) 0%, rgba(9,16,32,0.88) 45%, rgba(6,12,26,0.94) 100%);
            border-radius: 18px;
            border: 1px solid rgba(148, 163, 184, 0.25);
            box-shadow: 0 12px 30px rgba(15, 23, 42, 0.45);
            overflow: hidden;
        }
        .tv-midia-table table {
            width: 100%;
            border-collapse: collapse;
        }
        .tv-midia-table thead tr {
            background: linear-gradient(90deg, rgba(21,34,64,0.95) 0%, rgba(29,42,72,0.95) 100%);
        }
        .tv-midia-table thead th {
            padding: 18px 22px;
            text-transform: uppercase;
            font-size: 0.86rem;
            letter-spacing: 0.1em;
            color: rgba(226, 232, 240, 0.82);
            border-bottom: 1px solid rgba(148, 163, 184, 0.35);
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
    unsafe_allow_html=True,
)


TERMOMETRO_DATA_INICIO = date(2025, 1, 1)

LEADS_CORRETORES_REMOVIDOS = {
    "ODAIR DIAS DOS SANTOS",
    "ODAIR SANTOS",
}


@st.cache_data(ttl=300)
def load_leads_midia() -> pd.DataFrame:
    conn = get_md_connection()
    sql = """
        SELECT 
            Idlead AS idlead,
            CAST(data_consolidada AS DATE) AS data_consolidada,
            COALESCE(NULLIF(TRIM(Situacao), ''), '—') AS situacao_nome,
            COALESCE(NULLIF(TRIM(nome_situacao_anterior_lead), ''), '—') AS nome_situacao_anterior_lead,
            COALESCE(NULLIF(TRIM(corretor_consolidado), ''), '—') AS corretor_consolidado,
            COALESCE(NULLIF(TRIM(midia_consolidada), ''), '—') AS midia_consolidada
        FROM reservas.main.cv_leads
        WHERE data_consolidada IS NOT NULL
    """
    try:
        return conn.run_query(sql)
    except Exception:
        sql_alt = sql.replace("reservas.main.cv_leads", "reservas.cv_leads")
        return conn.run_query(sql_alt)


def render_midia_table_html(dataframe: pd.DataFrame) -> None:
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


def preparar_distribuicao_midia() -> pd.DataFrame:
    leads_df = load_leads_midia()
    if leads_df.empty:
        return pd.DataFrame()

    leads_df = leads_df.copy()
    leads_df['data_consolidada'] = pd.to_datetime(leads_df['data_consolidada'], errors='coerce')
    leads_df = leads_df[leads_df['data_consolidada'].notna()]

    data_final_analise = datetime.now().date()
    leads_df = leads_df[
        (leads_df['data_consolidada'].dt.date >= TERMOMETRO_DATA_INICIO)
        & (leads_df['data_consolidada'].dt.date <= data_final_analise)
    ]

    leads_df['corretor_consolidado'] = leads_df['corretor_consolidado'].fillna('—')
    leads_df = leads_df[~leads_df['corretor_consolidado'].str.upper().isin(LEADS_CORRETORES_REMOVIDOS)]

    situacoes_excluidas = {"descartado", "em pré-cadastro"}
    leads_df['situacao_normalizada'] = leads_df['situacao_nome'].str.lower().str.strip()
    leads_df = leads_df[~leads_df['situacao_normalizada'].isin(situacoes_excluidas)]

    if leads_df.empty:
        return pd.DataFrame()

    midia_resumo = (
        leads_df.groupby('midia_consolidada')
        .agg(
            total_leads=('idlead', 'count'),
            vendas=('situacao_normalizada', lambda x: (x == 'venda realizada').sum())
        )
        .reset_index()
    )

    if midia_resumo.empty:
        return pd.DataFrame()

    total_leads_midia = midia_resumo['total_leads'].sum()
    if total_leads_midia > 0:
        midia_resumo['percent_leads'] = (midia_resumo['total_leads'] / total_leads_midia * 100).round(1)
    else:
        midia_resumo['percent_leads'] = 0.0

    midia_resumo['percent_conversao'] = midia_resumo.apply(
        lambda row: round((row['vendas'] / row['total_leads'] * 100), 1) if row['total_leads'] > 0 else 0.0,
        axis=1
    )

    midia_resumo = midia_resumo.sort_values('total_leads', ascending=False)

    midia_display = midia_resumo.copy()
    midia_display['Mídia'] = midia_display['midia_consolidada']
    midia_display['Total Leads'] = midia_display['total_leads'].apply(format_int)
    midia_display['Vendas Realizadas'] = midia_display['vendas'].apply(format_int)
    midia_display['% Leads'] = midia_display['percent_leads'].map(lambda v: f"{v:.1f}%")
    midia_display['% Conversão'] = midia_display['percent_conversao'].map(lambda v: f"{v:.1f}%")
    midia_display = midia_display[['Mídia', 'Total Leads', 'Vendas Realizadas', '% Leads', '% Conversão']]

    return midia_display


st.title("📣 Distribuição por Mídia")
st.caption("Dados consolidados desde janeiro/2025 — atualização automática ao abrir a página")

midia_tabela = preparar_distribuicao_midia()

if midia_tabela.empty:
    st.info("Não encontramos dados de mídia para o período selecionado.")
else:
    render_midia_table_html(midia_tabela)
