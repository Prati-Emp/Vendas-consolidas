"""
Indicadores Jurídico (Jira - projeto JRD)

Base: view administracao.Jira_projeto_juridico_consolidado
"""

from __future__ import annotations

import html
import re
import textwrap
import unicodedata
from datetime import date as date_type
from typing import Any, Callable, List, Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.utils.md_conn import get_md_connection
from advanced_auth import get_current_user


# Textos longos da aba → tooltip no «?» ao lado de «Por motivo»
_JUR_TT_TEMPO_ELAB_ABA = (
    "Usa a coluna Tempo em elaboração (min) da view (tempo acumulado no status, via Time in Status). "
    "Valores convertidos para horas. O período é o da data de fechamento (datas ao lado); "
    "o filtro Por motivo aplica-se só a esta aba."
)
_JUR_TT_ELAB_CONF_ABA = (
    "Por issue: lemos Linha do tempo (status) (transições de → para). "
    "Elaborada = passou por Em elaboração ao menos uma vez; Conferida = passou por Conferência ao menos uma vez. "
    "Repetições da mesma etapa contam uma vez por issue. Resumos: Motivo à esquerda e Responsável à direita. "
    "O filtro Por motivo no topo restringe só esta aba."
)
_JUR_TT_REJEITADAS_ABA = (
    "Filtro por **motivo** da requisição (consolidado): aplica-se somente à aba **Rejeitadas**. "
    "As **datas** seguem o mesmo recorte global de **data de fechamento** das demais abas."
)


def _jur_por_motivo_label_with_tooltip(*, tooltip: str) -> str:
    """Rótulo «📍 Por motivo» + interrogação com tooltip nativo (atributo title)."""
    t_attr = html.escape(" ".join(tooltip.split()))
    return (
        '<div style="font-size:0.875rem;color:rgba(250,250,250,0.82);margin:0 0 0.08rem 0;line-height:1.1;'
        'display:flex;align-items:center;gap:0.35rem;flex-wrap:wrap;">'
        "<span>📍 Por motivo</span>"
        f'<abbr title="{t_attr}" style="cursor:help;text-decoration:none;display:inline-flex;align-items:center;'
        "justify-content:center;min-width:1.1rem;height:1.1rem;border:1px solid rgba(250,250,250,0.35);"
        'border-radius:999px;font-size:0.72rem;font-weight:600;line-height:1;color:rgba(250,250,250,0.92);">?</abbr>'
        "</div>"
    )


def _jur_filter_top_label(text: str) -> str:
    """Rótulo padrão para alinhar os campos no topo das abas."""
    return (
        '<div style="font-size:0.875rem;color:rgba(250,250,250,0.82);'
        'margin:0 0 0.25rem 0;line-height:1.2;">'
        f"{html.escape(text)}"
        "</div>"
    )


def _jur_add_total_row(df: pd.DataFrame, total_label: str = "Total") -> pd.DataFrame:
    """Adiciona uma linha final de total para colunas numéricas."""
    if df is None or df.empty:
        return df

    out = df.copy()
    total_row: dict[str, Any] = {}
    numeric_cols = [c for c in out.columns if pd.api.types.is_numeric_dtype(out[c])]

    for c in out.columns:
        if c in numeric_cols:
            total_row[c] = out[c].fillna(0).sum()
        else:
            total_row[c] = ""

    label_col = next((c for c in out.columns if c not in numeric_cols), out.columns[0])
    total_row[label_col] = total_label

    return pd.concat([out, pd.DataFrame([total_row])], ignore_index=True)


def _jur_fin_mark_pull_main_to_graf() -> None:
    """Quando o usuário altera os filtros do topo, copia o estado para a linha acima dos gráficos no próximo run."""
    st.session_state["jur_fin_pull_main_to_graf"] = True


_K_FECH_I = "jur_ind_fechamento_inicio"
_K_FECH_F = "jur_ind_fechamento_fim"
_KT_ELAB_FECH_I = "jur_ind_tempo_elab_fech_inicio"
_KT_ELAB_FECH_F = "jur_ind_tempo_elab_fech_fim"
_KT_ELAB_MOT = "jur_ind_tempo_elab_motivo"
_K_EC_FECH_I = "jur_ind_elab_conf_fech_inicio"
_K_EC_FECH_F = "jur_ind_elab_conf_fech_fim"
_K_EC_MOT = "jur_ind_elab_conf_motivo"
_K_REJ_FECH_I = "jur_ind_rejeitadas_fech_inicio"
_K_REJ_FECH_F = "jur_ind_rejeitadas_fech_fim"
_K_REJ_MOT = "jur_ind_rejeitadas_motivo"


def _jur_sync_main_fech_to_tempo_tab() -> None:
    """Mantém o filtro de datas da aba Tempo de elaboração alinhado ao da aba Finalizados."""
    st.session_state[_KT_ELAB_FECH_I] = st.session_state[_K_FECH_I]
    st.session_state[_KT_ELAB_FECH_F] = st.session_state[_K_FECH_F]


def _jur_sync_main_fech_to_elab_conf_tab() -> None:
    """Espelha o período global nas datas da aba Elaborada vs Conferência."""
    st.session_state[_K_EC_FECH_I] = st.session_state[_K_FECH_I]
    st.session_state[_K_EC_FECH_F] = st.session_state[_K_FECH_F]


def _jur_sync_main_fech_to_rejeitadas_tab() -> None:
    """Espelha o período global nas datas da aba Rejeitadas."""
    st.session_state[_K_REJ_FECH_I] = st.session_state[_K_FECH_I]
    st.session_state[_K_REJ_FECH_F] = st.session_state[_K_FECH_F]


def _jur_fin_main_fech_change_sync_tempo() -> None:
    _jur_fin_mark_pull_main_to_graf()
    _jur_sync_main_fech_to_tempo_tab()
    _jur_sync_main_fech_to_elab_conf_tab()
    _jur_sync_main_fech_to_rejeitadas_tab()


def _jur_tempo_elab_fech_change_apply_main() -> None:
    """Alteração nas datas na aba Tempo de elaboração atualiza o período global (data de fechamento)."""
    st.session_state[_K_FECH_I] = st.session_state[_KT_ELAB_FECH_I]
    st.session_state[_K_FECH_F] = st.session_state[_KT_ELAB_FECH_F]
    _jur_fin_mark_pull_main_to_graf()
    _jur_sync_main_fech_to_elab_conf_tab()
    _jur_sync_main_fech_to_rejeitadas_tab()
    st.rerun()


def _jur_elab_conf_fech_change_apply_main() -> None:
    """Alteração nas datas na aba Elaborada vs Conferência atualiza o período global."""
    st.session_state[_K_FECH_I] = st.session_state[_K_EC_FECH_I]
    st.session_state[_K_FECH_F] = st.session_state[_K_EC_FECH_F]
    _jur_fin_mark_pull_main_to_graf()
    _jur_sync_main_fech_to_tempo_tab()
    _jur_sync_main_fech_to_rejeitadas_tab()
    st.rerun()


def _jur_rejeitadas_fech_change_apply_main() -> None:
    """Alteração nas datas na aba Rejeitadas atualiza o período global."""
    st.session_state[_K_FECH_I] = st.session_state[_K_REJ_FECH_I]
    st.session_state[_K_FECH_F] = st.session_state[_K_REJ_FECH_F]
    _jur_fin_mark_pull_main_to_graf()
    _jur_sync_main_fech_to_tempo_tab()
    _jur_sync_main_fech_to_elab_conf_tab()
    st.rerun()


def _normalize(value: Any) -> str:
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


def _find_col(df: pd.DataFrame, candidates: List[str]) -> str:
    if df.empty:
        return ""
    norm_cols = {c: _normalize(c) for c in df.columns}
    for cand in candidates:
        c_norm = _normalize(cand)
        for col, col_norm in norm_cols.items():
            if c_norm and c_norm in col_norm:
                return str(col)
    return ""


