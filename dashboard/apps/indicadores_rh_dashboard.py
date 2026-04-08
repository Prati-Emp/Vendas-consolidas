"""
Dashboard de Indicadores de Gestão de Pessoas —
solicitações (Jira DHO), atestados (indicador_de_atestados) e demografia (Tecsmart).
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, List, Optional, Sequence, Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from dashboard.apps.acompanhamento_solicitacoes_dashboard import (  # noqa: E402
    COL_TEMPO_APROVACAO_VAGA,
    COL_TEMPO_FECHAMENTO_VAGA,
    COL_TEMPO_TOTAL_CONTRATACAO,
    _normalize_text_for_match,
    compute_requisicao_vaga_tempos_table,
    compute_solicitacoes_matrix_by_quadro,
    load_jira_dho_acompanhamento,
)
from dashboard.utils.md_conn import get_md_connection

TEC_CONSOLIDADO = "administracao.Tecsmart_indicadores"
TEC_EQUIPE = "administracao.Tecsmart_indicadores_equipe"
TEC_FILIAL = "administracao.Tecsmart_indicadores_filial"
FUNC_GERAL_RH = "administracao.funcionario_geral_rh_consolidado"
INDICADOR_ATESTADOS = "administracao.indicador_de_atestados"

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


@st.cache_data(ttl=600)
def load_funcionario_geral_rh() -> pd.DataFrame:
    md = get_md_connection()
    try:
        return md.run_query(f"SELECT * FROM {FUNC_GERAL_RH}")
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=600)
def load_indicador_de_atestados() -> pd.DataFrame:
    md = get_md_connection()
    try:
        return md.run_query(f"SELECT * FROM {INDICADOR_ATESTADOS}")
    except Exception:
        return pd.DataFrame()


def _norm_txt(s: Any) -> str:
    if s is None:
        return ""
    v = str(s).strip().lower()
    v = v.replace("á", "a").replace("à", "a").replace("ã", "a").replace("â", "a")
    v = v.replace("é", "e").replace("ê", "e")
    v = v.replace("í", "i")
    v = v.replace("ó", "o").replace("ô", "o").replace("õ", "o")
    v = v.replace("ú", "u")
    v = v.replace("ç", "c")
    v = v.replace("-", "_").replace(" ", "_")
    return v


def _pick_col(df: pd.DataFrame, candidates: Sequence[str]) -> str:
    if df.empty:
        return ""
    cols = list(df.columns)
    norm = {c: _norm_txt(c) for c in cols}

    # 1) Match exato primeiro (evita colisões como "idade" em "nacionalidade")
    for cand in candidates:
        n = _norm_txt(cand)
        for c, cn in norm.items():
            if n == cn:
                return c

    # 2) Match por token (ex.: "vinculo" em "tipo_de_vinculo")
    for cand in candidates:
        n = _norm_txt(cand)
        for c, cn in norm.items():
            tokens = [t for t in cn.split("_") if t]
            if n in tokens:
                return c

    # 3) Fallback por contains (último recurso)
    for cand in candidates:
        n = _norm_txt(cand)
        for c, cn in norm.items():
            if n and n in cn:
                return c
    return ""


def _value_counts_table(df: pd.DataFrame, col: str, label: str) -> pd.DataFrame:
    if not col or col not in df.columns:
        return pd.DataFrame()
    s = df[col].astype(str).str.strip().replace({"": "NÃO INFORMADO", "nan": "NÃO INFORMADO"})
    out = (
        s.value_counts(dropna=False)
        .rename_axis(label)
        .reset_index(name="Quantidade")
        .sort_values("Quantidade", ascending=False)
    )
    out["Percentual"] = (out["Quantidade"] / max(int(out["Quantidade"].sum()), 1)) * 100
    return out


def _render_dist(df: pd.DataFrame, col: str, label: str, key_suffix: str) -> None:
    tbl = _value_counts_table(df, col, label)
    if tbl.empty:
        st.info(f"Coluna de {label.lower()} não encontrada.")
        return
    fig = px.bar(tbl.head(15), x=label, y="Quantidade", title=label)
    fig.update_layout(xaxis_title="", yaxis_title="Quantidade")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(
        tbl,
        hide_index=True,
        use_container_width=True,
        key=f"demog_tbl_{key_suffix}",
        column_config={
            "Quantidade": st.column_config.NumberColumn(format="%d"),
            "Percentual": st.column_config.NumberColumn(format="%.1f%%"),
        },
    )


def _render_estrutura_dashboard(
    df: pd.DataFrame,
    col_vinc: str,
    col_eq: str,
    col_cargo: str,
    col_instr: str,
) -> None:
    """Renderiza seção de estrutura (vínculo, equipe e cargo)."""

    def _clean_opts(col: str) -> pd.Series:
        if not col or col not in df.columns:
            return pd.Series("NÃO INFORMADO", index=df.index)
        return (
            df[col]
            .astype(str)
            .str.strip()
            .replace({"": "NÃO INFORMADO", "nan": "NÃO INFORMADO"})
        )

    vinc_s = _clean_opts(col_vinc)
    eq_s = _clean_opts(col_eq)
    cargo_s = _clean_opts(col_cargo)
    instr_s = _clean_opts(col_instr)
    if df.empty:
        st.info("Sem dados para os filtros selecionados.")
        return

    vinc_div = vinc_s
    eq_div = eq_s
    cargo_div = cargo_s
    instr_div = instr_s

    def _bar_table(series: pd.Series, y_label: str, topn: int = 15) -> pd.DataFrame:
        tbl = (
            series.value_counts()
            .rename_axis(y_label)
            .reset_index(name="Quantidade")
            .sort_values("Quantidade", ascending=False)
        )
        if tbl.shape[0] > topn:
            tbl = tbl.head(topn)
        return tbl.sort_values("Quantidade", ascending=True)

    tbl_eq = (
        eq_div.value_counts()
        .rename_axis("Equipe")
        .reset_index(name="Quantidade")
        .sort_values("Quantidade", ascending=False)
    )
    total_eq = max(int(tbl_eq["Quantidade"].sum()), 1)
    tbl_eq["%"] = (tbl_eq["Quantidade"] / total_eq) * 100

    tbl_cargo = (
        cargo_div.value_counts()
        .rename_axis("Cargo")
        .reset_index(name="Quantidade")
        .sort_values("Quantidade", ascending=False)
    )
    total_cargo = max(int(tbl_cargo["Quantidade"].sum()), 1)
    tbl_cargo["%"] = (tbl_cargo["Quantidade"] / total_cargo) * 100

    # Vínculo (gráfico) lado a lado com Grau de instrução (gráfico)
    c1, c2 = st.columns(2)
    with c1:
        tbl_vinc_graf = (
            vinc_div.value_counts()
            .rename_axis("Vínculo empregatício")
            .reset_index(name="Quantidade")
            .sort_values("Quantidade", ascending=True)
        )
        fig_vinc = px.bar(
            tbl_vinc_graf,
            x="Vínculo empregatício",
            y="Quantidade",
            title="Vínculo empregatício",
            color="Quantidade",
            color_continuous_scale="Blues",
            text="Quantidade",
        )
        fig_vinc.update_layout(
            template="plotly_dark",
            coloraxis_showscale=False,
            margin=dict(l=10, r=10, t=50, b=10),
        )
        fig_vinc.update_traces(texttemplate="<b>%{text}</b>", textposition="outside")
        st.plotly_chart(fig_vinc, use_container_width=True)

    with c2:
        tbl_instr = (
            instr_div.value_counts()
            .rename_axis("Grau de instrução")
            .reset_index(name="Quantidade")
            .sort_values("Quantidade", ascending=True)
        )
        fig_instr = px.bar(
            tbl_instr,
            x="Quantidade",
            y="Grau de instrução",
            orientation="h",
            title="Grau de Instrução",
            color="Quantidade",
            color_continuous_scale="Blues",
            text="Quantidade",
        )
        fig_instr.update_layout(
            template="plotly_dark",
            coloraxis_showscale=False,
            margin=dict(l=10, r=10, t=50, b=10),
        )
        fig_instr.update_traces(texttemplate="<b>%{text}</b>", textposition="inside")
        st.plotly_chart(fig_instr, use_container_width=True)

    # Tabelas de cargo e equipe lado a lado
    t1, t2 = st.columns(2)
    with t1:
        st.subheader("Cargo")
        st.dataframe(
            tbl_cargo,
            hide_index=True,
            use_container_width=True,
            key="estr_tabela_cargo",
            column_config={
                "Quantidade": st.column_config.NumberColumn(format="%d"),
                "%": st.column_config.NumberColumn(format="%.1f%%"),
            },
        )
    with t2:
        st.subheader("Equipe")
        st.dataframe(
            tbl_eq,
            hide_index=True,
            use_container_width=True,
            key="estr_tabela_equipe",
            column_config={
                "Quantidade": st.column_config.NumberColumn(format="%d"),
                "%": st.column_config.NumberColumn(format="%.1f%%"),
            },
        )


def _render_demografia_rh() -> None:
    st.subheader("Demografia da empresa")
    df = load_funcionario_geral_rh()
    if df.empty:
        st.warning("Sem dados para demografia.")
        return

    col_hier = _pick_col(df, ["hierarquia"])
    col_sexo = _pick_col(df, ["sexo"])
    col_raca = _pick_col(df, ["raca"])
    col_pcd = _pick_col(df, ["tipo_de_deficiencia"])
    col_tempo = _pick_col(df, ["tempo_de_empresa_meses"])
    col_idade = _pick_col(df, ["idade"])
    col_estado = _pick_col(df, ["estado_civil"])
    col_instr = _pick_col(df, ["grau_de_instrucao", "grau_instrucao", "instrucao", "escolaridade"])
    col_vinc = _pick_col(df, ["tipo_de_vinculo", "vinculo"])
    col_nac = _pick_col(df, ["nacionalidade"])
    col_eq = _pick_col(df, ["equipe"])
    col_cargo = _pick_col(df, ["funcionario", "cargo"])
    col_colab = _pick_col(df, ["colaborador", "nome", "nome_do_colaborador"])
    col_adm = _pick_col(df, ["admicao", "admissao", "admiss_o"])
    col_exp1 = _pick_col(df, ["experiencia_vencimento"])
    col_exp2 = _pick_col(df, ["experiencia_2_vencimento"])

    # Base para KPIs e quadro hierárquico
    base = df.copy()
    if col_hier:
        base["_hier"] = base[col_hier].astype(str).str.strip().replace({"": "NÃO INFORMADO"})
    else:
        base["_hier"] = "NÃO INFORMADO"
    if col_sexo:
        sx = base[col_sexo].astype(str).str.lower()
        base["_mulher"] = sx.str.contains("femin", na=False)
    else:
        base["_mulher"] = False
    minoria_racial = pd.Series(False, index=base.index)
    if col_raca:
        rr = base[col_raca].astype(str).str.strip().str.lower()
        minoria_racial = (~rr.isin(["", "nan", "none", "na", "<na>", "não informado"])) & (~rr.isin(["branco", "branca"]))
    base["_minoria"] = minoria_racial

    tabs = st.tabs(["Resumo", "Tempo e experiência", "Diversidade"])
    with tabs[0]:
        def _clean_global_col(col_name: str) -> pd.Series:
            if not col_name or col_name not in df.columns:
                return pd.Series("NÃO INFORMADO", index=df.index)
            return (
                df[col_name]
                .astype(str)
                .str.strip()
                .replace({"": "NÃO INFORMADO", "nan": "NÃO INFORMADO", "None": "NÃO INFORMADO"})
            )

        sexo_g = _clean_global_col(col_sexo)
        raca_g = _clean_global_col(col_raca)
        hier_g = base["_hier"].astype(str).str.strip().replace({"": "NÃO INFORMADO"})
        cargo_g = _clean_global_col(col_cargo)
        equipe_g = _clean_global_col(col_eq)

        filtros_resumo = {
            "Sexo": sexo_g,
            "Raça": raca_g,
            "Nível hierárquico": hier_g,
            "Cargo": cargo_g,
            "Equipe": equipe_g,
        }
        rf1, rf2 = st.columns(2)
        with rf1:
            col_filtro_resumo = st.selectbox(
                "1) Escolha a coluna para filtrar",
                options=list(filtros_resumo.keys()),
                index=0,
                key="resumo_filtro_coluna_dinamica",
            )
        serie_filtro_resumo = filtros_resumo[col_filtro_resumo]
        opcoes_filtro_resumo = sorted(
            [
                v
                for v in serie_filtro_resumo.dropna().astype(str).str.strip().unique().tolist()
                if v
            ]
        )
        with rf2:
            valores_filtro_resumo = st.multiselect(
                f"2) Filtrar itens de {col_filtro_resumo}",
                options=opcoes_filtro_resumo,
                default=[],
                key="resumo_filtro_valores_dinamico",
                placeholder="Todos",
            )

        mask_resumo = pd.Series(True, index=df.index)
        if valores_filtro_resumo:
            mask_resumo &= serie_filtro_resumo.isin(valores_filtro_resumo)

        base_resumo = base[mask_resumo].copy()
        df_resumo = df[mask_resumo].copy()

        if base_resumo.empty:
            st.info("Sem dados para os filtros globais selecionados.")


        cards = st.columns(5)
        homens_total = int(sexo_g[mask_resumo].str.lower().str.contains("mascul", na=False).sum())
        mulheres_total = int(base_resumo["_mulher"].sum())
        pcd_total = 0
        if col_pcd and col_pcd in df_resumo.columns:
            pcd_s = (
                df_resumo[col_pcd]
                .astype(str)
                .str.strip()
                .str.lower()
            )
            pcd_total = int(
                (
                    (~pcd_s.isin(["", "nan", "none", "na", "<na>", "não informado"]))
                    & (pcd_s != "nenhum")
                ).sum()
            )
        idosos_60_total = 0
        if col_idade and col_idade in df_resumo.columns:
            idade_s = pd.to_numeric(df_resumo[col_idade], errors="coerce")
            idosos_60_total = int((idade_s >= 60).sum())

        with cards[0]:
            st.metric("Colaboradores", f"{len(base_resumo):,}".replace(",", "."))
        with cards[1]:
            st.metric("Homens", f"{homens_total:,}".replace(",", "."))
        with cards[2]:
            st.metric("Mulheres", f"{mulheres_total:,}".replace(",", "."))
        with cards[3]:
            st.metric("PCD", f"{pcd_total:,}".replace(",", "."))
        with cards[4]:
            st.metric("60+", f"{idosos_60_total:,}".replace(",", "."))

        m = (
            base_resumo.groupby("_hier")
            .agg(
                Total=("_hier", "count"),
                Mulheres=("_mulher", "sum"),
                Minorias=("_minoria", "sum"),
            )
            .reset_index()
            .rename(columns={"_hier": "Nível hierárquico"})
            .sort_values("Total", ascending=False)
        )
        st.subheader("Número de colaboradores por nível hierárquico")
        st.dataframe(
            m,
            hide_index=True,
            use_container_width=True,
            key="demog_hier_minorias",
            column_config={
                "Total": st.column_config.NumberColumn(format="%d"),
                "Mulheres": st.column_config.NumberColumn(format="%d"),
                "Minorias": st.column_config.NumberColumn(format="%d"),
            },
        )
        st.caption("Minorias = raça informada diferente de 'Branco' (campos vazios/não informados não entram).")

        # Tabelas de cargo e equipe também no Resumo
        st.divider()
        t_cargo, t_equipe = st.columns(2)
        with t_cargo:
            st.subheader("Cargo")
            if col_cargo and col_cargo in df_resumo.columns:
                cargo_s = (
                    df_resumo[col_cargo]
                    .astype(str)
                    .str.strip()
                    .replace({"": "NÃO INFORMADO", "nan": "NÃO INFORMADO"})
                )
                tbl_cargo = (
                    cargo_s.value_counts()
                    .rename_axis("Cargo")
                    .reset_index(name="Quantidade")
                    .sort_values("Quantidade", ascending=False)
                )
                total_cargo = max(int(tbl_cargo["Quantidade"].sum()), 1)
                tbl_cargo["%"] = (tbl_cargo["Quantidade"] / total_cargo) * 100
                st.dataframe(
                    tbl_cargo,
                    hide_index=True,
                    use_container_width=True,
                    key="resumo_tabela_cargo",
                    column_config={
                        "Quantidade": st.column_config.NumberColumn(format="%d"),
                        "%": st.column_config.NumberColumn(format="%.1f%%"),
                    },
                )
            else:
                st.info("Coluna de cargo não encontrada.")
        with t_equipe:
            st.subheader("Equipe")
            if col_eq and col_eq in df_resumo.columns:
                eq_s = (
                    df_resumo[col_eq]
                    .astype(str)
                    .str.strip()
                    .replace({"": "NÃO INFORMADO", "nan": "NÃO INFORMADO"})
                )
                tbl_eq = (
                    eq_s.value_counts()
                    .rename_axis("Equipe")
                    .reset_index(name="Quantidade")
                    .sort_values("Quantidade", ascending=False)
                )
                total_eq = max(int(tbl_eq["Quantidade"].sum()), 1)
                tbl_eq["%"] = (tbl_eq["Quantidade"] / total_eq) * 100
                st.dataframe(
                    tbl_eq,
                    hide_index=True,
                    use_container_width=True,
                    key="resumo_tabela_equipe",
                    column_config={
                        "Quantidade": st.column_config.NumberColumn(format="%d"),
                        "%": st.column_config.NumberColumn(format="%.1f%%"),
                    },
                )
            else:
                st.info("Coluna de equipe não encontrada.")

    with tabs[1]:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Tempo de empresa")
            if col_tempo:
                v = pd.to_numeric(df[col_tempo], errors="coerce")
                bins = pd.cut(
                    v,
                    bins=[-1, 3, 6, 12, 24, 60, 9999],
                    labels=[
                        "0-3m",
                        "3-6m",
                        "1 ano",
                        "1-2 anos",
                        "2-5 anos",
                        "5+ anos",
                    ],
                    include_lowest=True,
                )
                tbl = bins.value_counts(sort=False).rename_axis("Faixa").reset_index(name="Quantidade")
                total_tempo = max(int(tbl["Quantidade"].sum()), 1)
                tbl["%"] = (tbl["Quantidade"] / total_tempo) * 100
                st.dataframe(
                    tbl,
                    hide_index=True,
                    use_container_width=True,
                    key="demog_tempo_empresa",
                    column_config={
                        "Quantidade": st.column_config.NumberColumn(format="%d"),
                        "%": st.column_config.NumberColumn(format="%.1f%%"),
                    },
                )
            else:
                st.info("Coluna de tempo de empresa não encontrada.")
        with c2:
            st.subheader("Idade")
            if col_idade:
                i = pd.to_numeric(df[col_idade], errors="coerce")
                bins = pd.cut(
                    i,
                    bins=[-1, 20, 30, 40, 50, 60, 200],
                    labels=["<21", "21-30", "31-40", "41-50", "51-60", "60+"],
                    include_lowest=True,
                )
                tbl = bins.value_counts(sort=False).rename_axis("Faixa").reset_index(name="Quantidade")
                total_idade = max(int(tbl["Quantidade"].sum()), 1)
                tbl["%"] = (tbl["Quantidade"] / total_idade) * 100
                st.dataframe(
                    tbl,
                    hide_index=True,
                    use_container_width=True,
                    key="demog_idade",
                    column_config={
                        "Quantidade": st.column_config.NumberColumn(format="%d"),
                        "%": st.column_config.NumberColumn(format="%.1f%%"),
                    },
                )
            else:
                st.info("Coluna de idade não encontrada.")

        st.subheader("Tempo de empresa e idade (detalhado)")
        if col_tempo or col_idade:
            tempo_vals = pd.to_numeric(df[col_tempo], errors="coerce") if col_tempo else pd.Series(pd.NA, index=df.index)
            idade_vals = pd.to_numeric(df[col_idade], errors="coerce") if col_idade else pd.Series(pd.NA, index=df.index)

            tempo_faixa = pd.cut(
                tempo_vals,
                bins=[-1, 3, 6, 12, 24, 60, 9999],
                labels=["0-3m", "3-6m", "1 ano", "1-2 anos", "2-5 anos", "5+ anos"],
                include_lowest=True,
            ) if col_tempo else pd.Series(pd.NA, index=df.index)

            idade_faixa = pd.cut(
                idade_vals,
                bins=[-1, 20, 30, 40, 50, 60, 200],
                labels=["<21", "21-30", "31-40", "41-50", "51-60", "60+"],
                include_lowest=True,
            ) if col_idade else pd.Series(pd.NA, index=df.index)

            detalhe_tempo_idade = pd.DataFrame(
                {
                    "Colaborador": df[col_colab].astype(str).str.strip() if col_colab else pd.Series("", index=df.index),
                    "Equipe": df[col_eq].astype(str).str.strip() if col_eq else pd.Series("", index=df.index),
                    "Cargo": df[col_cargo].astype(str).str.strip() if col_cargo else pd.Series("", index=df.index),
                    "Faixa tempo de empresa": tempo_faixa.astype(str).replace({"nan": "Não informado"}),
                    "Faixa idade": idade_faixa.astype(str).replace({"nan": "Não informado"}),
                }
            )
            detalhe_tempo_idade = detalhe_tempo_idade.sort_values(
                by=["Faixa tempo de empresa", "Faixa idade", "Colaborador"],
                ascending=[True, True, True],
            )
            filtro_cols_tempo_idade = {
                "Faixa tempo de empresa": "Faixa tempo de empresa",
                "Faixa idade": "Faixa idade",
                "Equipe": "Equipe",
                "Cargo": "Cargo",
                "Colaborador": "Colaborador",
            }
            tf1, tf2 = st.columns(2)
            with tf1:
                col_filtro_label_ti = st.selectbox(
                    "1) Escolha a coluna para filtrar",
                    options=list(filtro_cols_tempo_idade.keys()),
                    index=0,
                    key="demog_filtro_coluna_tempo_idade",
                )
            col_filtro_ti = filtro_cols_tempo_idade[col_filtro_label_ti]
            valores_disponiveis_ti = sorted(
                [
                    v
                    for v in detalhe_tempo_idade[col_filtro_ti].dropna().astype(str).str.strip().unique().tolist()
                    if v
                ]
            )
            with tf2:
                valores_selecionados_ti = st.multiselect(
                    f"2) Filtrar itens de {col_filtro_label_ti}",
                    options=valores_disponiveis_ti,
                    default=[],
                    key="demog_filtro_valores_tempo_idade",
                    placeholder="",
                )

            if valores_selecionados_ti:
                detalhe_tempo_idade = detalhe_tempo_idade[
                    detalhe_tempo_idade[col_filtro_ti].isin(valores_selecionados_ti)
                ].copy()

            st.dataframe(
                detalhe_tempo_idade,
                hide_index=True,
                use_container_width=True,
                key="demog_tempo_idade_detalhado",
            )
        else:
            st.info("Colunas de tempo de empresa e idade não encontradas.")

        st.subheader("Período de experiência")
        if col_exp1 or col_exp2:
            exp1 = pd.to_datetime(df[col_exp1], errors="coerce") if col_exp1 else pd.Series(pd.NaT, index=df.index)
            exp2 = pd.to_datetime(df[col_exp2], errors="coerce") if col_exp2 else pd.Series(pd.NaT, index=df.index)
            today = pd.Timestamp.today().normalize()
            # Fim da experiência = maior data entre 1ª e 2ª (evita subcontar quem está na 2ª)
            exp_end = pd.concat([exp1, exp2], axis=1).max(axis=1)

            # Consolidar por colaborador para evitar duplicidades de linhas na base
            if col_colab:
                colab_s = df[col_colab].astype(str).str.strip()
                colab_s = colab_s.replace({"": pd.NA, "nan": pd.NA})
                base_exp = pd.DataFrame({"Colaborador": colab_s, "_exp_end": exp_end})
                exp_max = base_exp.dropna(subset=["Colaborador"]).groupby("Colaborador", as_index=False)["_exp_end"].max()
                status = pd.Series("Não informado", index=exp_max.index)
                status = status.mask(exp_max["_exp_end"].notna() & (exp_max["_exp_end"] >= today), "Em experiência")
            else:
                status = pd.Series("Não informado", index=df.index)
                status = status.mask(exp_end.notna() & (exp_end >= today), "Em experiência")

            # Exibir apenas a situação "Em experiência"
            qtd_em_exp = int((status == "Em experiência").sum())
            tbl = pd.DataFrame([{"Situação": "Em experiência", "Quantidade": qtd_em_exp}])
            st.dataframe(tbl, hide_index=True, use_container_width=True, key="demog_experiencia")

            # Detalhamento: somente pessoas atualmente em experiência (1ª ou 2ª)
            em_primeira = exp1.notna() & (today <= exp1.dt.normalize())
            em_segunda = (~em_primeira) & exp2.notna() & (today <= exp2.dt.normalize())
            em_experiencia = em_primeira | em_segunda

            if em_experiencia.any():
                adm = pd.to_datetime(df[col_adm], errors="coerce") if col_adm else pd.Series(pd.NaT, index=df.index)
                fase = pd.Series("", index=df.index)
                fase = fase.mask(em_primeira, "1ª experiência")
                fase = fase.mask(em_segunda, "2ª experiência")

                venc = pd.Series(pd.NaT, index=df.index)
                venc = venc.where(~em_primeira, exp1)
                venc = venc.where(~em_segunda, exp2)

                inicio_fase = pd.Series(pd.NaT, index=df.index)
                # Na 1ª experiência, conta desde admissão.
                inicio_fase = inicio_fase.where(~em_primeira, adm)
                # Na 2ª experiência, conta desde o fim da 1ª (fallback para admissão se faltar exp1).
                inicio_fase = inicio_fase.where(~em_segunda, exp1.fillna(adm))

                dias_exp = (today - inicio_fase.dt.normalize()).dt.days
                dias_exp = dias_exp.where(dias_exp.notna(), 0).clip(lower=0).astype(int)

                detalhe = pd.DataFrame(
                    {
                        "Colaborador": df[col_colab].astype(str).str.strip() if col_colab else pd.Series("", index=df.index),
                        "Equipe": df[col_eq].astype(str).str.strip() if col_eq else pd.Series("", index=df.index),
                        "Cargo": df[col_cargo].astype(str).str.strip() if col_cargo else pd.Series("", index=df.index),
                        "Fase": fase,
                        "Vencimento da experiência": venc.dt.strftime("%Y-%m-%d"),
                        "Dias em experiência": dias_exp,
                    }
                )
                detalhe = detalhe[em_experiencia].copy()
                detalhe = detalhe.sort_values(
                    by=["Vencimento da experiência", "Colaborador"],
                    ascending=[True, True],
                )
                if "Colaborador" in detalhe.columns:
                    detalhe["Colaborador"] = detalhe["Colaborador"].astype(str).str.strip()
                    detalhe = detalhe[detalhe["Colaborador"].replace({"": pd.NA, "nan": pd.NA}).notna()].copy()
                    # Se a base vier duplicada, manter a linha com vencimento mais próximo (primeiro após sort)
                    detalhe = detalhe.drop_duplicates(subset=["Colaborador"], keep="first")

                st.subheader("Pessoas em experiência (detalhado)")
                filtro_cols = {
                    "Fase": "Fase",
                    "Equipe": "Equipe",
                    "Cargo": "Cargo",
                    "Colaborador": "Colaborador",
                }
                f1, f2 = st.columns(2)
                with f1:
                    col_filtro_label = st.selectbox(
                        "1) Escolha a coluna para filtrar",
                        options=list(filtro_cols.keys()),
                        index=0,
                        key="demog_filtro_coluna_experiencia",
                    )
                col_filtro = filtro_cols[col_filtro_label]
                valores_disponiveis = sorted(
                    [
                        v
                        for v in detalhe[col_filtro].dropna().astype(str).str.strip().unique().tolist()
                        if v
                    ]
                )
                with f2:
                    valores_selecionados = st.multiselect(
                        f"2) Filtrar itens de {col_filtro_label}",
                        options=valores_disponiveis,
                        default=[],
                        key="demog_filtro_valores_experiencia",
                        placeholder="",
                    )

                # UX: quando não selecionar itens, mostramos tudo.
                if valores_selecionados:
                    detalhe_filtrado = detalhe[detalhe[col_filtro].isin(valores_selecionados)].copy()
                else:
                    detalhe_filtrado = detalhe.copy()

                st.dataframe(
                    detalhe_filtrado,
                    hide_index=True,
                    use_container_width=True,
                    key="demog_pessoas_em_experiencia",
                    column_config={
                        "Dias em experiência": st.column_config.NumberColumn(format="%d"),
                    },
                )
            else:
                st.info("Não há pessoas em experiência no momento.")
        else:
            st.info("Colunas de experiência não encontradas.")

    with tabs[2]:
        st.markdown(
            """
            <style>
            .div-kpi-grid { display:grid; grid-template-columns: repeat(4, minmax(180px, 1fr)); gap:12px; margin: 6px 0 14px 0; }
            .div-kpi-card { background: var(--secondary-background-color); border: 1px solid rgba(127,127,127,0.28); border-radius: 12px; padding: 10px 12px; min-height: 78px; display:flex; flex-direction:column; justify-content:center; }
            .div-kpi-title { font-size: 12px; color: var(--text-color); opacity: 0.8; margin-bottom: 4px; }
            .div-kpi-value { font-size: 30px; line-height: 1.1; font-weight: 700; color: var(--text-color); word-break: break-word; }
            .div-kpi-sub { font-size: 20px; line-height: 1.2; font-weight: 600; color: var(--text-color); word-break: break-word; }
            @media (max-width: 1200px) { .div-kpi-grid { grid-template-columns: repeat(2, minmax(180px, 1fr)); } }
            </style>
            """,
            unsafe_allow_html=True,
        )

        df_div = df.copy()

        def _clean_series(col_name: str) -> pd.Series:
            if not col_name or col_name not in df_div.columns:
                return pd.Series("NÃO INFORMADO", index=df_div.index)
            s = (
                df_div[col_name]
                .astype(str)
                .str.strip()
                .replace({"": "NÃO INFORMADO", "nan": "NÃO INFORMADO", "None": "NÃO INFORMADO"})
            )
            return s

        sexo_s = _clean_series(col_sexo)
        nac_s = _clean_series(col_nac)
        raca_s = _clean_series(col_raca)
        instr_s = _clean_series(col_instr)
        estado_s = _clean_series(col_estado)
        vinc_s = _clean_series(col_vinc)
        eq_s = _clean_series(col_eq)
        cargo_s = _clean_series(col_cargo)
        colab_s = _clean_series(col_colab) if col_colab and col_colab in df_div.columns else None

        filtros_diversidade: dict[str, pd.Series] = {}
        if colab_s is not None:
            filtros_diversidade["Colaborador"] = colab_s
        filtros_diversidade.update(
            {
                "Gênero": sexo_s,
                "Nacionalidade": nac_s,
                "Raça": raca_s,
                "Vínculo empregatício": vinc_s,
                "Grau de instrução": instr_s,
                "Equipe": eq_s,
                "Cargo": cargo_s,
            }
        )
        df1, df2 = st.columns(2)
        with df1:
            col_filtro_div = st.selectbox(
                "1) Escolha a coluna para filtrar",
                options=list(filtros_diversidade.keys()),
                index=0,
                key="diversidade_filtro_coluna_dinamica",
            )
        serie_filtro_div = filtros_diversidade[col_filtro_div]
        opcoes_filtro_div = sorted(
            [
                v
                for v in serie_filtro_div.dropna().astype(str).str.strip().unique().tolist()
                if v
            ]
        )
        with df2:
            valores_filtro_div = st.multiselect(
                f"2) Filtrar itens de {col_filtro_div}",
                options=opcoes_filtro_div,
                default=[],
                key="diversidade_filtro_valores_dinamico",
                placeholder="Todos",
            )

        mask = pd.Series(True, index=df_div.index)
        if valores_filtro_div:
            mask &= serie_filtro_div.isin(valores_filtro_div)
        div = df_div[mask].copy()
        if div.empty:
            st.info("Sem dados para os filtros selecionados.")
        else:
            sexo_div = sexo_s[mask]
            nac_div = nac_s[mask]
            raca_div = raca_s[mask]
            instr_div = instr_s[mask]
            estado_div = estado_s[mask]

            def _bar_textpos_for_count(n: int) -> str:
                # Se houver poucas barras, texto "dentro" costuma ficar espremido em barras pequenas.
                return "outside" if n <= 6 else "inside"

            total = int(div.shape[0])
            feminino = int(sexo_div.str.lower().str.contains("femin", na=False).sum())
            perc_fem = (feminino / total * 100.0) if total else 0.0
            nac_top = nac_div.value_counts().idxmax() if not nac_div.empty else "N/A"
            nac_top_pct = (nac_div.value_counts().max() / total * 100.0) if total else 0.0
            instr_top = instr_div.value_counts().idxmax() if not instr_div.empty else "N/A"
            instr_top_pct = (instr_div.value_counts().max() / total * 100.0) if total else 0.0

            st.markdown(
                f"""
                <div class="div-kpi-grid">
                  <div class="div-kpi-card">
                    <div class="div-kpi-title">👥 Total de colaboradores</div>
                    <div class="div-kpi-value">{_format_int(total)}</div>
                  </div>
                  <div class="div-kpi-card">
                    <div class="div-kpi-title">♀ Representatividade feminina</div>
                    <div class="div-kpi-value">{f"{perc_fem:.1f}%".replace(".", ",")}</div>
                  </div>
                  <div class="div-kpi-card">
                    <div class="div-kpi-title">🎓 Escolaridade predominante</div>
                    <div class="div-kpi-sub">{instr_top}: {f"{instr_top_pct:.1f}%".replace(".", ",")}</div>
                  </div>
                  <div class="div-kpi-card">
                    <div class="div-kpi-title">🌍 Nacionalidade predominante</div>
                    <div class="div-kpi-sub">{nac_top}: {f"{nac_top_pct:.1f}%".replace(".", ",")}</div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            c1, c2 = st.columns(2)
            with c1:
                sexo_tbl = sexo_div.value_counts().rename_axis("Sexo").reset_index(name="Quantidade")
                # Paleta consistente com a referência: Masculino em azul e Feminino em coral.
                sexo_vals = sexo_tbl["Sexo"].astype(str).tolist()
                gender_map = {}
                for s in sexo_vals:
                    ss = str(s).strip().lower()
                    if "femin" in ss:
                        gender_map[s] = "#FF6B5E"
                    elif "mascul" in ss:
                        gender_map[s] = "#6EA8FE"
                    else:
                        gender_map[s] = "#94A3B8"
                fig_sexo = px.pie(
                    sexo_tbl,
                    values="Quantidade",
                    names="Sexo",
                    color="Sexo",
                    hole=0.55,
                    title="Distribuição por Gênero",
                    color_discrete_map=gender_map,
                )
                # Reduz o tamanho da rosca ~30% (domain define área ocupada do gráfico).
                fig_sexo.update_traces(
                    textposition="inside",
                    textinfo="percent+label",
                    texttemplate="<b>%{label}</b><br><b>%{percent}</b>",
                    insidetextorientation="horizontal",
                    sort=False,
                    direction="clockwise",
                    rotation=93,
                    domain={"x": [0.15, 0.85], "y": [0.15, 0.85]},
                    marker=dict(line=dict(color="#0B1220", width=0.8)),
                )
                fig_sexo.update_layout(
                    template="plotly_dark",
                    legend_title_text="",
                    margin=dict(l=10, r=10, t=50, b=10),
                )
                st.plotly_chart(fig_sexo, use_container_width=True)
            with c2:
                raca_tbl = (
                    raca_div.value_counts().rename_axis("Raça").reset_index(name="Quantidade")
                    .sort_values("Quantidade", ascending=True)
                )
                fig_raca = px.bar(
                    raca_tbl,
                    x="Quantidade",
                    y="Raça",
                    orientation="h",
                    title="Distribuição por Raça",
                    color="Quantidade",
                    color_continuous_scale="Blues",
                    text="Quantidade",
                )
                fig_raca.update_layout(
                    template="plotly_dark",
                    coloraxis_showscale=False,
                    margin=dict(l=10, r=10, t=50, b=10),
                )
                fig_raca.update_traces(
                    textposition=_bar_textpos_for_count(len(raca_tbl)),
                    texttemplate="<b>%{text}</b>",
                )
                st.plotly_chart(fig_raca, use_container_width=True)

            c3, c4 = st.columns(2)
            with c3:
                nac_tbl = (
                    nac_div.value_counts().rename_axis("Nacionalidade").reset_index(name="Quantidade")
                    .sort_values("Quantidade", ascending=False)
                )
                fig_nac = px.bar(
                    nac_tbl.head(10),
                    x="Nacionalidade",
                    y="Quantidade",
                    title="Nacionalidade",
                    color="Quantidade",
                    color_continuous_scale="Blues",
                    text="Quantidade",
                )
                fig_nac.update_layout(
                    template="plotly_dark",
                    coloraxis_showscale=False,
                    margin=dict(l=10, r=10, t=50, b=10),
                )
                fig_nac.update_traces(
                    textposition=_bar_textpos_for_count(len(nac_tbl.head(10))),
                    texttemplate="<b>%{text}</b>",
                )
                st.plotly_chart(fig_nac, use_container_width=True)
            with c4:
                estado_tbl = (
                    estado_div.value_counts().rename_axis("Estado civil").reset_index(name="Quantidade")
                    .sort_values("Quantidade", ascending=True)
                )
                fig_estado = px.bar(
                    estado_tbl,
                    x="Quantidade",
                    y="Estado civil",
                    orientation="h",
                    title="Estado Civil",
                    color="Quantidade",
                    color_continuous_scale="Blues",
                    text="Quantidade",
                )
                fig_estado.update_layout(
                    template="plotly_dark",
                    coloraxis_showscale=False,
                    margin=dict(l=10, r=10, t=50, b=10),
                )
                fig_estado.update_traces(
                    textposition=_bar_textpos_for_count(len(estado_tbl)),
                    texttemplate="<b>%{text}</b>",
                )
                st.plotly_chart(fig_estado, use_container_width=True)

            st.divider()
            st.subheader("Diversidade (detalhado)")

            def _serie_texto_div(dframe: pd.DataFrame, col: Optional[str]) -> pd.Series:
                if not col or col not in dframe.columns:
                    return pd.Series("NÃO INFORMADO", index=dframe.index)
                return (
                    dframe[col]
                    .astype(str)
                    .str.strip()
                    .replace({"": "NÃO INFORMADO", "nan": "NÃO INFORMADO", "None": "NÃO INFORMADO"})
                )

            blocos: dict[str, pd.Series] = {}
            if col_colab and col_colab in div.columns:
                blocos["Colaborador"] = _serie_texto_div(div, col_colab)
            blocos["Equipe"] = _serie_texto_div(div, col_eq)
            blocos["Cargo"] = _serie_texto_div(div, col_cargo)
            blocos["Gênero"] = _serie_texto_div(div, col_sexo)
            blocos["Raça"] = _serie_texto_div(div, col_raca)
            blocos["Nacionalidade"] = _serie_texto_div(div, col_nac)
            blocos["Estado civil"] = _serie_texto_div(div, col_estado)
            blocos["Grau de instrução"] = _serie_texto_div(div, col_instr)
            blocos["Vínculo empregatício"] = _serie_texto_div(div, col_vinc)
            if col_hier and col_hier in div.columns:
                blocos["Nível hierárquico"] = _serie_texto_div(div, col_hier)
            if col_pcd and col_pcd in div.columns:
                blocos["PCD / tipo deficiência"] = _serie_texto_div(div, col_pcd)
            if col_idade and col_idade in div.columns:
                idade_num = pd.to_numeric(div[col_idade], errors="coerce")
                blocos["Idade (anos)"] = idade_num.round(0).astype("Int64")
            if col_tempo and col_tempo in div.columns:
                tempo_num = pd.to_numeric(div[col_tempo], errors="coerce")
                blocos["Tempo de empresa (meses)"] = tempo_num.round(1)

            detalhe_div = pd.DataFrame(blocos)
            detalhe_div = detalhe_div.sort_values(
                by=["Colaborador"] if "Colaborador" in detalhe_div.columns else list(detalhe_div.columns)[:1],
                ascending=[True],
            )

            filtro_cols_div_det = {c: c for c in detalhe_div.columns}
            ddet1, ddet2 = st.columns(2)
            with ddet1:
                col_filtro_div_det_label = st.selectbox(
                    "1) Escolha a coluna para filtrar",
                    options=list(filtro_cols_div_det.keys()),
                    index=0,
                    key="demog_div_filtro_coluna_detalhe",
                )
            col_filtro_div_det = filtro_cols_div_det[col_filtro_div_det_label]
            valores_disp_div_det = sorted(
                {
                    v
                    for v in detalhe_div[col_filtro_div_det]
                    .dropna()
                    .astype(str)
                    .str.strip()
                    .unique()
                    .tolist()
                    if str(v).strip()
                }
            )
            with ddet2:
                valores_sel_div_det = st.multiselect(
                    f"2) Filtrar itens de {col_filtro_div_det_label}",
                    options=valores_disp_div_det,
                    default=[],
                    key="demog_div_filtro_valores_detalhe",
                    placeholder="",
                )
            if valores_sel_div_det:
                # Comparar como string para incluir idade/tempo exibidos
                mask_f = (
                    detalhe_div[col_filtro_div_det]
                    .astype(str)
                    .str.strip()
                    .isin([str(x).strip() for x in valores_sel_div_det])
                )
                detalhe_div = detalhe_div.loc[mask_f].copy()

            st.dataframe(
                detalhe_div,
                hide_index=True,
                use_container_width=True,
                key="demog_diversidade_detalhado",
            )

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
    help_matriz_solicitacoes = (
        "Fonte: `administracao.Jira_projeto_dho_consolidado`, com o mesmo recorte de cada quadro "
        "do acompanhamento Kanban. **Aguardando atendimento**: status *Backlog*. **Em andamento**: demais etapas do fluxo "
        "até conclusão ou rejeição. **Concluídas**: *Finalizado* (também Done, Closed, Resolvido). "
        "**Rejeitadas**: *Rejeitado* (ou Rejected)."
    )
    st.subheader("Matriz de solicitações por quadro", help=help_matriz_solicitacoes)
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
            vagas_finalizadas=("Situação da vaga", lambda s: int((s == "Finalizada").sum())),
            vagas_abertas=("Situação da vaga", lambda s: int((s != "Finalizada").sum())),
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
            "vagas_abertas": "Vagas abertas",
            "tempo_fechamento_medio": "Tempo de aprovação (média)",
            "tempo_aprovacao_medio": "Tempo até aceite candidato (média)",
            "tempo_total_contratacao_medio": "Tempo total de processo (média)",
        }
    )
    grp = grp.sort_values(
        by=["Vagas finalizadas", "Vagas abertas", "Cargo"], ascending=[False, False, True]
    ).reset_index(drop=True)
    return grp


