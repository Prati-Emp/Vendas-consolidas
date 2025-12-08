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
    
    # Sempre excluir fornecedores Pozza e Marlós
    filters.append("UPPER(Fornecedor) NOT LIKE '%POZZA%' AND UPPER(Fornecedor) NOT LIKE '%MARLOS%'")
    
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
    
    where_clause = f"WHERE {' AND '.join(filters)}"
    
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
        df = md_conn.run_query(query, params if params else None)
        
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
    
    # Sempre excluir fornecedores Pozza e Marlós
    filters.append("UPPER(Fornecedor) NOT LIKE '%POZZA%' AND UPPER(Fornecedor) NOT LIKE '%MARLOS%'")
    
    if data_inicio:
        filters.append("Data_Contrato >= ?")
        params.append(data_inicio)
    
    if data_fim:
        filters.append("Data_Contrato <= ?")
        params.append(data_fim)
    
    where_clause = f"WHERE {' AND '.join(filters)}"
    
    query = f"""
        SELECT DISTINCT Fornecedor
        FROM reservas.main.sienge_contratos_suprimentos
        {where_clause}
        ORDER BY Fornecedor
    """
    
    try:
        df = md_conn.run_query(query, params if params else None)
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
        df = md_conn.run_query(query, params if params else None)
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
            'prazo_medio_dias': 0,
            'contratos_proximos_termino_30': 0,
            'contratos_proximos_termino_60': 0,
            'contratos_proximos_termino_90': 0,
        }
    
    # Calcular prazo médio (diferença entre data final e data início)
    df_prazo = df.copy()
    if 'Data_Final_Contrato' in df_prazo.columns and 'Data_Inicio_Contrato' in df_prazo.columns:
        df_prazo['Prazo_Dias'] = (df_prazo['Data_Final_Contrato'] - df_prazo['Data_Inicio_Contrato']).dt.days
        prazo_medio = df_prazo['Prazo_Dias'].mean()
        prazo_medio = prazo_medio if pd.notna(prazo_medio) else 0
    else:
        prazo_medio = 0
    
    # Calcular contratos próximos de terminar
    hoje = pd.Timestamp.now().normalize()
    contratos_30 = 0
    contratos_60 = 0
    contratos_90 = 0
    
    if 'Data_Final_Contrato' in df.columns:
        # Filtrar apenas contratos ativos (não concluídos nem rescindidos)
        df_ativos = df[df['Status'].isin(['PARTIALLY_MEASURED', 'PENDING', 'FULLY_MEASURED'])]
        
        if not df_ativos.empty:
            # Contratos que terminam nos próximos 30 dias
            data_30 = hoje + timedelta(days=30)
            contratos_30 = len(df_ativos[
                (df_ativos['Data_Final_Contrato'] >= hoje) & 
                (df_ativos['Data_Final_Contrato'] <= data_30)
            ])
            
            # Contratos que terminam nos próximos 60 dias
            data_60 = hoje + timedelta(days=60)
            contratos_60 = len(df_ativos[
                (df_ativos['Data_Final_Contrato'] >= hoje) & 
                (df_ativos['Data_Final_Contrato'] <= data_60)
            ])
            
            # Contratos que terminam nos próximos 90 dias
            data_90 = hoje + timedelta(days=90)
            contratos_90 = len(df_ativos[
                (df_ativos['Data_Final_Contrato'] >= hoje) & 
                (df_ativos['Data_Final_Contrato'] <= data_90)
            ])
    
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
        'prazo_medio_dias': int(prazo_medio),
        'contratos_proximos_termino_30': contratos_30,
        'contratos_proximos_termino_60': contratos_60,
        'contratos_proximos_termino_90': contratos_90,
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


