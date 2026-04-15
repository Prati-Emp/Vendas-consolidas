"""
Dashboard de Acompanhamento Jurídico - Quadro Kanban do Jira (Jurídico).

Fonte: view administracao.Jira_projeto_juridico_consolidado
Objetivo: reproduzir o Kanban usado no acompanhamento de solicitações (DHO),
mas com layout/UX equivalente e mapeamento flexível de colunas.
"""

from __future__ import annotations

import html
import re
import unicodedata
from typing import Any, Dict, List

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from dashboard.utils.md_conn import get_md_connection
from advanced_auth import get_current_user


def _normalize_text_for_match(value: Any) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    if not s or s.lower() in {"none", "nan", "nat", "<na>"}:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"\s+", " ", s)
    return s


def _find_column(df: pd.DataFrame, candidates: List[str]) -> str:
    if df.empty:
        return ""
    normalized_cols = {c: _normalize_text_for_match(c) for c in df.columns}
    for cand in candidates:
        cand_norm = _normalize_text_for_match(cand)
        for col, col_norm in normalized_cols.items():
            if cand_norm and cand_norm in col_norm:
                return str(col)
    return ""


def _extract_emails_from_cell(value: Any) -> List[str]:
    """
    Extrai e-mails de uma célula que pode conter vários valores separados por vírgula.
    Normaliza para lower-case e remove espaços.
    """
    if value is None:
        return []
    raw = str(value).strip()
    if not raw or raw.lower() in {"none", "nan", "nat", "<na>"}:
        return []
    # aceita separadores comuns
    raw = raw.replace(";", ",").replace("|", ",").replace("\n", ",")
    parts = [p.strip().lower() for p in raw.split(",")]
    out = []
    for p in parts:
        if not p:
            continue
        # limpeza leve: remove espaços internos
        p = re.sub(r"\s+", "", p)
        if "@" in p and "." in p:
            out.append(p)
    return out