def _extract_emails_cell(value: Any) -> List[str]:
    if value is None:
        return []
    raw = str(value).strip()
    if not raw or raw.lower() in {"none", "nan", "nat", "<na>"}:
        return []
    raw = raw.replace(";", ",").replace("|", ",").replace("\n", ",")
    parts = [re.sub(r"\s+", "", p.strip().lower()) for p in raw.split(",")]
    return [p for p in parts if p and "@" in p and "." in p]


def _filter_by_email_access(df: pd.DataFrame) -> pd.DataFrame:
    """Mesmo padrão do Kanban: filtra por `JRD - e-mail`, com bypass para admins."""
    if df.empty:
        return df
    user = get_current_user() or {}
    email = (user.get("email") or "").strip().lower()
    if not email:
        return df.iloc[0:0].copy()

    bypass = {
        "odair.santos@grupoprati.com",
        "odair2d@hotmail.com",
        "gustavo.sordi@grupoprati.com",
        "joao.fantinel@grupoprati.com",
    }
    if email in bypass:
        return df

    col_email = _find_col(df, ["JRD - e-mail", "JRD - email", "JRD email", "e-mail", "email"])
    if not col_email or col_email not in df.columns:
        return df.iloc[0:0].copy()
    mask = df[col_email].apply(lambda x: email in _extract_emails_cell(x))
    return df.loc[mask].copy()


@st.cache_data(ttl=600)
def load_jira_juridico_consolidado() -> pd.DataFrame:
    md_conn = get_md_connection()
    sql = "SELECT * FROM administracao.Jira_projeto_juridico_consolidado"
    try:
        return md_conn.run_query(sql)
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        return pd.DataFrame()


def _status_is_rejeitado(s: Any) -> bool:
    n = _normalize(s)
    return bool(n) and ("rejeit" in n or "reprov" in n)


def _empreendimento_label_tabela(value: Any) -> str:
    """
    Rótulo exibido só na tabela «Por Empreendimento»: padroniza Villa Bella I/II para 1/2.
    (Ex.: «Obra 0villa bella I» → «Obra 0villa bella 1».)
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "Não informado"
    s = str(value).strip()
    if not s:
        return "Não informado"
    if _normalize(s) == "nao informado":
        return s
    # II antes de I para não pegar o primeiro «I» de «II»
    t = re.sub(r"(?i)(\d*villa\s*bella)\s+II\b", r"\1 2", s)
    t = re.sub(r"(?i)(\d*villa\s*bella)\s+I\b", r"\1 1", t)
    return t


# Margens fixas para os 3 gráficos alinharem entre si. Evitar ML excessivo: em colunas estreitas do Streamlit
# rouba a área útil e as barras ficam “finas”; ~185–195px costuma equilibrar rótulo vs amplitude.
_JUR_HBAR_ML = 168
_JUR_HBAR_MR = 50
_JUR_HBAR_TITLE_SZ = 17
_JUR_HBAR_Y_TICK_SZ = 13
# Mesmo padrão visual do dashboard de Repasses (integração nativa de tema do Streamlit + Plotly).
_JUR_HBAR_MARKER = "#002b55"
# Tamanho do número à direita da barra (Repasses usa 14 nas anotações de quantidade).
_JUR_HBAR_ANNO_QSZ = 14


def _jur_hex_luminance(hex_color: str) -> float | None:
    """Luminância perceptiva 0–255 para #hex; None se inválido."""
    s = str(hex_color or "").strip().lower()
    if not s.startswith("#"):
        return None
    s = s.lstrip("#")
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    if len(s) != 6:
        return None
    try:
        r = int(s[0:2], 16)
        g = int(s[2:4], 16)
        b = int(s[4:6], 16)
    except ValueError:
        return None
    return 0.299 * r + 0.587 * g + 0.114 * b


def _jur_hbar_annotation_value_color() -> str:
    """
    Valores à direita da barra: branco no UI escuro; #111827 no claro.
    Com System ou `theme.base` vazio no servidor, usa fundo secundário e textColor para inferir.
    """
    base = (st.get_option("theme.base") or "").strip().lower()
    if base == "light":
        return "#111827"
    if base == "dark":
        return "#FFFFFF"

    bg = (st.get_option("theme.backgroundColor") or "").strip()
    lum_bg = _jur_hex_luminance(bg)
    if lum_bg is not None and lum_bg < 140:
        return "#FFFFFF"

    sb = (st.get_option("theme.secondaryBackgroundColor") or "").strip()
    lum_sb = _jur_hex_luminance(sb)
    if lum_sb is not None and lum_sb < 140:
        return "#FFFFFF"

    tc = (st.get_option("theme.textColor") or "").strip()
    lum_tx = _jur_hex_luminance(tc)
    if lum_tx is not None and lum_tx >= 140:
        return "#FFFFFF"

    return "#111827"


def _jur_hbar_value_annotations(y_labels: List[Any], x_values: List[float], fmt: Callable[[Any], str]) -> list[dict[str, Any]]:
    """Quantidade/valor à direita da barra, negrito; cor do número conforme tema claro/escuro."""
    ac = _jur_hbar_annotation_value_color()
    annotations: list[dict[str, Any]] = []
    for y, raw in zip(y_labels, x_values):
        fv = float(raw)
        s = fmt(raw)
        annotations.append(
            dict(
                x=fv,
                y=y,
                text=f" <b>{s}</b>",
                xanchor="left",
                yanchor="middle",
                showarrow=False,
                font=dict(color=ac, size=_JUR_HBAR_ANNO_QSZ),
            )
        )
    return annotations


def _plot_juridico_hbar_qtd(title: str, df: pd.DataFrame, label_col: str, *, max_categorias: int = 30) -> go.Figure:
    """
    Barras horizontais como Repasses: fundo transparente, barra #002b55;
    valores em anotação com cor clara/escura conforme tema; título/eixo pelo `st.plotly_chart` padrão.
    """
    _tit = dict(
        text=title,
        font=dict(size=_JUR_HBAR_TITLE_SZ),
        x=0.5,
        xanchor="center",
        yanchor="top",
    )
    _marg = dict(l=_JUR_HBAR_ML, r=_JUR_HBAR_MR, t=62, b=12)

    if df.empty or label_col not in df.columns:
        fig = go.Figure()
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            title=_tit,
            height=240,
            margin=_marg,
        )
        return fig

    d = df.sort_values("Qtd", ascending=True).tail(max_categorias).copy()
    raw_lbl = d[label_col].astype(str).str.strip()
    labels = raw_lbl.apply(lambda s: (s[:46] + "…") if len(s) > 47 else s)
    qty = d["Qtd"].astype(int)
    x_max = int(qty.max()) if len(qty) else 1
    y_list = labels.tolist()
    q_list = [float(x) for x in qty.tolist()]
    annos = _jur_hbar_value_annotations(y_list, q_list, lambda v: str(int(v)))
    _marg_dyn = dict(l=_JUR_HBAR_ML, r=88, t=62, b=12)
    # Folga para o número após a barra (todas as linhas têm anotação).
    x_hi_pad = 1.42

    fig = go.Figure(
        go.Bar(
            x=qty,
            y=labels,
            orientation="h",
            marker=dict(color=_JUR_HBAR_MARKER, line=dict(width=0)),
            cliponaxis=False,
            hovertemplate="%{y}<br>Qtd: %{x}<extra></extra>",
        )
    )
    h = min(820, max(280, 34 * len(labels) + 140))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        title=_tit,
        margin=_marg_dyn,
        height=h,
        annotations=annos,
        xaxis=dict(
            visible=False,
            range=[0, max(x_max * x_hi_pad, 1)] if x_max else None,
            fixedrange=True,
        ),
        yaxis=dict(
            title="",
            automargin=False,
            tickfont=dict(size=_JUR_HBAR_Y_TICK_SZ),
        ),
        showlegend=False,
        bargap=0.18,
    )
    return fig


