"""
Indicadores Jurídico (Jira - projeto JRD)

Base: view administracao.Jira_projeto_juridico_consolidado
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, List, Optional

import pandas as pd
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

    # Filtros rápidos (tipo/obra) na sidebar
    with st.sidebar:
        st.markdown("### 🔎 Filtros (Jurídico)")
        df_f = df_raw.copy()

        def _ms(label: str, col: str, key: str) -> List[str]:
            if not col or col not in df_f.columns:
                return []
            opts = sorted(
                {
                    v
                    for v in df_f[col].dropna().astype(str).str.strip().tolist()
                    if v and v.lower() not in {"none", "nan", "nat", "<na>"}
                }
            )
            return st.multiselect(label, options=opts, default=[], key=key, placeholder="")

        sel_tipo = _ms("Tipo de contrato", tipo_contrato_col, "jur_ind_tipo") if tipo_contrato_col else []
        sel_obra = _ms("Obra", obra_col, "jur_ind_obra") if obra_col else []
        if sel_tipo and tipo_contrato_col:
            df_f = df_f[df_f[tipo_contrato_col].astype(str).str.strip().isin(sel_tipo)]
        if sel_obra and obra_col:
            df_f = df_f[df_f[obra_col].astype(str).str.strip().isin(sel_obra)]

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
                fin["Mês"] = fin["_dt_fech"].dt.to_period("M").astype(str)
                fin["Tipo de contrato"] = (
                    fin[tipo_contrato_col].astype(str).str.strip() if tipo_contrato_col else "Não informado"
                )
                fin["Motivo"] = fin[motivo_col].astype(str).str.strip() if motivo_col else "Não informado"
                fin["Área"] = fin[area_col_ind].astype(str).str.strip() if area_col_ind else "Não informado"
                fin["Empreendimento"] = fin[emp_col_ind].astype(str).str.strip() if emp_col_ind else "Não informado"
                for c in ["Tipo de contrato", "Motivo", "Área", "Empreendimento"]:
                    fin[c] = fin[c].replace({"": "Não informado", "nan": "Não informado", "None": "Não informado"})

                # Gráfico de evolução mensal
                st.markdown("##### Evolução Mensal")
                df_mes = fin.groupby("Mês").size().reset_index(name="Qtd").sort_values("Mês")
                st.bar_chart(df_mes.set_index("Mês"), y="Qtd")

                st.markdown("##### Detalhamento do Período")
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.markdown("**📍 Por Motivo**")
                    df_motivo = (
                        fin.groupby("Motivo")
                        .size()
                        .reset_index(name="Qtd")
                        .sort_values("Qtd", ascending=False)
                    )
                    st.dataframe(df_motivo, hide_index=True, use_container_width=True, key="jur_ind_fin_motivo")

                with col2:
                    st.markdown("**🏢 Por Área**")
                    df_area = (
                        fin.groupby("Área")
                        .size()
                        .reset_index(name="Qtd")
                        .sort_values("Qtd", ascending=False)
                    )
                    st.dataframe(df_area, hide_index=True, use_container_width=True, key="jur_ind_fin_area")

                with col3:
                    st.markdown("**🏗️ Por Empreendimento**")
                    fin_emp = fin.assign(
                        **{
                            "Empreendimento": fin["Empreendimento"].map(_empreendimento_label_tabela),
                        }
                    )
                    df_emp = (
                        fin_emp.groupby("Empreendimento")
                        .size()
                        .reset_index(name="Qtd")
                        .sort_values("Qtd", ascending=False)
                    )
                    st.dataframe(df_emp, hide_index=True, use_container_width=True, key="jur_ind_fin_emp")

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

