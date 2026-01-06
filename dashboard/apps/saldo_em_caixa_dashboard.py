"""
Dashboard de Saldo Em Caixa - Análise de saldos bancários consolidados.
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
def load_saldos_bancarios_raw() -> pd.DataFrame:
    """Carrega os dados crus da view saldos_bancarios_consolidado no MotherDuck."""
    md_conn = get_md_connection()
    
    sql = """
    SELECT *
    FROM administracao.saldos_bancarios_consolidado
    """
    
    try:
        df = md_conn.run_query(sql)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        return pd.DataFrame()

def prepare_saldos_bancarios(df: pd.DataFrame) -> pd.DataFrame:
    """Prepara o dataset de saldos bancários."""
    df = df.copy()
    
    # Normalizar datas
    date_cols = [col for col in df.columns if 'data' in col.lower() or 'date' in col.lower()]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], dayfirst=True, errors="coerce")
    
    # Normalizar valores monetários
    valor_cols = [col for col in df.columns if 'valor' in col.lower() or 'saldo' in col.lower() or 'valor' in col.lower()]
    for col in valor_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    
    return df

def render_visao_geral(df: pd.DataFrame):
    """Renderiza a aba de Visão Geral."""
    
    st.subheader("📊 Indicadores Financeiros")
    
    # Identificar colunas de saldo/valor
    saldo_cols = [col for col in df.columns if 'saldo' in col.lower() or 'valor' in col.lower()]
    
    if not saldo_cols:
        st.warning("⚠️ Nenhuma coluna de saldo encontrada nos dados.")
        return
    
    # Usar a primeira coluna de saldo encontrada
    saldo_col = saldo_cols[0]
    
    # KPIs Principais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        saldo_total = df[saldo_col].sum() if saldo_col in df.columns else 0.0
        st.metric("Saldo Total", format_currency_short(saldo_total))
        
    with col2:
        total_contas = df.shape[0] if not df.empty else 0
        st.metric("Total de Contas", f"{total_contas:,}")
    
    with col3:
        saldo_medio = df[saldo_col].mean() if saldo_col in df.columns and not df.empty else 0.0
        st.metric("Saldo Médio", format_currency_short(saldo_medio))
    
    with col4:
        # Identificar coluna de banco/instituição
        banco_cols = [col for col in df.columns if 'banco' in col.lower() or 'instituicao' in col.lower() or 'conta' in col.lower()]
        if banco_cols:
            total_bancos = df[banco_cols[0]].nunique() if banco_cols[0] in df.columns else 0
            st.metric("Total de Bancos", f"{total_bancos:,}")
        else:
            st.metric("Total de Bancos", "N/A")
    
    st.divider()
    
    # Análise por Banco/Instituição
    banco_cols = [col for col in df.columns if 'banco' in col.lower() or 'instituicao' in col.lower() or 'conta' in col.lower()]
    if banco_cols:
        st.subheader("🏦 Análise por Banco")
        
        banco_col = banco_cols[0]
        
        banco_analysis = (
            df.groupby(banco_col)
            .agg({
                saldo_col: "sum"
            })
            .reset_index()
            .rename(columns={
                banco_col: "Banco",
                saldo_col: "Saldo Total"
            })
        )
        
        banco_analysis = banco_analysis.sort_values("Saldo Total", ascending=False)
        
        # Formatar Valores
        banco_analysis["Saldo"] = banco_analysis["Saldo Total"].apply(format_currency_short)
        
        st.dataframe(
            banco_analysis[["Banco", "Saldo"]],
            hide_index=True,
            use_container_width=True,
            key="banco_analysis_table",
            column_config={
                "Banco": st.column_config.TextColumn("Banco"),
                "Saldo": st.column_config.TextColumn("Saldo Total", help="Saldo total por banco")
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
        key="saldos_detalhado_table"
    )

def render_analise_temporal(df: pd.DataFrame):
    """Renderiza a aba de Análise Temporal."""
    
    st.subheader("📅 Evolução Temporal de Saldos")
    
    # Identificar colunas
    date_cols = [col for col in df.columns if 'data' in col.lower() or 'date' in col.lower()]
    banco_cols = [col for col in df.columns if 'banco' in col.lower()]
    categoria_cols = [col for col in df.columns if 'categoria' in col.lower()]
    valor_cols = [col for col in df.columns if 'valor' in col.lower()]
    
    if not date_cols or not valor_cols:
        st.warning("⚠️ Dados insuficientes para análise temporal. Verifique se há colunas de data e valor.")
        return
    
    date_col = date_cols[0]
    banco_col = banco_cols[0] if banco_cols else None
    categoria_col = categoria_cols[0] if categoria_cols else None
    valor_col = valor_cols[0]
    
    # Filtrar apenas "Saldo Acumulado" e bancos Sicredi e CEF
    df_temporal = df.copy()
    df_temporal["Data"] = pd.to_datetime(df_temporal[date_col], errors="coerce")
    df_temporal = df_temporal[df_temporal["Data"].notna()]
    
    if df_temporal.empty:
        st.warning("⚠️ Nenhuma data válida encontrada para análise temporal.")
        return
    
    # Filtrar por categoria "Saldo Acumulado"
    if categoria_col and categoria_col in df_temporal.columns:
        df_temporal = df_temporal[
            df_temporal[categoria_col].str.contains("Saldo Acumulado", case=False, na=False)
        ]
    
    # Filtrar apenas Sicredi e CEF
    if banco_col and banco_col in df_temporal.columns:
        df_temporal = df_temporal[
            df_temporal[banco_col].isin(["Sicredi", "CEF"])
        ]
    
    if df_temporal.empty:
        st.warning("⚠️ Nenhum dado encontrado para 'Saldo Acumulado' dos bancos Sicredi e CEF.")
        return
    
    # Agregar por data (dia a dia) somando Sicredi + CEF
    evolucao_saldos = (
        df_temporal.groupby(df_temporal["Data"].dt.date)
        .agg({
            valor_col: "sum"
        })
        .reset_index()
    )
    
    evolucao_saldos["Data"] = pd.to_datetime(evolucao_saldos["Data"])
    evolucao_saldos = evolucao_saldos.rename(columns={valor_col: "Saldo Acumulado"})
    evolucao_saldos = evolucao_saldos.sort_values("Data")
    
    # Gráfico de linha
    fig = px.line(
        evolucao_saldos,
        x="Data",
        y="Saldo Acumulado",
        title="Evolução Diária do Saldo Acumulado (Sicredi + CEF)",
        markers=True
    )
    
    fig.update_layout(
        xaxis_title="Data",
        yaxis_title="Saldo Acumulado (R$)",
        hovermode="x unified",
        xaxis=dict(
            tickformat="%d/%m/%Y",
            tickangle=-45
        ),
        yaxis=dict(
            tickformat=",.0f"
        )
    )
    
    # Adicionar valores nos pontos
    fig.update_traces(
        mode='lines+markers',
        hovertemplate='<b>Data:</b> %{x|%d/%m/%Y}<br><b>Saldo Acumulado:</b> R$ %{y:,.2f}<extra></extra>'
    )
    
    st.plotly_chart(fig, use_container_width=True)

def render_saldo_em_caixa_dashboard(
    show_title: bool = True, show_caption: bool = True
) -> None:
    """Renderiza o dashboard completo de Saldo Em Caixa."""
    
    if show_title:
        st.title("💵 Dashboard de Saldo Em Caixa")
    
    if show_caption:
        st.caption(
            "Análise detalhada dos saldos bancários consolidados."
        )
    
    # Carregar dados
    with st.spinner("Carregando dados..."):
        df_raw = load_saldos_bancarios_raw()
        
    if df_raw.empty:
        st.warning("⚠️ Nenhum dado encontrado.")
        return
    
    # Preparar dados
    df_prep = prepare_saldos_bancarios(df_raw)
    
    if df_prep.empty:
        st.warning("⚠️ Nenhum dado válido encontrado após preparação.")
        return
    
    # --- FILTROS GLOBAIS ---
    with st.sidebar:
        st.header("🔧 Filtros Globais")
        
        # Identificar colunas de data para filtro
        date_cols = [col for col in df_prep.columns if 'data' in col.lower() or 'date' in col.lower()]
        
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
        
        st.session_state["saldos_filtro_inicio"] = start_date
        st.session_state["saldos_filtro_fim"] = end_date
        
        st.divider()
        st.subheader("Filtros Específicos")
        
        # Filtro de Banco/Instituição
        banco_cols = [col for col in df_prep.columns if 'banco' in col.lower() or 'instituicao' in col.lower() or 'conta' in col.lower()]
        selected_bancos = []
        if banco_cols:
            banco_col = banco_cols[0]
            bancos = sorted(df_prep[banco_col].dropna().unique())
            selected_bancos = st.multiselect(
                "Banco/Instituição",
                bancos,
                default=[],
                placeholder="Selecione os bancos"
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
    
    # Filtro de Banco
    if banco_cols and selected_bancos:
        banco_col = banco_cols[0]
        df_final = df_final[df_final[banco_col].isin(selected_bancos)]
    
    # --- RENDERIZAÇÃO POR ABAS ---
    
    tab1, tab2 = st.tabs(["📊 Visão Geral", "📅 Análise Temporal"])
    
    with tab1:
        render_visao_geral(df_final)
    
    with tab2:
        render_analise_temporal(df_final)

