"""
Dashboard de Acompanhamento de Solicitações - Quadros Kanban do Jira DHO.
Exibe 4 quadros: Rotinas Trabalhistas, Movimentações (MC), Requisição de Vaga (RC), Treinamentos (T&D).
"""

from __future__ import annotations

import html
import re
import unicodedata
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from dashboard.utils.md_conn import get_md_connection

# Mapeamento: coluna "Motivo_da_Requisição" conforme filtros do Jira
# Fonte: filtros dos quadros Kanban do Jira (RH/DHO)
BOARD_FILTERS: Dict[str, Dict[str, Any]] = {
    "rotinas_trabalhistas": {
        "label": "📋 Rotinas Trabalhistas",
        "col": "Motivo_da_Requisição",
        "values": ["Afastamento", "Demissão", "Férias"],
    },
    "treinamentos_td": {
        "label": "🎓 Treinamentos (T&D)",
        "col": "Motivo_da_Requisição",
        "values": ["Treinamentos"],
    },
    "movimentacoes_mc": {
        "label": "🔄 Movimentações (MC)",
        "col": "Motivo_da_Requisição",
        "values": [
            "Alteração Salarial", "Promoção", "Mudança de CNPJ",
            "Mudança de horário", "Movimentação"
        ],
    },
    "requisicao_vaga_rc": {
        "label": "📝 Requisição de Vaga (RC)",
        "col": "Motivo_da_Requisição",
        "values": ["Aumento de Quadro", "Substituição"],
    },
}

