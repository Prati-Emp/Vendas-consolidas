"""
Dashboard de Indicadores de Gestão de Pessoas —
solicitações (Jira DHO) e indicadores operacionais (views Tecsmart no MotherDuck).
"""

from __future__ import annotations

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
    compute_requisicao_vaga_tempos_table,
    compute_solicitacoes_matrix_by_quadro,
    load_jira_dho_acompanhamento,
)
from dashboard.utils.md_conn import get_md_connection

TEC_CONSOLIDADO = "administracao.Tecsmart_indicadores"
TEC_EQUIPE = "administracao.Tecsmart_indicadores_equipe"
TEC_FILIAL = "administracao.Tecsmart_indicadores_filial"
FUNC_GERAL_RH = "administracao.funcionario_geral_rh_consolidado"

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

        f1, f2, f3 = st.columns(3)
        with f1:
            sexo_sel_resumo = st.multiselect(
                "Sexo",
                options=sorted(sexo_g.unique().tolist()),
                default=[],
                key="resumo_filtro_sexo",
                placeholder="Todos",
            )
        with f2:
            raca_sel_resumo = st.multiselect(
                "Raça",
                options=sorted(raca_g.unique().tolist()),
                default=[],
                key="resumo_filtro_raca",
                placeholder="Todos",
            )
        with f3:
            hier_sel_resumo = st.multiselect(
                "Nível hierárquico",
                options=sorted(hier_g.unique().tolist()),
                default=[],
                key="resumo_filtro_hierarquia",
                placeholder="Todos",
            )

        f4, f5 = st.columns(2)
        with f4:
            cargo_sel_resumo = st.multiselect(
                "Cargo",
                options=sorted(cargo_g.unique().tolist()),
                default=[],
                key="resumo_filtro_cargo",
                placeholder="Todos",
            )
        with f5:
            equipe_sel_resumo = st.multiselect(
                "Equipe",
                options=sorted(equipe_g.unique().tolist()),
                default=[],
                key="resumo_filtro_equipe",
                placeholder="Todos",
            )

        mask_resumo = pd.Series(True, index=df.index)
        if sexo_sel_resumo:
            mask_resumo &= sexo_g.isin(sexo_sel_resumo)
        if raca_sel_resumo:
            mask_resumo &= raca_g.isin(raca_sel_resumo)
        if hier_sel_resumo:
            mask_resumo &= hier_g.isin(hier_sel_resumo)
        if cargo_sel_resumo:
            mask_resumo &= cargo_g.isin(cargo_sel_resumo)
        if equipe_sel_resumo:
            mask_resumo &= equipe_g.isin(equipe_sel_resumo)

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
                    bins=[-1, 6, 12, 24, 60, 9999],
                    labels=[
                        "0-6m",
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
                bins=[-1, 6, 12, 24, 60, 9999],
                labels=["0-6m", "1 ano", "1-2 anos", "2-5 anos", "5+ anos"],
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
            exp_end = exp1.fillna(exp2)
            status = pd.Series("Não informado", index=df.index)
            today = pd.Timestamp.today().normalize()
            status = status.mask(exp_end.notna() & (exp_end >= today), "Em experiência")
            status = status.mask(exp_end.notna() & (exp_end < today), "Encerrado")
            tbl = status.value_counts().rename_axis("Situação").reset_index(name="Quantidade")
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
            .div-kpi-card { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.10); border-radius: 12px; padding: 10px 12px; min-height: 78px; display:flex; flex-direction:column; justify-content:center; }
            .div-kpi-title { font-size: 12px; color: #cbd5e1; margin-bottom: 4px; }
            .div-kpi-value { font-size: 32px; line-height: 1.1; font-weight: 700; color: #f8fafc; word-break: break-word; }
            .div-kpi-sub { font-size: 18px; line-height: 1.2; font-weight: 600; color: #f8fafc; }
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

        sexo_opts = sorted(sexo_s.unique().tolist())
        nac_opts = sorted(nac_s.unique().tolist())
        raca_opts = sorted(raca_s.unique().tolist())
        vinc_opts = sorted(vinc_s.unique().tolist())
        instr_opts = sorted(instr_s.unique().tolist())
        eq_opts = sorted(eq_s.unique().tolist())
        cargo_opts = sorted(cargo_s.unique().tolist())

        d1, d2, d3, d4 = st.columns(4)
        with d1:
            sexo_sel = st.multiselect(
                "Gênero",
                options=sexo_opts,
                default=[],
                key="filtro_unico_sexo",
                placeholder="Todos",
            )
        with d2:
            nac_sel = st.multiselect(
                "Nacionalidade",
                options=nac_opts,
                default=[],
                key="filtro_unico_nacionalidade",
                placeholder="Todos",
            )
        with d3:
            raca_sel = st.multiselect(
                "Raça",
                options=raca_opts,
                default=[],
                key="filtro_unico_raca",
                placeholder="Todos",
            )
        with d4:
            vinc_sel = st.multiselect(
                "Vínculo empregatício",
                options=vinc_opts,
                default=[],
                key="filtro_unico_vinculo",
                placeholder="Todos",
            )
        e1, e2, e3 = st.columns(3)
        with e1:
            instr_sel = st.multiselect(
                "Grau de instrução",
                options=instr_opts,
                default=[],
                key="filtro_unico_instrucao",
                placeholder="Todos",
            )
        with e2:
            eq_sel = st.multiselect(
                "Equipe",
                options=eq_opts,
                default=[],
                key="filtro_unico_equipe",
                placeholder="Todos",
            )
        with e3:
            cargo_sel = st.multiselect(
                "Cargo",
                options=cargo_opts,
                default=[],
                key="filtro_unico_cargo",
                placeholder="Todos",
            )

        sexo_mask = sexo_s.isin(sexo_sel) if sexo_sel else pd.Series(True, index=df_div.index)
        nac_mask = nac_s.isin(nac_sel) if nac_sel else pd.Series(True, index=df_div.index)
        raca_mask = raca_s.isin(raca_sel) if raca_sel else pd.Series(True, index=df_div.index)
        vinc_mask = vinc_s.isin(vinc_sel) if vinc_sel else pd.Series(True, index=df_div.index)
        instr_mask = instr_s.isin(instr_sel) if instr_sel else pd.Series(True, index=df_div.index)
        eq_mask = eq_s.isin(eq_sel) if eq_sel else pd.Series(True, index=df_div.index)
        cargo_mask = cargo_s.isin(cargo_sel) if cargo_sel else pd.Series(True, index=df_div.index)
        mask = sexo_mask & nac_mask & raca_mask & vinc_mask & instr_mask & eq_mask & cargo_mask
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
                    <div class="div-kpi-value">{instr_top}: {f"{instr_top_pct:.1f}%".replace(".", ",")}</div>
                  </div>
                  <div class="div-kpi-card">
                    <div class="div-kpi-title">🌍 Nacionalidade predominante</div>
                    <div class="div-kpi-value">{nac_top}: {f"{nac_top_pct:.1f}%".replace(".", ",")}</div>
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
            _render_estrutura_dashboard(div, col_vinc, col_eq, col_cargo, col_instr)

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
    tab_jira, tab_tec = st.tabs(["Solicitações (Jira)", "Demografia"])

    with tab_jira:
        render_jira_matriz_solicitacoes_por_quadro()
        st.divider()
        render_jira_requisicao_vaga_tempos()

    with tab_tec:
        _render_demografia_rh()
