"""
Indicadores Jurídico (Jira - projeto JRD)

Base: view administracao.Jira_projeto_juridico_consolidado
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, List, Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.utils.md_conn import get_md_connection
from advanced_auth import get_current_user


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


def _plot_juridico_hbar_qtd(title: str, df: pd.DataFrame, label_col: str, *, max_categorias: int = 30) -> go.Figure:
    """
    Barras horizontais (tema escuro, barras azuis), quantidade no fim da barra — alinhado ao estilo «funil» de reservas.
    """
    if df.empty or label_col not in df.columns:
        fig = go.Figure()
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0E1117",
            plot_bgcolor="#0E1117",
            title=dict(text=title, font=dict(size=14, color="#FAFAFA")),
            height=200,
            margin=dict(l=8, r=8, t=48, b=8),
        )
        return fig

    d = df.sort_values("Qtd", ascending=True).tail(max_categorias).copy()
    raw_lbl = d[label_col].astype(str).str.strip()
    labels = raw_lbl.apply(lambda s: (s[:46] + "…") if len(s) > 47 else s)
    qty = d["Qtd"].astype(int)

    fig = go.Figure(
        go.Bar(
            x=qty,
            y=labels,
            orientation="h",
            marker=dict(color="#4FC3F7", line=dict(width=0)),
            text=qty.astype(str),
            textposition="outside",
            textfont=dict(color="#ECEFF1", size=11),
            cliponaxis=False,
            hovertemplate="%{y}<br>Qtd: %{x}<extra></extra>",
        )
    )
    x_max = int(qty.max()) if len(qty) else 1
    dtick = max(1, x_max // 6) if x_max > 6 else 1
    h = min(640, max(200, 26 * len(labels) + 110))
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0E1117",
        plot_bgcolor="#0E1117",
        title=dict(text=title, font=dict(size=14, color="#FAFAFA")),
        margin=dict(l=8, r=52, t=52, b=36),
        height=h,
        xaxis=dict(
            title="Qtd",
            gridcolor="#30363D",
            zeroline=False,
            dtick=dtick,
            range=[0, x_max * 1.18] if x_max else None,
        ),
        yaxis=dict(title="", automargin=True, tickfont=dict(size=11, color="#E0E0E0")),
        showlegend=False,
        bargap=0.32,
    )
    return fig


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

    # Sidebar: apenas intervalo por Data de fechamento (afeta todo o painel)
    with st.sidebar:
        st.markdown("### 🔎 Filtros (Jurídico)")
        df_f = df_raw.copy()
        if not data_fechamento_col:
            st.warning("Coluna **Data de fechamento** não encontrada; filtro de período indisponível.")
        else:
            _dt_side = pd.to_datetime(df_f[data_fechamento_col], errors="coerce")
            _dt_valid = _dt_side.dropna()
            if _dt_valid.empty:
                st.info("Não há datas de fechamento preenchidas para filtrar.")
            else:
                d_lo = _dt_valid.min().normalize().date()
                d_hi = _dt_valid.max().normalize().date()
                ds = st.date_input(
                    "Data de fechamento — início",
                    value=d_lo,
                    min_value=d_lo,
                    max_value=d_hi,
                    key="jur_ind_fechamento_inicio",
                    help="Primeiro dia do intervalo (inclusivo).",
                )
                de = st.date_input(
                    "Data de fechamento — fim",
                    value=d_hi,
                    min_value=d_lo,
                    max_value=d_hi,
                    key="jur_ind_fechamento_fim",
                    help="Último dia do intervalo (inclusivo).",
                )
                ts_a = pd.Timestamp(ds).normalize()
                ts_b = pd.Timestamp(de).normalize()
                if ts_a > ts_b:
                    ts_a, ts_b = ts_b, ts_a
                _mask_dt = _dt_side.notna() & (_dt_side.dt.normalize() >= ts_a) & (_dt_side.dt.normalize() <= ts_b)
                df_f = df_f.loc[_mask_dt].copy()

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
                sm = list(st.session_state.get(_k_m, []) or [])
                sa = list(st.session_state.get(_k_a, []) or [])
                se = list(st.session_state.get(_k_e, []) or [])
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

                st.session_state[_k_m] = sm
                st.session_state[_k_a] = sa
                st.session_state[_k_e] = se

                st.markdown("##### Detalhamento do Período")
                st.caption(
                    "Filtros em conjunto nas tabelas e nos gráficos de barras. **As opções de cada lista já respeitam o que foi "
                    "escolhido nos outros filtros** (apenas combinações que existem na base)."
                )
                f1, f2, f3 = st.columns(3)
                with f1:
                    sel_mot_det = st.multiselect(
                        "📍 Por Motivo",
                        options=mot_opts,
                        key=_k_m,
                        placeholder="Todos",
                    )
                with f2:
                    sel_area_det = st.multiselect(
                        "🏢 Por Área",
                        options=area_opts,
                        key=_k_a,
                        placeholder="Todos",
                    )
                with f3:
                    sel_emp_det = st.multiselect(
                        "🏗️ Por Empreendimento",
                        options=emp_opts,
                        key=_k_e,
                        placeholder="Todos",
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
                            df_motivo,
                            hide_index=True,
                            use_container_width=True,
                            key="jur_ind_fin_motivo",
                        )

                with col2:
                    if fin_f.empty:
                        st.info("Sem registros para os filtros atuais.")
                    else:
                        st.dataframe(
                            df_area,
                            hide_index=True,
                            use_container_width=True,
                            key="jur_ind_fin_area",
                        )

                with col3:
                    if fin_f.empty:
                        st.info("Sem registros para os filtros atuais.")
                    else:
                        st.dataframe(
                            df_emp,
                            hide_index=True,
                            use_container_width=True,
                            key="jur_ind_fin_emp",
                        )

                st.markdown("##### Distribuição (barras horizontais)")
                if fin_f.empty:
                    st.info("Sem dados para os gráficos com os filtros atuais.")
                else:
                    st.caption(
                        "Mesmos totais das tabelas acima. Até **30** categorias por gráfico (maiores quantidades). "
                        "Quantidade exibida ao fim de cada barra."
                    )
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

    # 2) Tempo de elaboração (proxy: hoje ou data limite - start_date) por tipo contrato
    with tab2:
        st.subheader("⏳ Tempo de elaboração (dias) por tipo de contrato")
        if not created_col:
            st.info("Coluna de início/criação não encontrada (Start_date/Criado em).")
        else:
            start_dt = pd.to_datetime(df_f[created_col], errors="coerce")
            end_dt = pd.Timestamp.today().normalize()
            if duedate_col and duedate_col in df_f.columns:
                # usa data limite quando existir, senão hoje (proxy simples)
                due = pd.to_datetime(df_f[duedate_col], errors="coerce").dt.normalize()
                end_series = due.fillna(end_dt)
            else:
                end_series = pd.Series(end_dt, index=df_f.index)
            dias = (end_series - start_dt.dt.normalize()).dt.days
            dias = dias.where(dias.notna() & (dias >= 0))

            tipo_series = df_f[tipo_contrato_col].astype(str).str.strip() if tipo_contrato_col else pd.Series("Não informado", index=df_f.index)
            tbl_tempo = (
                pd.DataFrame({"Tipo de contrato": tipo_series, "Dias": dias})
                .dropna(subset=["Dias"])
                .groupby("Tipo de contrato", dropna=False)["Dias"]
                .agg(Qtd="count", Media="mean", Mediana="median", P90=lambda s: float(s.quantile(0.9)))
                .reset_index()
                .sort_values("Media", ascending=False)
            )
            if tbl_tempo.empty:
                st.info("Sem dados suficientes para calcular tempo de elaboração.")
            else:
                st.dataframe(tbl_tempo, hide_index=True, use_container_width=True, key="jur_ind_tempo_elaboracao")

    # 3) Qtd elaborada e conferida por colaborador (Status = Em elaboração / Conferência)
    with tab3:
        st.subheader("👤 Elaborada vs Conferência por colaborador")
        if not status_col or not responsavel_col:
            st.info("Colunas de Status/Responsável não encontradas.")
        else:
            s_norm = df_f[status_col].astype(str).map(_normalize)
            mask_ec = s_norm.isin({_normalize("Em elaboração"), _normalize("Conferência")})
            ec = df_f.loc[mask_ec].copy()
            if ec.empty:
                st.info("Sem itens em Elaboração/Conferência.")
            else:
                ec["_status"] = ec[status_col].astype(str).str.strip()
                ec["_resp"] = ec[responsavel_col].astype(str).str.strip()
                tbl_ec = (
                    ec.groupby(["_resp", "_status"])
                    .size()
                    .reset_index(name="Qtd")
                    .sort_values(["Qtd"], ascending=False)
                )
                st.dataframe(tbl_ec, hide_index=True, use_container_width=True, key="jur_ind_elab_conf_resp")

    # 4) Qtd rejeitada por contrato e obra
    with tab4:
        st.subheader("❌ Rejeitadas por tipo de contrato e obra")
        if not status_col:
            st.info("Coluna de Status não encontrada.")
        else:
            rej = df_f.loc[df_f[status_col].apply(_status_is_rejeitado)].copy()
            if rej.empty:
                st.info("Sem itens rejeitados.")
            else:
                rej["_tipo"] = rej[tipo_contrato_col].astype(str).str.strip() if tipo_contrato_col else "Não informado"
                rej["_obra"] = rej[obra_col].astype(str).str.strip() if obra_col else "Não informado"
                tbl_rej = (
                    rej.groupby(["_tipo", "_obra"], dropna=False)
                    .size()
                    .reset_index(name="Qtd")
                    .sort_values("Qtd", ascending=False)
                )
                st.dataframe(tbl_rej, hide_index=True, use_container_width=True, key="jur_ind_rejeitados")

