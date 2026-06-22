"""
Página de Análises por Dimensões
Visualizações de barras por mídia, tipo de venda, imobiliária e corretores.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import List, Optional
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
if str(APP_DIR) not in sys.path:
    sys.path.append(str(APP_DIR))

from project_paths import ensure_dashboard_on_path

ensure_dashboard_on_path()
from advanced_auth import require_auth, require_page_access  # noqa: E402

# Importar utilitários locais
from utils.md_conn import get_analytics_by_dimension
from utils.formatters import (
    fmt_brl, 
    fmt_int, 
    fmt_percent,
    fmt_compact_currency
)

# Configuração da página
st.set_page_config(
    page_title="Análises por Dimensões - Vendas Consolidadas",
    page_icon="📊",
    layout="wide"
)

require_auth(dashboard_title="Dashboard de Vendas Consolidadas")
require_page_access("vendas")

# CSS customizado para a página
st.markdown("""
<style>
    .analyses-header {
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .chart-container {
        background-color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin: 0.5rem 0;
    }
    .export-section {
        background-color: #e3f2fd;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

def get_session_filters():
    """Obtém filtros da sessão principal."""
    return {
        'data_inicial': st.session_state.get('data_inicial'),
        'data_final': st.session_state.get('data_final'),
        'midia_selecionada': st.session_state.get('midia_selecionada', []),
        'tipovenda_selecionada': st.session_state.get('tipovenda_selecionada', [])
    }

def create_horizontal_bar_chart(df: pd.DataFrame, 
                               x_col: str, 
                               y_col: str, 
                               title: str,
                               color_col: Optional[str] = None) -> go.Figure:
    """
    Cria gráfico de barras horizontais.
    
    Args:
        df: DataFrame com dados
        x_col: Coluna para eixo X (valores)
        y_col: Coluna para eixo Y (categorias)
        title: Título do gráfico
        color_col: Coluna para cores (opcional)
        
    Returns:
        Figura do Plotly
    """
    fig = go.Figure()
    
    # Ordenar dados por valor
    df_sorted = df.sort_values(x_col, ascending=True)
    
    # Criar barras
    fig.add_trace(go.Bar(
        y=df_sorted[y_col],
        x=df_sorted[x_col],
        orientation='h',
        text=[fmt_brl(val) for val in df_sorted[x_col]],
        textposition='auto',
        hovertemplate='<b>%{y}</b><br>' +
                     f'{title}: R$ %{{x:,.2f}}<br>' +
                     'Qtd Vendas: %{customdata[0]}<br>' +
                     'Ticket Médio: R$ %{customdata[1]:,.2f}<extra></extra>',
        customdata=df_sorted[['qtd_vendas', 'ticket_medio']],
        marker=dict(
            color=df_sorted[x_col],
            colorscale='Blues',
            showscale=True,
            colorbar=dict(title="Valor (R$)")
        )
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title="Valor Total (R$)",
        yaxis_title="",
        height=max(400, len(df) * 30),  # Altura dinâmica baseada no número de itens
        template='plotly_white',
        showlegend=False
    )
    
    # Formatar eixo X como moeda
    fig.update_layout(xaxis_tickformat='R$ ,.0f')
    
    return fig

def create_vertical_bar_chart(df: pd.DataFrame, 
                             x_col: str, 
                             y_col: str, 
                             title: str) -> go.Figure:
    """
    Cria gráfico de barras verticais.
    
    Args:
        df: DataFrame com dados
        x_col: Coluna para eixo X (categorias)
        y_col: Coluna para eixo Y (valores)
        title: Título do gráfico
        
    Returns:
        Figura do Plotly
    """
    fig = go.Figure()
    
    # Ordenar dados por valor
    df_sorted = df.sort_values(y_col, ascending=False)
    
    # Criar barras
    fig.add_trace(go.Bar(
        x=df_sorted[x_col],
        y=df_sorted[y_col],
        text=[fmt_brl(val) for val in df_sorted[y_col]],
        textposition='auto',
        hovertemplate='<b>%{x}</b><br>' +
                     f'{title}: R$ %{{y:,.2f}}<br>' +
                     'Qtd Vendas: %{customdata[0]}<br>' +
                     'Ticket Médio: R$ %{customdata[1]:,.2f}<extra></extra>',
        customdata=df_sorted[['qtd_vendas', 'ticket_medio']],
        marker=dict(
            color=df_sorted[y_col],
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(title="Valor (R$)")
        )
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title="",
        yaxis_title="Valor Total (R$)",
        height=500,
        template='plotly_white',
        showlegend=False,
        xaxis_tickangle=-45
    )
    
    # Formatar eixo Y como moeda
    fig.update_layout(yaxis_tickformat='R$ ,.0f')
    
    return fig

def render_midia_analysis(filters: dict):
    """Renderiza análise por mídia."""
    st.markdown("## 📱 Análise por Mídia")
    
    with st.spinner("🔄 Carregando dados de mídia..."):
        try:
            midia_data = get_analytics_by_dimension(
                filters['data_inicial'],
                filters['data_final'],
                'midia',
                filters['midia_selecionada'],
                filters['tipovenda_selecionada'],
                limit=20
            )
            
            if midia_data.empty:
                st.warning("⚠️ Nenhum dado de mídia encontrado.")
                return
            
            # Gráfico de barras horizontais
            fig = create_horizontal_bar_chart(
                midia_data, 
                'total_valor', 
                'midia', 
                'Vendas por Mídia'
            )
            
            st.plotly_chart(fig, width='stretch')
            
            # Tabela resumo
            with st.expander("📋 Detalhes por Mídia"):
                display_data = midia_data.copy()
                display_data['total_valor'] = display_data['total_valor'].apply(fmt_brl)
                display_data['ticket_medio'] = display_data['ticket_medio'].apply(fmt_brl)
                display_data['qtd_vendas'] = display_data['qtd_vendas'].apply(fmt_int)
                display_data.columns = ['Mídia', 'Qtd Vendas', 'Valor Total', 'Ticket Médio']
                st.dataframe(display_data, width='stretch')
                
        except Exception as e:
            st.error(f"❌ Erro ao carregar dados de mídia: {str(e)}")

def render_tipovenda_analysis(filters: dict):
    """Renderiza análise por tipo de venda."""
    st.markdown("## 🏷️ Análise por Tipo de Venda")
    
    with st.spinner("🔄 Carregando dados de tipo de venda..."):
        try:
            tipovenda_data = get_analytics_by_dimension(
                filters['data_inicial'],
                filters['data_final'],
                'tipovenda',
                filters['midia_selecionada'],
                filters['tipovenda_selecionada'],
                limit=20
            )
            
            if tipovenda_data.empty:
                st.warning("⚠️ Nenhum dado de tipo de venda encontrado.")
                return
            
            # Gráfico de barras horizontais
            fig = create_horizontal_bar_chart(
                tipovenda_data, 
                'total_valor', 
                'tipovenda', 
                'Vendas por Tipo de Venda'
            )
            
            st.plotly_chart(fig, width='stretch')
            
            # Tabela resumo
            with st.expander("📋 Detalhes por Tipo de Venda"):
                display_data = tipovenda_data.copy()
                display_data['total_valor'] = display_data['total_valor'].apply(fmt_brl)
                display_data['ticket_medio'] = display_data['ticket_medio'].apply(fmt_brl)
                display_data['qtd_vendas'] = display_data['qtd_vendas'].apply(fmt_int)
                display_data.columns = ['Tipo de Venda', 'Qtd Vendas', 'Valor Total', 'Ticket Médio']
                st.dataframe(display_data, width='stretch')
                
        except Exception as e:
            st.error(f"❌ Erro ao carregar dados de tipo de venda: {str(e)}")

def render_imobiliaria_analysis(filters: dict):
    """Renderiza análise por imobiliária."""
    st.markdown("## 🏢 Análise por Imobiliária")
    
    with st.spinner("🔄 Carregando dados de imobiliárias..."):
        try:
            imobiliaria_data = get_analytics_by_dimension(
                filters['data_inicial'],
                filters['data_final'],
                'imobiliaria',
                filters['midia_selecionada'],
                filters['tipovenda_selecionada'],
                limit=15
            )
            
            if imobiliaria_data.empty:
                st.warning("⚠️ Nenhum dado de imobiliária encontrado.")
                return
            
            # Gráfico de barras verticais
            fig = create_vertical_bar_chart(
                imobiliaria_data, 
                'imobiliaria', 
                'total_valor', 
                'Top 15 Imobiliárias por Valor'
            )
            
            st.plotly_chart(fig, width='stretch')
            
            # Tabela resumo
            with st.expander("📋 Detalhes por Imobiliária"):
                display_data = imobiliaria_data.copy()
                display_data['total_valor'] = display_data['total_valor'].apply(fmt_brl)
                display_data['ticket_medio'] = display_data['ticket_medio'].apply(fmt_brl)
                display_data['qtd_vendas'] = display_data['qtd_vendas'].apply(fmt_int)
                display_data.columns = ['Imobiliária', 'Qtd Vendas', 'Valor Total', 'Ticket Médio']
                st.dataframe(display_data, width='stretch')
                
        except Exception as e:
            st.error(f"❌ Erro ao carregar dados de imobiliárias: {str(e)}")

def render_corretor_analysis(filters: dict):
    """Renderiza análise por corretor."""
    st.markdown("## 👥 Análise por Corretor")
    
    with st.spinner("🔄 Carregando dados de corretores..."):
        try:
            corretor_data = get_analytics_by_dimension(
                filters['data_inicial'],
                filters['data_final'],
                'corretor',
                filters['midia_selecionada'],
                filters['tipovenda_selecionada'],
                limit=20
            )
            
            if corretor_data.empty:
                st.warning("⚠️ Nenhum dado de corretor encontrado.")
                return
            
            # Tabela de top corretores
            st.markdown("### 🏆 Top 20 Corretores")
            
            # Preparar dados para exibição
            display_data = corretor_data.copy()
            display_data['total_valor'] = display_data['total_valor'].apply(fmt_brl)
            display_data['ticket_medio'] = display_data['ticket_medio'].apply(fmt_brl)
            display_data['qtd_vendas'] = display_data['qtd_vendas'].apply(fmt_int)
            
            # Adicionar ranking
            display_data['Ranking'] = range(1, len(display_data) + 1)
            display_data = display_data[['Ranking', 'corretor', 'qtd_vendas', 'total_valor', 'ticket_medio']]
            display_data.columns = ['Ranking', 'Corretor', 'Qtd Vendas', 'Valor Total', 'Ticket Médio']
            
            st.dataframe(display_data, width='stretch', hide_index=True)
            
            # Gráfico de barras horizontais para top 10
            st.markdown("### 📊 Top 10 Corretores (Gráfico)")
            
            top_10 = corretor_data.head(10)
            fig = create_horizontal_bar_chart(
                top_10, 
                'total_valor', 
                'corretor', 
                'Top 10 Corretores por Valor'
            )
            
            st.plotly_chart(fig, width='stretch')
                
        except Exception as e:
            st.error(f"❌ Erro ao carregar dados de corretores: {str(e)}")

def render_export_section():
    """Renderiza seção de exportação."""
    st.markdown("""
    <div class="export-section">
        <h4>📥 Exportar Análises</h4>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.info("💡 **Dica:** Use os botões de download dos gráficos para salvar as visualizações")
    
    with col2:
        st.info("📊 **Dados:** As tabelas podem ser copiadas diretamente do Streamlit")
    
    with col3:
        st.info("🔄 **Atualização:** Os dados são atualizados automaticamente com os filtros")

def render_summary_metrics(filters: dict):
    """Renderiza métricas resumidas."""
    st.markdown("---")
    st.markdown("### 📈 Resumo das Análises")
    
    # Carregar dados para métricas resumidas
    try:
        # Mídia
        midia_data = get_analytics_by_dimension(
            filters['data_inicial'],
            filters['data_final'],
            'midia',
            filters['midia_selecionada'],
            filters['tipovenda_selecionada'],
            limit=100
        )
        
        # Imobiliária
        imobiliaria_data = get_analytics_by_dimension(
            filters['data_inicial'],
            filters['data_final'],
            'imobiliaria',
            filters['midia_selecionada'],
            filters['tipovenda_selecionada'],
            limit=100
        )
        
        # Corretor
        corretor_data = get_analytics_by_dimension(
            filters['data_inicial'],
            filters['data_final'],
            'corretor',
            filters['midia_selecionada'],
            filters['tipovenda_selecionada'],
            limit=100
        )
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_midias = len(midia_data)
            st.metric("Mídias Ativas", fmt_int(total_midias))
        
        with col2:
            total_imobiliarias = len(imobiliaria_data)
            st.metric("Imobiliárias", fmt_int(total_imobiliarias))
        
        with col3:
            total_corretores = len(corretor_data)
            st.metric("Corretores", fmt_int(total_corretores))
        
        with col4:
            if not midia_data.empty:
                top_midia_valor = midia_data.iloc[0]['total_valor']
                st.metric("Top Mídia", fmt_brl(top_midia_valor))
            else:
                st.metric("Top Mídia", "N/A")
                
    except Exception as e:
        st.warning(f"⚠️ Erro ao carregar métricas resumidas: {str(e)}")

def main():
    """Função principal da página."""
    # Header
    st.markdown('<h1 class="analyses-header">📊 Análises por Dimensões</h1>', unsafe_allow_html=True)
    
    # Verificar se filtros foram aplicados
    filters = get_session_filters()
    
    if not filters['data_inicial'] or not filters['data_final']:
        st.warning("⚠️ Nenhum filtro aplicado. Volte à página principal para configurar os filtros.")
        st.info("👈 Use a sidebar para navegar de volta ao Dashboard principal")
        return
    
    # Mostrar filtros aplicados
    st.markdown("### 🔍 Filtros Aplicados")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.info(f"**Período:** {filters['data_inicial']} a {filters['data_final']}")
    
    with col2:
        midia_text = ", ".join(filters['midia_selecionada']) if filters['midia_selecionada'] else "Todas"
        st.info(f"**Mídia:** {midia_text}")
    
    with col3:
        tipovenda_text = ", ".join(filters['tipovenda_selecionada']) if filters['tipovenda_selecionada'] else "Todos"
        st.info(f"**Tipo Venda:** {tipovenda_text}")
    
    # Renderizar análises
    render_midia_analysis(filters)
    st.markdown("---")
    render_tipovenda_analysis(filters)
    st.markdown("---")
    render_imobiliaria_analysis(filters)
    st.markdown("---")
    render_corretor_analysis(filters)
    
    # Métricas resumidas
    render_summary_metrics(filters)
    
    # Seção de exportação
    render_export_section()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; font-size: 0.8rem;'>
        📊 Análises por Dimensões | 
        🔗 Dados do MotherDuck | 
        ⏰ Atualizado em: {timestamp}
    </div>
    """.format(timestamp=pd.Timestamp.now().strftime('%d/%m/%Y %H:%M:%S')), unsafe_allow_html=True)

if __name__ == "__main__":
    main()
