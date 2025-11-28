"""
Dashboard Compras - Monitoramento de compras e fornecedores.
"""

import streamlit as st
import pandas as pd
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

from dashboard.utils.md_conn import get_md_connection


@st.cache_data(ttl=300)
def load_pedidos_compras(
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    comprador: Optional[List[str]] = None,
    empreendimento: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Carrega dados de pedidos de compras do banco reservas.
    
    Args:
        data_inicio: Data inicial (YYYY-MM-DD)
        data_fim: Data final (YYYY-MM-DD)
        comprador: Lista de compradores para filtrar
        empreendimento: Lista de empreendimentos para filtrar
        
    Returns:
        DataFrame com dados de pedidos de compras
    """
    md_conn = get_md_connection()
    
    # Construir filtros
    filters = []
    params = []
    
    if data_inicio:
        filters.append("Data_Pedido >= ?")
        params.append(data_inicio)
    
    if data_fim:
        filters.append("Data_Pedido <= ?")
        params.append(data_fim)
    
    if comprador and len(comprador) > 0:
        placeholders = ','.join(['?' for _ in comprador])
        filters.append(f"Comprador IN ({placeholders})")
        params.extend(comprador)
    
    if empreendimento and len(empreendimento) > 0:
        # Se for lista de IDs, usar IN
        if all(isinstance(e, (int, str)) and str(e).isdigit() for e in empreendimento):
            placeholders = ','.join(['?' for _ in empreendimento])
            filters.append(f"ID_Empreendimento IN ({placeholders})")
            params.extend([int(e) if isinstance(e, str) and e.isdigit() else e for e in empreendimento])
        else:
            # Se for lista de nomes, fazer JOIN com reservas_abril
            # Mas por enquanto, vamos usar ID_Empreendimento
            pass
    
    filter_sql = " AND ".join(filters) if filters else "1=1"
    
    # Query para obter dados com nome do empreendimento
    sql = f"""
    SELECT 
        pc.ID_Pedido,
        pc.Status,
        pc.Atrasado,
        pc.ID_Fornecedor,
        pc.ID_Empreendimento,
        COALESCE(
            (SELECT DISTINCT empreendimento 
             FROM reservas.main.reservas_abril 
             WHERE idempreendimento = pc.ID_Empreendimento 
             LIMIT 1),
            CAST(pc.ID_Empreendimento AS VARCHAR)
        ) AS Empreendimento,
        pc.Comprador,
        pc.Data_Pedido::DATE AS Data_Pedido,
        pc.Notas AS Titulo,
        COALESCE(pc.Desconto, 0) AS Desconto,
        COALESCE(pc.Acrescimos, 0) AS Acrescimos,
        COALESCE(pc.Valor_Total, 0) AS Valor_Total,
        COALESCE(pc.Total_Frete, 0) AS Total_Frete
    FROM reservas.main.sienge_pedidos_compras pc
    WHERE {filter_sql}
    ORDER BY pc.Data_Pedido DESC
    """
    
    try:
        df = md_conn.run_query(sql, params)
        
        # Converter Data_Pedido para datetime se necessário
        if 'Data_Pedido' in df.columns and not df.empty:
            df['Data_Pedido'] = pd.to_datetime(df['Data_Pedido'], errors='coerce')
        
        return df
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados: {str(e)}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_unique_compradores() -> List[str]:
    """Obtém lista única de compradores."""
    md_conn = get_md_connection()
    sql = """
    SELECT DISTINCT Comprador
    FROM reservas.main.sienge_pedidos_compras
    WHERE Comprador IS NOT NULL
    ORDER BY Comprador
    """
    df = md_conn.run_query(sql)
    return df['Comprador'].tolist() if not df.empty else []


@st.cache_data(ttl=300)
def get_unique_empreendimentos() -> List[Dict[str, Any]]:
    """Obtém lista única de empreendimentos com ID e nome."""
    md_conn = get_md_connection()
    sql = """
    SELECT DISTINCT 
        pc.ID_Empreendimento,
        COALESCE(
            (SELECT DISTINCT empreendimento 
             FROM reservas.main.reservas_abril 
             WHERE idempreendimento = pc.ID_Empreendimento 
             LIMIT 1),
            CAST(pc.ID_Empreendimento AS VARCHAR)
        ) AS Empreendimento
    FROM reservas.main.sienge_pedidos_compras pc
    WHERE pc.ID_Empreendimento IS NOT NULL
    ORDER BY Empreendimento
    """
    df = md_conn.run_query(sql)
    
    if df.empty:
        return []
    
    return [
        {"id": int(row['ID_Empreendimento']), "nome": str(row['Empreendimento'])}
        for _, row in df.iterrows()
    ]


def calcular_indicadores(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calcula indicadores principais de compras.
    
    Args:
        df: DataFrame com dados de pedidos de compras
        
    Returns:
        Dicionário com indicadores calculados
    """
    if df.empty:
        return {
            'valor_descontos': 0.0,
            'valor_pedidos': 0.0,
            'percentual_desconto': 0.0,
            'total_pedidos': 0,
            'pedidos_atrasados': 0,
            'percentual_atrasados': 0.0,
            'valor_medio_pedido': 0.0,
        }
    
    # Calcular indicadores
    valor_descontos = float(df['Desconto'].sum())
    valor_pedidos = float(df['Valor_Total'].sum())
    
    # % desconto = (Valor_Descontos / Valor_Pedidos_Compra) * 100
    percentual_desconto = (valor_descontos / valor_pedidos * 100) if valor_pedidos > 0 else 0.0
    
    total_pedidos = len(df)
    pedidos_atrasados = int(df['Atrasado'].sum()) if 'Atrasado' in df.columns else 0
    percentual_atrasados = (pedidos_atrasados / total_pedidos * 100) if total_pedidos > 0 else 0.0
    valor_medio_pedido = float(df['Valor_Total'].mean()) if not df.empty else 0.0
    
    return {
        'valor_descontos': valor_descontos,
        'valor_pedidos': valor_pedidos,
        'percentual_desconto': percentual_desconto,
        'total_pedidos': total_pedidos,
        'pedidos_atrasados': pedidos_atrasados,
        'percentual_atrasados': percentual_atrasados,
        'valor_medio_pedido': valor_medio_pedido,
    }


def formatar_moeda(valor: float) -> str:
    """Formata valor como moeda brasileira."""
    if pd.isna(valor) or valor == 0:
        return "R$ 0,00"
    # Formatar com separador de milhares e decimais brasileiros
    valor_str = f"{valor:,.2f}"
    # Separar parte inteira e decimal
    partes = valor_str.split('.')
    parte_inteira = partes[0].replace(',', '.')
    parte_decimal = partes[1] if len(partes) > 1 else '00'
    return f"R$ {parte_inteira},{parte_decimal}"


def formatar_percentual(valor: float) -> str:
    """Formata valor como percentual."""
    return f"{valor:.2f}%"


def render_compras_dashboard(
    *,
    show_title: bool = True,
    show_caption: bool = True,
):
    """
    Renderiza o dashboard de Compras.

    Args:
        show_title: Exibe título principal.
        show_caption: Exibe legenda/logo abaixo do título.
    """
    if show_title:
        st.title("🛒 Dashboard de Compras")
        if show_caption:
            st.caption("Monitoramento de compras e fornecedores")

    # Sidebar - Filtros
    with st.sidebar:
        st.header("🔍 Filtros")
        
        # Filtro de período
        st.subheader("Período")
        default_inicio = datetime(2025, 1, 1)
        default_fim = datetime.now()

        data_inicio = st.date_input(
            "Data Inicial",
            value=default_inicio,
            key="compras_data_inicio"
        )

        data_fim = st.date_input(
            "Data Final",
            value=default_fim,
            key="compras_data_fim"
        )
        
        # Filtro de comprador
        st.subheader("Comprador")
        compradores_disponiveis = get_unique_compradores()
        comprador_selecionado = st.multiselect(
            "Selecione o(s) comprador(es)",
            options=compradores_disponiveis,
            key="compras_comprador"
        )
        
        # Filtro de empreendimento
        st.subheader("Empreendimento")
        empreendimentos_disponiveis = get_unique_empreendimentos()
        empreendimento_opcoes = [f"{e['nome']} (ID: {e['id']})" for e in empreendimentos_disponiveis]
        empreendimento_selecionado = st.multiselect(
            "Selecione o(s) empreendimento(s)",
            options=empreendimento_opcoes,
            key="compras_empreendimento"
        )
        
        # Extrair IDs dos empreendimentos selecionados
        empreendimento_ids = []
        if empreendimento_selecionado:
            for sel in empreendimento_selecionado:
                # Extrair ID do formato "Nome (ID: X)"
                try:
                    id_str = sel.split("ID: ")[1].rstrip(")")
                    empreendimento_ids.append(int(id_str))
                except:
                    pass
        
        # Filtro de título (Notas)
        st.subheader("Título")
        titulo_filtro = st.text_input(
            "Buscar por título (Notas)",
            key="compras_titulo",
            placeholder="Digite parte do título..."
        )
    
    # Carregar dados
    with st.spinner("Carregando dados de compras..."):
        df = load_pedidos_compras(
            data_inicio=data_inicio.strftime('%Y-%m-%d') if data_inicio else None,
            data_fim=data_fim.strftime('%Y-%m-%d') if data_fim else None,
            comprador=comprador_selecionado if comprador_selecionado else None,
            empreendimento=empreendimento_ids if empreendimento_ids else None,
        )
        
        # Aplicar filtro de título se fornecido
        if titulo_filtro and not df.empty:
            df = df[df['Titulo'].astype(str).str.contains(titulo_filtro, case=False, na=False)]
    
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
            "Valor de Compras",
            formatar_moeda(indicadores['valor_pedidos']),
            help="Soma do valor total de todos os pedidos de compra"
        )
    
    with col2:
        st.metric(
            "Valor de Descontos",
            formatar_moeda(indicadores['valor_descontos']),
            help="Soma total de descontos aplicados"
        )
    
    with col3:
        st.metric(
            "% de Desconto",
            formatar_percentual(indicadores['percentual_desconto']),
            help="Percentual de desconto em relação ao valor total dos pedidos"
        )
    
    with col4:
        st.metric(
            "Total de Pedidos",
            f"{indicadores['total_pedidos']:,}",
            help="Quantidade total de pedidos de compra"
        )
    
    # Seção 2: KPIs Secundários
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Pedidos Atrasados",
            f"{indicadores['pedidos_atrasados']:,}",
            f"{formatar_percentual(indicadores['percentual_atrasados'])}",
            help="Quantidade e percentual de pedidos atrasados"
        )
    
    with col2:
        st.metric(
            "Valor Médio por Pedido",
            formatar_moeda(indicadores['valor_medio_pedido']),
            help="Valor médio de cada pedido de compra"
        )
    
    with col3:
        # Calcular % comprado no prazo (-2 dias)
        # Por enquanto, vamos usar o status para determinar
        if 'Status' in df.columns:
            status_entregue = df[df['Status'].str.contains('DELIVERED', case=False, na=False)]
            total_entregue = len(status_entregue)
            percentual_entregue = (total_entregue / len(df) * 100) if len(df) > 0 else 0.0
            st.metric(
                "Pedidos Entregues",
                f"{total_entregue:,}",
                f"{formatar_percentual(percentual_entregue)}",
                help="Quantidade e percentual de pedidos entregues"
            )
        else:
            st.metric("Pedidos Entregues", "—", help="Dados não disponíveis")
    
    # Seção 3: Análises Adicionais
    st.markdown("---")
    st.subheader("📈 Análises Detalhadas")
    
    # Tabs para diferentes análises
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Por Comprador",
        "🏢 Por Empreendimento",
        "📅 Timeline",
        "📋 Detalhamento"
    ])
    
    with tab1:
        st.subheader("Análise por Comprador")
        
        if 'Comprador' in df.columns:
            analise_comprador = df.groupby('Comprador').agg({
                'Valor_Total': ['sum', 'mean', 'count'],
                'Desconto': 'sum',
            }).reset_index()
            
            analise_comprador.columns = ['Comprador', 'Valor_Total', 'Valor_Medio', 'Qtd_Pedidos', 'Total_Desconto']
            analise_comprador['%_Desconto'] = (analise_comprador['Total_Desconto'] / analise_comprador['Valor_Total'] * 100).fillna(0)
            analise_comprador = analise_comprador.sort_values('Valor_Total', ascending=False)
            
            # Formatação
            analise_comprador['Valor_Total'] = analise_comprador['Valor_Total'].apply(formatar_moeda)
            analise_comprador['Valor_Medio'] = analise_comprador['Valor_Medio'].apply(formatar_moeda)
            analise_comprador['Total_Desconto'] = analise_comprador['Total_Desconto'].apply(formatar_moeda)
            analise_comprador['%_Desconto'] = analise_comprador['%_Desconto'].apply(formatar_percentual)
            
            st.dataframe(
                analise_comprador,
                use_container_width=True,
                hide_index=True
            )
            
            # Gráfico (usar valores numéricos antes da formatação)
            analise_comprador_num = df.groupby('Comprador').agg({
                'Valor_Total': 'sum',
            }).reset_index().sort_values('Valor_Total', ascending=False).head(10)
            
            fig = px.bar(
                analise_comprador_num,
                x='Comprador',
                y='Valor_Total',
                title='Top 10 Compradores por Valor Total',
                labels={'Valor_Total': 'Valor Total (R$)', 'Comprador': 'Comprador'}
            )
            fig.update_yaxes(tickformat='$,.2f')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Dados de comprador não disponíveis.")
    
    with tab2:
        st.subheader("Análise por Empreendimento")
        
        if 'Empreendimento' in df.columns:
            analise_empreendimento = df.groupby('Empreendimento').agg({
                'Valor_Total': ['sum', 'mean', 'count'],
                'Desconto': 'sum',
            }).reset_index()
            
            analise_empreendimento.columns = ['Empreendimento', 'Valor_Total', 'Valor_Medio', 'Qtd_Pedidos', 'Total_Desconto']
            analise_empreendimento['%_Desconto'] = (analise_empreendimento['Total_Desconto'] / analise_empreendimento['Valor_Total'] * 100).fillna(0)
            analise_empreendimento = analise_empreendimento.sort_values('Valor_Total', ascending=False)
            
            # Formatação
            analise_empreendimento['Valor_Total'] = analise_empreendimento['Valor_Total'].apply(formatar_moeda)
            analise_empreendimento['Valor_Medio'] = analise_empreendimento['Valor_Medio'].apply(formatar_moeda)
            analise_empreendimento['Total_Desconto'] = analise_empreendimento['Total_Desconto'].apply(formatar_moeda)
            analise_empreendimento['%_Desconto'] = analise_empreendimento['%_Desconto'].apply(formatar_percentual)
            
            st.dataframe(
                analise_empreendimento,
                use_container_width=True,
                hide_index=True
            )
            
            # Gráfico (usar valores numéricos antes da formatação)
            analise_empreendimento_num = df.groupby('Empreendimento').agg({
                'Valor_Total': 'sum',
            }).reset_index().sort_values('Valor_Total', ascending=False).head(10)
            
            fig = px.bar(
                analise_empreendimento_num,
                x='Empreendimento',
                y='Valor_Total',
                title='Top 10 Empreendimentos por Valor Total',
                labels={'Valor_Total': 'Valor Total (R$)', 'Empreendimento': 'Empreendimento'}
            )
            fig.update_yaxes(tickformat='$,.2f')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Dados de empreendimento não disponíveis.")
    
    with tab3:
        st.subheader("Timeline de Compras")
        
        if 'Data_Pedido' in df.columns and not df.empty:
            # Agrupar por mês
            df_timeline = df.copy()
            df_timeline['Mes'] = df_timeline['Data_Pedido'].dt.to_period('M').astype(str)
            
            timeline_agg = df_timeline.groupby('Mes').agg({
                'Valor_Total': 'sum',
                'Desconto': 'sum',
                'ID_Pedido': 'count'
            }).reset_index()
            
            timeline_agg.columns = ['Mes', 'Valor_Total', 'Total_Desconto', 'Qtd_Pedidos']
            timeline_agg = timeline_agg.sort_values('Mes')
            timeline_agg['Percentual_Desconto'] = timeline_agg.apply(
                lambda row: (row['Total_Desconto'] / row['Valor_Total'] * 100)
                if row['Valor_Total'] else 0.0,
                axis=1
            )
            
            # Gráfico de linha
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=timeline_agg['Mes'],
                y=timeline_agg['Valor_Total'],
                mode='lines+markers',
                name='Valor Total',
                line=dict(color='#1f77b4', width=2)
            ))
            fig.add_trace(go.Scatter(
                x=timeline_agg['Mes'],
                y=timeline_agg['Total_Desconto'],
                mode='lines+markers',
                name='Total Descontos',
                line=dict(color='#ff7f0e', width=2)
            ))
            
            fig.update_layout(
                title='Evolução de Compras ao Longo do Tempo',
                xaxis_title='Mês',
                yaxis_title='Valor (R$)',
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabela
            timeline_agg['Valor_Total'] = timeline_agg['Valor_Total'].apply(formatar_moeda)
            timeline_agg['Total_Desconto'] = timeline_agg['Total_Desconto'].apply(formatar_moeda)
            timeline_agg['Percentual_Desconto'] = timeline_agg['Percentual_Desconto'].apply(formatar_percentual)
            
            st.dataframe(
                timeline_agg,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Dados de data não disponíveis.")
    
    with tab4:
        st.subheader("Detalhamento de Pedidos")
        
        # Colunas para exibir
        colunas_display = [
            'ID_Pedido', 'Data_Pedido', 'Comprador', 'Empreendimento',
            'Status', 'Atrasado', 'Valor_Total', 'Desconto', 'Titulo'
        ]
        
        colunas_disponiveis = [col for col in colunas_display if col in df.columns]
        
        df_display = df[colunas_disponiveis].copy()
        
        # Formatação
        if 'Valor_Total' in df_display.columns:
            df_display['Valor_Total'] = df_display['Valor_Total'].apply(formatar_moeda)
        if 'Desconto' in df_display.columns:
            df_display['Desconto'] = df_display['Desconto'].apply(formatar_moeda)
        if 'Atrasado' in df_display.columns:
            df_display['Atrasado'] = df_display['Atrasado'].map({True: 'Sim', False: 'Não'})
        
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True
        )
        
        # Botão de download
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"pedidos_compras_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
