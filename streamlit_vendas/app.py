"""
App Streamlit principal - Dashboard de Vendas Consolidadas
Sistema de analytics de vendas conectado ao MotherDuck.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
from typing import List, Optional

# Importar sistema de autenticação
from auth import require_auth

# Importar utilitários locais
from utils.md_conn import (
    get_md_connection, 
    get_date_range, 
    get_kpis, 
    get_timeline_data,
    get_top_empreendimentos,
    get_unique_values
)
from utils.formatters import (
    fmt_brl, 
    fmt_int, 
    fmt_percent, 
    fmt_compact_currency,
    format_kpi_value
)

# Configuração da página
st.set_page_config(
    page_title="Dashboard de Vendas Consolidadas",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .kpi-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin: 0.5rem 0;
    }
    .kpi-value {
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
    }
    .kpi-label {
        font-size: 0.9rem;
        color: #666;
        margin-top: 0.5rem;
    }
    .metric-container {
        background-color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .sidebar .sidebar-content {
        background-color: #f8f9fa;
    }
    .stSelectbox > div > div {
        background-color: white;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Inicializa o estado da sessão."""
    if 'filtros_aplicados' not in st.session_state:
        st.session_state.filtros_aplicados = False
    if 'data_inicial' not in st.session_state:
        st.session_state.data_inicial = None
    if 'data_final' not in st.session_state:
        st.session_state.data_final = None
    if 'midia_selecionada' not in st.session_state:
        st.session_state.midia_selecionada = []
    if 'tipovenda_selecionada' not in st.session_state:
        st.session_state.tipovenda_selecionada = []

def render_sidebar_filters():
    """Renderiza os filtros globais na sidebar."""
    st.sidebar.markdown("## 🔍 Filtros Globais")
    
    try:
        # Obter range de datas disponível
        data_min, data_max = get_date_range()
        data_min_dt = datetime.strptime(data_min, '%Y-%m-%d').date()
        data_max_dt = datetime.strptime(data_max, '%Y-%m-%d').date()
        
        # Filtro de período
        st.sidebar.markdown("### 📅 Período")
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            data_inicial = st.date_input(
                "Data Inicial",
                value=data_min_dt,
                min_value=data_min_dt,
                max_value=data_max_dt,
                key="filtro_data_inicial"
            )
        
        with col2:
            data_final = st.date_input(
                "Data Final",
                value=data_max_dt,
                min_value=data_min_dt,
                max_value=data_max_dt,
                key="filtro_data_final"
            )
        
        # Validar período
        if data_inicial > data_final:
            st.sidebar.error("⚠️ Data inicial deve ser anterior à data final")
            return None, None, [], []
        
        # Filtros opcionais
        st.sidebar.markdown("### 📱 Mídia")
        try:
            midias_disponiveis = get_unique_values('midia')
            midia_selecionada = st.sidebar.multiselect(
                "Selecione as mídias",
                options=midias_disponiveis,
                default=[],
                key="filtro_midia"
            )
        except Exception as e:
            st.sidebar.warning(f"Erro ao carregar mídias: {str(e)}")
            midia_selecionada = []
        
        st.sidebar.markdown("### 🏷️ Tipo de Venda")
        try:
            tipos_disponiveis = get_unique_values('tipovenda')
            tipovenda_selecionada = st.sidebar.multiselect(
                "Selecione os tipos de venda",
                options=tipos_disponiveis,
                default=[],
                key="filtro_tipovenda"
            )
        except Exception as e:
            st.sidebar.warning(f"Erro ao carregar tipos de venda: {str(e)}")
            tipovenda_selecionada = []
        
        # Botão para aplicar filtros
        if st.sidebar.button("🔄 Aplicar Filtros", type="primary"):
            st.session_state.filtros_aplicados = True
            st.session_state.data_inicial = data_inicial.strftime('%Y-%m-%d')
            st.session_state.data_final = data_final.strftime('%Y-%m-%d')
            st.session_state.midia_selecionada = midia_selecionada
            st.session_state.tipovenda_selecionada = tipovenda_selecionada
            st.rerun()
        
        # Informações do período selecionado
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📊 Período Selecionado")
        st.sidebar.info(f"""
        **Início:** {data_inicial.strftime('%d/%m/%Y')}  
        **Fim:** {data_final.strftime('%d/%m/%Y')}  
        **Duração:** {(data_final - data_inicial).days + 1} dias
        """)
        
        return (
            data_inicial.strftime('%Y-%m-%d'),
            data_final.strftime('%Y-%m-%d'),
            midia_selecionada,
            tipovenda_selecionada
        )
        
    except Exception as e:
        st.sidebar.error(f"❌ Erro ao carregar filtros: {str(e)}")
        return None, None, [], []