def _plot_juridico_hbar_horas(
    title: str,
    df: pd.DataFrame,
    label_col: str,
    value_col: str = "Total_h",
    *,
    max_categorias: int = 30,
) -> go.Figure:
    """Barras horizontais com total de horas — mesmo padrão Repasses / `hbar_qtd` (tema Streamlit)."""
    _tit = dict(
        text=title,
        font=dict(size=_JUR_HBAR_TITLE_SZ),
        x=0.5,
        xanchor="center",
        yanchor="top",
    )
    _marg = dict(l=_JUR_HBAR_ML, r=_JUR_HBAR_MR, t=62, b=12)

    if df.empty or label_col not in df.columns or value_col not in df.columns:
        fig = go.Figure()
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            title=_tit,
            height=240,
            margin=_marg,
        )
        return fig

    d = df.sort_values(value_col, ascending=True).tail(max_categorias).copy()
    raw_lbl = d[label_col].astype(str).str.strip()
    labels = raw_lbl.apply(lambda s: (s[:46] + "…") if len(s) > 47 else s)
    val = d[value_col].astype(float)
    x_max = float(val.max()) if len(val) else 1.0
    y_list = labels.tolist()
    v_list = [float(x) for x in val.tolist()]
    annos = _jur_hbar_value_annotations(y_list, v_list, lambda v: f"{float(v):.1f}")
    _marg_dyn = dict(l=_JUR_HBAR_ML, r=88, t=62, b=12)
    x_hi_pad = 1.42

    fig = go.Figure(
        go.Bar(
            x=val,
            y=labels,
            orientation="h",
            marker=dict(color=_JUR_HBAR_MARKER, line=dict(width=0)),
            cliponaxis=False,
            hovertemplate="%{y}<br>Total: %{x:.2f} h<extra></extra>",
        )
    )
    h = min(820, max(280, 34 * len(labels) + 140))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        title=_tit,
        margin=_marg_dyn,
        height=h,
        annotations=annos,
        xaxis=dict(
            visible=False,
            range=[0, max(x_max * x_hi_pad, 0.01)] if x_max > 0 else None,
            fixedrange=True,
        ),
        yaxis=dict(
            title="",
            automargin=False,
            tickfont=dict(size=_JUR_HBAR_Y_TICK_SZ),
        ),
        showlegend=False,
        bargap=0.18,
    )
    return fig


def _jur_motivo_series(df: pd.DataFrame, motivo_col: str) -> pd.Series:
    """Mesma lógica visual da aba Finalizados para o campo Motivo."""
    if motivo_col and motivo_col in df.columns:
        s = df[motivo_col].astype(str).str.strip()
    else:
        s = pd.Series("Não informado", index=df.index)
    s = s.replace({"": "Não informado", "nan": "Não informado", "None": "Não informado"})
    return s


