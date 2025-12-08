"""
Dashboard Contratos - Monitoramento de contratos de suprimentos.
"""

import streamlit as st
import pandas as pd
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, date
import plotly.express as px
import plotly.graph_objects as go

from dashboard.utils.md_conn import get_md_connection
import duckdb
import os
from dotenv import load_dotenv

load_dotenv()


@st.cache_data(ttl=300)
def load_contratos(
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    fornecedor: Optional[List[str]] = None,
    responsavel: Optional[List[str]] = None,
    status: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Carrega dados de contratos do banco reservas.
    
    Args:
        data_inicio: Data inicial (YYYY-MM-DD)
        data_fim: Data final (YYYY-MM-DD)
        fornecedor: Lista de fornecedores para filtrar
        responsavel: Lista de responsáveis para filtrar
        status: Lista de status para filtrar
        
    Returns:
        DataFrame com dados de contratos
    """
    md_conn = get_md_connection()
    
    # Construir filtros
    filters = []
    params = []
    
    if data_inicio:
        filters.append("Data_Contrato >= ?")
        params.append(data_inicio)
    
    if data_fim:
        filters.append("Data_Contrato <= ?")
        params.append(data_fim)
    
    if fornecedor:
        placeholders = ','.join(['?' for _ in fornecedor])
        filters.append(f"Fornecedor IN ({placeholders})")
        params.extend(fornecedor)
    
    if responsavel:
        placeholders = ','.join(['?' for _ in responsavel])
        filters.append(f"Responsavel IN ({placeholders})")
        params.extend(responsavel)
    
    if status:
        placeholders = ','.join(['?' for _ in status])
        filters.append(f"Status IN ({placeholders})")
        params.extend(status)
    
    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    
    query = f"""
        SELECT 
            Documento,
            Numero_Contrato,
            ID_Fornecedor,
            Fornecedor,
            Empresa,
            Responsavel,
            Status,
            Aprovacao,
            Autorizacao,
            Data_Contrato,
            Data_Inicio_Contrato,
            Data_Final_Contrato,
            COALESCE(Total_MaoObra, 0) as Total_MaoObra,
            COALESCE(Total_Material, 0) as Total_Material,
            (COALESCE(Total_MaoObra, 0) + COALESCE(Total_Material, 0)) as Valor_Total,
            Consistente,
            Objeto,
            Notas
        FROM reservas.main.sienge_contratos_suprimentos
        {where_clause}
        ORDER BY Data_Contrato DESC
    """
    
    try:
        if params:
            df = md_conn.execute(query, params).df()
        else:
            df = md_conn.execute(query).df()
        
        # Converter datas
        date_columns = ['Data_Contrato', 'Data_Inicio_Contrato', 'Data_Final_Contrato']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_unique_fornecedores(data_inicio: Optional[str] = None, data_fim: Optional[str] = None) -> List[str]:
    """Retorna lista única de fornecedores, opcionalmente filtrados por período."""
    md_conn = get_md_connection()
    
    filters = []
    params = []
    
    if data_inicio:
        filters.append("Data_Contrato >= ?")
        params.append(data_inicio)
    
    if data_fim:
        filters.append("Data_Contrato <= ?")
        params.append(data_fim)
    
    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    
    query = f"""
        SELECT DISTINCT Fornecedor
        FROM reservas.main.sienge_contratos_suprimentos
        {where_clause}
        ORDER BY Fornecedor
    """
    
    try:
        if params:
            df = md_conn.execute(query, params).df()
        else:
            df = md_conn.execute(query).df()
        return df['Fornecedor'].dropna().unique().tolist()
    except Exception as e:
        st.error(f"Erro ao carregar fornecedores: {str(e)}")
        return []


@st.cache_data(ttl=300)
def get_unique_responsaveis(data_inicio: Optional[str] = None, data_fim: Optional[str] = None) -> List[str]:
    """Retorna lista única de responsáveis, opcionalmente filtrados por período."""
    md_conn = get_md_connection()
    
    filters = []
    params = []
    
    if data_inicio:
        filters.append("Data_Contrato >= ?")
        params.append(data_inicio)
    
    if data_fim:
        filters.append("Data_Contrato <= ?")
        params.append(data_fim)
    
    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    
    query = f"""
        SELECT DISTINCT Responsavel
        FROM reservas.main.sienge_contratos_suprimentos
        {where_clause}
        ORDER BY Responsavel
    """
    
    try:
        if params:
            df = md_conn.execute(query, params).df()
        else:
            df = md_conn.execute(query).df()
        return df['Responsavel'].dropna().unique().tolist()
    except Exception as e:
        st.error(f"Erro ao carregar responsáveis: {str(e)}")
        return []


def formatar_moeda(valor: float) -> str:
    """Formata valor como moeda brasileira."""
    if pd.isna(valor) or valor == 0:
        return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def calcular_indicadores(df: pd.DataFrame) -> Dict[str, Any]:
    """Calcula indicadores principais dos contratos."""
    if df.empty:
        return {
            'total_contratos': 0,
            'valor_total': 0.0,
            'valor_mao_obra': 0.0,
            'valor_material': 0.0,
            'contratos_unicos': 0,
            'fornecedores_unicos': 0,
            'contratos_aprovados': 0,
            'contratos_autorizados': 0,
            'contratos_ativos': 0,
            'contratos_rescindidos': 0,
        }
    
    return {
        'total_contratos': len(df),
        'valor_total': df['Valor_Total'].sum(),
        'valor_mao_obra': df['Total_MaoObra'].sum(),
        'valor_material': df['Total_Material'].sum(),
        'contratos_unicos': df['Numero_Contrato'].nunique(),
        'fornecedores_unicos': df['Fornecedor'].nunique(),
        'contratos_aprovados': len(df[df['Aprovacao'] == 'APPROVED']),
        'contratos_autorizados': len(df[df['Autorizacao'] == True]),
        'contratos_ativos': len(df[df['Status'].isin(['PARTIALLY_MEASURED', 'PENDING', 'FULLY_MEASURED'])]),
        'contratos_rescindidos': len(df[df['Status'] == 'RESCINDED']),
    }


def calcular_indicadores_por_fornecedor(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula indicadores agrupados por fornecedor."""
    if df.empty:
        return pd.DataFrame()
    
    df_grouped = df.groupby('Fornecedor').agg({
        'Numero_Contrato': 'nunique',
        'Valor_Total': 'sum',
        'Total_MaoObra': 'sum',
        'Total_Material': 'sum',
    }).reset_index()
    
    df_grouped.columns = ['Fornecedor', 'Qtd_Contratos', 'Valor_Total', 'Valor_MaoObra', 'Valor_Material']
    df_grouped = df_grouped.sort_values('Valor_Total', ascending=False)
    
    return df_grouped


def calcular_indicadores_por_periodo(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula indicadores agrupados por período (mês/ano)."""
    if df.empty or 'Data_Contrato' not in df.columns:
        return pd.DataFrame()
    
    df_periodo = df.copy()
    df_periodo['Ano_Mes'] = df_periodo['Data_Contrato'].dt.to_period('M').astype(str)
    
    df_grouped = df_periodo.groupby('Ano_Mes').agg({
        'Numero_Contrato': 'nunique',
        'Valor_Total': 'sum',
        'Total_MaoObra': 'sum',
        'Total_Material': 'sum',
    }).reset_index()
    
    df_grouped.columns = ['Período', 'Qtd_Contratos', 'Valor_Total', 'Valor_MaoObra', 'Valor_Material']
    df_grouped = df_grouped.sort_values('Período')
    
    return df_grouped


def calcular_indicadores_por_status(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula indicadores agrupados por status."""
    if df.empty:
        return pd.DataFrame()
    
    # Mapear status para português
    status_map = {
        'PARTIALLY_MEASURED': 'Parcialmente Medido',
        'COMPLETED': 'Concluído',
        'RESCINDED': 'Rescindido',
        'PENDING': 'Pendente',
        'FULLY_MEASURED': 'Totalmente Medido',
    }
    
    df_grouped = df.groupby('Status').agg({
        'Numero_Contrato': 'nunique',
        'Valor_Total': 'sum',
        'Total_MaoObra': 'sum',
        'Total_Material': 'sum',
    }).reset_index()
    
    df_grouped['Status_PT'] = df_grouped['Status'].map(status_map).fillna(df_grouped['Status'])
    df_grouped.columns = ['Status', 'Qtd_Contratos', 'Valor_Total', 'Valor_MaoObra', 'Valor_Material', 'Status_PT']
    df_grouped = df_grouped.sort_values('Valor_Total', ascending=False)
    
    return df_grouped


def render_contratos_dashboard(
    *,
    show_title: bool = True,
    show_caption: bool = True,
) -> None:
    """
    Renderiza o dashboard de Contratos.
    
    Args:
        show_title: Exibe título principal.
        show_caption: Exibe legenda/logo abaixo do título.
    """
    if show_title:
        st.title("📋 Dashboard de Contratos")
        if show_caption:
            st.caption("Monitoramento de contratos de suprimentos")

    # Sidebar - Filtros
    with st.sidebar:
        st.header("🔍 Filtros")
        
        # Filtro de período
        st.subheader("Período")
        default_inicio = datetime(2024, 1, 1)
        default_fim = datetime.now()

        data_inicio = st.date_input(
            "Data Inicial",
            value=default_inicio,
            max_value=date.today(),
            key="contratos_data_inicio"
        )

        data_fim = st.date_input(
            "Data Final",
            value=default_fim,
            max_value=date.today(),
            key="contratos_data_fim"
        )
        
        # Filtro de fornecedor
        st.subheader("Fornecedor")
        data_ini_str = data_inicio.strftime('%Y-%m-%d') if data_inicio else None
        data_fim_str = data_fim.strftime('%Y-%m-%d') if data_fim else None
        
        fornecedores_disponiveis = get_unique_fornecedores(data_ini_str, data_fim_str)
        fornecedor_selecionado = st.multiselect(
            "Selecione o(s) fornecedor(es)",
            options=fornecedores_disponiveis,
            key="contratos_fornecedor"
        )
        
        # Filtro de responsável
        st.subheader("Responsável")
        responsaveis_disponiveis = get_unique_responsaveis(data_ini_str, data_fim_str)
        responsavel_selecionado = st.multiselect(
            "Selecione o(s) responsável(eis)",
            options=responsaveis_disponiveis,
            key="contratos_responsavel"
        )
        
        # Filtro de status
        st.subheader("Status")
        status_opcoes = [
            'PARTIALLY_MEASURED',
            'COMPLETED',
            'RESCINDED',
            'PENDING',
            'FULLY_MEASURED',
        ]
        status_map = {
            'PARTIALLY_MEASURED': 'Parcialmente Medido',
            'COMPLETED': 'Concluído',
            'RESCINDED': 'Rescindido',
            'PENDING': 'Pendente',
            'FULLY_MEASURED': 'Totalmente Medido',
        }
        status_labels = [f"{status_map.get(s, s)} ({s})" for s in status_opcoes]
        status_selecionado = st.multiselect(
            "Selecione o(s) status",
            options=status_opcoes,
            format_func=lambda x: status_map.get(x, x),
            key="contratos_status"
        )
    
    # Carregar dados
    with st.spinner("Carregando dados de contratos..."):
        df = load_contratos(
            data_inicio=data_inicio.strftime('%Y-%m-%d') if data_inicio else None,
            data_fim=data_fim.strftime('%Y-%m-%d') if data_fim else None,
            fornecedor=fornecedor_selecionado if fornecedor_selecionado else None,
            responsavel=responsavel_selecionado if responsavel_selecionado else None,
            status=status_selecionado if status_selecionado else None,
        )
    
    if df.empty:
        st.warning("⚠️ Nenhum dado encontrado para os filtros selecionados.")
        return
    
    # Calcular indicadores
    indicadores = calcular_indicadores(df)
    
    # Seção 1: KPIs Principais
    st.markdown("---")
    st.subheader("📊 Indicadores Principais")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total de Contratos",
            f"{indicadores['total_contratos']:,}",
            help="Quantidade total de contratos no período"
        )
    
    with col2:
        st.metric(
            "Valor Total",
            formatar_moeda(indicadores['valor_total']),
            help="Soma de todos os valores (Mão de Obra + Material)"
        )
    
    with col3:
        st.metric(
            "Valor Mão de Obra",
            formatar_moeda(indicadores['valor_mao_obra']),
            help="Soma dos valores de mão de obra"
        )
    
    with col4:
        st.metric(
            "Valor Material",
            formatar_moeda(indicadores['valor_material']),
            help="Soma dos valores de material"
        )
    
    # Segunda linha de KPIs
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
        st.metric(
            "Contratos Únicos",
            f"{indicadores['contratos_unicos']:,}",
            help="Quantidade de números de contrato distintos"
        )
    
    with col6:
        st.metric(
            "Fornecedores",
            f"{indicadores['fornecedores_unicos']:,}",
            help="Quantidade de fornecedores distintos"
        )
    
    with col7:
        st.metric(
            "Contratos Aprovados",
            f"{indicadores['contratos_aprovados']:,}",
            help="Contratos com status APPROVED"
        )
    
    with col8:
        st.metric(
            "Contratos Ativos",
            f"{indicadores['contratos_ativos']:,}",
            help="Contratos em andamento (não concluídos nem rescindidos)"
        )
    
    # Seção 2: Análises Detalhadas
    st.markdown("---")
    st.subheader("📈 Análises Detalhadas")
    
    # Tabs para diferentes análises
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Por Fornecedor",
        "📅 Por Período",
        "📋 Por Status",
        "🔍 Detalhamento"
    ])
    
    with tab1:
        st.markdown("### 📊 Indicadores por Fornecedor")
        df_fornecedor = calcular_indicadores_por_fornecedor(df)
        
        if not df_fornecedor.empty:
            # Formatar valores para exibição
            df_exib = df_fornecedor.copy()
            df_exib['Valor_Total'] = df_exib['Valor_Total'].apply(formatar_moeda)
            df_exib['Valor_MaoObra'] = df_exib['Valor_MaoObra'].apply(formatar_moeda)
            df_exib['Valor_Material'] = df_exib['Valor_Material'].apply(formatar_moeda)
            
            st.dataframe(
                df_exib,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Fornecedor": st.column_config.TextColumn("Fornecedor", width="large"),
                    "Qtd_Contratos": st.column_config.NumberColumn("Qtd. Contratos", format="%d"),
                    "Valor_Total": st.column_config.TextColumn("Valor Total"),
                    "Valor_MaoObra": st.column_config.TextColumn("Valor Mão de Obra"),
                    "Valor_Material": st.column_config.TextColumn("Valor Material"),
                }
            )
            
            # Gráfico de barras - Top 10 fornecedores por valor
            st.markdown("#### Top 10 Fornecedores por Valor Total")
            df_top10 = df_fornecedor.head(10)
            fig = px.bar(
                df_top10,
                x='Fornecedor',
                y='Valor_Total',
                title="Top 10 Fornecedores por Valor Total",
                labels={'Valor_Total': 'Valor Total (R$)', 'Fornecedor': 'Fornecedor'},
            )
            fig.update_xaxes(tickangle=-45)
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhum dado disponível para análise por fornecedor.")
    
    with tab2:
        st.markdown("### 📅 Indicadores por Período")
        df_periodo = calcular_indicadores_por_periodo(df)
        
        if not df_periodo.empty:
            # Formatar valores para exibição
            df_exib = df_periodo.copy()
            df_exib['Valor_Total'] = df_exib['Valor_Total'].apply(formatar_moeda)
            df_exib['Valor_MaoObra'] = df_exib['Valor_MaoObra'].apply(formatar_moeda)
            df_exib['Valor_Material'] = df_exib['Valor_Material'].apply(formatar_moeda)
            
            st.dataframe(
                df_exib,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Período": st.column_config.TextColumn("Período", width="medium"),
                    "Qtd_Contratos": st.column_config.NumberColumn("Qtd. Contratos", format="%d"),
                    "Valor_Total": st.column_config.TextColumn("Valor Total"),
                    "Valor_MaoObra": st.column_config.TextColumn("Valor Mão de Obra"),
                    "Valor_Material": st.column_config.TextColumn("Valor Material"),
                }
            )
            
            # Gráfico de linha - Evolução do valor total
            st.markdown("#### Evolução do Valor Total por Período")
            fig = px.line(
                df_periodo,
                x='Período',
                y='Valor_Total',
                markers=True,
                title="Evolução do Valor Total de Contratos",
                labels={'Valor_Total': 'Valor Total (R$)', 'Período': 'Período'},
            )
            fig.update_xaxes(tickangle=-45)
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
            
            # Gráfico de barras empilhadas - Mão de obra vs Material
            st.markdown("#### Composição: Mão de Obra vs Material")
            df_comp = df_periodo[['Período', 'Valor_MaoObra', 'Valor_Material']].copy()
            df_comp = df_comp.set_index('Período')
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df_comp.index,
                y=df_comp['Valor_MaoObra'],
                name='Mão de Obra',
                marker_color='#1f77b4'
            ))
            fig.add_trace(go.Bar(
                x=df_comp.index,
                y=df_comp['Valor_Material'],
                name='Material',
                marker_color='#ff7f0e'
            ))
            fig.update_layout(
                barmode='stack',
                title="Composição de Valores por Período",
                xaxis_title="Período",
                yaxis_title="Valor (R$)",
                height=400
            )
            fig.update_xaxes(tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhum dado disponível para análise por período.")
    
    with tab3:
        st.markdown("### 📋 Indicadores por Status")
        df_status = calcular_indicadores_por_status(df)
        
        if not df_status.empty:
            # Formatar valores para exibição
            df_exib = df_status[['Status_PT', 'Qtd_Contratos', 'Valor_Total', 'Valor_MaoObra', 'Valor_Material']].copy()
            df_exib.columns = ['Status', 'Qtd_Contratos', 'Valor_Total', 'Valor_MaoObra', 'Valor_Material']
            df_exib['Valor_Total'] = df_exib['Valor_Total'].apply(formatar_moeda)
            df_exib['Valor_MaoObra'] = df_exib['Valor_MaoObra'].apply(formatar_moeda)
            df_exib['Valor_Material'] = df_exib['Valor_Material'].apply(formatar_moeda)
            
            st.dataframe(
                df_exib,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Status": st.column_config.TextColumn("Status", width="medium"),
                    "Qtd_Contratos": st.column_config.NumberColumn("Qtd. Contratos", format="%d"),
                    "Valor_Total": st.column_config.TextColumn("Valor Total"),
                    "Valor_MaoObra": st.column_config.TextColumn("Valor Mão de Obra"),
                    "Valor_Material": st.column_config.TextColumn("Valor Material"),
                }
            )
            
            # Gráfico de pizza - Distribuição por status
            st.markdown("#### Distribuição de Contratos por Status")
            fig = px.pie(
                df_status,
                values='Qtd_Contratos',
                names='Status_PT',
                title="Distribuição de Contratos por Status",
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhum dado disponível para análise por status.")
    
    with tab4:
        st.markdown("### 🔍 Detalhamento dos Contratos")
        
        # Preparar dados para exibição
        df_detalhe = df[[
            'Numero_Contrato',
            'Fornecedor',
            'Responsavel',
            'Status',
            'Data_Contrato',
            'Data_Inicio_Contrato',
            'Data_Final_Contrato',
            'Valor_Total',
            'Total_MaoObra',
            'Total_Material',
            'Objeto'
        ]].copy()
        
        # Formatar datas
        for col in ['Data_Contrato', 'Data_Inicio_Contrato', 'Data_Final_Contrato']:
            if col in df_detalhe.columns:
                df_detalhe[col] = pd.to_datetime(df_detalhe[col]).dt.strftime('%d/%m/%Y')
        
        # Formatar valores
        df_detalhe['Valor_Total'] = df_detalhe['Valor_Total'].apply(formatar_moeda)
        df_detalhe['Total_MaoObra'] = df_detalhe['Total_MaoObra'].apply(formatar_moeda)
        df_detalhe['Total_Material'] = df_detalhe['Total_Material'].apply(formatar_moeda)
        
        # Mapear status
        status_map = {
            'PARTIALLY_MEASURED': 'Parcialmente Medido',
            'COMPLETED': 'Concluído',
            'RESCINDED': 'Rescindido',
            'PENDING': 'Pendente',
            'FULLY_MEASURED': 'Totalmente Medido',
        }
        df_detalhe['Status'] = df_detalhe['Status'].map(status_map).fillna(df_detalhe['Status'])
        
        # Renomear colunas
        df_detalhe.columns = [
            'Número do Contrato',
            'Fornecedor',
            'Responsável',
            'Status',
            'Data do Contrato',
            'Data Início',
            'Data Final',
            'Valor Total',
            'Valor Mão de Obra',
            'Valor Material',
            'Objeto'
        ]
        
        st.dataframe(
            df_detalhe,
            use_container_width=True,
            hide_index=True,
        )