# Mapeamento de nomes de colunas/status para exibição (status_original → nome_exibido)
# Ajuste conforme os nomes desejados para cada quadro
STATUS_DISPLAY_NAMES: Dict[str, Dict[str, str]] = {
    "treinamentos_td": {
        "Backlog": "SOLICITAÇÕES",
        "Aprovação Diretoria": "DIRETORIA",
        "Aprovação Presidência": "PRESIDÊNCIA",
        "Aprovado": "APROVADO",
        "Finalizado": "FINALIZADO",
        "Rejeitado": "REJEITADO",
    },
    "rotinas_trabalhistas": {
        "Backlog": "SOLICITAÇÕES",
        "Aprovação Diretoria": "DIRETORIA",
        "Aprovação Presidência": "PRESIDÊNCIA",
        "Aprovado": "APROVADO",
        "Finalizado": "FINALIZADO",
        "Rejeitado": "REJEITADO",
    },
    "movimentacoes_mc": {
        "Backlog": "SOLICITAÇÕES",
        "Aprovação Diretoria": "DIRETORIA",
        "Aprovação Presidência": "PRESIDÊNCIA",
        "Aprovado": "APROVADO",
        "Exames Gerais": "EXAMES",
        "Documentação": "DOCUMENTAÇÃO E CADASTRO",
        "Finalizado": "FINALIZADO",
        "Rejeitado": "REJEITADO",
    },
    "requisicao_vaga_rc": {
        "Backlog": "SOLICITAÇÕES DE VAGA",
        "Aprovação Diretoria": "DIRETORIA",
        "Aprovação Presidência": "PRESIDÊNCIA",
        "Triagem": "TRIAGEM",
        "Prospecção": "PROSPECÇÃO",
        "Entrevista RH": "ENTREVISTA RH",
        "Provas": "PROVAS",
        "Compliance": "COMPLIANCE",
        "Entrevista com Gestor": "ENTREVISTA COM GESTOR",
        "Aguardando Gestor": "AGUARDANDO GESTOR",
        "Carta Proposta": "CARTA PROPOSTA",
        "Documentos e Cadastro": "DOCUMENTOS",
        "Exames Admissão": "EXAMES",
        "Aguardando Integração": "AGUARDANDO INTEGRAÇÃO",
        "Finalizado": "FINALIZADO",
        "Rejeitado": "REJEITADO",
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
    col = config.get("col", "Motivo_da_Requisição")
    values = config.get("values", [])

    if col not in df.columns:
        col = "Motivo_da_Requisição" if "Motivo_da_Requisição" in df.columns else None
    if col is None:
        return df

    df_col = df[col].astype(str).str.strip()
    mask = df_col.isin(values)

    # Ajuste manual solicitado: "Triagem" deve sair de Movimentações (MC)
    # e passar para Requisições de Vagas (RC).
    # Como o dashboard filtra por "Motivo_da_Requisição", fazemos uma exceção por STATUS.
    triagem_norm_target = "triagem"
    status_col = _get_status_column(df)
    if status_col and status_col in df.columns:
        df_status_norm = (
            df[status_col]
            .astype(str)
            .str.strip()
            .apply(lambda x: unicodedata.normalize("NFKD", x))
            .apply(lambda x: "".join(c for c in x if not unicodedata.combining(c)))
            .str.lower()
        )
        triagem_mask = df_status_norm == triagem_norm_target

        if board_key == "movimentacoes_mc":
            mask = mask & ~triagem_mask
        elif board_key == "requisicao_vaga_rc":
            mask = mask | triagem_mask

    if not mask.any() and config.get("fallback_contains"):
        for term in config["fallback_contains"]:
            mask = mask | df_col.str.lower().str.contains(term, na=False, regex=False)
    return df[mask].copy()


def _get_status_display_name(board_key: str, status_val: str) -> str:
    """Retorna o nome de exibição do status, ou o original se não houver mapeamento."""
    mapping = STATUS_DISPLAY_NAMES.get(board_key, {})
    s_raw = str(status_val).strip()

    def _normalize_for_mapping(x: str) -> str:
        # Normaliza para comparar mesmo com variação de acentos/case do Jira.
        x_norm = unicodedata.normalize("NFKD", str(x).strip())
        x_norm = "".join(c for c in x_norm if not unicodedata.combining(c))
        x_norm = x_norm.lower()
        x_norm = re.sub(r"\s+", " ", x_norm)
        return x_norm

    if s_raw in mapping:
        return mapping[s_raw]

    s_norm = _normalize_for_mapping(s_raw)
    for k, v in mapping.items():
        if _normalize_for_mapping(k) == s_norm:
            return v

    return s_raw


def _get_status_column(df: pd.DataFrame) -> str:
    """Identifica a coluna de Status."""
    for c in ["Status", "status"]:
        if c in df.columns:
            return c
    for col in df.columns:
        if "status" in col.lower():
            return col
    return ""


def _build_kanban_column_html(
    df: pd.DataFrame, status_col: str, status_val: str, chave_col: str, resumo_col: str, tipo_col: str
) -> str:
    """Monta o HTML de uma coluna do Kanban."""
    df_status = df[df[status_col] == status_val]
    cards_html = ""
    for _, row in df_status.iterrows():
        chave = html.escape(str(row.get(chave_col, "")) if chave_col else "")
        resumo_raw = str(row.get(resumo_col, "")) if resumo_col else ""
        resumo = html.escape(resumo_raw[:120] + ("..." if len(resumo_raw) > 120 else ""))
        tipo = html.escape(str(row.get(tipo_col, "")) if tipo_col else "")

        cards_html += f"""
        <div class="kanban-card">
            <div class="kanban-card-chave">{chave}</div>
            <div class="kanban-card-resumo">{resumo}</div>
            <div class="kanban-card-tipo">{tipo}</div>
        </div>
        """
    return cards_html if cards_html else '<div style="color: #888; font-style: italic; padding: 8px;">Nenhum item</div>'


def _render_kanban_board(df: pd.DataFrame, title: str, board_key: str = "") -> None:
    """Renderiza um quadro Kanban completo com colunas por status e scroll horizontal."""
    if df.empty:
        st.info(f"Nenhum item encontrado para **{title}**.")
        return

    status_col = _get_status_column(df)
    if not status_col:
        st.warning("Coluna de Status não encontrada nos dados.")
        st.dataframe(df.head(20), use_container_width=True, hide_index=True)
        return

    statuses = [s for s in df[status_col].dropna().unique().tolist() if str(s).strip()]

    def _normalize_for_compare(x: str) -> str:
        x_norm = unicodedata.normalize("NFKD", str(x).strip())
        x_norm = "".join(c for c in x_norm if not unicodedata.combining(c))
        x_norm = x_norm.lower()
        x_norm = re.sub(r"\s+", " ", x_norm)
        return x_norm

    # Ordem fixa para Rotinas Trabalhistas (de cima pra baixo)
    if board_key == "rotinas_trabalhistas":
        desired_status_order = [
            "Backlog",
            "Aprovação Diretoria",
            "Aprovação Presidência",
            "Aprovado",
            "Finalizado",
            "Rejeitado",
        ]
        desired_norm_index = { _normalize_for_compare(s): i for i, s in enumerate(desired_status_order) }

        def _sort_status_rotinas(s: str) -> tuple[int, str]:
            n = _normalize_for_compare(s)
            return (desired_norm_index.get(n, 999), n)

        statuses = sorted(statuses, key=_sort_status_rotinas)
    # Ordem fixa para Movimentações (de cima pra baixo) - sequência da imagem
    elif board_key == "movimentacoes_mc":
        desired_status_order = [
            "Backlog",
            "Aprovação Diretoria",
            "Aprovação Presidência",
            "Aprovado",
            "Exames Gerais",
            "Documentação",
            "Finalizado",
            "Rejeitado",
        ]
        desired_norm_index = { _normalize_for_compare(s): i for i, s in enumerate(desired_status_order) }

        def _sort_status_mov(s: str) -> tuple[int, str]:
            n = _normalize_for_compare(s)
            return (desired_norm_index.get(n, 999), n)

        statuses = sorted(statuses, key=_sort_status_mov)
    # Ordem fixa para Requisições de Vagas (de cima pra baixo) - sequência da imagem
    elif board_key == "requisicao_vaga_rc":
        desired_status_order = [
            "Backlog",
            "Aprovação Diretoria",
            "Aprovação Presidência",
            "Triagem",
            "Prospecção",
            "Entrevista RH",
            "Provas",
            "Compliance",
            "Entrevista com Gestor",
            "Aguardando Gestor",
            "Carta Proposta",
            "Documentos e Cadastro",
            "Exames Admissão",
            "Aguardando Integração",
            "Finalizado",
            "Rejeitado",
        ]
        desired_norm_index = { _normalize_for_compare(s): i for i, s in enumerate(desired_status_order) }

        def _sort_status_rc(s: str) -> tuple[int, str]:
            n = _normalize_for_compare(s)
            return (desired_norm_index.get(n, 999), n)

        statuses = sorted(statuses, key=_sort_status_rc)
    else:
        def _sort_status_default(s: str) -> tuple[int, str]:
            s_str = str(s).strip()
            return (0, s_str) if _normalize_for_compare(s_str) == "backlog" else (1, _normalize_for_compare(s_str))

        statuses = sorted(statuses, key=_sort_status_default)

    if not statuses:
        st.info("Nenhum status encontrado.")
        return

    chave_col = "Chave" if "Chave" in df.columns else (df.columns[0] if len(df.columns) > 0 else "")
    resumo_col = "Resumo" if "Resumo" in df.columns else ""
    tipo_col = "Tipo_de_item" if "Tipo_de_item" in df.columns else ""

    # Montar todo o Kanban em HTML com container scrollável
    columns_html = ""
    for status_val in statuses:
        count = len(df[df[status_col] == status_val])
        cards = _build_kanban_column_html(df, status_col, status_val, chave_col, resumo_col, tipo_col)
        outer_label = _get_status_display_name(board_key, status_val)
        inner_status_label = html.escape(str(status_val).strip().upper())
        columns_html += f"""
        <div class="kanban-column">
            <div class="kanban-column-title">{html.escape(outer_label)}</div>
            <div class="kanban-internal-status">{inner_status_label} ({count})</div>
            <hr style="border: none; border-top: 1px solid #dee2e6; margin: 0 0 12px 0;">
            {cards}
        </div>
        """

    scroll_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">
    <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: inherit; background: transparent; color: #333; }}
    .kanban-scroll-container {{
        overflow-x: scroll;
        overflow-y: hidden;
        padding-bottom: 16px;
    }}
    /* Usa scrollbar nativa do navegador (mesma lógica da vertical) - adapta automaticamente ao tema */
    .kanban-board {{
        display: flex;
        flex-direction: row;
        width: max-content;
        min-width: 100%;
        padding: 8px 0;
    }}
    .kanban-column {{
        flex: 0 0 220px;
        min-width: 220px;
        max-width: 280px;
        background: #f8f9fa;
        border-radius: 8px;
        padding: 12px;
        margin-right: 12px;
    }}
    .kanban-column-title {{ font-weight: 600; margin-bottom: 8px; font-size: 0.95rem; }}
    .kanban-internal-status {{
        font-weight: 600;
        font-size: 0.75rem;
        color: #1a73e8;
        background: rgba(26,115,232,0.06);
        border: 1px solid rgba(26,115,232,0.25);
        border-radius: 6px;
        padding: 4px 8px;
        margin: 0 0 12px 0;
    }}
    .kanban-card {{
        background: #fff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        font-size: 0.9rem;
    }}
    .kanban-card-chave {{ font-weight: 600; color: #1a73e8; margin-bottom: 4px; }}
    .kanban-card-resumo {{ color: #333; margin-bottom: 4px; word-wrap: break-word; }}
    .kanban-card-tipo {{ font-size: 0.8rem; color: #666; }}
    </style>
    </head>
    <body>
    <div class="kanban-scroll-container">
        <div class="kanban-board">
            {columns_html}
        </div>
    </div>
    </body>
    </html>
    """
    components.html(scroll_html, height=520, scrolling=True)


def render_acompanhamento_solicitacoes_dashboard() -> None:
    """Renderiza o dashboard completo de Acompanhamento de Solicitações."""
    st.subheader("📋 Acompanhamento de Solicitações")
    st.caption("Quadros Kanban baseados em Jira_projeto_dho_consolidado")

    with st.spinner("Carregando dados do Jira DHO..."):
        df_raw = load_jira_dho_acompanhamento()

    if df_raw.empty:
        st.warning("⚠️ Nenhum dado encontrado na view Jira_projeto_dho_consolidado.")
        return

    # Sidebar: ajuda para configurar filtros e nomes
    with st.sidebar:
        with st.expander("🔧 Configurar quadros"):
            tipo_col = "Motivo_da_Requisição" if "Motivo_da_Requisição" in df_raw.columns else None
            if tipo_col:
                valores = sorted(df_raw[tipo_col].dropna().astype(str).str.strip().unique().tolist())
                st.caption(f"Valores em **{tipo_col}** (filtros do Jira):")
                st.code(", ".join(f'"{v}"' for v in valores[:30]), language=None)
                if len(valores) > 30:
                    st.caption(f"... e mais {len(valores) - 30}")
        with st.expander("📝 Nomes das colunas (Treinamentos)"):
            df_td = _filter_df_by_board(df_raw, "treinamentos_td")
            status_col = _get_status_column(df_td) if not df_td.empty else None
            if status_col:
                statuses_td = sorted(df_td[status_col].dropna().astype(str).str.strip().unique().tolist())
                st.caption("Status no Jira (use em STATUS_DISPLAY_NAMES):")
                st.code(", ".join(f'"{v}"' for v in statuses_td[:25]), language=None)
        with st.expander("📝 Nomes das colunas (Rotinas Trabalhistas)"):
            df_rt = _filter_df_by_board(df_raw, "rotinas_trabalhistas")
            status_col_rt = _get_status_column(df_rt) if not df_rt.empty else None
            if status_col_rt:
                statuses_rt = sorted(df_rt[status_col_rt].dropna().astype(str).str.strip().unique().tolist())
                st.caption("Status no Jira (use em STATUS_DISPLAY_NAMES):")
                st.code(", ".join(f'"{v}"' for v in statuses_rt[:25]), language=None)

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
            _render_kanban_board(df_board, BOARD_FILTERS[board_key]["label"], board_key)