def _jur_statuses_from_linha_tempo(value: Any) -> set[str]:
    """
    Extrai nomes de status já visitados a partir de «Linha do tempo (status)».
    Formato esperado: trechos «de -> para @ data» separados por «|» (changelog).
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return set()
    raw = str(value).strip()
    if not raw or raw.lower() in {"none", "nan", "nat", "<na>"}:
        return set()
    out: set[str] = set()
    for segment in re.split(r"\s*\|\s*", raw):
        segment = segment.strip()
        if "->" not in segment:
            continue
        left, right = segment.split("->", 1)
        de = left.strip()
        para = right.split("@", 1)[0].strip()
        if de:
            out.add(_normalize(de))
        if para:
            out.add(_normalize(para))
    return out


def _jur_passou_em_elaboracao_linha(linha_timeline: Any) -> bool:
    """1 se a issue passou por «Em elaboração» ao menos uma vez (indiferente de quantas)."""
    st_set = _jur_statuses_from_linha_tempo(linha_timeline)
    for x in st_set:
        if "em elaboracao" in x:
            return True
    return False


def _jur_passou_conferencia_linha(linha_timeline: Any) -> bool:
    """1 se a issue passou por «Conferência» ao menos uma vez (indiferente de quantas)."""
    st_set = _jur_statuses_from_linha_tempo(linha_timeline)
    for x in st_set:
        if "conferencia" in x:
            return True
    return False


def _jur_cascade_opcoes(
    fin_base: pd.DataFrame, km: str, ka: str, ke: str
) -> tuple[List[str], List[str], List[str]]:
    """Sanitiza seleções na session e devolve listas ordenadas para multiselect (Motivo / Área / Empreendimento)."""
    sm = list(st.session_state.get(km, []) or [])
    sa = list(st.session_state.get(ka, []) or [])
    se = list(st.session_state.get(ke, []) or [])
    if not isinstance(sm, list):
        sm = []
    if not isinstance(sa, list):
        sa = []
    if not isinstance(se, list):
        se = []

    for _ in range(12):
        dm = fin_base
        if sa:
            dm = dm.loc[dm["Área"].isin(sa)]
        if se:
            dm = dm.loc[dm["_emp_filt"].isin(se)]
        mot_opts = sorted({str(x) for x in dm["Motivo"].tolist() if str(x).strip()})

        da = fin_base
        if sm:
            da = da.loc[da["Motivo"].isin(sm)]
        if se:
            da = da.loc[da["_emp_filt"].isin(se)]
        area_opts = sorted({str(x) for x in da["Área"].tolist() if str(x).strip()})

        de = fin_base
        if sm:
            de = de.loc[de["Motivo"].isin(sm)]
        if sa:
            de = de.loc[de["Área"].isin(sa)]
        emp_opts = sorted({str(x) for x in de["_emp_filt"].tolist() if str(x).strip()})

        sm2 = [x for x in sm if x in mot_opts]
        sa2 = [x for x in sa if x in area_opts]
        se2 = [x for x in se if x in emp_opts]
        if sm2 == sm and sa2 == sa and se2 == se:
            break
        sm, sa, se = sm2, sa2, se2

    st.session_state[km] = sm
    st.session_state[ka] = sa
    st.session_state[ke] = se

    dm = fin_base
    if sa:
        dm = dm.loc[dm["Área"].isin(sa)]
    if se:
        dm = dm.loc[dm["_emp_filt"].isin(se)]
    mot_opts_f = sorted({str(x) for x in dm["Motivo"].tolist() if str(x).strip()})

    da = fin_base
    if sm:
        da = da.loc[da["Motivo"].isin(sm)]
    if se:
        da = da.loc[da["_emp_filt"].isin(se)]
    area_opts_f = sorted({str(x) for x in da["Área"].tolist() if str(x).strip()})

    de = fin_base
    if sm:
        de = de.loc[de["Motivo"].isin(sm)]
    if sa:
        de = de.loc[de["Área"].isin(sa)]
    emp_opts_f = sorted({str(x) for x in de["_emp_filt"].tolist() if str(x).strip()})

    return mot_opts_f, area_opts_f, emp_opts_f


def render_indicadores_juridico_dashboard() -> None:
    st.subheader("📈 Indicadores Jurídico")

    with st.spinner("Carregando dados do Jira Jurídico..."):
        df_raw = load_jira_juridico_consolidado()

    if df_raw.empty:
        st.warning("⚠️ Nenhum dado encontrado na view Jira_projeto_juridico_consolidado.")
        return

    df_raw = _filter_by_email_access(df_raw)
    if df_raw.empty:
        st.info("Você não possui itens vinculados ao seu e-mail no Jurídico.")
        return

    # Colunas (detecta variações)
    status_col = _find_col(df_raw, ["status", "jrd - status", "jrd status"])
    tipo_contrato_col = _find_col(df_raw, ["tipo de contrato", "jrd - tipo de contrato", "contrato"])
    obra_col = _find_col(df_raw, ["obra", "empreendimento", "area", "área"])
    motivo_col = _find_col(
        df_raw,
        [
            "motivo consolidado",
            "jrd motivo consolidado",
            "jrd - motivo consolidado",
            "jrd motivo da requisicao consolidada",
            "jrd motivo da requisição consolidada",
            "motivo da requisição consolidada",
            "motivo",
        ],
    )
    area_col_ind = _find_col(df_raw, ["jrd - área", "jrd area", "área", "area"])
    emp_col_ind = _find_col(df_raw, ["jrd - empreendimento", "jrd empreendimento", "empreendimento"])
    data_fechamento_col = _find_col(
        df_raw,
        [
            "data de fechamento",
            "jrd - data de fechamento",
            "data fechamento",
            "fechamento",
        ],
    )
    responsavel_col = _find_col(df_raw, ["responsavel", "responsável", "assignee"])
    created_col = _find_col(df_raw, ["start_date", "criado em", "created", "data de criacao", "data criação"])
    duedate_col = _find_col(df_raw, ["data limite", "duedate", "deadline"])
    chave_col = _find_col(df_raw, ["chave", "issue key", "key"])
    resumo_col_ind = _find_col(
        df_raw,
        ["jrd - resumo", "jrd resumo", "resumo", "summary", "título", "titulo"],
    )
    ultimo_comentario_col = _find_col(
        df_raw,
        [
            "ultimo_comentario",
            "último comentário",
            "ultimo comentario",
            "último_comentário",
            "jrd - ultimo comentario",
            "jrd - último comentário",
            "ultimo comentário",
            "last comment",
        ],
    )
    tempo_elab_min_col = _find_col(
        df_raw,
        [
            "tempo em elaboração (min)",
            "tempo em elaboracao (min)",
            "tempo elaboração (min)",
            "tempo elaboracao (min)",
        ],
    )
    linha_tempo_col = _find_col(
        df_raw,
        [
            "linha do tempo (status)",
            "linha do tempo status",
            "linha tempo status",
        ],
    )

    # Período por Data de fechamento: estado na sessão + recorte em df_f (afeta todas as abas)
    df_f = df_raw.copy()
    _jur_date_ok = False
    _jur_d_lo: Optional[date_type] = None
    _jur_d_hi: Optional[date_type] = None
    _k_fech_i, _k_fech_f = "jur_ind_fechamento_inicio", "jur_ind_fechamento_fim"

    if data_fechamento_col:
        _dt_jur = pd.to_datetime(df_raw[data_fechamento_col], errors="coerce")
        _ok_jur = _dt_jur.dropna()
        if not _ok_jur.empty:
            _jur_date_ok = True
            _jur_d_lo = _ok_jur.min().normalize().date()
            _jur_d_hi = _ok_jur.max().normalize().date()
            for _k, _d in ((_k_fech_i, _jur_d_lo), (_k_fech_f, _jur_d_hi)):
                if _k not in st.session_state:
                    st.session_state[_k] = _d
                else:
                    v = st.session_state[_k]
                    if not isinstance(v, date_type) or v < _jur_d_lo or v > _jur_d_hi:
                        st.session_state[_k] = _d
            # Mesmo período nas abas Tempo de elaboração e Elaborada vs Conferência
            for _kt, _km in ((_KT_ELAB_FECH_I, _k_fech_i), (_KT_ELAB_FECH_F, _k_fech_f)):
                if _kt not in st.session_state:
                    st.session_state[_kt] = st.session_state[_km]
            for _kt, _km in ((_K_EC_FECH_I, _k_fech_i), (_K_EC_FECH_F, _k_fech_f)):
                if _kt not in st.session_state:
                    st.session_state[_kt] = st.session_state[_km]
            for _kt, _km in ((_K_REJ_FECH_I, _k_fech_i), (_K_REJ_FECH_F, _k_fech_f)):
                if _kt not in st.session_state:
                    st.session_state[_kt] = st.session_state[_km]
            ts_a = pd.Timestamp(st.session_state[_k_fech_i]).normalize()
            ts_b = pd.Timestamp(st.session_state[_k_fech_f]).normalize()
            if ts_a > ts_b:
                ts_a, ts_b = ts_b, ts_a
            _mask_dt = _dt_jur.notna() & (_dt_jur.dt.normalize() >= ts_a) & (_dt_jur.dt.normalize() <= ts_b)
            df_f = df_raw.loc[_mask_dt].copy()

    with st.sidebar:
        st.markdown("### 🔎 Filtros (Jurídico)")
        st.caption(
            "O intervalo de **Data de fechamento** pode ser ajustado na aba **Finalizados**, **Tempo de elaboração**, "
            "**Elaborada vs Conferência**, **Rejeitadas** ou acima dos gráficos (Finalizados); "
            "motivo/área/empreendimento da aba Finalizados."
        )

    if df_f.empty:
        st.info("Nenhum item após filtros.")
        return

    st.divider()

    # Cria as abas para os indicadores
    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "✅ Finalizados",
            "⏳ Tempo de elaboração",
            "👤 Elaborada vs Conferência",
            "❌ Rejeitadas",
        ]
    )

    # 1) QTD finalizados por mês: linhas com "Data de fechamento" preenchida (proxy de finalizado)
    with tab1:
        st.subheader("✅ Finalizados (Visão Geral)")
        if not data_fechamento_col:
            st.info("Coluna 'Data de fechamento' não encontrada na view.")
        else:
            if _jur_date_ok and _jur_d_lo is not None and _jur_d_hi is not None:
                st.markdown(
                    """
                    <style>
                    /* Campos de data do período: mais compactos */
                    div[data-testid="stVerticalBlockBorderWrapper"]:has(div[data-baseweb="datepicker"]) {
                        max-width: 200px;
                    }
                    div[data-testid="column"]:has(div[data-baseweb="datepicker"]) {
                        flex: 0 0 auto !important;
                        width: min(200px, 100%) !important;
                        min-width: unset !important;
                    }
                    </style>
                    """,
                    unsafe_allow_html=True,
                )
                cdi, cdf, _gap = st.columns([1, 1, 4])
                with cdi:
                    st.caption("Data inicial")
                    st.date_input(
                        "Data de fechamento — início",
                        min_value=_jur_d_lo,
                        max_value=_jur_d_hi,
                        key=_k_fech_i,
                        help="Primeiro dia do intervalo (inclusivo).",
                        label_visibility="collapsed",
                        on_change=_jur_fin_main_fech_change_sync_tempo,
                    )
                with cdf:
                    st.caption("Data final")
                    st.date_input(
                        "Data de fechamento — fim",
                        min_value=_jur_d_lo,
                        max_value=_jur_d_hi,
                        key=_k_fech_f,
                        help="Último dia do intervalo (inclusivo).",
                        label_visibility="collapsed",
                        on_change=_jur_fin_main_fech_change_sync_tempo,
                    )
            elif not _jur_date_ok:
                st.info("Não há datas de fechamento preenchidas para filtrar o período.")

            fin = df_f.copy()
            fin["_dt_fech"] = pd.to_datetime(fin[data_fechamento_col], errors="coerce")
            fin = fin.loc[fin["_dt_fech"].notna()].copy()
            if fin.empty:
                st.info("Nenhuma linha com 'Data de fechamento' informada.")
            else:
                fin["Tipo de contrato"] = (
                    fin[tipo_contrato_col].astype(str).str.strip() if tipo_contrato_col else "Não informado"
                )
                fin["Motivo"] = fin[motivo_col].astype(str).str.strip() if motivo_col else "Não informado"
                fin["Área"] = fin[area_col_ind].astype(str).str.strip() if area_col_ind else "Não informado"
                fin["Empreendimento"] = fin[emp_col_ind].astype(str).str.strip() if emp_col_ind else "Não informado"
                for c in ["Tipo de contrato", "Motivo", "Área", "Empreendimento"]:
                    fin[c] = fin[c].replace({"": "Não informado", "nan": "Não informado", "None": "Não informado"})

                # Base com chave de empreendimento padronizada (alinhada à tabela «Por Empreendimento»)
                fin_base = fin.copy()
                fin_base["_emp_filt"] = fin_base["Empreendimento"].map(_empreendimento_label_tabela)

                # Opções em cascata: cada filtro restringe as listas dos outros (seleções inválidas são descartadas)
                _k_m, _k_a, _k_e = "jur_fin_det_motivo", "jur_fin_det_area", "jur_fin_det_emp"
                mot_opts, area_opts, emp_opts = _jur_cascade_opcoes(fin_base, _k_m, _k_a, _k_e)

                f1, f2, f3 = st.columns(3)
                with f1:
                    sel_mot_det = st.multiselect(
                        "📍 Por Motivo",
                        options=mot_opts,
                        key=_k_m,
                        placeholder="Todos",
                        on_change=_jur_fin_mark_pull_main_to_graf,
                    )
                with f2:
                    sel_area_det = st.multiselect(
                        "🏢 Por Área",
                        options=area_opts,
                        key=_k_a,
                        placeholder="Todos",
                        on_change=_jur_fin_mark_pull_main_to_graf,
                    )
                with f3:
                    sel_emp_det = st.multiselect(
                        "🏗️ Por Empreendimento",
                        options=emp_opts,
                        key=_k_e,
                        placeholder="Todos",
                        on_change=_jur_fin_mark_pull_main_to_graf,
                    )

                fin_f = fin_base
                if sel_mot_det:
                    fin_f = fin_f.loc[fin_f["Motivo"].isin(sel_mot_det)]
                if sel_area_det:
                    fin_f = fin_f.loc[fin_f["Área"].isin(sel_area_det)]
                if sel_emp_det:
                    fin_f = fin_f.loc[fin_f["_emp_filt"].isin(sel_emp_det)]

                df_motivo = pd.DataFrame()
                df_area = pd.DataFrame()
                df_emp = pd.DataFrame()
                if not fin_f.empty:
                    df_motivo = (
                        fin_f.groupby("Motivo")
                        .size()
                        .reset_index(name="Qtd")
                        .sort_values("Qtd", ascending=False)
                    )
                    df_area = (
                        fin_f.groupby("Área")
                        .size()
                        .reset_index(name="Qtd")
                        .sort_values("Qtd", ascending=False)
                    )
                    df_emp = (
                        fin_f.groupby("_emp_filt")
                        .size()
                        .reset_index(name="Qtd")
                        .rename(columns={"_emp_filt": "Empreendimento"})
                        .sort_values("Qtd", ascending=False)
                    )

                col1, col2, col3 = st.columns(3)

                with col1:
                    if fin_f.empty:
                        st.info("Sem registros para os filtros atuais.")
                    else:
                        st.dataframe(
                            _jur_add_total_row(df_motivo),
                            hide_index=True,
                            use_container_width=True,
                            key="jur_ind_fin_motivo",
                        )

                with col2:
                    if fin_f.empty:
                        st.info("Sem registros para os filtros atuais.")
                    else:
                        st.dataframe(
                            _jur_add_total_row(df_area),
                            hide_index=True,
                            use_container_width=True,
                            key="jur_ind_fin_area",
                        )

                with col3:
                    if fin_f.empty:
                        st.info("Sem registros para os filtros atuais.")
                    else:
                        st.dataframe(
                            _jur_add_total_row(df_emp),
                            hide_index=True,
                            use_container_width=True,
                            key="jur_ind_fin_emp",
                        )

                # Mesmos filtros do topo, acima dos gráficos (chaves _graf + sincronização com o topo)
                _k_f_i_g = f"{_k_fech_i}_graf"
                _k_f_f_g = f"{_k_fech_f}_graf"
                _k_m_g, _k_a_g, _k_e_g = f"{_k_m}_graf", f"{_k_a}_graf", f"{_k_e}_graf"
                _pull = bool(st.session_state.pop("jur_fin_pull_main_to_graf", False))
                if _pull or _k_m_g not in st.session_state:
                    if _jur_date_ok:
                        st.session_state[_k_f_i_g] = st.session_state[_k_fech_i]
                        st.session_state[_k_f_f_g] = st.session_state[_k_fech_f]
                    st.session_state[_k_m_g] = list(st.session_state.get(_k_m, []) or [])
                    st.session_state[_k_a_g] = list(st.session_state.get(_k_a, []) or [])
                    st.session_state[_k_e_g] = list(st.session_state.get(_k_e, []) or [])

                if _jur_date_ok and _jur_d_lo is not None and _jur_d_hi is not None:
                    st.markdown(
                        """
                        <style>
                        div[data-testid="column"]:has(div[data-baseweb="datepicker"]) {
                            flex: 0 0 auto !important;
                            width: min(200px, 100%) !important;
                            min-width: unset !important;
                        }
                        </style>
                        """,
                        unsafe_allow_html=True,
                    )
                    gdi, gdf, _ggap = st.columns([1, 1, 4])
                    with gdi:
                        st.caption("Data inicial")
                        st.date_input(
                            "Data de fechamento — início (gráficos)",
                            min_value=_jur_d_lo,
                            max_value=_jur_d_hi,
                            key=_k_f_i_g,
                            help="Igual ao filtro do topo; afeta tabelas e gráficos.",
                            label_visibility="collapsed",
                        )
                    with gdf:
                        st.caption("Data final")
                        st.date_input(
                            "Data de fechamento — fim (gráficos)",
                            min_value=_jur_d_lo,
                            max_value=_jur_d_hi,
                            key=_k_f_f_g,
                            help="Igual ao filtro do topo; afeta tabelas e gráficos.",
                            label_visibility="collapsed",
                        )

                mot_g, area_g, emp_g = _jur_cascade_opcoes(fin_base, _k_m_g, _k_a_g, _k_e_g)
                gf1, gf2, gf3 = st.columns(3)
                with gf1:
                    st.multiselect(
                        "📍 Por Motivo",
                        options=mot_g,
                        key=_k_m_g,
                        placeholder="Todos",
                    )
                with gf2:
                    st.multiselect(
                        "🏢 Por Área",
                        options=area_g,
                        key=_k_a_g,
                        placeholder="Todos",
                    )
                with gf3:
                    st.multiselect(
                        "🏗️ Por Empreendimento",
                        options=emp_g,
                        key=_k_e_g,
                        placeholder="Todos",
                    )

                _graf_diff = False
                if _jur_date_ok:
                    if st.session_state.get(_k_f_i_g) != st.session_state.get(_k_fech_i):
                        _graf_diff = True
                    if st.session_state.get(_k_f_f_g) != st.session_state.get(_k_fech_f):
                        _graf_diff = True
                if list(st.session_state.get(_k_m_g, []) or []) != list(
                    st.session_state.get(_k_m, []) or []
                ) or list(st.session_state.get(_k_a_g, []) or []) != list(
                    st.session_state.get(_k_a, []) or []
                ) or list(st.session_state.get(_k_e_g, []) or []) != list(
                    st.session_state.get(_k_e, []) or []
                ):
                    _graf_diff = True
                if _graf_diff:
                    if _jur_date_ok:
                        st.session_state[_k_fech_i] = st.session_state[_k_f_i_g]
                        st.session_state[_k_fech_f] = st.session_state[_k_f_f_g]
                    st.session_state[_k_m] = list(st.session_state.get(_k_m_g, []) or [])
                    st.session_state[_k_a] = list(st.session_state.get(_k_a_g, []) or [])
                    st.session_state[_k_e] = list(st.session_state.get(_k_e_g, []) or [])
                    # No próximo run a cascata do topo pode podar seleções; puxar de volta evita divergência _graf vs main.
                    st.session_state["jur_fin_pull_main_to_graf"] = True
                    st.rerun()

                if fin_f.empty:
                    st.info("Sem dados para os gráficos com os filtros atuais.")
                else:
                    st.markdown(
                        """
                        <style>
                        div[data-testid="column"]:has(div[data-testid="stPlotlyChart"]) {
                            padding-left: 0.15rem !important;
                            padding-right: 0.15rem !important;
                        }
                        </style>
                        """,
                        unsafe_allow_html=True,
                    )
                    try:
                        gc1, gc2, gc3 = st.columns(3, gap="small")
                    except TypeError:
                        gc1, gc2, gc3 = st.columns(3)
                    with gc1:
                        fig_m = _plot_juridico_hbar_qtd("📍 Por Motivo", df_motivo, "Motivo")
                        st.plotly_chart(fig_m, use_container_width=True, key="jur_hbar_motivo")
                    with gc2:
                        fig_a = _plot_juridico_hbar_qtd("🏢 Por Área", df_area, "Área")
                        st.plotly_chart(fig_a, use_container_width=True, key="jur_hbar_area")
                    with gc3:
                        fig_e = _plot_juridico_hbar_qtd("🏗️ Por Empreendimento", df_emp, "Empreendimento")
                        st.plotly_chart(fig_e, use_container_width=True, key="jur_hbar_emp")

    # 2) Tempo em «Em elaboração» (min na view → h), por motivo + detalhe por issue
    with tab2:
        st.subheader("⏳ Tempo de elaboração")
        if _jur_date_ok and _jur_d_lo is not None and _jur_d_hi is not None and data_fechamento_col:
            _te_mot_opts: List[str] = []
            if motivo_col and motivo_col in df_f.columns:
                _tmp_m = df_f.copy()
                _tmp_m["Motivo"] = _jur_motivo_series(_tmp_m, motivo_col)
                if tempo_elab_min_col and tempo_elab_min_col in df_f.columns:
                    _nm = pd.to_numeric(_tmp_m[tempo_elab_min_col], errors="coerce")
                    _tmp_m = _tmp_m.loc[_nm.notna()]
                _te_mot_opts = sorted(
                    {str(x) for x in _tmp_m["Motivo"].tolist() if str(x).strip()}
                )

            st.markdown(
                """
                <style>
                div[data-testid="stVerticalBlockBorderWrapper"]:has(div[data-baseweb="datepicker"]) {
                    max-width: 200px;
                }
                div[data-testid="column"]:has(div[data-baseweb="datepicker"]) {
                    flex: 0 0 auto !important;
                    width: min(200px, 100%) !important;
                    min-width: unset !important;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )
            te_mot, te_di, te_df, _te_gap = st.columns([2.4, 1, 1, 2.6])
            with te_mot:
                st.markdown(
                    _jur_por_motivo_label_with_tooltip(tooltip=_JUR_TT_TEMPO_ELAB_ABA),
                    unsafe_allow_html=True,
                )
                if not motivo_col or motivo_col not in df_f.columns:
                    st.caption("_Coluna Motivo não disponível._")
                elif not _te_mot_opts:
                    st.caption("_Nenhum motivo com tempo em elaboração neste período._")
                else:
                    st.multiselect(
                        "Filtro motivo — tempo elaboração",
                        options=_te_mot_opts,
                        placeholder="Todos",
                        key=_KT_ELAB_MOT,
                        help="Restringe tabela, gráfico e detalhe nesta aba apenas.",
                        label_visibility="collapsed",
                    )
            with te_di:
                st.markdown(_jur_filter_top_label("Data inicial"), unsafe_allow_html=True)
                st.date_input(
                    "Data de fechamento — início (tempo elaboração)",
                    min_value=_jur_d_lo,
                    max_value=_jur_d_hi,
                    key=_KT_ELAB_FECH_I,
                    help="Recorte por data de fechamento (igual à aba Finalizados). Atualiza todas as abas.",
                    label_visibility="collapsed",
                    on_change=_jur_tempo_elab_fech_change_apply_main,
                )
            with te_df:
                st.markdown(_jur_filter_top_label("Data final"), unsafe_allow_html=True)
                st.date_input(
                    "Data de fechamento — fim (tempo elaboração)",
                    min_value=_jur_d_lo,
                    max_value=_jur_d_hi,
                    key=_KT_ELAB_FECH_F,
                    help="Recorte por data de fechamento (igual à aba Finalizados). Atualiza todas as abas.",
                    label_visibility="collapsed",
                    on_change=_jur_tempo_elab_fech_change_apply_main,
                )
        elif not data_fechamento_col:
            pass
        elif not _jur_date_ok:
            st.info("Não há datas de fechamento preenchidas para filtrar o período.")
        if not tempo_elab_min_col or tempo_elab_min_col not in df_f.columns:
            st.info(
                "Coluna **Tempo em elaboração (min)** não encontrada na view. "
                "Confira se a view `Jira_projeto_juridico_consolidado` expõe essa métrica."
            )
        else:
            te = df_f.copy()
            te["_min_elab"] = pd.to_numeric(te[tempo_elab_min_col], errors="coerce")
            te = te.loc[te["_min_elab"].notna()].copy()
            te["Tempo (h)"] = te["_min_elab"] / 60.0
            te["Motivo"] = _jur_motivo_series(te, motivo_col)

            _sel_tm = list(st.session_state.get(_KT_ELAB_MOT, []) or [])
            if _sel_tm:
                _mot_valid = set(te["Motivo"].astype(str).unique())
                _sel_tm = [x for x in _sel_tm if str(x) in _mot_valid]
                if _sel_tm:
                    te = te.loc[te["Motivo"].isin(_sel_tm)].copy()

            if te.empty:
                st.info("Nenhuma linha com tempo em elaboração (min) preenchido no período filtrado.")
            else:
                tbl_by_motivo = (
                    te.groupby("Motivo", dropna=False)
                    .agg(Qtd=("Tempo (h)", "count"), Total_h=("Tempo (h)", "sum"), Media_h=("Tempo (h)", "mean"))
                    .reset_index()
                    .sort_values("Total_h", ascending=False)
                )
                tbl_display = tbl_by_motivo.assign(
                    **{
                        "Total (h)": tbl_by_motivo["Total_h"].round(2),
                        "Média (h)": tbl_by_motivo["Media_h"].round(2),
                    }
                )[["Motivo", "Qtd", "Total (h)", "Média (h)"]]

                ct, cg = st.columns(2)
                with ct:
                    st.markdown("**Por motivo**")
                    st.dataframe(
                        _jur_add_total_row(tbl_display),
                        hide_index=True,
                        use_container_width=True,
                        height=min(420, 40 + 36 * len(tbl_display)),
                        key="jur_ind_tempo_elab_motivo_tbl",
                    )
                with cg:
                    fig_h = _plot_juridico_hbar_horas(
                        "Total de horas por motivo",
                        tbl_by_motivo,
                        "Motivo",
                        "Total_h",
                    )
                    st.plotly_chart(fig_h, use_container_width=True, key="jur_hbar_tempo_motivo")

                st.markdown("**Detalhamento por issue**")
                chave_s = (
                    te[chave_col].astype(str).str.strip()
                    if chave_col and chave_col in te.columns
                    else pd.Series("", index=te.index)
                )
                resp_s = (
                    te[responsavel_col].astype(str).str.strip()
                    if responsavel_col and responsavel_col in te.columns
                    else pd.Series("", index=te.index)
                )
                resumo_s = (
                    te[resumo_col_ind].astype(str).str.strip()
                    if resumo_col_ind and resumo_col_ind in te.columns
                    else pd.Series("", index=te.index)
                )
                detail = pd.DataFrame(
                    {
                        "Chave": chave_s,
                        "Motivo": te["Motivo"],
                        "Responsável": resp_s,
                        "Resumo": resumo_s,
                        "Tempo (h)": te["Tempo (h)"].round(2),
                    }
                ).sort_values("Tempo (h)", ascending=False)
                st.dataframe(
                    _jur_add_total_row(detail),
                    hide_index=True,
                    use_container_width=True,
                    height=min(520, 40 + 36 * min(len(detail), 14)),
                    key="jur_ind_tempo_elab_detail",
                )

    # 3) Elaborada vs Conferência: linha do tempo; resumos por Motivo (esq.) e Responsável (dir.)
    with tab3:
        st.subheader("👤 Elaborada vs Conferência")
        if not responsavel_col or responsavel_col not in df_f.columns:
            st.info("Coluna **Responsável** não encontrada na view.")
        elif not linha_tempo_col or linha_tempo_col not in df_f.columns:
            st.info(
                "Coluna **Linha do tempo (status)** não localizada. "
                "Ela vem do changelog no pipeline jurídico consolidado."
            )
        else:
            _ec_mot_opts: List[str] = []
            if motivo_col and motivo_col in df_f.columns:
                _ec_tmp = df_f.copy()
                _ec_tmp["Motivo"] = _jur_motivo_series(_ec_tmp, motivo_col)
                _lt_ec = _ec_tmp[linha_tempo_col].astype(str).str.strip()
                _ec_tmp = _ec_tmp.loc[
                    _lt_ec.ne("")
                    & ~_lt_ec.str.lower().isin({"none", "nan", "nat", "<na>"})
                ]
                _ec_mot_opts = sorted(
                    {str(x) for x in _ec_tmp["Motivo"].tolist() if str(x).strip()}
                )

            if _jur_date_ok and _jur_d_lo is not None and _jur_d_hi is not None and data_fechamento_col:
                st.markdown(
                    """
                    <style>
                    div[data-testid="stVerticalBlockBorderWrapper"]:has(div[data-baseweb="datepicker"]) {
                        max-width: 200px;
                    }
                    div[data-testid="column"]:has(div[data-baseweb="datepicker"]) {
                        flex: 0 0 auto !important;
                        width: min(200px, 100%) !important;
                        min-width: unset !important;
                    }
                    </style>
                    """,
                    unsafe_allow_html=True,
                )
                ec_mot, ec_di, ec_df, _ec_gap = st.columns([2.4, 1, 1, 2.6])
                with ec_mot:
                    st.markdown(
                        _jur_por_motivo_label_with_tooltip(tooltip=_JUR_TT_ELAB_CONF_ABA),
                        unsafe_allow_html=True,
                    )
                    if not motivo_col or motivo_col not in df_f.columns:
                        st.caption("_Coluna Motivo não disponível._")
                    elif not _ec_mot_opts:
                        st.caption("_Nenhum motivo com linha do tempo neste período._")
                    else:
                        st.multiselect(
                            "Filtro motivo — elaborada vs conferência",
                            options=_ec_mot_opts,
                            placeholder="Todos",
                            key=_K_EC_MOT,
                            help="Restringe só esta aba (tabelas e detalhe).",
                            label_visibility="collapsed",
                        )
                with ec_di:
                    st.markdown(_jur_filter_top_label("Data inicial"), unsafe_allow_html=True)
                    st.date_input(
                        "Data de fechamento — início (elab. vs conf.)",
                        min_value=_jur_d_lo,
                        max_value=_jur_d_hi,
                        key=_K_EC_FECH_I,
                        help="Recorte global por data de fechamento (igual às outras abas).",
                        label_visibility="collapsed",
                        on_change=_jur_elab_conf_fech_change_apply_main,
                    )
                with ec_df:
                    st.markdown(_jur_filter_top_label("Data final"), unsafe_allow_html=True)
                    st.date_input(
                        "Data de fechamento — fim (elab. vs conf.)",
                        min_value=_jur_d_lo,
                        max_value=_jur_d_hi,
                        key=_K_EC_FECH_F,
                        help="Recorte global por data de fechamento (igual às outras abas).",
                        label_visibility="collapsed",
                        on_change=_jur_elab_conf_fech_change_apply_main,
                    )
            elif data_fechamento_col and not _jur_date_ok:
                st.info("Não há datas de fechamento preenchidas para filtrar o período.")

            w = df_f.copy()
            w["_resp"] = w[responsavel_col].astype(str).str.strip()
            w["_resp"] = w["_resp"].replace({"": "Não informado", "nan": "Não informado", "None": "Não informado"})
            w["_elab"] = w[linha_tempo_col].apply(_jur_passou_em_elaboracao_linha)
            w["_conf"] = w[linha_tempo_col].apply(_jur_passou_conferencia_linha)
            w["Motivo"] = _jur_motivo_series(w, motivo_col)

            _sel_ec_m = list(st.session_state.get(_K_EC_MOT, []) or [])
            if _sel_ec_m:
                _mot_v = set(w["Motivo"].astype(str).unique())
                _sel_ec_m = [str(x) for x in _sel_ec_m if str(x) in _mot_v]
                if _sel_ec_m:
                    w = w.loc[w["Motivo"].isin(_sel_ec_m)].copy()

            tbl_ec = (
                w.groupby("_resp", dropna=False)
                .agg(_elab_sum=("_elab", "sum"), _conf_sum=("_conf", "sum"))
                .reset_index()
                .rename(
                    columns={
                        "_resp": "Responsável",
                        "_elab_sum": "Qtd elaborada",
                        "_conf_sum": "Qtd conferida",
                    }
                )
                .sort_values(["Qtd elaborada", "Qtd conferida"], ascending=False)
            )
            tbl_mot = (
                w.groupby("Motivo", dropna=False)
                .agg(_elab_sum=("_elab", "sum"), _conf_sum=("_conf", "sum"))
                .reset_index()
                .rename(
                    columns={
                        "_elab_sum": "Qtd elaborada",
                        "_conf_sum": "Qtd conferida",
                    }
                )
                .sort_values(["Qtd elaborada", "Qtd conferida"], ascending=False)
            )
            if tbl_ec.empty or (tbl_ec["Qtd elaborada"].sum() == 0 and tbl_ec["Qtd conferida"].sum() == 0):
                st.info(
                    "Nenhuma passagem por **Em elaboração** ou **Conferência** detectada na linha do tempo, "
                    "no período filtrado."
                )
            else:
                cte, cge = st.columns(2)
                with cte:
                    st.markdown("**Resumo por motivo**")
                    st.dataframe(
                        _jur_add_total_row(tbl_mot),
                        hide_index=True,
                        use_container_width=True,
                        height=min(480, 40 + 36 * len(tbl_mot)),
                        key="jur_ind_elab_conf_mot_tbl",
                    )
                with cge:
                    st.markdown("**Resumo por responsável**")
                    st.dataframe(
                        _jur_add_total_row(tbl_ec),
                        hide_index=True,
                        use_container_width=True,
                        height=min(480, 40 + 36 * len(tbl_ec)),
                        key="jur_ind_elab_conf_tbl",
                    )

                st.markdown("**Detalhamento por issue**")
                chave_d = (
                    w[chave_col].astype(str).str.strip()
                    if chave_col and chave_col in w.columns
                    else pd.Series("", index=w.index)
                )
                resumo_d = (
                    w[resumo_col_ind].astype(str).str.strip()
                    if resumo_col_ind and resumo_col_ind in w.columns
                    else pd.Series("", index=w.index)
                )
                def _trunc_lt(val: Any) -> str:
                    s = str(val).strip() if val is not None else ""
                    if s.lower() in {"none", "nan", "nat", "<na>"}:
                        return ""
                    return (s[:220] + "…") if len(s) > 220 else s

                lt_short = w[linha_tempo_col].apply(_trunc_lt)
                detail_ec = pd.DataFrame(
                    {
                        "Chave": chave_d,
                        "Responsável": w["_resp"],
                        "Motivo": w["Motivo"],
                        "Elaboração": w["_elab"].map({True: "Sim", False: "Não"}),
                        "Conferência": w["_conf"].map({True: "Sim", False: "Não"}),
                        "Resumo": resumo_d,
                        "Linha do tempo (trecho)": lt_short,
                    }
                )
                detail_ec = detail_ec.sort_values(
                    ["Elaboração", "Conferência", "Motivo", "Chave"],
                    ascending=[False, False, True, True],
                )
                st.dataframe(
                    _jur_add_total_row(detail_ec),
                    hide_index=True,
                    use_container_width=True,
                    height=min(520, 40 + 36 * min(len(detail_ec), 14)),
                    key="jur_ind_elab_conf_detail",
                )

    # 4) Rejeitadas: filtros (motivo + período) e resumos por motivo×obra e por responsável
    with tab4:
        st.subheader("❌ Rejeitadas")
        st.caption(
            "Itens cujo **Status** indica rejeição ou reprovação, no recorte de **data de fechamento** das demais abas."
        )
        if not status_col:
            st.info("Coluna de **Status** não encontrada na view.")
        else:
            rej_base = df_f.loc[df_f[status_col].apply(_status_is_rejeitado)].copy()
            rej_base["Motivo"] = _jur_motivo_series(rej_base, motivo_col)
            _rej_mot_opts = sorted(
                {str(x) for x in rej_base["Motivo"].tolist() if str(x).strip()}
            )

            if _jur_date_ok and _jur_d_lo is not None and _jur_d_hi is not None and data_fechamento_col:
                st.markdown(
                    """
                    <style>
                    div[data-testid="stVerticalBlockBorderWrapper"]:has(div[data-baseweb="datepicker"]) {
                        max-width: 200px;
                    }
                    div[data-testid="column"]:has(div[data-baseweb="datepicker"]) {
                        flex: 0 0 auto !important;
                        width: min(200px, 100%) !important;
                        min-width: unset !important;
                    }
                    </style>
                    """,
                    unsafe_allow_html=True,
                )
                rj_mot, rj_di, rj_df, _rj_gap = st.columns([2.4, 1, 1, 2.6])
                with rj_mot:
                    st.markdown(
                        _jur_por_motivo_label_with_tooltip(tooltip=_JUR_TT_REJEITADAS_ABA),
                        unsafe_allow_html=True,
                    )
                    if not motivo_col or motivo_col not in df_f.columns:
                        st.caption("_Coluna Motivo não disponível._")
                    elif not _rej_mot_opts:
                        st.caption("_Nenhum motivo entre rejeitados neste período._")
                    else:
                        st.multiselect(
                            "Filtro motivo — rejeitadas",
                            options=_rej_mot_opts,
                            placeholder="Todos",
                            key=_K_REJ_MOT,
                            help="Restringe só esta aba (tabelas e detalhe).",
                            label_visibility="collapsed",
                        )
                with rj_di:
                    st.markdown(_jur_filter_top_label("Data inicial"), unsafe_allow_html=True)
                    st.date_input(
                        "Data de fechamento — início (rejeitadas)",
                        min_value=_jur_d_lo,
                        max_value=_jur_d_hi,
                        key=_K_REJ_FECH_I,
                        help="Recorte global por data de fechamento (igual às outras abas).",
                        label_visibility="collapsed",
                        on_change=_jur_rejeitadas_fech_change_apply_main,
                    )
                with rj_df:
                    st.markdown(_jur_filter_top_label("Data final"), unsafe_allow_html=True)
                    st.date_input(
                        "Data de fechamento — fim (rejeitadas)",
                        min_value=_jur_d_lo,
                        max_value=_jur_d_hi,
                        key=_K_REJ_FECH_F,
                        help="Recorte global por data de fechamento (igual às outras abas).",
                        label_visibility="collapsed",
                        on_change=_jur_rejeitadas_fech_change_apply_main,
                    )
            elif data_fechamento_col and not _jur_date_ok:
                st.info("Não há datas de fechamento preenchidas para filtrar o período.")

            rej = rej_base.copy()
            _sel_rj_m = list(st.session_state.get(_K_REJ_MOT, []) or [])
            if _sel_rj_m:
                _mot_v_r = set(rej["Motivo"].astype(str).unique())
                _sel_rj_m = [str(x) for x in _sel_rj_m if str(x) in _mot_v_r]
                if _sel_rj_m:
                    rej = rej.loc[rej["Motivo"].isin(_sel_rj_m)].copy()

            if rej.empty:
                st.info("Nenhum item rejeitado no período filtrado.")
            else:
                rej["_motivo"] = rej["Motivo"].astype(str).str.strip()
                rej["_obra"] = rej[obra_col].astype(str).str.strip() if obra_col else "Não informado"
                for _c in ("_motivo", "_obra"):
                    rej[_c] = rej[_c].replace(
                        {"": "Não informado", "nan": "Não informado", "None": "Não informado"}
                    )

                if responsavel_col and responsavel_col in rej.columns:
                    rej["_resp"] = rej[responsavel_col].astype(str).str.strip()
                else:
                    rej["_resp"] = "Não informado"
                rej["_resp"] = rej["_resp"].replace(
                    {"": "Não informado", "nan": "Não informado", "None": "Não informado"}
                )

                tbl_rej_tipo = (
                    rej.groupby(["_motivo", "_obra"], dropna=False)
                    .size()
                    .reset_index(name="Quantidade")
                    .rename(columns={"_motivo": "Motivo", "_obra": "Obra / empreendimento"})
                    .sort_values("Quantidade", ascending=False)
                )
                tbl_rej_resp = (
                    rej.groupby("_resp", dropna=False)
                    .size()
                    .reset_index(name="Quantidade")
                    .rename(columns={"_resp": "Responsável"})
                    .sort_values("Quantidade", ascending=False)
                )

                c_r1, c_r2 = st.columns(2)
                with c_r1:
                    st.markdown("**Por motivo e obra**")
                    st.dataframe(
                        _jur_add_total_row(tbl_rej_tipo),
                        hide_index=True,
                        use_container_width=True,
                        height=min(480, 40 + 36 * len(tbl_rej_tipo)),
                        key="jur_ind_rejeitados_tipo_obra",
                    )
                with c_r2:
                    st.markdown("**Por responsável**")
                    st.dataframe(
                        _jur_add_total_row(tbl_rej_resp),
                        hide_index=True,
                        use_container_width=True,
                        height=min(480, 40 + 36 * len(tbl_rej_resp)),
                        key="jur_ind_rejeitados_resp",
                    )

                st.markdown("**Detalhamento por issue**")
                chave_r = (
                    rej[chave_col].astype(str).str.strip()
                    if chave_col and chave_col in rej.columns
                    else pd.Series("", index=rej.index)
                )
                stat_r = (
                    rej[status_col].astype(str).str.strip()
                    if status_col and status_col in rej.columns
                    else pd.Series("", index=rej.index)
                )
                resumo_r = (
                    rej[resumo_col_ind].astype(str).str.strip()
                    if resumo_col_ind and resumo_col_ind in rej.columns
                    else pd.Series("", index=rej.index)
                )
                ult_com_r = (
                    rej[ultimo_comentario_col].astype(str).str.strip()
                    if ultimo_comentario_col and ultimo_comentario_col in rej.columns
                    else pd.Series("", index=rej.index)
                )
                detail_cols = {
                    "Chave": chave_r,
                    "Status": stat_r,
                    "Motivo": rej["Motivo"],
                    "Responsável": rej["_resp"],
                    "Obra / empreendimento": rej["_obra"],
                }
                if data_fechamento_col and data_fechamento_col in rej.columns:
                    _fech_r = pd.to_datetime(rej[data_fechamento_col], errors="coerce")
                    _fech_s = _fech_r.dt.strftime("%d/%m/%Y")
                    detail_cols["Data de fechamento"] = _fech_s.mask(_fech_r.isna(), "")
                detail_cols["Resumo"] = resumo_r
                detail_cols["Último comentário"] = ult_com_r
                detail_rej = pd.DataFrame(detail_cols)
                detail_rej = detail_rej.sort_values(
                    ["Motivo", "Obra / empreendimento", "Chave"], ascending=[True, True, True]
                )
                detail_rej_view = detail_rej.copy()
                detail_rej_view["Último comentário"] = detail_rej_view["Último comentário"].apply(
                    lambda v: textwrap.fill(str(v), width=110, break_long_words=False, break_on_hyphens=False)
                    if str(v).strip()
                    else ""
                )
                st.data_editor(
                    detail_rej_view,
                    hide_index=True,
                    use_container_width=False,
                    width=2200,
                    disabled=True,
                    row_height=78,
                    column_config={
                        "Último comentário": st.column_config.TextColumn(
                            "Último comentário", width="large"
                        )
                    },
                    height=min(520, 40 + 36 * min(len(detail_rej), 14)),
                    key="jur_ind_rejeitados_detail",
                )