def render_kpis(kpis: dict):
    """Renderiza os KPIs principais."""
    st.markdown("## 📈 Indicadores Principais")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total de Vendas",
            value=fmt_int(kpis['total_vendas']),
            help=f"Quantidade total de vendas no período"
        )
    
    with col2:
        st.metric(
            label="Valor Total",
            value=fmt_brl(kpis['total_valor']),
            help=f"Valor total das vendas no período"
        )
    
    with col3:
        st.metric(
            label="Ticket Médio",
            value=fmt_brl(kpis['ticket_medio']),
            help=f"Valor médio por venda"
        )
    
    with col4:
        st.metric(
            label="Maior Venda",
            value=fmt_brl(kpis['maior_venda']),
            help=f"Maior valor de venda individual"
        )

def render_timeline(timeline_data: pd.DataFrame):
    """Renderiza o gráfico de timeline mensal."""
    if timeline_data.empty:
        st.warning("⚠️ Nenhum dado disponível para o período selecionado")
        return
    
    st.markdown("## 📅 Evolução Mensal das Vendas")
    
    # Criar gráfico de linha
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=timeline_data['mes'],
        y=timeline_data['total_valor'],
        mode='lines+markers',
        name='Valor Total',
        line=dict(color='#1f77b4', width=3),
        marker=dict(size=8),
        hovertemplate='<b>%{x|%B/%Y}</b><br>' +
                     'Valor: R$ %{y:,.2f}<br>' +
                     'Vendas: %{customdata[0]}<br>' +
                     'Ticket Médio: R$ %{customdata[1]:,.2f}<extra></extra>',
        customdata=timeline_data[['qtd_vendas', 'ticket_medio']]
    ))
    
    fig.update_layout(
        title="Evolução do Valor Total das Vendas por Mês",
        xaxis_title="Mês",
        yaxis_title="Valor Total (R$)",
        hovermode='x unified',
        template='plotly_white',
        height=400
    )
    
    # Formatar eixo Y como moeda
    fig.update_yaxis(tickformat='R$ ,.0f')
    
    st.plotly_chart(fig, width='stretch')
    
    # Tabela resumo da timeline
    with st.expander("📋 Detalhes Mensais"):
        timeline_display = timeline_data.copy()
        timeline_display['mes'] = pd.to_datetime(timeline_display['mes']).dt.strftime('%B/%Y')
        timeline_display['total_valor'] = timeline_display['total_valor'].apply(fmt_brl)
        timeline_display['ticket_medio'] = timeline_display['ticket_medio'].apply(fmt_brl)
        timeline_display['qtd_vendas'] = timeline_display['qtd_vendas'].apply(fmt_int)
        
        timeline_display.columns = ['Mês', 'Qtd Vendas', 'Valor Total', 'Ticket Médio']
        st.dataframe(timeline_display, width='stretch')

def render_top_empreendimentos(top_empreendimentos: pd.DataFrame):
    """Renderiza as tabelas de top empreendimentos."""
    if top_empreendimentos.empty:
        st.warning("⚠️ Nenhum dado disponível para empreendimentos")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("## 🏆 Top Empreendimentos por Valor")
        
        # Preparar dados para exibição
        top_valor = top_empreendimentos.copy()
        top_valor['total_valor'] = top_valor['total_valor'].apply(fmt_brl)
        top_valor['ticket_medio'] = top_valor['ticket_medio'].apply(fmt_brl)
        top_valor['qtd_vendas'] = top_valor['qtd_vendas'].apply(fmt_int)
        
        # Renomear colunas
        top_valor.columns = ['Empreendimento', 'Qtd Vendas', 'Valor Total', 'Ticket Médio']
        
        st.dataframe(
            top_valor,
            width='stretch',
            hide_index=True
        )
    
    with col2:
        st.markdown("## 📊 Top Empreendimentos por Quantidade")
        
        # Ordenar por quantidade
        top_qtd = top_empreendimentos.copy()
        top_qtd = top_qtd.sort_values('qtd_vendas', ascending=False)
        top_qtd['total_valor'] = top_qtd['total_valor'].apply(fmt_brl)
        top_qtd['ticket_medio'] = top_qtd['ticket_medio'].apply(fmt_brl)
        top_qtd['qtd_vendas'] = top_qtd['qtd_vendas'].apply(fmt_int)
        
        # Renomear colunas
        top_qtd.columns = ['Empreendimento', 'Qtd Vendas', 'Valor Total', 'Ticket Médio']
        
        st.dataframe(
            top_qtd,
            width='stretch',
            hide_index=True
        )

