"""
Dashboard de RH - Análise de dados do Jira projeto DHO consolidado.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.utils.md_conn import get_md_connection

def format_currency_short(value: float) -> str:
    """Formata valores de forma abreviada para caber em uma linha (Mi / Mil)."""
    if pd.isna(value) or value == 0:
        return "R$ 0"

    sign = "-" if value < 0 else ""
    v = abs(value)

    if v >= 1_000_000:
        return f"{sign}R$ {v/1_000_000:.1f}Mi"
    elif v >= 1_000:
        return f"{sign}R$ {v/1_000:.1f}Mil"
    else:
        return f"{sign}R$ {v:,.0f}".replace(",", ".")

@st.cache_data(ttl=600)
def load_jira_dho_raw() -> pd.DataFrame:
    """Carrega os dados crus da view Jira_projeto_dho_consolidado no MotherDuck."""
    md_conn = get_md_connection()
    
    sql = """
    SELECT *
    FROM administracao.Jira_projeto_dho_consolidado
    """
    
    try:
        df = md_conn.run_query(sql)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        return pd.DataFrame()

def prepare_jira_dho(df: pd.DataFrame) -> pd.DataFrame:
    """Prepara o dataset do Jira DHO."""
    df = df.copy()
    
    # Normalizar datas
    date_cols = [col for col in df.columns if 'data' in col.lower() or 'date' in col.lower() or 'created' in col.lower() or 'updated' in col.lower()]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], dayfirst=True, errors="coerce")
    
    # Normalizar valores numéricos
    numeric_cols = [col for col in df.columns if 'valor' in col.lower() or 'tempo' in col.lower() or 'horas' in col.lower() or 'story' in col.lower()]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    
    return df

def render_visao_geral(df: pd.DataFrame):
    """Renderiza a aba de Visão Geral."""
    
    st.subheader("📊 Indicadores de RH")
    
    # Identificar colunas relevantes
    status_cols = [col for col in df.columns if 'status' in col.lower()]
    assignee_cols = [col for col in df.columns if 'assignee' in col.lower() or 'responsavel' in col.lower() or 'usuario' in col.lower()]
    issue_cols = [col for col in df.columns if 'issue' in col.lower() or 'key' in col.lower() or 'ticket' in col.lower()]
    
    # KPIs Principais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_issues = df.shape[0] if not df.empty else 0
        st.metric("Total de Issues", f"{total_issues:,}")
        
    with col2:
        if status_cols:
            status_col = status_cols[0]
            status_abertos = df[df[status_col].isin(['Open', 'To Do', 'In Progress', 'Aberto', 'Em Andamento'])].shape[0] if status_col in df.columns else 0
            st.metric("Issues Abertas", f"{status_abertos:,}")
        else:
            st.metric("Issues Abertas", "N/A")
    
    with col3:
        if assignee_cols:
            assignee_col = assignee_cols[0]
            total_usuarios = df[assignee_col].nunique() if assignee_col in df.columns else 0
            st.metric("Usuários Ativos", f"{total_usuarios:,}")
        else:
            st.metric("Usuários Ativos", "N/A")
    
    with col4:
        if status_cols:
            status_col = status_cols[0]
            status_fechados = df[df[status_col].isin(['Done', 'Closed', 'Resolved', 'Fechado', 'Resolvido'])].shape[0] if status_col in df.columns else 0
            st.metric("Issues Fechadas", f"{status_fechados:,}")
        else:
            st.metric("Issues Fechadas", "N/A")
    
    st.divider()
    
    # Análise por Status
    if status_cols:
        st.subheader("📈 Análise por Status")
        
        status_col = status_cols[0]
        
        status_analysis = (
            df.groupby(status_col)
            .size()
            .reset_index(name="Quantidade")
            .sort_values("Quantidade", ascending=False)
        )
        
        # Gráfico de pizza
        fig = px.pie(
            status_analysis,
            values="Quantidade",
            names=status_col,
            title="Distribuição por Status"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Tabela
        st.dataframe(
            status_analysis,
            hide_index=True,
            use_container_width=True,
            key="status_analysis_table",
            column_config={
                status_col: st.column_config.TextColumn("Status"),
                "Quantidade": st.column_config.NumberColumn("Quantidade", format="%d")
            }
        )
    
    st.divider()
    
    # Análise por Usuário/Responsável
    if assignee_cols:
        st.subheader("👥 Análise por Usuário")
        
        assignee_col = assignee_cols[0]
        
        usuario_analysis = (
            df.groupby(assignee_col)
            .size()
            .reset_index(name="Quantidade")
            .sort_values("Quantidade", ascending=False)
            .head(20)
        )
        
        st.dataframe(
            usuario_analysis,
            hide_index=True,
            use_container_width=True,
            key="usuario_analysis_table",
            column_config={
                assignee_col: st.column_config.TextColumn("Usuário"),
                "Quantidade": st.column_config.NumberColumn("Quantidade de Issues", format="%d")
            }
        )
    
    st.divider()
    
    # Tabela Detalhada
    st.subheader("📋 Detalhamento Completo")
    
    # Preparar colunas para exibição
    display_cols = [col for col in df.columns if col not in ['index', 'id']]
    
    st.dataframe(
        df[display_cols],
        hide_index=True,
        use_container_width=True,
        key="jira_detalhado_table"
    )

def render_analise_temporal(df: pd.DataFrame):
    """Renderiza a aba de Análise Temporal."""
    
    st.subheader("📅 Evolução Temporal de Issues")
    
    # Identificar colunas de data
    date_cols = [col for col in df.columns if 'data' in col.lower() or 'date' in col.lower() or 'created' in col.lower()]
    
    if not date_cols:
        st.warning("⚠️ Dados insuficientes para análise temporal. Verifique se há colunas de data.")
        return
    
    date_col = date_cols[0]
    
    # Agregar por data
    df_temporal = df.copy()
    df_temporal["Data"] = pd.to_datetime(df_temporal[date_col], errors="coerce")
    df_temporal = df_temporal[df_temporal["Data"].notna()]
    
    if df_temporal.empty:
        st.warning("⚠️ Nenhuma data válida encontrada para análise temporal.")
        return
    
    evolucao_issues = (
        df_temporal.groupby(df_temporal["Data"].dt.to_period("M"))
        .size()
        .reset_index(name="Quantidade")
    )
    
    evolucao_issues["Data"] = evolucao_issues["Data"].dt.to_timestamp()
    evolucao_issues["Mês"] = evolucao_issues["Data"].dt.strftime("%Y-%m")
    
    # Gráfico de linha
    fig = px.line(
        evolucao_issues,
        x="Data",
        y="Quantidade",
        title="Evolução Mensal de Issues",
        markers=True
    )
    
    fig.update_layout(
        xaxis_title="Mês",
        yaxis_title="Quantidade de Issues",
        hovermode="x unified"
    )
    
    st.plotly_chart(fig, use_container_width=True)

def render_rh_dashboard(
    show_title: bool = True, show_caption: bool = True
) -> None:
    """Renderiza o dashboard completo de RH."""
    
    if show_title:
        st.title("👥 Dashboard de RH")
    
    if show_caption:
        st.caption(
            "Análise detalhada dos dados do Jira projeto DHO consolidado."
        )
    
    # Carregar dados
    with st.spinner("Carregando dados..."):
        df_raw = load_jira_dho_raw()
        
    if df_raw.empty:
        st.warning("⚠️ Nenhum dado encontrado.")
        return
    
    # Preparar dados
    df_prep = prepare_jira_dho(df_raw)
    
    if df_prep.empty:
        st.warning("⚠️ Nenhum dado válido encontrado após preparação.")
        return
    
    # --- FILTROS GLOBAIS ---
    with st.sidebar:
        st.header("🔧 Filtros Globais")
        
        # Identificar colunas de data para filtro
        date_cols = [col for col in df_prep.columns if 'data' in col.lower() or 'date' in col.lower() or 'created' in col.lower()]
        
        if date_cols:
            date_col = date_cols[0]
            if df_prep[date_col].notna().any():
                min_date = df_prep[date_col].min().date()
                max_date = df_prep[date_col].max().date()
            else:
                min_date = date.today() - timedelta(days=365)
                max_date = date.today()
        else:
            min_date = date.today() - timedelta(days=365)
            max_date = date.today()
        
        start_date = st.date_input(
            "Data inicial",
            value=min_date,
            min_value=min_date,
            max_value=max_date,
            format="DD/MM/YYYY"
        )
        
        end_date = st.date_input(
            "Data final",
            value=max_date,
            min_value=min_date,
            max_value=max_date,
            format="DD/MM/YYYY"
        )
        
        st.session_state["rh_filtro_inicio"] = start_date
        st.session_state["rh_filtro_fim"] = end_date
        
        st.divider()
        st.subheader("Filtros Específicos")
        
        # Filtro de Status
        status_cols = [col for col in df_prep.columns if 'status' in col.lower()]
        selected_status = []
        if status_cols:
            status_col = status_cols[0]
            statuses = sorted(df_prep[status_col].dropna().unique())
            selected_status = st.multiselect(
                "Status",
                statuses,
                default=[],
                placeholder="Selecione os status"
            )
        
        # Filtro de Usuário/Responsável
        assignee_cols = [col for col in df_prep.columns if 'assignee' in col.lower() or 'responsavel' in col.lower() or 'usuario' in col.lower()]
        selected_usuarios = []
        if assignee_cols:
            assignee_col = assignee_cols[0]
            usuarios = sorted(df_prep[assignee_col].dropna().unique())
            selected_usuarios = st.multiselect(
                "Usuário/Responsável",
                usuarios,
                default=[],
                placeholder="Selecione os usuários"
            )
    
    # --- APLICAR FILTROS ---
    
    df_final = df_prep.copy()
    
    # Filtro de Data
    if date_cols and start_date and end_date:
        date_col = date_cols[0]
        if date_col in df_final.columns:
            df_final = df_final[
                (df_final[date_col].dt.date >= start_date) &
                (df_final[date_col].dt.date <= end_date)
            ]
    
    # Filtro de Status
    if status_cols and selected_status:
        status_col = status_cols[0]
        df_final = df_final[df_final[status_col].isin(selected_status)]
    
    # Filtro de Usuário
    if assignee_cols and selected_usuarios:
        assignee_col = assignee_cols[0]
        df_final = df_final[df_final[assignee_col].isin(selected_usuarios)]
    
    # --- RENDERIZAÇÃO POR ABAS ---
    
    tab1, tab2 = st.tabs(["📊 Visão Geral", "📅 Análise Temporal"])
    
    with tab1:
        render_visao_geral(df_final)
    
    with tab2:
        render_analise_temporal(df_final)

