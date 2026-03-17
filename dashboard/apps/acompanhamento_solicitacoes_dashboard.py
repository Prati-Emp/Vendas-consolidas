"""
Dashboard de Acompanhamento de Solicitações - Quadros Kanban do Jira DHO.
Exibe 4 quadros: Rotinas Trabalhistas, Movimentações (MC), Requisição de Vaga (RC), Treinamentos (T&D).
"""

from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from dashboard.utils.md_conn import get_md_connection

# Mapeamento: qual coluna e valores para cada quadro (baseado em Tipo_de_item ou Categoria)
# Ajuste conforme os valores reais no Jira
BOARD_FILTERS: Dict[str, Dict[str, Any]] = {
    "rotinas_trabalhistas": {
        "label": "📋 Rotinas Trabalhistas",
        "col": "Tipo_de_item",  # ou "Categoria" se existir
        "values": [
            "Demissão", "Férias", "Admissão", "Afastamento", "Desligamento",
            "Adiantamento", "Rescisão", "Aposentadoria", "Licença", "Alteração de Dados"
        ],
        "fallback_contains": ["demissão", "férias", "admissão", "afastamento", "desligamento", "rescisão"]
    },
    "movimentacoes_mc": {
        "label": "🔄 Movimentações (MC)",
        "col": "Tipo_de_item",
        "values": ["Movimentação de Cargo", "Movimentação", "MC", "Alteração de Cargo"],
        "fallback_contains": ["movimentação", "movimentacao", "mc", "cargo"]
    },
    "requisicao_vaga_rc": {
        "label": "📝 Requisição de Vaga (RC)",
        "col": "Tipo_de_item",
        "values": ["Requisição de Vaga", "Requisição de Cargo", "RC", "Vaga"],
        "fallback_contains": ["requisição", "requisicao", "vaga", "rc"]
    },
    "treinamentos_td": {
        "label": "🎓 Treinamentos (T&D)",
        "col": "Tipo_de_item",
        "values": ["Treinamento", "T&D", "Capacitação", "Curso"],
        "fallback_contains": ["treinamento", "capacitação", "curso", "t&d"]
    },
}


@st.cache_data(ttl=600)
def load_jira_dho_acompanhamento() -> pd.DataFrame:
    """Carrega dados da view Jira_projeto_dho_consolidado."""
    md_conn = get_md_connection()
    sql = "SELECT * FROM administracao.Jira_projeto_dho_consolidado"
    try:
        return md_conn.run_query(sql)
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        return pd.DataFrame()


def _filter_df_by_board(df: pd.DataFrame, board_key: str) -> pd.DataFrame:
    """Filtra o DataFrame para um quadro específico."""
    if df.empty:
        return df
    config = BOARD_FILTERS.get(board_key, {})
    col = config.get("col", "Tipo_de_item")
    values = config.get("values", [])
    fallback = config.get("fallback_contains", [])

    if col not in df.columns:
        col = "Categoria" if "Categoria" in df.columns else None
    if col is None:
        return df

    df_col = df[col].astype(str).str.strip()
    mask = df_col.isin(values)
    if not mask.any() and fallback:
        for term in fallback:
            mask = mask | df_col.str.lower().str.contains(term, na=False, regex=False)
    return df[mask].copy()


def _get_status_column(df: pd.DataFrame) -> str:
    """Identifica a coluna de Status."""
    for c in ["Status", "status"]:
        if c in df.columns:
            return c
    for col in df.columns:
        if "status" in col.lower():
            return col
    return ""


