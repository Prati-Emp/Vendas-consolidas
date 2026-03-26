"""
Dashboard de Indicadores de Gestão de Pessoas —
solicitações (Jira DHO) e indicadores operacionais (views Tecsmart no MotherDuck).
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from dashboard.apps.acompanhamento_solicitacoes_dashboard import (  # noqa: E402
    COL_TEMPO_APROVACAO_VAGA,
    COL_TEMPO_FECHAMENTO_VAGA,
    COL_TEMPO_TOTAL_CONTRATACAO,
    compute_requisicao_vaga_tempos_table,
    compute_solicitacoes_matrix_by_quadro,
    load_jira_dho_acompanhamento,
)
from dashboard.utils.md_conn import get_md_connection

TEC_CONSOLIDADO = "administracao.Tecsmart_indicadores"
TEC_EQUIPE = "administracao.Tecsmart_indicadores_equipe"
TEC_FILIAL = "administracao.Tecsmart_indicadores_filial"

NUMERIC_MEASURES: Tuple[str, ...] = (
    "headcount",
    "admissoes",
    "saidas",
    "turnover_percentual",
    "turnover_ate_90_dias",
    "turnover_ate_um_ano",
    "turnover_mais_um_ano",
    "horas_atestados",
    "total_horas_previstas",
    "horas_previstas_ajustadas",
    "horas_atestados_declaracoes",
    "total_horas_faltas",
    "absenteismo_percentual",
)


def _format_int(n: float) -> str:
    if pd.isna(n):
        return "0"
    return f"{int(round(n)):,}".replace(",", ".")


def _format_pct(n: float, decimals: int = 1) -> str:
    if pd.isna(n):
        return "0%"
    return f"{float(n):.{decimals}f}%".replace(".", ",")


@st.cache_data(ttl=600)
def load_tecsmart_consolidado() -> pd.DataFrame:
    md = get_md_connection()
    try:
        return md.run_query(f"SELECT * FROM {TEC_CONSOLIDADO} ORDER BY data")
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=600)
def load_tecsmart_equipe() -> pd.DataFrame:
    md = get_md_connection()
    try:
        return md.run_query(f"SELECT * FROM {TEC_EQUIPE} ORDER BY data, equipe")
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=600)
def load_tecsmart_filial() -> pd.DataFrame:
    md = get_md_connection()
    try:
        return md.run_query(f"SELECT * FROM {TEC_FILIAL} ORDER BY data, filial")
    except Exception:
        return pd.DataFrame()


def prepare_tecsmart_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    if "data" in out.columns:
        out["data"] = pd.to_datetime(out["data"], errors="coerce")
    for col in NUMERIC_MEASURES:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0)
    out = out[out["data"].notna()] if "data" in out.columns else out
    return out


def months_range_filter(
    df: pd.DataFrame, months_back: int
) -> pd.DataFrame:
    if df.empty or "data" not in df.columns:
        return df
    end = df["data"].max()
    start = end - pd.DateOffset(months=months_back)
    return df[(df["data"] >= start) & (df["data"] <= end)].copy()


def fig_lines(
    df: pd.DataFrame,
    y_cols: Sequence[str],
    title: str,
    labels: Optional[dict] = None,
) -> go.Figure:
    if df.empty:
        fig = go.Figure()
        fig.update_layout(title=title, annotations=[{"text": "Sem dados", "xref": "paper", "yref": "paper"}])
        return fig
    dfm = df[["data"] + list(y_cols)].melt(id_vars=["data"], var_name="indicador", value_name="valor")
    mapping = labels or {}
    dfm["indicador"] = dfm["indicador"].map(lambda c: mapping.get(c, c))
    fig = px.line(
        dfm,
        x="data",
        y="valor",
        color="indicador",
        markers=True,
        title=title,
    )
    fig.update_layout(legend_title_text="", xaxis_title="Período", yaxis_title="")
    fig.update_xaxes(tickformat="%Y-%m")
    return fig


def render_kpi_row_consolidado(row: pd.Series) -> None:
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.metric("Headcount", _format_int(row.get("headcount", 0)))
    with c2:
        st.metric("Admissões", _format_int(row.get("admissoes", 0)))
    with c3:
        st.metric("Saídas", _format_int(row.get("saidas", 0)))
    with c4:
        st.metric("Turnover", _format_pct(row.get("turnover_percentual", 0)))
    with c5:
        st.metric("Absenteísmo", _format_pct(row.get("absenteismo_percentual", 0)))
    with c6:
        h = row.get("horas_atestados", 0)
        st.metric("Horas atestados / decl.", f"{float(h):,.1f}".replace(",", "X").replace(".", ",").replace("X", "."))


def tab_consolidado(df_raw: pd.DataFrame) -> None:
    df = prepare_tecsmart_df(df_raw)
    if df.empty:
        st.warning(
            "Não foi possível carregar a view consolidada. "
            f"Verifique se `{TEC_CONSOLIDADO}` existe e se há permissão de leitura."
        )
        return

    st.caption(f"Referência: {TEC_CONSOLIDADO}")

    months_back = st.slider(
        "Meses na série temporal",
        min_value=3,
        max_value=48,
        value=18,
        step=1,
        key="ind_rh_months_cons",
    )
    df_f = months_range_filter(df, months_back)
    if df_f.empty:
        st.warning("Sem períodos no intervalo selecionado.")
        return

    months_sorted = sorted(df_f["data"].dt.to_period("M").unique(), reverse=True)
    month_labels = {p: str(p) for p in months_sorted}
    sel = st.selectbox(
        "Mês para KPIs em destaque",
        options=list(month_labels.keys()),
        format_func=lambda p: month_labels[p],
        key="ind_rh_kpi_month_cons",
    )
    row = df_f[df_f["data"].dt.to_period("M") == sel]
    if not row.empty:
        render_kpi_row_consolidado(row.iloc[0])
    st.divider()

    label_map = {
        "headcount": "Headcount",
        "admissoes": "Admissões",
        "saidas": "Saídas",
    }
    st.plotly_chart(
        fig_lines(df_f, ["headcount", "admissoes", "saidas"], "Headcount, admissões e saídas", label_map),
        use_container_width=True,
    )

    label_t = {
        "turnover_percentual": "Turnover total",
        "turnover_ate_90_dias": "Até 90 dias",
        "turnover_ate_um_ano": "Até 1 ano",
        "turnover_mais_um_ano": "Mais de 1 ano",
    }
    st.plotly_chart(
        fig_lines(df_f, list(label_t.keys()), "Turnover (%) por tempo de empresa", label_t),
        use_container_width=True,
    )

    fig2 = make_subplots(specs=[[{"secondary_y": True}]])
    fig2.add_trace(
        go.Scatter(
            x=df_f["data"],
            y=df_f["absenteismo_percentual"],
            name="Absenteísmo %",
            mode="lines+markers",
        ),
        secondary_y=False,
    )
    fig2.add_trace(
        go.Scatter(
            x=df_f["data"],
            y=df_f["horas_atestados"],
            name="Horas atestados",
            mode="lines+markers",
        ),
        secondary_y=True,
    )
    fig2.update_layout(
        title="Absenteísmo e horas de atestados/declarações",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    fig2.update_xaxes(title_text="Período")
    fig2.update_yaxes(title_text="Absenteísmo %", secondary_y=False)
    fig2.update_yaxes(title_text="Horas", secondary_y=True)
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Detalhamento mensal (filtrado)")
    display = df_f.sort_values("data", ascending=False)
    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        key="ind_rh_tbl_cons",
    )


def tab_por_dimensao(
    df_raw: pd.DataFrame,
    dim_col: str,
    view_name: str,
    cache_key_suffix: str,
) -> None:
    df = prepare_tecsmart_df(df_raw)
    if df.empty or dim_col not in df.columns:
        st.warning(
            "Não foi possível carregar dados para esta visão. "
            f"Confira `{view_name}`."
        )
        return

    st.caption(f"Referência: {view_name}")

    months_back = st.slider(
        "Meses na série temporal",
        min_value=3,
        max_value=48,
        value=18,
        step=1,
        key=f"ind_rh_months_{cache_key_suffix}",
    )
    df_f = months_range_filter(df, months_back)
    if df_f.empty:
        st.warning("Sem períodos no intervalo selecionado.")
        return

    uniques: List[str] = sorted(
        {str(x) for x in df_f[dim_col].dropna().unique() if str(x).strip() != ""}
    )
    chosen = st.multiselect(
        f"Filtrar {dim_col}",
        options=uniques,
        default=uniques[: min(12, len(uniques))],
        key=f"ind_rh_multiselect_{cache_key_suffix}",
    )
    if not chosen:
        st.info(f"Selecione ao menos um valor em «{dim_col}».")
        return

    df_s = df_f[df_f[dim_col].astype(str).isin(chosen)]

    st.subheader("Evolução do headcount por recorte")
    wide_h = (
        df_s.pivot_table(index="data", columns=dim_col, values="headcount", aggfunc="sum")
        .fillna(0)
        .reset_index()
    )
    if not wide_h.empty and wide_h.shape[1] > 1:
        fig_h = px.line(
            wide_h.melt(id_vars=["data"], var_name=dim_col, value_name="headcount"),
            x="data",
            y="headcount",
            color=dim_col,
            markers=True,
            title="Headcount",
        )
        fig_h.update_layout(xaxis_title="Período", yaxis_title="Headcount")
        st.plotly_chart(fig_h, use_container_width=True)

    st.subheader("Último período por recorte (KPIs)")
    last_dates = df_s.groupby(dim_col)["data"].transform("max")
    df_last = df_s[df_s["data"] == last_dates].drop_duplicates(subset=[dim_col])
    show_cols = [
        dim_col,
        "data",
        "headcount",
        "admissoes",
        "saidas",
        "turnover_percentual",
        "absenteismo_percentual",
        "horas_atestados",
    ]
    show_cols = [c for c in show_cols if c in df_last.columns]
    tbl = df_last[show_cols].sort_values(dim_col)
    st.dataframe(tbl, use_container_width=True, hide_index=True, key=f"ind_rh_tbl_{cache_key_suffix}")

    st.subheader("Série completa (filtrado)")
    st.dataframe(
        df_s.sort_values([dim_col, "data"]),
        use_container_width=True,
        hide_index=True,
        key=f"ind_rh_tbl_full_{cache_key_suffix}",
    )


def render_jira_matriz_solicitacoes_por_quadro() -> None:
    """Matriz quadros × (Aguardando atendimento / Em andamento / Concluídas / Rejeitadas), mesma base do Kanban."""
    st.subheader("Matriz de solicitações por quadro")
    st.caption(
        "Fonte: `administracao.Jira_projeto_dho_consolidado`, com o mesmo recorte de cada quadro "
        "do acompanhamento Kanban. **Aguardando atendimento**: status *Backlog*. **Em andamento**: demais etapas do fluxo "
        "até conclusão ou rejeição. **Concluídas**: *Finalizado* (também Done, Closed, Resolvido). "
        "**Rejeitadas**: *Rejeitado* (ou Rejected)."
    )
    df = load_jira_dho_acompanhamento()
    if df.empty:
        st.warning("Sem dados do Jira para exibir a matriz.")
        return
    mat = compute_solicitacoes_matrix_by_quadro(df)
    if mat.empty:
        st.warning("Não foi possível montar a matriz (verifique a coluna de status no dataset).")
        return

    col_cfg = {
        "Quadro": st.column_config.TextColumn("Quadro", width="large"),
        "Aguardando atendimento": st.column_config.NumberColumn(
            "Aguardando atendimento", format="%d"
        ),
        "Em andamento": st.column_config.NumberColumn("Em andamento", format="%d"),
        "Concluídas": st.column_config.NumberColumn("Concluídas", format="%d"),
        "Rejeitadas": st.column_config.NumberColumn("Rejeitadas", format="%d"),
        "Total": st.column_config.NumberColumn("Total", format="%d"),
    }
    st.dataframe(
        mat,
        column_config=col_cfg,
        hide_index=True,
        use_container_width=True,
        key="ind_rh_matriz_quadros_solicitacoes",
    )


def _format_mean_median_dias(n: int, mean: float, median: float) -> tuple[str, str]:
    if n <= 0:
        return "—", "—"
    mean_s = f"{mean:.1f}".replace(".", ",") + " dias"
    med_s = f"{median:.1f}".replace(".", ",") + " dias"
    return mean_s, med_s


def _tempo_stats(tbl: pd.DataFrame, col: str) -> tuple[int, float, float]:
    v = pd.to_numeric(tbl[col], errors="coerce").dropna()
    if v.empty:
        return 0, float("nan"), float("nan")
    return int(v.shape[0]), float(v.mean()), float(v.median())


def _build_tempos_por_cargo_table(tbl: pd.DataFrame) -> pd.DataFrame:
    """Agrupa tempos de requisição de vaga por cargo (médias e quantidade)."""
    if tbl.empty or "Cargo" not in tbl.columns:
        return pd.DataFrame()

    base = tbl.copy()
    base["Cargo"] = base["Cargo"].fillna("").astype(str).str.strip()
    base["Cargo"] = base["Cargo"].replace("", "NÃO INFORMADO")

    for c in (
        COL_TEMPO_FECHAMENTO_VAGA,
        COL_TEMPO_APROVACAO_VAGA,
        COL_TEMPO_TOTAL_CONTRATACAO,
    ):
        if c in base.columns:
            base[c] = pd.to_numeric(base[c], errors="coerce")

    grp = (
        base.groupby("Cargo", dropna=False)
        .agg(
            vagas_finalizadas=("Chave", "count"),
            tempo_fechamento_medio=(COL_TEMPO_FECHAMENTO_VAGA, "mean"),
            tempo_aprovacao_medio=(COL_TEMPO_APROVACAO_VAGA, "mean"),
            tempo_total_contratacao_medio=(COL_TEMPO_TOTAL_CONTRATACAO, "mean"),
        )
        .reset_index()
    )

    grp = grp.rename(
        columns={
            "Cargo": "Cargo",
            "vagas_finalizadas": "Vagas finalizadas",
            "tempo_fechamento_medio": "Tempo data aprovação (média)",
            "tempo_aprovacao_medio": "Data de aceite (média)",
            "tempo_total_contratacao_medio": "Data de fechamento (média)",
        }
    )
    grp = grp.sort_values(
        by=["Vagas finalizadas", "Cargo"], ascending=[False, True]
    ).reset_index(drop=True)
    return grp


def render_jira_requisicao_vaga_tempos() -> None:
    """Tempos médios no quadro RC para issues finalizadas."""
    st.subheader("Requisição de vagas — tempos (Finalizado)")
    st.caption(
        "Somente o quadro **Requisição de vaga (RC)** com status **Finalizado** (e equivalentes). "
        "**Início**: *Start date*; se ausente, *Data de início*. "
        "**Tempo data aprovação**: do início até **Data de aprovação**. "
        "**Data de aceite**: do início até **Data de fechamento**; se a **Data finalização** "
        "for anterior (processo já encerrado, mas fechamento preenchido depois no Jira), usa-se a **Data finalização** "
        "como data final desse prazo. "
        "**Data de fechamento**: do início até **Data finalização** (tempo total do ciclo da vaga). "
        "Cálculo em **dias corridos**."
    )
    df = load_jira_dho_acompanhamento()
    tbl = compute_requisicao_vaga_tempos_table(df)
    if tbl.empty:
        st.info(
            "Nenhuma requisição de vaga **finalizada** encontrada, ou faltam colunas de data/início "
            "para calcular os tempos."
        )
        return

    n1, m1, d1 = _tempo_stats(tbl, COL_TEMPO_FECHAMENTO_VAGA)
    n2, m2, d2 = _tempo_stats(tbl, COL_TEMPO_APROVACAO_VAGA)
    n3, m3, d3 = _tempo_stats(tbl, COL_TEMPO_TOTAL_CONTRATACAO)

    k1, h1 = _format_mean_median_dias(n1, m1, d1)
    k2, h2 = _format_mean_median_dias(n2, m2, d2)
    k3, h3 = _format_mean_median_dias(n3, m3, d3)

    r1, r2, r3 = st.columns(3)
    with r1:
        st.metric("Tempo data aprovação (média)", k1, help="Início → data de aprovação")
    with r2:
        st.metric(
            "Data de aceite (média)",
            k2,
            help="Início → data de fechamento; se finalização for mais cedo, usa-se ela como fim.",
        )
    with r3:
        st.metric("Data de fechamento (média)", k3, help="Início → data finalização (ciclo total)")

    st.subheader("Tempos por cargo")
    st.caption("Média em dias corridos por cargo, considerando apenas vagas finalizadas.")
    tbl_cargo = _build_tempos_por_cargo_table(tbl)
    if tbl_cargo.empty:
        st.info("Sem dados suficientes de cargo para montar o quadro por cargo.")
    else:
        st.dataframe(
            tbl_cargo,
            hide_index=True,
            use_container_width=True,
            key="ind_rh_req_vaga_tempos_por_cargo_tbl",
            column_config={
                "Vagas finalizadas": st.column_config.NumberColumn(format="%d"),
                "Tempo data aprovação (média)": st.column_config.NumberColumn(format="%.1f"),
                "Data de aceite (média)": st.column_config.NumberColumn(format="%.1f"),
                "Data de fechamento (média)": st.column_config.NumberColumn(format="%.1f"),
            },
        )

    st.subheader("Detalhamento por solicitação")
    num_cfg = st.column_config.NumberColumn(format="%d")
    st.dataframe(
        tbl,
        hide_index=True,
        use_container_width=True,
        key="ind_rh_req_vaga_tempos_tbl",
        column_config={
            COL_TEMPO_FECHAMENTO_VAGA: num_cfg,
            COL_TEMPO_APROVACAO_VAGA: num_cfg,
            COL_TEMPO_TOTAL_CONTRATACAO: num_cfg,
        },
    )


def render_indicadores_rh_dashboard(
    show_title: bool = True,
    show_caption: bool = True,
) -> None:
    """Renderiza indicadores de gestão de pessoas (Jira + Tecsmart)."""
    if show_title:
        st.title("Indicadores de gestão de pessoas")
    if show_caption:
        st.caption(
            "Aba **Solicitações (Jira)**: matriz por quadro e tempos no quadro de requisição de vagas. "
            "Aba **Operacional (Tecsmart)**: headcount, admissões, saídas, turnover e absenteísmo."
        )

    tab_jira, tab_tec = st.tabs(["Solicitações (Jira)", "Operacional (Tecsmart)"])

    with tab_jira:
        jira_matriz, jira_rv = st.tabs(
            ["Matriz por quadro", "Requisição de vagas — tempos"]
        )
        with jira_matriz:
            render_jira_matriz_solicitacoes_por_quadro()
        with jira_rv:
            render_jira_requisicao_vaga_tempos()

    with tab_tec:
        tab_con, tab_eq, tab_fi = st.tabs(
            ["Visão consolidada", "Por equipe", "Por filial"]
        )

        with tab_con:
            tab_consolidado(load_tecsmart_consolidado())

        with tab_eq:
            tab_por_dimensao(
                load_tecsmart_equipe(),
                "equipe",
                TEC_EQUIPE,
                "equipe",
            )

        with tab_fi:
            tab_por_dimensao(
                load_tecsmart_filial(),
                "filial",
                TEC_FILIAL,
                "filial",
            )