def render_jira_requisicao_vaga_tempos() -> None:
    """Tempos médios no quadro RC para vagas finalizadas e abertas."""
    help_requisicao_tempos = (
        "Somente o quadro **Requisição de vaga (RC)**. "
        "**Início**: *Start date*; se ausente, *Data de início*. "
        "**Tempo de aprovação**: do início até **Data de aprovação**. "
        "**Tempo até aceite candidato**: do início até **Data de fechamento**; se a **Data finalização** "
        "for anterior (processo já encerrado, mas fechamento preenchido depois no Jira), usa-se a **Data finalização** "
        "como data final desse prazo. "
        "**Tempo total de processo**: do início até **Data finalização**. Para vagas abertas, usa-se **a data atual**, "
        "exceto em **Rejeitadas** sem finalização (usa a última data disponível ou não calcula se não houver data). "
        "Cálculo em **dias corridos**.\n\n"
        "**Filtros**: período por **data de referência** da vaga. "
        "Para vagas finalizadas: **Data finalização**. Para vagas abertas: **Início** (*Start date* / *Data de início*). "
        "Opcional: **Supervisão**."
    )
    st.subheader("Requisição de vagas — tempos", help=help_requisicao_tempos)
    df = load_jira_dho_acompanhamento()
    tbl = compute_requisicao_vaga_tempos_table(df)
    if tbl.empty:
        st.info(
            "Nenhuma requisição de vaga encontrada, ou faltam colunas de data/início "
            "para calcular os tempos."
        )
        return

    ts_ini_tbl = pd.to_datetime(tbl["Início"], errors="coerce")
    ts_finalizacao_tbl = pd.to_datetime(tbl["Data finalização"], errors="coerce")
    is_finalizada = tbl["Situação da vaga"].astype(str).str.strip().eq("Finalizada")
    data_ref_filtro = ts_finalizacao_tbl.where(is_finalizada, ts_ini_tbl).fillna(ts_ini_tbl)

    dates_ref = data_ref_filtro.dropna()
    if dates_ref.empty:
        d_range_lo = date.today() - timedelta(days=365)
        d_range_hi = date.today()
    else:
        d_range_lo = dates_ref.min().date()
        d_range_hi = dates_ref.max().date()

    f1, f2, f3, f4 = st.columns(4)
    with f1:
        situacao_opts = ["Finalizada", "Aberta"]
        situacao_sel = st.multiselect(
            "Situação da vaga",
            options=situacao_opts,
            default=[],
            key="ind_rh_req_vaga_filtro_situacao",
            placeholder="Todas",
        )
    with f2:
        sup_opts = sorted(
            {v for v in tbl["Supervisão"].astype(str).str.strip().unique() if v},
            key=lambda x: x.lower(),
        )
        sup_sel = st.multiselect(
            "Supervisão",
            options=sup_opts,
            default=[],
            key="ind_rh_req_vaga_filtro_sup",
            placeholder="Todas",
        )
    with f3:
        filtro_ini = st.date_input(
            "Data de início",
            value=d_range_lo,
            min_value=d_range_lo,
            max_value=d_range_hi,
            key="ind_rh_req_vaga_filtro_ini",
        )
    with f4:
        filtro_fim = st.date_input(
            "Data de fim",
            value=d_range_hi,
            min_value=d_range_lo,
            max_value=d_range_hi,
            key="ind_rh_req_vaga_filtro_fim",
        )

    if filtro_ini > filtro_fim:
        st.warning("A data inicial do período é maior que a final; ajuste o filtro.")
        return

    ts_a = pd.Timestamp(filtro_ini).normalize()
    ts_b = pd.Timestamp(filtro_fim).normalize()
    mask_date = (
        data_ref_filtro.notna()
        & (data_ref_filtro.dt.normalize() >= ts_a)
        & (data_ref_filtro.dt.normalize() <= ts_b)
    )
    tbl_f = tbl.loc[mask_date].copy()
    if situacao_sel:
        tbl_f = tbl_f[tbl_f["Situação da vaga"].isin(situacao_sel)]
    if sup_sel:
        sel_norm = {_normalize_text_for_match(v) for v in sup_sel if v}
        sup_norm = tbl_f["Supervisão"].map(_normalize_text_for_match)
        tbl_f = tbl_f[sup_norm.isin(sel_norm)]

    if tbl_f.empty:
        st.info("Nenhuma solicitação no recorte de datas e supervisão selecionados.")
        return

    n1, m1, d1 = _tempo_stats(tbl_f, COL_TEMPO_FECHAMENTO_VAGA)
    n2, m2, d2 = _tempo_stats(tbl_f, COL_TEMPO_APROVACAO_VAGA)
    n3, m3, d3 = _tempo_stats(tbl_f, COL_TEMPO_TOTAL_CONTRATACAO)

    k1, _ = _format_mean_median_dias(n1, m1, d1)
    k2, _ = _format_mean_median_dias(n2, m2, d2)
    k3, _ = _format_mean_median_dias(n3, m3, d3)

    r1, r2, r3 = st.columns(3)
    with r1:
        st.metric("Tempo de aprovação (média)", k1, help="Início → data de aprovação")
    with r2:
        st.metric(
            "Tempo até aceite candidato (média)",
            k2,
            help="Início → data de fechamento; se finalização for mais cedo, usa-se ela como fim.",
        )
    with r3:
        st.metric(
            "Tempo total de processo (média)", k3, help="Início → data finalização (ciclo total)"
        )

    st.subheader(
        "Tempos por cargo",
        help="Média em dias corridos por cargo, com contagem de vagas finalizadas e abertas no período filtrado.",
    )
    tbl_cargo = _build_tempos_por_cargo_table(tbl_f)
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
                "Vagas abertas": st.column_config.NumberColumn(format="%d"),
                "Tempo de aprovação (média)": st.column_config.NumberColumn(format="%.1f"),
                "Tempo até aceite candidato (média)": st.column_config.NumberColumn(format="%.1f"),
                "Tempo total de processo (média)": st.column_config.NumberColumn(format="%.1f"),
            },
        )

    st.subheader("Detalhamento por solicitação")
    num_cfg = st.column_config.NumberColumn(format="%d")
    st.dataframe(
        tbl_f,
        hide_index=True,
        use_container_width=True,
        key="ind_rh_req_vaga_tempos_tbl",
        column_config={
            COL_TEMPO_FECHAMENTO_VAGA: num_cfg,
            COL_TEMPO_APROVACAO_VAGA: num_cfg,
            COL_TEMPO_TOTAL_CONTRATACAO: num_cfg,
        },
    )