def render_export_section():
    """Renderiza seção de exportação de dados."""
    st.markdown("---")
    st.markdown("## 📥 Exportar Dados")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 Baixar KPIs (CSV)", help="Baixar resumo dos indicadores"):
            # Criar CSV com KPIs
            kpis_data = {
                'Métrica': ['Total Vendas', 'Valor Total', 'Ticket Médio', 'Maior Venda', 'Menor Venda'],
                'Valor': [
                    st.session_state.get('kpis', {}).get('total_vendas', 0),
                    st.session_state.get('kpis', {}).get('total_valor', 0),
                    st.session_state.get('kpis', {}).get('ticket_medio', 0),
                    st.session_state.get('kpis', {}).get('maior_venda', 0),
                    st.session_state.get('kpis', {}).get('menor_venda', 0)
                ]
            }
            kpis_df = pd.DataFrame(kpis_data)
            csv = kpis_df.to_csv(index=False)
            st.download_button(
                label="⬇️ Download KPIs",
                data=csv,
                file_name=f"kpis_vendas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    
    with col2:
        if st.button("📈 Baixar Timeline (CSV)", help="Baixar dados da timeline mensal"):
            if 'timeline_data' in st.session_state:
                timeline_df = st.session_state['timeline_data'].copy()
                csv = timeline_df.to_csv(index=False)
                st.download_button(
                    label="⬇️ Download Timeline",
                    data=csv,
                    file_name=f"timeline_vendas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            else:
                st.warning("Nenhum dado de timeline disponível")

def main():
    """Função principal do app."""
    # Proteger com autenticação
    require_auth()
    
    # Inicializar estado da sessão
    initialize_session_state()
    
    # Header principal
    st.markdown('<h1 class="main-header">📊 Dashboard de Vendas Consolidadas</h1>', unsafe_allow_html=True)
    
    # Renderizar filtros na sidebar
    data_inicial, data_final, midia_selecionada, tipovenda_selecionada = render_sidebar_filters()
    
    # Verificar se filtros foram aplicados
    if not st.session_state.filtros_aplicados:
        st.info("👈 Configure os filtros na sidebar e clique em 'Aplicar Filtros' para visualizar os dados")
        return
    
    # Usar dados da sessão se disponíveis
    if st.session_state.data_inicial:
        data_inicial = st.session_state.data_inicial
        data_final = st.session_state.data_final
        midia_selecionada = st.session_state.midia_selecionada
        tipovenda_selecionada = st.session_state.tipovenda_selecionada
    
    # Verificar se temos dados para processar
    if not data_inicial or not data_final:
        st.error("❌ Período inválido. Verifique as datas selecionadas.")
        return
    
    # Mostrar filtros aplicados
    st.markdown("### 🔍 Filtros Aplicados")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.info(f"**Período:** {datetime.strptime(data_inicial, '%Y-%m-%d').strftime('%d/%m/%Y')} a {datetime.strptime(data_final, '%Y-%m-%d').strftime('%d/%m/%Y')}")
    
    with col2:
        midia_text = ", ".join(midia_selecionada) if midia_selecionada else "Todas"
        st.info(f"**Mídia:** {midia_text}")
    
    with col3:
        tipovenda_text = ", ".join(tipovenda_selecionada) if tipovenda_selecionada else "Todos"
        st.info(f"**Tipo Venda:** {tipovenda_text}")
    
    with col4:
        st.info(f"**Registros:** Carregando...")
    
    # Carregar dados com loading
    with st.spinner("🔄 Carregando dados..."):
        try:
            # Carregar KPIs
            kpis = get_kpis(data_inicial, data_final, midia_selecionada, tipovenda_selecionada)
            st.session_state.kpis = kpis
            
            # Carregar timeline
            timeline_data = get_timeline_data(data_inicial, data_final, midia_selecionada, tipovenda_selecionada)
            st.session_state.timeline_data = timeline_data
            
            # Carregar top empreendimentos
            top_empreendimentos = get_top_empreendimentos(data_inicial, data_final, midia_selecionada, tipovenda_selecionada, limit=10)
            st.session_state.top_empreendimentos = top_empreendimentos
            
            # Atualizar contador de registros
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Erro ao carregar dados: {str(e)}")
            return
    
    # Renderizar seções principais
    render_kpis(kpis)
    st.markdown("---")
    render_timeline(timeline_data)
    st.markdown("---")
    render_top_empreendimentos(top_empreendimentos)
    render_export_section()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; font-size: 0.8rem;'>
        📊 Dashboard de Vendas Consolidadas | 
        🔗 Conectado ao MotherDuck | 
        ⏰ Atualizado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
    </div>
    """.format(datetime=datetime), unsafe_allow_html=True)

if __name__ == "__main__":
    main()