def _render_kanban_cards(df: pd.DataFrame, status_col: str, status_val: str) -> None:
    """Renderiza os cards de um status em formato Kanban."""
    df_status = df[df[status_col] == status_val]
    if df_status.empty:
        st.markdown("*Nenhum item*")
        return

    chave_col = "Chave" if "Chave" in df.columns else (df.columns[0] if len(df.columns) > 0 else "")
    resumo_col = "Resumo" if "Resumo" in df.columns else ""
    tipo_col = "Tipo_de_item" if "Tipo_de_item" in df.columns else ""

    for _, row in df_status.iterrows():
        chave = html.escape(str(row.get(chave_col, "")) if chave_col else "")
        resumo_raw = str(row.get(resumo_col, "")) if resumo_col else ""
        resumo = html.escape(resumo_raw[:80] + ("..." if len(resumo_raw) > 80 else ""))
        tipo = html.escape(str(row.get(tipo_col, "")) if tipo_col else "")

        card_html = f"""
        <div style="
            background: #fff;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 10px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            font-size: 0.9rem;
        ">
            <div style="font-weight: 600; color: #1a73e8; margin-bottom: 4px;">{chave}</div>
            <div style="color: #333; margin-bottom: 4px;">{resumo}</div>
            <div style="font-size: 0.8rem; color: #666;">{tipo}</div>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)


def _render_kanban_board(df: pd.DataFrame, title: str) -> None:
    """Renderiza um quadro Kanban completo com colunas por status."""
    if df.empty:
        st.info(f"Nenhum item encontrado para **{title}**.")
        return

    status_col = _get_status_column(df)
    if not status_col:
        st.warning("Coluna de Status não encontrada nos dados.")
        st.dataframe(df.head(20), use_container_width=True, hide_index=True)
        return

    statuses = df[status_col].dropna().unique().tolist()
    statuses = sorted([s for s in statuses if str(s).strip()], key=str)

    if not statuses:
        st.info("Nenhum status encontrado.")
        return

    # Layout: uma coluna por status
    cols = st.columns(len(statuses))
    for i, status_val in enumerate(statuses):
        with cols[i]:
            count = len(df[df[status_col] == status_val])
            st.markdown(f"**{status_val}** ({count})")
            st.markdown("---")
            _render_kanban_cards(df, status_col, status_val)


def render_acompanhamento_solicitacoes_dashboard() -> None:
    """Renderiza o dashboard completo de Acompanhamento de Solicitações."""
    st.subheader("📋 Acompanhamento de Solicitações")
    st.caption("Quadros Kanban baseados em Jira_projeto_dho_consolidado")

    with st.spinner("Carregando dados do Jira DHO..."):
        df_raw = load_jira_dho_acompanhamento()

    if df_raw.empty:
        st.warning("⚠️ Nenhum dado encontrado na view Jira_projeto_dho_consolidado.")
        return

    # Sidebar: ajuda para configurar filtros
    with st.sidebar:
        with st.expander("🔧 Configurar quadros"):
            tipo_col = "Tipo_de_item" if "Tipo_de_item" in df_raw.columns else ("Categoria" if "Categoria" in df_raw.columns else None)
            if tipo_col:
                valores = sorted(df_raw[tipo_col].dropna().astype(str).unique().tolist())
                st.caption(f"Valores em **{tipo_col}** (use em BOARD_FILTERS):")
                st.code(", ".join(f'"{v}"' for v in valores[:30]), language=None)
                if len(valores) > 30:
                    st.caption(f"... e mais {len(valores) - 30}")

    # 4 abas lado a lado
    tab_keys = list(BOARD_FILTERS.keys())
    tabs = st.tabs([BOARD_FILTERS[k]["label"] for k in tab_keys])

    for i, (tab, board_key) in enumerate(zip(tabs, tab_keys)):
        with tab:
            df_board = _filter_df_by_board(df_raw, board_key)
            if df_board.empty and i == 0 and not df_raw.empty:
                # Fallback: se o primeiro quadro está vazio, mostrar todos os dados com aviso
                st.info("💡 Nenhum item encontrado com os filtros atuais. Exibindo todos os itens. Ajuste **BOARD_FILTERS** em `acompanhamento_solicitacoes_dashboard.py` conforme os valores de **Tipo_de_item** no Jira.")
                df_board = df_raw.copy()
            _render_kanban_board(df_board, BOARD_FILTERS[board_key]["label"])
