"""
Dashboard de Repasses - Análise de repasses imobiliários.
Foco em quantidade, valor e tempo médio por situação.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.utils.md_conn import get_md_connection

# Ordem específica de status de repasse (conforme solicitado)
STATUS_ORDER = [
    "Aguardando Documentação",
    "Documentação Recebida",
    "Em Análise",
    "Aprovado",
    "Contrato Registrado",
    "Repasse Realizado",
    "Cancelado",
    "Outros",
]

# Mapeamento de colunas possíveis para nomes canônicos
COLUMN_ALIASES: Dict[str, List[str]] = {
    "referencia": ["referencia", "ref", "id", "idrepasse"],
    "empreendimento": ["empreendimento", "obra", "projeto", "nome_empreendimento"],
    "empresa": ["empresa", "emp", "enterprise", "enterpriseId"],
    "unidade": ["unidade", "unid", "un", "unidade_obra"],
    "situacao": ["Para", "situacao", "situação", "status", "estado"],
    "valor_contrato": ["valor_contrato", "valor", "valor_total", "vlr_contrato"],
    "data_cad": ["data_cad", "data_cadastro", "dt_cad", "data_criacao"],
}


def _detect_columns(columns: List[str]) -> Dict[str, str]:
    """Detecta e mapeia colunas para nomes canônicos."""
    mapping = {}
    columns_lower = [c.lower() for c in columns]

    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias.lower() in columns_lower:
                idx = columns_lower.index(alias.lower())
                mapping[canonical] = columns[idx]
                break

    return mapping


@st.cache_data(ttl=600)
def load_repasses_raw() -> pd.DataFrame:
    """Carrega os dados crus da tabela cv_repasses no MotherDuck."""
    md_conn = get_md_connection()
    sql = """
    SELECT 
        referencia,
        idrepasse,
        empreendimento,
        Para AS situacao,
        valor_contrato,
        data_cad
    FROM reservas.cv_repasses
    WHERE referencia IS NOT NULL
    """
    df = md_conn.run_query(sql)
    
    # Adicionar colunas empresa e unidade se não existirem
    if "empresa" not in df.columns:
        df["empresa"] = "Não informado"
    else:
        df["empresa"] = df["empresa"].fillna("Não informado")
    
    if "unidade" not in df.columns:
        df["unidade"] = "Não informado"
    else:
        df["unidade"] = df["unidade"].fillna("Não informado")
    
    return df


@st.cache_data(ttl=600)
def load_workflow_raw() -> pd.DataFrame:
    """Carrega os dados crus da tabela cv_repasses_workflow no MotherDuck."""
    md_conn = get_md_connection()
    sql = """
    SELECT 
        referencia,
        situacao,
        tempo,
        data_cad
    FROM reservas.cv_repasses_workflow
    WHERE referencia IS NOT NULL
      AND situacao IS NOT NULL
    """
    return md_conn.run_query(sql)


def prepare_dataset(
    df_repasses: pd.DataFrame, df_workflow: pd.DataFrame
) -> pd.DataFrame:
    """Prepara e combina os datasets de repasses e workflow."""
    # Normalizar colunas de repasses
    df_repasses = df_repasses.copy()
    if "data_cad" in df_repasses.columns:
        df_repasses["data_cad"] = pd.to_datetime(
            df_repasses["data_cad"], dayfirst=True, errors="coerce"
        )

    # Normalizar colunas de workflow
    df_workflow = df_workflow.copy()
    if "data_cad" in df_workflow.columns:
        df_workflow["data_cad"] = pd.to_datetime(
            df_workflow["data_cad"], dayfirst=True, errors="coerce"
        )

    # Calcular tempo médio por situação
    tempo_medio_por_situacao = (
        df_workflow.groupby("situacao")["tempo"]
        .mean()
        .reset_index()
        .rename(columns={"tempo": "tempo_medio_dias"})
    )

    # Combinar dados
    df_combined = df_repasses.merge(
        tempo_medio_por_situacao, on="situacao", how="left"
    )

    # Normalizar valores
    if "valor_contrato" in df_combined.columns:
        df_combined["valor_contrato"] = pd.to_numeric(
            df_combined["valor_contrato"], errors="coerce"
        )

    # Normalizar situação para ordem específica
    df_combined["situacao"] = df_combined["situacao"].fillna("Outros")
    df_combined["situacao_ordem"] = df_combined["situacao"].apply(
        lambda x: STATUS_ORDER.index(x) if x in STATUS_ORDER else len(STATUS_ORDER)
    )

    return df_combined


def calculate_kpis(df: pd.DataFrame) -> Dict[str, any]:
    """Calcula KPIs principais."""
    if df.empty:
        return {
            "total_repasses": 0,
            "valor_total": 0.0,
            "valor_medio": 0.0,
            "tempo_medio_geral": 0.0,
        }

    total_repasses = df["referencia"].nunique() if "referencia" in df.columns else len(df)
    valor_total = (
        df["valor_contrato"].sum()
        if "valor_contrato" in df.columns
        else 0.0
    )
    valor_medio = (
        df["valor_contrato"].mean()
        if "valor_contrato" in df.columns
        else 0.0
    )
    tempo_medio_geral = (
        df["tempo_medio_dias"].mean()
        if "tempo_medio_dias" in df.columns
        else 0.0
    )

    return {
        "total_repasses": int(total_repasses),
        "valor_total": float(valor_total),
        "valor_medio": float(valor_medio),
        "tempo_medio_geral": float(tempo_medio_geral),
    }


def render_repasses_dashboard(
    show_title: bool = True, show_caption: bool = True
) -> None:
    """Renderiza o dashboard completo de repasses."""
    if show_title:
        st.title("💰 Dashboard de Repasses")

    if show_caption:
        st.caption(
            "📊 Análise de repasses imobiliários: quantidade, valor e tempo médio por situação"
        )

    # Carregar dados
    with st.spinner("Carregando dados de repasses..."):
        try:
            df_repasses = load_repasses_raw()
            df_workflow = load_workflow_raw()
            df = prepare_dataset(df_repasses, df_workflow)
        except Exception as e:
            st.error(f"❌ Erro ao carregar dados: {e}")
            return

    if df.empty:
        st.warning("⚠️ Nenhum dado encontrado.")
        return

    # Filtros na sidebar
    with st.sidebar:
        st.header("🔧 Filtros")

        # Filtro de data
        if "data_cad" in df.columns and df["data_cad"].notna().any():
            min_date = df["data_cad"].min().date()
            max_date = df["data_cad"].max().date()
            default_start = date(max_date.year, 1, 1)

            start_date = st.date_input(
                "Data inicial",
                value=default_start,
                min_value=min_date,
                max_value=max_date,
            )

            end_date = st.date_input(
                "Data final",
                value=max_date,
                min_value=min_date,
                max_value=max_date,
            )

            if start_date and end_date:
                df = df[
                    (df["data_cad"].dt.date >= start_date)
                    & (df["data_cad"].dt.date <= end_date)
                ]

        # Filtro de empresa
        if "empresa" in df.columns:
            empresas = sorted(df["empresa"].dropna().unique())
            selected_empresas = st.multiselect(
                "Empresa",
                empresas,
                default=empresas if len(empresas) <= 10 else [],
            )
            if selected_empresas:
                df = df[df["empresa"].isin(selected_empresas)]

        # Filtro de unidade
        if "unidade" in df.columns:
            unidades = sorted(df["unidade"].dropna().unique())
            selected_unidades = st.multiselect(
                "Unidade",
                unidades,
                default=unidades if len(unidades) <= 10 else [],
            )
            if selected_unidades:
                df = df[df["unidade"].isin(selected_unidades)]

        # Filtro de situação
        if "situacao" in df.columns:
            situacoes = sorted(df["situacao"].dropna().unique())
            selected_situacoes = st.multiselect(
                "Situação",
                situacoes,
                default=situacoes,
            )
            if selected_situacoes:
                df = df[df["situacao"].isin(selected_situacoes)]

    # KPIs
    kpis = calculate_kpis(df)
    st.subheader("📊 Indicadores Principais")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total de Repasses", f"{kpis['total_repasses']:,}")

    with col2:
        st.metric(
            "Valor Total",
            f"R$ {kpis['valor_total']:,.2f}".replace(",", "X").replace(
                ".", ","
            ).replace("X", "."),
        )

    with col3:
        st.metric(
            "Valor Médio",
            f"R$ {kpis['valor_medio']:,.2f}".replace(",", "X").replace(
                ".", ","
            ).replace("X", "."),
        )

    with col4:
        st.metric(
            "Tempo Médio Geral (dias)",
            f"{kpis['tempo_medio_geral']:.1f}" if kpis['tempo_medio_geral'] > 0 else "-",
        )

    st.divider()

    # Análise por situação
    st.subheader("📈 Análise por Situação")

    if "situacao" in df.columns:
        # Agrupar por situação
        situacao_analysis = (
            df.groupby("situacao")
            .agg(
                {
                    "referencia": "nunique" if "referencia" in df.columns else "count",
                    "valor_contrato": "sum",
                    "tempo_medio_dias": "mean",
                }
            )
            .reset_index()
        )
        situacao_analysis.columns = [
            "Situação",
            "Quantidade",
            "Valor Total",
            "Tempo Médio (dias)",
        ]

        # Ordenar pela ordem específica
        situacao_analysis["ordem"] = situacao_analysis["Situação"].apply(
            lambda x: STATUS_ORDER.index(x) if x in STATUS_ORDER else len(STATUS_ORDER)
        )
        situacao_analysis = situacao_analysis.sort_values("ordem").drop(columns=["ordem"])

        # Formatar valores
        situacao_analysis["Valor Total"] = situacao_analysis["Valor Total"].apply(
            lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
        situacao_analysis["Tempo Médio (dias)"] = situacao_analysis[
            "Tempo Médio (dias)"
        ].apply(lambda x: f"{x:.1f}" if pd.notna(x) and x > 0 else "-")

        col1, col2 = st.columns(2)

        with col1:
            st.dataframe(situacao_analysis, hide_index=True, use_container_width=True)

        with col2:
            # Gráfico de barras empilhadas
            fig = go.Figure()
            fig.add_trace(
                go.Bar(
                    name="Quantidade",
                    x=situacao_analysis["Situação"],
                    y=situacao_analysis["Quantidade"],
                    marker_color="#1f77b4",
                )
            )
            fig.update_layout(
                title="Repasses por Situação",
                xaxis_title="Situação",
                yaxis_title="Quantidade",
                barmode="group",
                height=400,
            )
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Análise por empreendimento
    if "empreendimento" in df.columns:
        st.subheader("🏢 Top 10 Empreendimentos")

        emp_analysis = (
            df.groupby("empreendimento")
            .agg(
                {
                    "referencia": "nunique" if "referencia" in df.columns else "count",
                    "valor_contrato": "sum",
                }
            )
            .reset_index()
        )
        emp_analysis.columns = ["Empreendimento", "Quantidade", "Valor Total"]
        emp_analysis = emp_analysis.sort_values("Quantidade", ascending=False).head(10)
        emp_analysis["Valor Total"] = emp_analysis["Valor Total"].apply(
            lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )

        st.dataframe(emp_analysis, hide_index=True, use_container_width=True)

    st.divider()

    # Análise temporal
    if "data_cad" in df.columns and df["data_cad"].notna().any():
        st.subheader("📅 Evolução Temporal")

        df["mes_ano"] = df["data_cad"].dt.to_period("M").dt.to_timestamp()
        temporal_analysis = (
            df.groupby("mes_ano")
            .agg(
                {
                    "referencia": "nunique" if "referencia" in df.columns else "count",
                    "valor_contrato": "sum",
                }
            )
            .reset_index()
        )
        temporal_analysis.columns = ["Mês", "Quantidade", "Valor Total"]

        fig = px.line(
            temporal_analysis,
            x="Mês",
            y="Quantidade",
            title="Evolução Mensal de Repasses",
            markers=True,
        )
        fig.update_xaxes(tickangle=45)
        st.plotly_chart(fig, use_container_width=True)