def _filter_by_row_email_access(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filtra os itens para o usuário logado com base na coluna `JRD - e-mail`.
    Regras:
    - Se a coluna existir, o usuário só vê linhas onde seu e-mail esteja listado (vírgula-separado).
    - Se não houver e-mail de sessão, não exibe nada.
    - Para o Odair, mantém visão completa (admin/owner do quadro).
    """
    if df.empty:
        return df

    user = get_current_user() or {}
    user_email = (user.get("email") or "").strip().lower()
    if not user_email:
        return df.iloc[0:0].copy()

    bypass = {
        "odair.santos@grupoprati.com",
        "odair2d@hotmail.com",
        "gustavo.sordi@grupoprati.com",
        "joao.fantinel@grupoprati.com",
        "angelica.moreira@grupoprati.com",
    }
    if user_email in bypass:
        return df

    col_email = _find_column(df, ["JRD - e-mail", "JRD - email", "JRD email", "e-mail", "email"])
    if not col_email or col_email not in df.columns:
        # se a coluna não existir, não há como validar acesso → não mostra nada
        return df.iloc[0:0].copy()

    emails_per_row = df[col_email].apply(_extract_emails_from_cell)
    mask = emails_per_row.apply(lambda lst: user_email in lst)
    return df.loc[mask].copy()

def _get_status_column(df: pd.DataFrame) -> str:
    if df.empty:
        return ""
    for c in ("Status", "status"):
        if c in df.columns:
            return c
    for col in df.columns:
        if "status" in str(col).lower():
            return str(col)
    # Jira jurídico costuma ter "JRD - Status"
    return _find_column(df, ["jrd - status", "jrd status", "status"])


def _normalize_status_list(values: List[str]) -> List[str]:
    """Normaliza uma lista de status para comparação."""
    return [_normalize_text_for_match(v) for v in values if str(v).strip()]


def _normalized_status_synonyms_for_column(status_val: str) -> frozenset[str]:
    """
    Valores normalizados que devem cair na mesma coluna do Kanban que `status_val`.
    O Jira costuma enviar singular («Finalizado», «Rejeitado») e o quadro usa plural no rótulo.
    """
    n = _normalize_text_for_match(status_val)
    if n == "finalizados":
        return frozenset({"finalizados", "finalizado"})
    if n == "rejeitados":
        return frozenset({"rejeitados", "rejeitado"})
    return frozenset({n})


def _mask_rows_for_kanban_column(df: pd.DataFrame, status_col: str, status_val: str) -> pd.Series:
    """Máscara booleana: linhas pertencentes à coluna de status `status_val` (com sinônimos)."""
    if df.empty or not status_col or status_col not in df.columns:
        return pd.Series(False, index=df.index)
    s_norm = df[status_col].astype(str).str.strip().map(_normalize_text_for_match)
    return s_norm.isin(_normalized_status_synonyms_for_column(status_val))


def _ordered_statuses_with_extras(
    df: pd.DataFrame, status_col: str, desired_status_order: List[str]
) -> List[str]:
    """
    Retorna lista de status na ordem desejada, adicionando ao final
    quaisquer status presentes nos dados e não listados no catálogo.
    A comparação é feita por texto normalizado (sem acentos/case).
    """
    if df.empty or not status_col or status_col not in df.columns:
        return []

    desired = [s for s in desired_status_order if str(s).strip()]
    desired_norm = _normalize_status_list(desired)
    desired_norm_set = set(desired_norm)
    # Evita coluna duplicada quando o Jira manda singular e o catálogo tem plural
    if "finalizados" in desired_norm_set:
        desired_norm_set.add("finalizado")
    if "rejeitados" in desired_norm_set:
        desired_norm_set.add("rejeitado")

    # Mantém o rótulo original informado no catálogo
    statuses_out = list(desired)

    # Extras do dataset
    extras: List[str] = []
    for s in df[status_col].dropna().unique().tolist():
        s_str = str(s).strip()
        if not s_str:
            continue
        n = _normalize_text_for_match(s_str)
        if n and n not in desired_norm_set:
            desired_norm_set.add(n)
            extras.append(s_str)

    extras.sort(key=lambda x: (_normalize_text_for_match(x), str(x).lower()))
    return statuses_out + extras


def _display_label_for_status(status_val: Any, display_map: Dict[str, str] | None) -> str:
    """Retorna rótulo de exibição para um status (usa normalização para casar)."""
    raw = str(status_val).strip()
    if not raw:
        return ""
    if not display_map:
        return raw.upper()
    n = _normalize_text_for_match(raw)
    for k, v in display_map.items():
        if _normalize_text_for_match(k) == n:
            mapped = str(v).strip() or raw
            return mapped.upper()
    return raw.upper()


def _split_solicitacoes_vs_vigentes(df: pd.DataFrame, status_col: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Divide o DataFrame em:
    - Solicitações: itens na(s) etapa(s) iniciais (ex.: Backlog / Solicitação)
    - Vigentes: itens em andamento (exclui encerrados/concluídos/rejeitados)
    Regra baseada em texto normalizado do Status (robusta a variações/acentos).
    """
    if df.empty or not status_col or status_col not in df.columns:
        return df.copy(), df.copy()

    s_norm = df[status_col].astype(str).str.strip().map(_normalize_text_for_match)

    # Catálogo de status por aba (definido pelo negócio)
    solicit_catalog = set(
        _normalize_status_list(
            [
                "Backlog",
                "Pausados",
                "Em elaboração",
                "Conferência",
                "ASS INTERNA",
                "ASS EXTERNA",
                "Aguardando assinatura",
                "Assinados",
                "Finalizados",
                "Rejeitados",
            ]
        )
    )
    # Jira: workflow muitas vezes singular («Finalizado», «Rejeitado»), igual na planilha exportada
    solicit_catalog.add("finalizado")
    solicit_catalog.add("rejeitado")

    vig_catalog = _normalize_status_list(["Vigente", "Em renovação", "Rescindido", "Arquivado"])

    df_solic = df.loc[s_norm.isin(solicit_catalog)].copy()
    df_vig = df.loc[s_norm.isin(set(vig_catalog))].copy()
    return df_solic, df_vig


def _get_area_and_empreendimento(df: pd.DataFrame, row: pd.Series) -> tuple[str, str]:
    """Retorna (Área, Empreendimento) quando existirem."""
    area_col = _find_column(df, ["JRD - Área", "JRD Area", "Área", "Area"])
    emp_col = _find_column(df, ["JRD - Empreendimento", "JRD Empreendimento", "Empreendimento"])

    def _pick(col_name: str) -> str:
        if not col_name or col_name not in df.columns:
            return ""
        v = row.get(col_name, "")
        return str(v).strip() if v is not None else ""

    area_v = _pick(area_col)
    emp_v = _pick(emp_col)
    if area_v.lower() in {"none", "nan", "nat", "<na>"}:
        area_v = ""
    if emp_v.lower() in {"none", "nan", "nat", "<na>"}:
        emp_v = ""
    return area_v, emp_v


def _get_area_like_value(df: pd.DataFrame, row: pd.Series) -> str:
    """Para filtros/buckets: usa Área; se vazio, cai para Empreendimento."""
    area_v, emp_v = _get_area_and_empreendimento(df, row)
    return area_v or emp_v


def _normalize_area_emp_compare(value: Any) -> str:
    """
    Normalização específica para comparar Área vs Empreendimento.
    Trata Villa Bella I/II como equivalente a 1/2 (e vice-versa).
    """
    n = _normalize_text_for_match(value)
    if not n:
        return ""

    # Normalizar variações do Villa Bella
    if "villa bella" in n or "villabella" in n:
        # garantir espaço para facilitar substituições
        s = n.replace("villabella", "villa bella")
        s = re.sub(r"\s+", " ", s).strip()
        # Romanos -> dígitos
        s = re.sub(r"\bvilla bella ii\b", "villa bella 2", s)
        s = re.sub(r"\bvilla bella i\b", "villa bella 1", s)
        return s

    return n


def _parse_date_cell(value: Any) -> pd.Timestamp | None:
    """Converte valor em Timestamp normalizado (ou None)."""
    dt = pd.to_datetime(value, errors="coerce")
    if pd.isna(dt):
        return None
    try:
        return dt.normalize()
    except Exception:
        return pd.Timestamp(dt).normalize()


def _tempo_badge_since_start(start_value: Any) -> tuple[str, str] | None:
    """
    Badge: X dias desde criação (Start_date).
    Cores:
    - até 7 dias: verde
    - até 15 dias: amarelo
    - depois: vermelho
    """
    start_dt = _parse_date_cell(start_value)
    if start_dt is None:
        return None
    today = pd.Timestamp.today().normalize()
    days = int((today - start_dt).days)
    if days < 0:
        days = 0

    if days <= 7:
        bg, fg = "#DCFCE7", "#166534"
    elif days <= 15:
        bg, fg = "#FEF3C7", "#92400E"
    else:
        bg, fg = "#FEE2E2", "#991B1B"

    return (f"⏱ {days} dias desde criação", f"background:{bg}; color:{fg}; border:1px solid rgba(0,0,0,0.08);")


def _tempo_badge_until_deadline(deadline_value: Any) -> tuple[str, str] | None:
    """
    Badge: contagem regressiva até a Data limite.
    Cores (dias restantes):
    - 30+ dias: verde
    - 15-29 dias: amarelo
    - 0-14 dias: vermelho
    - atrasado: vermelho (mostra "Atrasado X dias")
    """
    end_dt = _parse_date_cell(deadline_value)
    if end_dt is None:
        return None
    today = pd.Timestamp.today().normalize()
    remaining = int((end_dt - today).days)

    if remaining < 0:
        bg, fg = "#FEE2E2", "#991B1B"
        return (f"⏰ Atrasado {abs(remaining)} dias", f"background:{bg}; color:{fg}; border:1px solid rgba(0,0,0,0.08);")

    if remaining >= 30:
        bg, fg = "#DCFCE7", "#166534"
    elif remaining >= 15:
        bg, fg = "#FEF3C7", "#92400E"
    else:
        bg, fg = "#FEE2E2", "#991B1B"

    return (f"⏰ Faltam {remaining} dias", f"background:{bg}; color:{fg}; border:1px solid rgba(0,0,0,0.08);")


@st.cache_data(ttl=600)
def load_jira_juridico_acompanhamento() -> pd.DataFrame:
    """Carrega dados da view administracao.Jira_projeto_juridico_consolidado."""
    md_conn = get_md_connection()
    sql = "SELECT * FROM administracao.Jira_projeto_juridico_consolidado"
    try:
        return md_conn.run_query(sql)
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        return pd.DataFrame()


def _build_kanban_column_html(
    df: pd.DataFrame,
    status_col: str,
    status_val: str,
    chave_col: str,
    resumo_col: str,
    *,
    time_mode: str = "",
) -> str:
    mask = _mask_rows_for_kanban_column(df, status_col, status_val)
    df_status = df.loc[mask]
    if df_status.empty:
        return '<div style="color: #888; font-style: italic; padding: 8px;">Nenhum item</div>'

    def _clean_text(v: Any) -> str:
        if v is None:
            return ""
        t = str(v).strip()
        if not t or t.lower() in {"none", "nan", "nat", "<na>"}:
            return ""
        return t

    def _to_display_case(value: Any) -> str:
        text = _clean_text(value)
        if not text:
            return ""
        has_lower = any(ch.islower() for ch in text)
        has_upper = any(ch.isupper() for ch in text)
        if has_lower and has_upper:
            return text
        small_words = {"de", "da", "do", "das", "dos", "e", "em", "com", "para"}

        def repl(match: re.Match[str]) -> str:
            token = match.group(0)
            lower = token.lower()
            if lower in {"rh", "dho", "ti", "cnpj", "jrd"}:
                return lower.upper()
            return token.capitalize()

        normalized = re.sub(r"[A-Za-zÀ-ÿ0-9&/().-]+", repl, text.lower())
        for word in small_words:
            normalized = re.sub(rf"\b{word.capitalize()}\b", word, normalized)
        if normalized:
            normalized = normalized[0].upper() + normalized[1:]
        return normalized

    def _get_tag_color(tag: str) -> str:
        n = _normalize_text_for_match(tag)
        if any(k in n for k in ("contrato", "aditivo", "assinatura")):
            return "#3B82F6"
        if any(k in n for k in ("distrato", "rescis", "encerr")):
            return "#EF4444"
        if any(k in n for k in ("analise", "análise", "parecer")):
            return "#10B981"
        return "#6366F1"

    # Campos comuns na view jurídica (com detecção flexível)
    motivo_col = _find_column(df, ["jrd motivo da requisição consolidada", "motivo", "requisi"])
    responsavel_col = _find_column(df, ["responsavel", "responsável", "owner"])
    solicitante_col = _find_column(df, ["solicitante", "requerente", "nome", "colaborador"])
    tipo_col = _find_column(df, ["tipo de contrato", "tipo", "contrato"])
    area_col = _find_column(df, ["JRD - Área", "JRD Area", "Área", "Area"])
    # Data exibida no card: preferir "Data limite" (prazo), com fallback para criação/início
    data_col = _find_column(
        df,
        [
            "JRD - Data limite",
            "JRD Data limite",
            "Data limite",
            "data limite",
            "deadline",
            "due date",
            "data de criacao",
            "data criação",
            "cria",
            "created",
            "start",
        ],
    )
    start_col = _find_column(df, ["Start_date", "start date", "data de inicio", "data início", "inicio", "início"])

    cards_html = ""
    for _, row in df_status.iterrows():
        chave_txt = _clean_text(row.get(chave_col, "")) if chave_col else ""
        chave = html.escape(chave_txt.upper() if chave_txt else "")
        resumo_raw = _to_display_case(row.get(resumo_col, "")) if resumo_col else ""
        resumo_raw = resumo_raw[:140] + ("..." if len(resumo_raw) > 140 else "")
        resumo = html.escape(resumo_raw)

        motivo_raw = _to_display_case(row.get(motivo_col, "")) if motivo_col else ""
        motivo_raw = motivo_raw[:120] + ("..." if len(motivo_raw) > 120 else "")
        motivo = html.escape(motivo_raw)

        responsavel_raw = _to_display_case(row.get(responsavel_col, "")) if responsavel_col else ""
        responsavel = html.escape(responsavel_raw)

        solicitante_raw = _to_display_case(row.get(solicitante_col, "")) if solicitante_col else ""
        solicitante = html.escape(solicitante_raw)

        tipo_raw = _to_display_case(row.get(tipo_col, "")) if tipo_col else ""
        tipo = html.escape(tipo_raw)

        tempo_badge_html = ""
        if time_mode == "since_start":
            badge = _tempo_badge_since_start(row.get(start_col, None) if start_col else None)
            if badge:
                txt, style = badge
                tempo_badge_html = f'<div class="kanban-card-badge" style="{style}">{html.escape(txt)}</div>'
        elif time_mode == "until_deadline":
            badge = _tempo_badge_until_deadline(row.get(data_col, None) if data_col else None)
            if badge:
                txt, style = badge
                tempo_badge_html = f'<div class="kanban-card-badge" style="{style}">{html.escape(txt)}</div>'

        data_raw = _clean_text(row.get(data_col, "")) if data_col else ""
        data_txt = html.escape(data_raw)

        badge_color = _get_tag_color(motivo_raw or tipo_raw or "")
        resumo_html = f'<div class="kanban-card-resumo">{resumo}</div>' if resumo else ""
        motivo_norm = _normalize_text_for_match(motivo_raw)
        tipo_norm = _normalize_text_for_match(tipo_raw)
        show_motivo = bool(motivo_norm)
        show_tipo = bool(tipo_norm) and (tipo_norm != motivo_norm)

        motivo_html = (
            f'<div class="kanban-card-badge" style="background:{badge_color}; color:#fff;">{motivo}</div>'
            if show_motivo
            else ""
        )
        tipo_html = (
            f'<div class="kanban-card-badge" style="background:rgba(99,102,241,0.15); color:#C7D2FE; border:1px solid rgba(99,102,241,0.35);">{tipo}</div>'
            if show_tipo
            else ""
        )
        solicitante_html = f'<div class="kanban-card-line">👤 {solicitante}</div>' if solicitante else ""
        responsavel_html = f'<div class="kanban-card-line">Resp: {responsavel}</div>' if responsavel else ""
        if time_mode == "until_deadline":
            data_html = f'<div class="kanban-card-line">📅 {data_txt}</div>' if data_txt else ""
        else:
            data_html = ""

        area_v, emp_v = _get_area_and_empreendimento(df, row)
        area_raw = _to_display_case(area_v) if area_v else ""
        emp_raw = _to_display_case(emp_v) if emp_v else ""
        area_txt = html.escape(area_raw)
        emp_txt = html.escape(emp_raw)

        # Mostrar "Área" e "Empreendimento" logo abaixo do badge de tempo (Solicitações e Vigentes)
        area_html = (
            f'<div class="kanban-card-line">🏢 {area_txt}</div>'
            if (area_txt and time_mode in {"since_start", "until_deadline"})
            else ""
        )
        # Se Empreendimento repetir Área, não exibir (evita duplicidade visual)
        show_emp = bool(emp_v) and (
            _normalize_area_emp_compare(emp_v) != _normalize_area_emp_compare(area_v)
        )
        emp_html = (
            f'<div class="kanban-card-line">🏗 {emp_txt}</div>'
            if (show_emp and emp_txt and time_mode in {"since_start", "until_deadline"})
            else ""
        )

        cards_html += f"""
        <div class="kanban-card" style="border-left: 4px solid {badge_color};">
            <div class="kanban-card-chave">{chave}</div>
            {resumo_html}
            <div class="kanban-card-meta">
                {tempo_badge_html}
                {motivo_html}
                {tipo_html}
            </div>
            {area_html}
            {emp_html}
            {solicitante_html}
            {responsavel_html}
            {data_html}
        </div>
        """
    return cards_html if cards_html else '<div style="color: #888; font-style: italic; padding: 8px;">Nenhum item</div>'


def _render_kanban_board(
    df: pd.DataFrame,
    title: str,
    desired_status_order: List[str] | None = None,
    status_display_map: Dict[str, str] | None = None,
    *,
    time_mode: str = "",
) -> None:
    if df.empty:
        st.info(f"Nenhum item encontrado para **{title}**.")
        return

    status_col = _get_status_column(df)
    if not status_col or status_col not in df.columns:
        st.warning("Coluna de Status não encontrada nos dados.")
        st.dataframe(df.head(30), use_container_width=True, hide_index=True)
        return

    if desired_status_order:
        statuses = _ordered_statuses_with_extras(df, status_col, desired_status_order)
    else:
        def _norm(x: Any) -> str:
            return _normalize_text_for_match(x)

        statuses = [s for s in df[status_col].dropna().unique().tolist() if str(s).strip()]

        def _sort_status_default(s: Any) -> tuple[int, str]:
            s_str = str(s).strip()
            return (0, s_str) if _norm(s_str) == "backlog" else (1, _norm(s_str))

        statuses = sorted(statuses, key=_sort_status_default)
    if not statuses:
        st.info("Nenhum status encontrado.")
        return

    # Colunas principais (heurística)
    chave_col = _find_column(df, ["chave", "key"]) or ("Chave" if "Chave" in df.columns else (df.columns[0] if len(df.columns) > 0 else ""))
    resumo_col = _find_column(
        df,
        [
            "JRD - Resumo",
            "JRD Resumo",
            "resumo",
            "summary",
            "titul",
            "título",
        ],
    ) or ("Resumo" if "Resumo" in df.columns else "")

    # Altura dinâmica
    max_cards_in_column = 0
    for status_val in statuses:
        max_cards_in_column = max(
            max_cards_in_column, int(_mask_rows_for_kanban_column(df, status_col, status_val).sum())
        )
    board_height = max(520, min(1400, 200 + (max_cards_in_column * 150)))

    headers_html = ""
    cards_columns_html = ""
    for status_val in statuses:
        cards = _build_kanban_column_html(
            df,
            status_col,
            status_val,
            chave_col,
            resumo_col,
            time_mode=time_mode,
        )
        label = html.escape(_display_label_for_status(status_val, status_display_map))
        n_items = int(_mask_rows_for_kanban_column(df, status_col, status_val).sum())
        headers_html += f"""
        <div class="kanban-column kanban-column-header-cell">
            <div class="kanban-column-title">{label} <span class="kanban-column-count">({n_items})</span></div>
            <hr style="border: none; border-top: 1px solid #dee2e6; margin: 0;">
        </div>
        """
        cards_columns_html += f"""
        <div class="kanban-column kanban-column-cards">
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
    .kanban-sticky-top {{
        position: sticky;
        top: 0;
        z-index: 20;
        background: #0B1220;
        padding-bottom: 4px;
    }}
    .kanban-top-scroll {{
        overflow-x: auto;
        overflow-y: hidden;
        height: 14px;
        margin-bottom: 6px;
    }}
    .kanban-top-scroll-inner {{ height: 1px; }}
    .kanban-scroll-container {{
        overflow-x: scroll;
        overflow-y: hidden;
        padding-bottom: 16px;
    }}
    .kanban-headers-scroll {{
        overflow-x: auto;
        overflow-y: hidden;
        margin-bottom: 2px;
        scrollbar-width: none;
        -ms-overflow-style: none;
    }}
    .kanban-headers-scroll::-webkit-scrollbar {{ display: none; }}
    .kanban-board-headers, .kanban-board-cards {{
        display: flex;
        flex-direction: row;
        align-items: flex-start;
        width: max-content;
        min-width: 100%;
        padding: 8px 0;
    }}
    .kanban-column {{
        flex: 0 0 260px;
        width: 260px;
        min-width: 260px;
        max-width: 260px;
        overflow-x: hidden;
        background: #f8f9fa;
        border-radius: 8px;
        padding: 12px;
        margin-right: 12px;
    }}
    .kanban-column-title {{
        font-weight: 600;
        margin-bottom: 6px;
        font-size: 0.82rem;
        line-height: 1.15;
        text-align: center;
        letter-spacing: 0.2px;
        word-break: break-word;
        overflow-wrap: anywhere;
    }}
    .kanban-column-count {{
        font-weight: 700;
        font-size: 0.78em;
        color: #374151;
        white-space: nowrap;
    }}
    .kanban-card {{
        background: #fff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        width: 100%;
        max-width: 100%;
        word-break: break-word;
        overflow-wrap: anywhere;
    }}
    .kanban-card-chave {{
        font-weight: 600;
        color: #1a73e8;
        margin-bottom: 6px;
        font-size: 0.85rem;
    }}
    .kanban-card-resumo {{
        color: #1F2937;
        margin-bottom: 8px;
        font-weight: 700;
        line-height: 1.2;
        font-size: 0.95rem;
    }}
    .kanban-card-meta {{
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        margin-bottom: 10px;
        width: 100%;
        max-width: 100%;
        overflow: hidden;
    }}
    .kanban-card-badge {{
        display: inline-flex;
        align-items: center;
        border-radius: 999px;
        padding: 4px 8px;
        font-size: 0.72rem;
        font-weight: 600;
        line-height: 1;
        max-width: 100%;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        min-width: 0;
    }}
    .kanban-card-line {{
        font-size: 0.8rem;
        color: #374151;
        margin-bottom: 4px;
        max-width: 100%;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }}
    </style>
    </head>
    <body>
    <div class="kanban-sticky-top">
        <div id="kanbanTopScroll" class="kanban-top-scroll">
            <div id="kanbanTopScrollInner" class="kanban-top-scroll-inner"></div>
        </div>
        <div id="kanbanHeaderScroll" class="kanban-headers-scroll">
            <div id="kanbanHeaderBoard" class="kanban-board-headers">
                {headers_html}
            </div>
        </div>
    </div>
    <div id="kanbanBottomScroll" class="kanban-scroll-container">
        <div id="kanbanCardsBoard" class="kanban-board-cards">
            {cards_columns_html}
        </div>
    </div>
    <script>
    (function () {{
        const top = document.getElementById("kanbanTopScroll");
        const topInner = document.getElementById("kanbanTopScrollInner");
        const header = document.getElementById("kanbanHeaderScroll");
        const headerBoard = document.getElementById("kanbanHeaderBoard");
        const bottom = document.getElementById("kanbanBottomScroll");
        const cardsBoard = document.getElementById("kanbanCardsBoard");
        if (!top || !topInner || !header || !headerBoard || !bottom || !cardsBoard) return;

        const syncWidth = () => {{
            const width = Math.max(headerBoard.scrollWidth, cardsBoard.scrollWidth);
            topInner.style.width = `${{width}}px`;
        }};

        let syncingFromTop = false;
        let syncingFromHeader = false;
        let syncingFromBottom = false;

        top.addEventListener("scroll", () => {{
            if (syncingFromBottom || syncingFromHeader) return;
            syncingFromTop = true;
            bottom.scrollLeft = top.scrollLeft;
            header.scrollLeft = top.scrollLeft;
            requestAnimationFrame(() => {{ syncingFromTop = false; }});
        }});
        header.addEventListener("scroll", () => {{
            if (syncingFromTop || syncingFromBottom) return;
            syncingFromHeader = true;
            bottom.scrollLeft = header.scrollLeft;
            top.scrollLeft = header.scrollLeft;
            requestAnimationFrame(() => {{ syncingFromHeader = false; }});
        }});
        bottom.addEventListener("scroll", () => {{
            if (syncingFromTop || syncingFromHeader) return;
            syncingFromBottom = true;
            top.scrollLeft = bottom.scrollLeft;
            header.scrollLeft = bottom.scrollLeft;
            requestAnimationFrame(() => {{ syncingFromBottom = false; }});
        }});
        syncWidth();
        window.addEventListener("resize", syncWidth);
        window.addEventListener("load", syncWidth);
    }})();
    </script>
    </body>
    </html>
    """
    components.html(scroll_html, height=int(board_height), scrolling=True)


def render_acompanhamento_juridico_dashboard() -> None:
    st.subheader("⚖️ Acompanhamento Jurídico")

    with st.spinner("Carregando dados do Jira Jurídico..."):
        df_raw = load_jira_juridico_acompanhamento()

    if df_raw.empty:
        st.warning("⚠️ Nenhum dado encontrado na view Jira_projeto_juridico_consolidado.")
        return

    # Controle de acesso por item via coluna `JRD - e-mail`
    df_raw = _filter_by_row_email_access(df_raw)
    if df_raw.empty:
        st.info("Você não possui itens vinculados ao seu e-mail no Jurídico.")
        return

    # Sidebar: filtros simples por colunas relevantes (se existirem)
    with st.sidebar:
        st.markdown("### 🔎 Filtros")
        status_col = _get_status_column(df_raw)
        resp_col = _find_column(df_raw, ["responsavel", "responsável"])
        motivo_col = _find_column(
            df_raw,
            [
                "motivo consolidado",
                "jrd motivo consolidado",
                "jrd - motivo consolidado",
                "jrd motivo da requisição consolidada",
                "motivo da requisição consolidada",
                "motivo",
                "requisi",
            ],
        )
        area_col = _find_column(df_raw, ["JRD - Área", "JRD Area", "Área", "Area"])
        emp_col = _find_column(df_raw, ["JRD - Empreendimento", "JRD Empreendimento", "Empreendimento"])

        df_f = df_raw.copy()

        def _multi(col_label: str, col_name: str, key: str) -> List[str]:
            if not col_name or col_name not in df_f.columns:
                return []
            opts = sorted(
                {
                    v
                    for v in df_f[col_name].dropna().astype(str).str.strip().tolist()
                    if v and v.lower() not in {"none", "nan", "nat", "<na>"}
                }
            )
            return st.multiselect(col_label, options=opts, default=[], key=key, placeholder="")

        # Ordem solicitada: Motivo no topo; remove filtro por Status; adiciona Área e Empreendimento
        sel_motivo = _multi("Motivo", motivo_col, "jur_filter_motivo") if motivo_col else []
        sel_area = _multi("Área", area_col, "jur_filter_area") if area_col else []
        sel_emp = _multi("Empreendimento", emp_col, "jur_filter_emp") if emp_col else []
        sel_resp = _multi("Responsável", resp_col, "jur_filter_resp") if resp_col else []

        if sel_motivo and motivo_col:
            df_f = df_f[df_f[motivo_col].astype(str).str.strip().isin(sel_motivo)]
        if sel_area and area_col:
            df_f = df_f[df_f[area_col].astype(str).str.strip().isin(sel_area)]
        if sel_emp and emp_col:
            df_f = df_f[df_f[emp_col].astype(str).str.strip().isin(sel_emp)]
        if sel_resp and resp_col:
            df_f = df_f[df_f[resp_col].astype(str).str.strip().isin(sel_resp)]

    # Abas internas: Solicitações x Vigentes (com base na coluna Status)
    tab_solic, tab_vig = st.tabs(["📩 Solicitações", "📌 Vigentes"])
    df_solic, df_vig = _split_solicitacoes_vs_vigentes(df_f, status_col) if status_col else (df_f, df_f)

    with tab_solic:
        _render_kanban_board(
            df_solic,
            "Solicitações (Jurídico)",
            desired_status_order=[
                "Backlog",
                "Pausados",
                "Em elaboração",
                "Conferência",
                "ASS INTERNA",
                "ASS EXTERNA",
                "Aguardando assinatura",
                "Assinados",
                "Finalizados",
                "Rejeitados",
            ],
            status_display_map={"Backlog": "SOLICITAÇÕES"},
            time_mode="since_start",
        )
    with tab_vig:
        # Filtro clicável por Área (Vigentes)
        area_col_vig = _find_column(df_vig, ["JRD - Área", "JRD Area", "Área", "Area"])
        emp_col_vig = _find_column(df_vig, ["JRD - Empreendimento", "JRD Empreendimento", "Empreendimento"])

        def _area_bucket(v: Any) -> str:
            n = _normalize_text_for_match(v)
            if not n:
                return "Todo resto"
            # Villa Bella: tratar I/II como 1/2 (ex.: "Villa Bella II" == "Villa Bella 2")
            villa_norm = n.replace(" villa ", " ").replace("-", " ").replace("_", " ")
            villa_norm = re.sub(r"\s+", " ", villa_norm).strip()
            if (
                "villa bella 1" in villa_norm
                or "villabella 1" in villa_norm
                or "villa bella i" in villa_norm
                or "villabella i" in villa_norm
            ):
                return "Villa Bella 1"
            if (
                "villa bella 2" in villa_norm
                or "villabella 2" in villa_norm
                or "villa bella ii" in villa_norm
                or "villabella ii" in villa_norm
            ):
                return "Villa Bella 2"
            if "carmel" in n:
                return "Carmel"
            if "ducale" in n:
                return "Ducale"
            if "horizont" in n:
                return "Horizont"
            return "Todo resto"

        buckets = [
            "Villa Bella 1",
            "Villa Bella 2",
            "Carmel",
            "Ducale",
            "Horizont",
            "Todo resto",
        ]
        # Começa sem seleção (mostra tudo). Clicar 1x seleciona; clicar 2x na mesma opção limpa.
        if "jur_vig_area_bucket" not in st.session_state:
            st.session_state["jur_vig_area_bucket"] = None

        cols = st.columns(len(buckets))
        for col, b in zip(cols, buckets):
            with col:
                selected = st.session_state.get("jur_vig_area_bucket") == b
                if st.button(
                    b,
                    key=f"jur_vig_area_btn_{_normalize_text_for_match(b) or b}",
                    type="primary" if selected else "secondary",
                    use_container_width=True,
                ):
                    st.session_state["jur_vig_area_bucket"] = None if selected else b
                    st.rerun()

        df_vig_show = df_vig
        if (area_col_vig and area_col_vig in df_vig.columns) or (emp_col_vig and emp_col_vig in df_vig.columns):
            bucket_series = df_vig.apply(lambda r: _area_bucket(_get_area_like_value(df_vig, r)), axis=1)
            chosen = st.session_state.get("jur_vig_area_bucket")
            if chosen:
                df_vig_show = df_vig.loc[bucket_series == chosen].copy()

        _render_kanban_board(
            df_vig_show,
            "Vigentes (Jurídico)",
            desired_status_order=["Vigente", "Em renovação", "Rescindido", "Arquivado"],
            time_mode="until_deadline",
        )