def obter_contratos_proximos_termino(df: pd.DataFrame, dias: int = 30) -> pd.DataFrame:
    """Retorna contratos que estão próximos de terminar."""
    if df.empty or 'Data_Final_Contrato' not in df.columns:
        return pd.DataFrame()
    
    hoje = pd.Timestamp.now().normalize()
    data_limite = hoje + timedelta(days=dias)
    
    # Filtrar apenas contratos ativos
    df_ativos = df[df['Status'].isin(['PARTIALLY_MEASURED', 'PENDING', 'FULLY_MEASURED'])]
    
    # Filtrar contratos que terminam no período
    df_proximos = df_ativos[
        (df_ativos['Data_Final_Contrato'] >= hoje) & 
        (df_ativos['Data_Final_Contrato'] <= data_limite)
    ].copy()
    
    if df_proximos.empty:
        return pd.DataFrame()
    
    # Calcular dias restantes
    df_proximos['Dias_Restantes'] = (df_proximos['Data_Final_Contrato'] - hoje).dt.days
    
    # Ordenar por data final (mais próximos primeiro)
    df_proximos = df_proximos.sort_values('Data_Final_Contrato')
    
    return df_proximos


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
        # Data inicial: 1º de janeiro do ano corrente
        ano_corrente = datetime.now().year
        default_inicio = datetime(ano_corrente, 1, 1)
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
    
    # Terceira linha de KPIs - Prazos
    st.markdown("---")
    st.subheader("⏱️ Análise de Prazos")
    
    col9, col10, col11, col12 = st.columns(4)
    
    with col9:
        prazo_medio_meses = indicadores['prazo_medio_dias'] / 30.0 if indicadores['prazo_medio_dias'] > 0 else 0
        st.metric(
            "Prazo Médio",
            f"{indicadores['prazo_medio_dias']:,} dias",
            help=f"Prazo médio dos contratos ({prazo_medio_meses:.1f} meses)"
        )
    
    with col10:
        st.metric(
            "Próximos 30 dias",
            f"{indicadores['contratos_proximos_termino_30']:,}",
            help="Contratos ativos que terminam nos próximos 30 dias"
        )
    
    with col11:
        st.metric(
            "Próximos 60 dias",
            f"{indicadores['contratos_proximos_termino_60']:,}",
            help="Contratos ativos que terminam nos próximos 60 dias"
        )
    
    with col12:
        st.metric(
            "Próximos 90 dias",
            f"{indicadores['contratos_proximos_termino_90']:,}",
            help="Contratos ativos que terminam nos próximos 90 dias"
        )
    
    # Seção 2: Análises Detalhadas
    st.markdown("---")
    st.subheader("📈 Análises Detalhadas")
    
    # Tabs para diferentes análises
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Por Fornecedor",
        "📅 Por Período",
        "📋 Por Status",
        "⏰ Próximos de Terminar",
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
            
            # Gráfico de barras horizontais - Top 10 fornecedores por valor
            st.markdown("#### Top 10 Fornecedores por Valor Total")
            df_top10 = df_fornecedor.head(10).sort_values('Valor_Total', ascending=True)
            
            # Calcular percentual do valor total
            valor_total_geral = df_fornecedor['Valor_Total'].sum()
            df_top10['Percentual'] = (df_top10['Valor_Total'] / valor_total_geral * 100).round(2)
            
            fig = go.Figure()
            
            # Adicionar barras com percentual dentro
            max_x = df_top10['Valor_Total'].max()
            
            fig.add_trace(go.Bar(
                y=df_top10['Fornecedor'],
                x=df_top10['Valor_Total'],
                orientation='h',
                marker_color='#1f77b4',
                marker_line_width=0,
                text=[f"{p:.2f}%" for p in df_top10['Percentual']],
                textposition='inside',
                textfont=dict(color='white', size=12, weight='bold'),
                name='Valor Total',
                hovertemplate='<b>%{y}</b><br>Valor: %{x:,.2f}<br>Percentual: %{text}<extra></extra>',
                width=0.9  # Largura das barras (aumentada)
            ))
            
            # Criar anotações com valores monetários
            annotations = []
            for idx, row in df_top10.iterrows():
                annotations.append(
                    dict(
                        xref='x',
                        yref='y',
                        x=row['Valor_Total'],
                        y=row['Fornecedor'],
                        text=formatar_moeda(row['Valor_Total']),
                        showarrow=False,
                        xanchor='left',
                        xshift=15,
                        font=dict(color='white', size=11, weight='bold'),
                        bgcolor='rgba(0,0,0,0.7)',
                        bordercolor='rgba(255,255,255,0.4)',
                        borderwidth=1.5,
                        borderpad=6
                    )
                )
            
            fig.update_layout(
                title=None,  # Remover título do gráfico
                xaxis_title="Valor Total (R$)",
                yaxis_title=None,  # Remover label do eixo Y
                height=450,
                showlegend=False,
                margin=dict(l=200, r=250, t=20, b=50),  # Reduzir margem superior
                bargap=0.15,  # Reduzir espaçamento entre barras para barras mais largas
                xaxis=dict(range=[0, max_x * 1.5]),  # Expandir eixo X para acomodar os valores
                yaxis={'categoryorder': 'total ascending', 'title': None},  # Remover título do eixo Y
                annotations=annotations,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            
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
            
            # Gráfico de barras - Distribuição por status
            st.markdown("#### Distribuição de Contratos por Status")
            
            # Calcular percentual
            total_contratos = df_status['Qtd_Contratos'].sum()
            df_status['Percentual'] = (df_status['Qtd_Contratos'] / total_contratos * 100).round(2)
            
            # Ordenar por quantidade
            df_status_sorted = df_status.sort_values('Qtd_Contratos', ascending=True)
            
            fig = go.Figure()
            
            # Adicionar barras com percentual dentro
            max_x = df_status_sorted['Qtd_Contratos'].max()
            
            fig.add_trace(go.Bar(
                y=df_status_sorted['Status_PT'],
                x=df_status_sorted['Qtd_Contratos'],
                orientation='h',
                marker_color='#1f77b4',
                marker_line_width=0,
                text=[f"{p:.2f}%" for p in df_status_sorted['Percentual']],
                textposition='inside',
                textfont=dict(color='white', size=13, weight='bold'),
                name='Quantidade',
                hovertemplate='<b>%{y}</b><br>Quantidade: %{x}<br>Percentual: %{text}<extra></extra>',
                width=0.7  # Largura das barras (0.7 = 70% do espaço disponível)
            ))
            
            # Criar anotações com valores monetários
            annotations = []
            for idx, row in df_status_sorted.iterrows():
                annotations.append(
                    dict(
                        xref='x',
                        yref='y',
                        x=row['Qtd_Contratos'],
                        y=row['Status_PT'],
                        text=formatar_moeda(row['Valor_Total']),
                        showarrow=False,
                        xanchor='left',
                        xshift=15,
                        font=dict(color='white', size=12, weight='bold'),
                        bgcolor='rgba(0,0,0,0.7)',
                        bordercolor='rgba(255,255,255,0.4)',
                        borderwidth=1.5,
                        borderpad=6
                    )
                )
            
            fig.update_layout(
                title="Distribuição de Contratos por Status",
                xaxis_title="Quantidade de Contratos",
                yaxis_title="Status",
                height=450,
                showlegend=False,
                margin=dict(l=150, r=250, t=50, b=50),
                bargap=0.3,  # Espaçamento entre barras (menor = barras mais próximas)
                xaxis=dict(range=[0, max_x * 1.5]),  # Expandir eixo X para acomodar os valores
                annotations=annotations,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhum dado disponível para análise por status.")
    
    with tab4:
        st.markdown("### ⏰ Contratos Próximos de Terminar")
        
        # Selecionar período
        periodo_selecionado = st.selectbox(
            "Selecione o período:",
            options=[30, 60, 90],
            format_func=lambda x: f"Próximos {x} dias",
            key="periodo_termino"
        )
        
        # Obter contratos próximos de terminar
        df_proximos = obter_contratos_proximos_termino(df, periodo_selecionado)
        
        if not df_proximos.empty:
            st.info(f"📊 Encontrados **{len(df_proximos)}** contratos que terminam nos próximos **{periodo_selecionado} dias**")
            
            # Preparar dados para exibição
            df_exib = df_proximos[[
                'Numero_Contrato',
                'Fornecedor',
                'Responsavel',
                'Status',
                'Data_Final_Contrato',
                'Dias_Restantes',
                'Valor_Total',
                'Total_MaoObra',
                'Total_Material',
                'Objeto'
            ]].copy()
            
            # Formatar datas
            df_exib['Data_Final_Contrato'] = pd.to_datetime(df_exib['Data_Final_Contrato']).dt.strftime('%d/%m/%Y')
            
            # Formatar valores
            df_exib['Valor_Total'] = df_exib['Valor_Total'].apply(formatar_moeda)
            df_exib['Total_MaoObra'] = df_exib['Total_MaoObra'].apply(formatar_moeda)
            df_exib['Total_Material'] = df_exib['Total_Material'].apply(formatar_moeda)
            
            # Mapear status
            status_map = {
                'PARTIALLY_MEASURED': 'Parcialmente Medido',
                'COMPLETED': 'Concluído',
                'RESCINDED': 'Rescindido',
                'PENDING': 'Pendente',
                'FULLY_MEASURED': 'Totalmente Medido',
            }
            df_exib['Status'] = df_exib['Status'].map(status_map).fillna(df_exib['Status'])
            
            # Renomear colunas
            df_exib.columns = [
                'Número do Contrato',
                'Fornecedor',
                'Responsável',
                'Status',
                'Data Final',
                'Dias Restantes',
                'Valor Total',
                'Valor Mão de Obra',
                'Valor Material',
                'Objeto'
            ]
            
            # Ordenar por dias restantes
            df_exib = df_exib.sort_values('Dias Restantes')
            
            st.dataframe(
                df_exib,
                use_container_width=True,
                hide_index=True,
            )
            
            # Resumo por faixa de dias (sempre usa 90 dias, independente do filtro)
            st.markdown("#### 📊 Resumo por Faixa de Dias Restantes")
            
            # Explicação didática sobre as faixas
            with st.expander("ℹ️ Como interpretar esta tabela?", expanded=False):
                st.markdown("""
                **📋 O que esta tabela mostra:**
                
                Esta tabela agrupa **todos os contratos que vencem nos próximos 90 dias** em faixas de tempo:
                
                - **0-15 dias**: Contratos que vencem entre hoje e os próximos 15 dias
                - **16-30 dias**: Contratos que vencem entre 16 e 30 dias a partir de hoje
                - **31-60 dias**: Contratos que vencem entre 31 e 60 dias a partir de hoje
                - **61-90 dias**: Contratos que vencem entre 61 e 90 dias a partir de hoje
                
                **💡 Importante:**
                
                Esta tabela **não é afetada pelo filtro acima**. Ela sempre mostra todos os contratos 
                que vencem nos próximos 90 dias, agrupados por faixas. Isso permite ter uma visão 
                completa de todos os vencimentos, independente do período selecionado na tabela acima.
                
                **📊 Na tabela:**
                
                Cada linha mostra apenas os contratos daquela faixa específica. Por exemplo:
                - A linha "0-15 dias" mostra apenas contratos que vencem nos próximos 15 dias
                - A linha "16-30 dias" mostra apenas contratos que vencem entre 16 e 30 dias
                
                Isso permite identificar rapidamente quais contratos precisam de atenção imediata!
                """)
            
            # Obter todos os contratos de até 90 dias para o resumo (independente do filtro)
            df_resumo_completo = obter_contratos_proximos_termino(df, dias=90)
            df_resumo = df_resumo_completo.copy()
            df_resumo['Faixa'] = pd.cut(
                df_resumo['Dias_Restantes'],
                bins=[0, 15, 30, 60, 90],
                labels=['0-15 dias', '16-30 dias', '31-60 dias', '61-90 dias'],
                include_lowest=True
            )
            
            df_faixa = df_resumo.groupby('Faixa').agg({
                'Numero_Contrato': 'nunique',
                'Valor_Total': 'sum'
            }).reset_index()
            df_faixa.columns = ['Faixa de Dias', 'Quantidade', 'Valor Total']
            df_faixa['Valor Total'] = df_faixa['Valor Total'].apply(formatar_moeda)
            
            st.dataframe(
                df_faixa,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Faixa de Dias": st.column_config.TextColumn("Faixa de Dias", width="medium"),
                    "Quantidade": st.column_config.NumberColumn("Quantidade", format="%d"),
                    "Valor Total": st.column_config.TextColumn("Valor Total"),
                }
            )
        else:
            st.info(f"✅ Nenhum contrato ativo termina nos próximos {periodo_selecionado} dias.")
    
    with tab5:
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