def render_indicador_atestados() -> None:
    """Atestados a partir da view indicador_de_atestados (início e término do período)."""
    st.subheader("Atestados")
    df = load_indicador_de_atestados()
    if df.empty:
        st.warning("Sem dados em `indicador_de_atestados` ou falha ao consultar o MotherDuck.")
        return

    col_ini = _pick_col(df, ["inicio", "início", "data_inicio", "data_início"])
    col_fim = _pick_col(df, ["t_rmino", "t_termino", "termino", "término", "data_fim", "data_termino"])
    if not col_ini or col_ini not in df.columns:
        st.error("Coluna de início do atestado não encontrada (esperado algo como `inicio`).")
        return
    if not col_fim or col_fim not in df.columns:
        st.error("Coluna de término do atestado não encontrada (esperado algo como `t_rmino`).")
        return

    data_inicio = pd.to_datetime(df[col_ini], errors="coerce").dt.normalize()
    data_fim = pd.to_datetime(df[col_fim], errors="coerce").dt.normalize()

    out = pd.concat(
        [
            pd.DataFrame({"Data início": data_inicio, "Data fim": data_fim}),
            df.reset_index(drop=True),
        ],
        axis=1,
    )

    valid_dates = data_inicio.notna() | data_fim.notna()

    # Limites independentes por coluna (somente datas onde há informação)
    ini_min = data_inicio.dropna().min()
    ini_max = data_inicio.dropna().max()
    fim_min = data_fim.dropna().min()
    fim_max = data_fim.dropna().max()

    # Fallbacks seguros caso uma das colunas venha totalmente vazia
    if pd.isna(ini_min) or pd.isna(ini_max):
        ini_min = fim_min
        ini_max = fim_max
    if pd.isna(fim_min) or pd.isna(fim_max):
        fim_min = ini_min
        fim_max = ini_max

    if pd.notna(ini_min) and pd.notna(ini_max):
        d_ini_min = ini_min.date()
        d_ini_max = ini_max.date()
    else:
        d_ini_min = date.today() - timedelta(days=365)
        d_ini_max = date.today()

    if pd.notna(fim_min) and pd.notna(fim_max):
        d_fim_min = fim_min.date()
        d_fim_max = fim_max.date()
    else:
        d_fim_min = date.today() - timedelta(days=365)
        d_fim_max = date.today()

    # Filtros: (Equipe/Motivo) em 2 etapas + período (datas por último)
    r1, r2, r3, r4 = st.columns(4)

    col_equipe = _pick_col(df, ["equipe", "time", "team"])
    col_motivo_raw = _pick_col(df, ["motivo", "motivo_do_atestado", "tipo", "tipo_atestado"])
    col_colaborador = _pick_col(df, ["colaborador", "funcionario", "colab", "nome", "nome_colaborador"])
    filtros_extra: dict[str, str] = {}
    if col_equipe and col_equipe in out.columns:
        filtros_extra["Equipe"] = col_equipe
    if col_motivo_raw and col_motivo_raw in out.columns:
        filtros_extra["Motivo"] = col_motivo_raw
    if col_colaborador and col_colaborador in out.columns:
        filtros_extra["Colaborador"] = col_colaborador

    with r1:
        if filtros_extra:
            filtro_extra_label = st.selectbox(
                "1) Escolha o filtro",
                options=list(filtros_extra.keys()),
                index=0,
                key="atestados_filtro_extra_coluna",
            )
        else:
            filtro_extra_label = ""
            st.selectbox("1) Escolha o filtro", options=["—"], index=0, key="atestados_filtro_extra_coluna_disabled")

    filtro_extra_vals: list[str] = []
    with r2:
        if filtros_extra and filtro_extra_label:
            col_extra = filtros_extra[filtro_extra_label]
            opts_extra = sorted(
                [
                    v
                    for v in out[col_extra].dropna().astype(str).str.strip().unique().tolist()
                    if v
                ]
            )
            filtro_extra_vals = st.multiselect(
                f"2) Filtrar itens de {filtro_extra_label}",
                options=opts_extra,
                default=[],
                key="atestados_filtro_extra_valores",
                placeholder="Todos",
            )
        else:
            st.multiselect(
                "2) Filtrar itens",
                options=[],
                default=[],
                key="atestados_filtro_extra_valores_disabled",
                placeholder="—",
            )

    with r3:
        filtro_ini = st.date_input(
            "Filtrar a partir de (data início do atestado)",
            value=d_ini_min,
            min_value=d_ini_min,
            max_value=d_ini_max,
            key="atestados_filtro_data_ini",
        )
    with r4:
        filtro_fim = st.date_input(
            "Filtrar até (data fim do atestado)",
            value=d_fim_max,
            min_value=d_fim_min,
            max_value=d_fim_max,
            key="atestados_filtro_data_fim",
        )

    if filtro_ini > filtro_fim:
        st.warning("A data inicial do filtro é maior que a final; ajuste os valores.")
    else:
        ts_a = pd.Timestamp(filtro_ini).normalize()
        ts_b = pd.Timestamp(filtro_fim).normalize()

        # Filtro por coluna correspondente (com fallback quando houver apenas uma das datas):
        # - início: usa data_inicio; se ausente, usa data_fim
        # - fim: usa data_fim; se ausente, usa data_inicio
        inicio_ref = data_inicio.fillna(data_fim)
        fim_ref = data_fim.fillna(data_inicio)

        mask_periodo = (
            valid_dates
            & inicio_ref.notna()
            & fim_ref.notna()
            & (inicio_ref >= ts_a)
            & (fim_ref <= ts_b)
        )
        mask_final = mask_periodo.copy()
        if filtros_extra and filtro_extra_label and filtro_extra_vals:
            col_extra = filtros_extra[filtro_extra_label]
            s_extra = out[col_extra].astype(str).str.strip()
            mask_final &= s_extra.isin([str(x).strip() for x in filtro_extra_vals])

        out_f = out.loc[mask_final].copy() if mask_final.any() else out.iloc[0:0].copy()

        if out_f.empty and not out.empty:
            st.info("Nenhum atestado intersecta o período selecionado ou as linhas não têm datas válidas em início/término.")

        # Vamos organizar os KPIs em apenas 2 blocos:
        # 1) Quantidades (total + por motivo)
        # 2) Horas (total + por motivo)

        # Total de horas (regras):
        # - Se houver hora_inicio E hora_t_rmino, usa diferença entre horas.
        # - Se faltar uma das horas, ignora horas e usa datas (inicio/t_rmino).
        # - Se inicio e t_rmino forem no mesmo dia e sem horas completas, considera 8h48 (8.8h).
        # - Exclui do cálculo motivo "afastamento INSS".
        horas_final: Optional[pd.Series] = None
        total_horas = 0.0
        if not out_f.empty:
            col_motivo_calc = _pick_col(out_f, ["motivo", "motivo_do_atestado", "tipo", "tipo_atestado"])
            motivo_calc = (
                out_f[col_motivo_calc].astype(str).str.strip().str.lower()
                if col_motivo_calc and col_motivo_calc in out_f.columns
                else pd.Series("", index=out_f.index)
            )
            mask_motivo = ~motivo_calc.isin(["afastamento inss", "afastamento_inss"])

            col_h_ini = _pick_col(out_f, ["hora_inicio", "hora in", "hora início", "hora_incio"])
            col_h_fim = _pick_col(out_f, ["hora_t_rmino", "hora_termino", "hora término", "hora fim", "hora_fim"])

            # Datas já estão em Data início/Data fim (datetime normalizado)
            d_ini = pd.to_datetime(out_f["Data início"], errors="coerce").dt.normalize()
            d_fim = pd.to_datetime(out_f["Data fim"], errors="coerce").dt.normalize()

            # Parsing robusto de hora: tenta extrair HH:MM[:SS] (ou datetime/time)
            def _parse_time_to_seconds(s: pd.Series) -> pd.Series:
                if s is None or s.empty:
                    return pd.Series(float("nan"), index=out_f.index, dtype="float64")
                ss = s.copy()
                # Tenta datetime
                dt = pd.to_datetime(ss, errors="coerce")
                ok_dt = dt.notna()
                out_sec = pd.Series(float("nan"), index=ss.index, dtype="float64")
                if ok_dt.any():
                    out_sec.loc[ok_dt] = (
                        dt.loc[ok_dt].dt.hour * 3600
                        + dt.loc[ok_dt].dt.minute * 60
                        + dt.loc[ok_dt].dt.second
                    ).astype("float64")
                # Fallback: string HH:MM[:SS]
                rem = ~ok_dt
                if rem.any():
                    txt = ss.loc[rem].astype(str).str.strip()
                    parts = txt.str.split(":", expand=True)
                    if parts.shape[1] >= 2:
                        hh = pd.to_numeric(parts[0], errors="coerce")
                        mm = pd.to_numeric(parts[1], errors="coerce")
                        sec = pd.to_numeric(parts[2], errors="coerce") if parts.shape[1] >= 3 else 0
                        out_sec.loc[rem] = (hh * 3600 + mm * 60 + sec).astype("float64")
                return out_sec

            has_h_ini = bool(col_h_ini and col_h_ini in out_f.columns)
            has_h_fim = bool(col_h_fim and col_h_fim in out_f.columns)

            use_horas = pd.Series(False, index=out_f.index)
            horas_por_hora = pd.Series(float("nan"), index=out_f.index, dtype="float64")
            if has_h_ini and has_h_fim:
                h_ini_sec = _parse_time_to_seconds(out_f[col_h_ini])
                h_fim_sec = _parse_time_to_seconds(out_f[col_h_fim])
                use_horas = h_ini_sec.notna() & h_fim_sec.notna()
                delta_sec = (h_fim_sec - h_ini_sec).astype("float64")
                # Se ficar negativo (ex.: virou o dia), soma 24h como fallback.
                delta_sec = delta_sec.mask(delta_sec < 0, delta_sec + 24 * 3600)
                horas_por_hora = (delta_sec / 3600.0).where(use_horas)

            # Quando não usar horas (por falta de uma delas), usa datas
            dias = (d_fim - d_ini).dt.days
            same_day = (dias == 0) & d_ini.notna() & d_fim.notna()
            multi_day = (dias > 0) & d_ini.notna() & d_fim.notna()
            horas_por_data = pd.Series(float("nan"), index=out_f.index, dtype="float64")
            horas_por_data = horas_por_data.mask(same_day, 8.8)
            # Para múltiplos dias: dias corridos inclusivo * 8.8h
            horas_por_data = horas_por_data.mask(multi_day, (dias + 1).astype("float64") * 8.8)

            horas_final = pd.Series(0.0, index=out_f.index, dtype="float64")
            horas_final = horas_final.mask(use_horas, horas_por_hora.fillna(0.0))
            horas_final = horas_final.mask(~use_horas, horas_por_data.fillna(0.0))

            total_horas = float(horas_final[mask_motivo].sum())

        # Matriz por motivo: linhas = motivo; colunas = quantidade e horas
        col_motivo = _pick_col(out_f, ["motivo", "motivo_do_atestado", "tipo", "tipo_atestado"])
        if col_motivo and col_motivo in out_f.columns and not out_f.empty:
            motivo_s = (
                out_f[col_motivo]
                .astype(str)
                .str.strip()
                .replace({"": "NÃO INFORMADO", "nan": "NÃO INFORMADO", "None": "NÃO INFORMADO"})
            )
            qty_by_motivo = motivo_s.value_counts(dropna=False)

            horas_by_motivo = pd.Series(dtype="float64")
            if isinstance(horas_final, pd.Series):
                motivo_key = motivo_s.astype(str).str.strip().str.lower()
                motivo_mask_inss = motivo_key.isin(["afastamento inss", "afastamento_inss"])
                horas_sum = horas_final.where(~motivo_mask_inss, 0.0)
                horas_by_motivo = (
                    pd.DataFrame({"Motivo": motivo_s.astype(str), "Horas": horas_sum})
                    .groupby("Motivo", dropna=False)["Horas"]
                    .sum()
                )

            matriz = (
                pd.DataFrame({"Quantidade": qty_by_motivo})
                .join(horas_by_motivo.rename("Horas"), how="left")
                .fillna({"Horas": 0.0})
                .reset_index()
            )
            # `reset_index()` pode criar a coluna como `index` (ou herdar nome do índice).
            if "Motivo" not in matriz.columns:
                if "index" in matriz.columns:
                    matriz = matriz.rename(columns={"index": "Motivo"})
                else:
                    matriz = matriz.rename(columns={matriz.columns[0]: "Motivo"})
            matriz["Quantidade"] = matriz["Quantidade"].astype(int)
            matriz["Horas"] = pd.to_numeric(matriz["Horas"], errors="coerce").fillna(0.0)
            matriz = matriz.sort_values(["Quantidade", "Motivo"], ascending=[False, True]).reset_index(drop=True)

            total_row = pd.DataFrame(
                [
                    {
                        "Motivo": "TOTAL",
                        "Quantidade": int(matriz["Quantidade"].sum()),
                        "Horas": float(matriz["Horas"].sum()),
                    }
                ]
            )
            matriz_out = pd.concat([matriz, total_row], ignore_index=True)

            _help_horas_atestados = (
                "Regras do cálculo das horas:\n"
                "- Exclui do somatório o motivo **afastamento INSS**.\n"
                "- Se houver **hora_inicio** e **hora_t_rmino** (ambas preenchidas), usa a diferença entre elas.\n"
                "- Se houver somente uma das horas (apenas início ou apenas término), ignora horas e usa o cálculo por datas.\n"
                "- Sem par completo de horas: usa a diferença entre **inicio** e **t_rmino**.\n"
                "- Se **inicio** e **t_rmino** forem no mesmo dia: considera **8h48 (8,8h)**.\n"
                "- Se forem dias diferentes: considera (dias corridos inclusivo) × 8,8h.\n"
                "- Se a diferença por horas ficar negativa (virada de dia), soma 24h como ajuste."
            )
            st.subheader("Matriz por motivo")
            st.dataframe(
                matriz_out,
                hide_index=True,
                use_container_width=True,
                key="ind_rh_atestados_matriz_motivo",
                column_config={
                    "Motivo": st.column_config.TextColumn(width="large"),
                    "Quantidade": st.column_config.NumberColumn(format="%d"),
                    "Horas": st.column_config.NumberColumn(format="%.1f", help=_help_horas_atestados),
                },
            )

        # Detalhamento: remove colunas brutas duplicadas de data (já exibidas como Data início / Data fim)
        tbl_detalhe = out_f.copy()
        cols_drop_raw_dates = [c for c in (col_ini, col_fim) if c and c in tbl_detalhe.columns]
        tbl_detalhe = tbl_detalhe.drop(columns=cols_drop_raw_dates, errors="ignore")

        # Rótulos padrão (só quando o nome da coluna bate exatamente com a origem)
        _rename_atestados = {
            "hora_inicio": "Hora início",
            "hora_t_rmino": "Hora término",
            "motivo": "Motivo",
            "equipe": "Equipe",
            "colaborador": "Colaborador",
        }
        ren_exist = {k: v for k, v in _rename_atestados.items() if k in tbl_detalhe.columns and v not in tbl_detalhe.columns}
        tbl_detalhe = tbl_detalhe.rename(columns=ren_exist)

        # data criação (nome legado na planilha / DuckDB)
        for c in list(tbl_detalhe.columns):
            n = _norm_txt(c)
            if n in (
                _norm_txt("data_cria_o"),
                _norm_txt("datt_cria_o"),  # legado / typo
            ):
                tbl_detalhe = tbl_detalhe.rename(columns={c: "Data criação"})
                break

        def _series_somente_hora(s: pd.Series) -> pd.Series:
            """Exibe apenas HH:MM (remove data fictícia tipo 1900-01-01)."""
            dt = pd.to_datetime(s, errors="coerce")
            out = dt.dt.strftime("%H:%M")
            return out.where(dt.notna(), "")

        for col_h in ("Hora início", "Hora término"):
            if col_h in tbl_detalhe.columns:
                tbl_detalhe[col_h] = _series_somente_hora(tbl_detalhe[col_h])

        pri = ["Data início", "Data fim"]
        rest = [c for c in tbl_detalhe.columns if c not in pri]
        tbl_detalhe = tbl_detalhe[pri + rest]

        # Ordenar pelo início (mais antigo -> mais novo)
        if "Data início" in tbl_detalhe.columns:
            _dt_ini = pd.to_datetime(tbl_detalhe["Data início"], errors="coerce")
            tbl_detalhe = (
                tbl_detalhe.assign(**{"__dt_ini_sort": _dt_ini})
                .sort_values("__dt_ini_sort", ascending=True, na_position="last")
                .drop(columns=["__dt_ini_sort"])
            )

        st.subheader("Detalhamento")
        st.dataframe(
            tbl_detalhe,
            hide_index=True,
            use_container_width=True,
            key="ind_rh_atestados_tbl",
            column_config={
                "Data início": st.column_config.DatetimeColumn(format="DD/MM/YYYY"),
                "Data fim": st.column_config.DatetimeColumn(format="DD/MM/YYYY"),
            },
        )


def render_indicadores_rh_dashboard(
    show_title: bool = True,
    show_caption: bool = True,
) -> None:
    """Renderiza indicadores de gestão de pessoas (Jira + atestados + demografia)."""
    tab_jira, tab_atest, tab_tec = st.tabs(["Solicitações (Jira)", "Atestados", "Demografia"])

    with tab_jira:
        render_jira_matriz_solicitacoes_por_quadro()
        st.divider()
        render_jira_requisicao_vaga_tempos()

    with tab_atest:
        render_indicador_atestados()

    with tab_tec:
        _render_demografia_rh()
