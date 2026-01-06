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
    
    st.subheader("📋 Resumo Financeiro por Instituição")
    
    # Identificar colunas
    saldo_cols = [col for col in df.columns if 'saldo' in col.lower() or 'valor' in col.lower()]
    banco_cols = [col for col in df.columns if 'banco' in col.lower() or 'instituicao' in col.lower() or 'conta' in col.lower()]
    categoria_cols = [col for col in df.columns if 'categoria' in col.lower()]
    
    if not saldo_cols or not banco_cols or not categoria_cols:
        st.warning("⚠️ Dados insuficientes para gerar a visão geral (faltam colunas de Saldo, Banco ou Categoria).")
        return
    
    saldo_col = saldo_cols[0]
    banco_col = banco_cols[0]
    categoria_col = categoria_cols[0]
    
    # Categorias de interesse (baseado na imagem do usuário, mas adaptável ao que existir no banco)
    categorias_ordem = [
        "Saldo Anterior",
        "Pagamentos",
        "Aplicação",
        "Recebimentos",
        "Resgate",
        "Saldo Atual",
        "Saldo de Investimentos"
    ]
    
    # Filtrar apenas categorias que existem no dataframe
    categorias_existentes = df[categoria_col].unique()
    # Tenta fazer match case-insensitive
    categorias_filtradas = []
    for cat_ordem in categorias_ordem:
        match = next((c for c in categorias_existentes if str(c).lower() == cat_ordem.lower()), None)
        if match:
            categorias_filtradas.append(match)
    
    # Adicionar outras categorias que não estejam na lista, se houver (opcional, para não perder dados)
    # Por enquanto, vamos focar nas solicitadas ou mostrar todas se a lista for muito divergente
    if not categorias_filtradas:
        categorias_filtradas = list(categorias_existentes)
    
    # Pivot Table: Index=Categoria, Columns=Banco, Values=Valor
    pivot_df = pd.pivot_table(
        df[df[categoria_col].isin(categorias_filtradas)],
        values=saldo_col,
        index=categoria_col,
        columns=banco_col,
        aggfunc="sum",
        fill_value=0
    )
    
    # Reordenar index se possível
    pivot_df = pivot_df.reindex([c for c in categorias_filtradas if c in pivot_df.index])
    
    # Adicionar coluna Total
    pivot_df["Total"] = pivot_df.sum(axis=1)
    
    # Formatação para exibição
    st.dataframe(
        pivot_df.style.format("R$ {:,.2f}"),
        use_container_width=True,
        height=400
    )

    st.divider()

    # KPIs Principais (Totalizadores)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Tenta pegar Saldo Atual ou Saldo Total
        saldo_atual = df[df[categoria_col].astype(str).str.contains("Saldo Atual", case=False, na=False)][saldo_col].sum()
        if saldo_atual == 0: # Se não achar pela categoria, soma tudo (comportamento original)
             saldo_atual = df[saldo_col].sum()
        st.metric("Saldo Atual Total", format_currency_short(saldo_atual))
        
    with col2:
        recebimentos = df[df[categoria_col].astype(str).str.contains("Recebimentos", case=False, na=False)][saldo_col].sum()
        st.metric("Total Recebimentos", format_currency_short(recebimentos))
    
    with col3:
        pagamentos = df[df[categoria_col].astype(str).str.contains("Pagamentos", case=False, na=False)][saldo_col].sum()
        st.metric("Total Pagamentos", format_currency_short(pagamentos))
    
    with col4:
         # Saldo Investimentos
        investimentos = df[df[categoria_col].astype(str).str.contains("Investimentos", case=False, na=False)][saldo_col].sum()
        st.metric("Saldo Investimentos", format_currency_short(investimentos))
    
    st.divider()
    
    # Gráfico de Composição por Banco (Saldo Atual)
    st.subheader("🏦 Composição do Saldo Atual por Banco")
    
    # Filtrar apenas Saldo Atual para o gráfico de pizza/barra
    df_saldo_atual = df[df[categoria_col].astype(str).str.contains("Saldo Atual", case=False, na=False)]
    
    if not df_saldo_atual.empty:
        fig_bancos = px.pie(
            df_saldo_atual,
            values=saldo_col,
            names=banco_col,
            title="Distribuição do Saldo Atual",
            hole=0.4
        )
        st.plotly_chart(fig_bancos, use_container_width=True)
    else:
        st.info("Não foi possível gerar o gráfico de composição (Categoria 'Saldo Atual' não encontrada).")

def render_analise_temporal(df: pd.DataFrame):
    """Renderiza a aba de Análise Temporal."""
    
    st.subheader("📅 Evolução Temporal")
    
    # Identificar colunas
    date_cols = [col for col in df.columns if 'data' in col.lower() or 'date' in col.lower()]
    banco_cols = [col for col in df.columns if 'banco' in col.lower()]
    categoria_cols = [col for col in df.columns if 'categoria' in col.lower()]
    valor_cols = [col for col in df.columns if 'valor' in col.lower() or 'saldo' in col.lower()]
    
    if not date_cols or not valor_cols or not categoria_cols:
        st.warning("⚠️ Dados insuficientes para análise temporal. Verifique se há colunas de data, valor e categoria.")
        return
    
    date_col = date_cols[0]
    banco_col = banco_cols[0] if banco_cols else None
    categoria_col = categoria_cols[0]
    valor_col = valor_cols[0]
    
    # --- GRÁFICO 1: Saldo Acumulado (Sicredi + CEF) ---
    # Filtrar apenas "Saldo Acumulado" e bancos Sicredi e CEF
    df_acumulado = df.copy()
    df_acumulado["Data"] = pd.to_datetime(df_acumulado[date_col], errors="coerce")
    df_acumulado = df_acumulado[df_acumulado["Data"].notna()]
    
    df_acumulado_sicredi_cef = df_acumulado[
        (df_acumulado[categoria_col].str.contains("Saldo Acumulado", case=False, na=False)) &
        (df_acumulado[banco_col].isin(["Sicredi", "CEF"]))
    ]
    
    if not df_acumulado_sicredi_cef.empty:
        # Agregar por data (dia a dia) somando Sicredi + CEF
        evolucao_saldos = (
            df_acumulado_sicredi_cef.groupby(df_acumulado_sicredi_cef["Data"].dt.date)
            .agg({valor_col: "sum"})
            .reset_index()
        )
        evolucao_saldos["Data"] = pd.to_datetime(evolucao_saldos["Data"])
        evolucao_saldos = evolucao_saldos.rename(columns={valor_col: "Saldo Acumulado"})
        evolucao_saldos = evolucao_saldos.sort_values("Data")
        
        fig1 = px.line(
            evolucao_saldos,
            x="Data",
            y="Saldo Acumulado",
            title="Evolução Diária do Saldo Acumulado (Sicredi + CEF)",
            markers=True
        )
        fig1.update_layout(
            xaxis_title="Data", yaxis_title="Saldo (R$)", hovermode="x unified",
            yaxis=dict(tickformat=",.0f", tickprefix="R$ ")
        )
        st.plotly_chart(fig1, use_container_width=True, key="chart_saldo_acumulado")
    else:
        st.info("Dados de 'Saldo Acumulado' (Sicredi/CEF) não encontrados para o período.")

    st.divider()

    # --- GRÁFICO 2: Comparativo de Movimentações (Demais Categorias) ---
    st.subheader("📉 Comparativo de Movimentações")
    
    # Excluir "Saldo Acumulado" (categoria do gráfico 1)
    df_movimentacoes = df_acumulado[
        ~df_acumulado[categoria_col].str.contains("Saldo Acumulado", case=False, na=False)
    ].copy()
    
    if df_movimentacoes.empty:
        st.info("Nenhum dado de movimentação encontrado.")
        return

    col_filters1, col_filters2 = st.columns(2)
    
    with col_filters1:
        # Opção de visualização (Eixo de Cor)
        visao_tipo = st.radio(
            "Agrupar cores por:",
            ["Categoria", "Banco"],
            horizontal=True,
            key="radio_visao_temporal"
        )
    
    with col_filters2:
        # Opção de Modo de Barras
        barmode_option = st.radio(
            "Modo de Visualização:",
            ["Agrupado (Lado a lado)", "Empilhado (Somado)"],
            horizontal=True,
            key="radio_barmode"
        )
        plotly_barmode = "group" if "Agrupado" in barmode_option else "relative"

    group_col = categoria_col if visao_tipo == "Categoria" else banco_col
    
    # Filtro adicional para remover "Saldos" se desejar focar apenas em fluxo
    # Identificar categorias que parecem ser saldo de estoque vs fluxo
    todas_cats = sorted(df_movimentacoes[categoria_col].unique())
    cats_padrao = [c for c in todas_cats if "saldo" not in str(c).lower()]
    if not cats_padrao: # Se tudo tiver saldo no nome, seleciona tudo
        cats_padrao = todas_cats
        
    cats_selecionadas = st.multiselect(
        "Filtrar Categorias:",
        options=todas_cats,
        default=todas_cats, # Começa mostrando tudo conforme pedido, mas usuário pode tirar
        key="multiselect_cats_temporal"
    )
    
    if cats_selecionadas:
        df_movimentacoes = df_movimentacoes[df_movimentacoes[categoria_col].isin(cats_selecionadas)]

    if df_movimentacoes.empty:
        st.warning("Nenhuma categoria selecionada.")
        return
    
    # Agregar por Data e Grupo
    evolucao_mov = (
        df_movimentacoes.groupby([df_movimentacoes["Data"].dt.date, group_col])
        .agg({valor_col: "sum"})
        .reset_index()
    )
    evolucao_mov["Data"] = pd.to_datetime(evolucao_mov["Data"])
    
    # Gráfico de Barras
    fig2 = px.bar(
        evolucao_mov,
        x="Data",
        y=valor_col,
        color=group_col,
        title=f"Evolução Temporal por {visao_tipo}",
        barmode=plotly_barmode
    )
    
    fig2.update_layout(
        xaxis_title="Data", 
        yaxis_title="Valor (R$)", 
        hovermode="x unified", # Unificado ajuda a ver todos os valores do dia
        xaxis=dict(
            tickformat="%d/%m/%Y",
            tickangle=-45
        ),
        yaxis=dict(
            tickformat=",.0f", 
            tickprefix="R$ "
        ),
        legend_title_text=visao_tipo
    )
    
    # Ajustar Tooltips para ser mais limpo
    fig2.update_traces(
        hovertemplate='<b>%{fullData.name}</b><br>' +
                      'Data: %{x|%d/%m/%Y}<br>' +
                      'Valor: R$ %{y:,.2f}<extra></extra>'
    )
    
    st.plotly_chart(fig2, use_container_width=True, key="chart_movimentacoes_bar")

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

