"""
Dashboard Lead Time - Indicadores de Pedidos de Compras
Análise de lead time, tempo de atraso e % comprado no prazo.
Fonte: planilhas.relacao_de_pedidos_de_compras
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

# Importar sistema de autenticação avançado
try:
    from advanced_auth import require_auth, require_page_access
    
    # Proteger com autenticação
    require_auth()
    
    # Proteger acesso à página específica
    require_page_access("lead_time")
except ImportError as e:
    st.error(f"Erro ao importar sistema de autenticação: {e}")
    st.stop()

# Importar utilitários locais
from utils.md_conn import get_md_connection
from utils import display_navigation

# Configuração da página
st.set_page_config(
    page_title="Dashboard Lead Time",
    page_icon="⏱️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Display navigation bar (includes logo)
display_navigation()

# Store current page in session state
st.session_state['current_page'] = __file__


def get_md_connection_planilhas():
    """Conecta ao banco 'planilhas' do MotherDuck"""
    import duckdb
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    token = os.getenv('MOTHERDUCK_TOKEN') or os.getenv('Token_MD')
    
    if not token:
        raise ValueError("MOTHERDUCK_TOKEN não encontrado")
    
    duckdb.sql("INSTALL motherduck")
    duckdb.sql("LOAD motherduck")
    duckdb.sql(f"SET motherduck_token='{token}'")
    return duckdb.connect("md:planilhas")


@st.cache_data(ttl=3600)  # Cache por 1 hora (dados atualizados semanalmente)
def load_pedidos_compras_leadtime() -> pd.DataFrame:
    """
    Carrega dados de pedidos de compras do banco planilhas.
    
    Returns:
        DataFrame com dados de pedidos de compras
    """
    try:
        conn = get_md_connection_planilhas()
        
        # Query para obter dados da tabela
        sql = """
        SELECT *
        FROM planilhas.main.relacao_de_pedidos_de_compras
        ORDER BY data_pedido DESC
        """
        
        df = conn.execute(sql).df()
        conn.close()
        
        # Converter colunas de data se existirem
        date_columns = ['data_pedido', 'data_prevista', 'data_entregue']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        return df
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados: {str(e)}")
        return pd.DataFrame()


def calcular_indicadores_leadtime(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calcula indicadores de lead time conforme especificado.
    
    Args:
        df: DataFrame com dados de pedidos de compras
        
    Returns:
        Dicionário com indicadores calculados
    """
    if df.empty:
        return {
            'percentual_no_prazo': 0.0,
            'lead_time_comum': 0.0,
            'lead_time_ponderado': 0.0,
            'tempo_atraso_medio': 0.0,
            'total_pedidos': 0,
            'pedidos_no_prazo': 0,
            'pedidos_atrasados': 0,
        }
    
    # Garantir que temos as colunas necessárias
    required_cols = ['data_prevista', 'data_entregue', 'data_pedido']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        st.warning(f"⚠️ Colunas faltando: {', '.join(missing_cols)}")
        return {
            'percentual_no_prazo': 0.0,
            'lead_time_comum': 0.0,
            'lead_time_ponderado': 0.0,
            'tempo_atraso_medio': 0.0,
            'total_pedidos': 0,
            'pedidos_no_prazo': 0,
            'pedidos_atrasados': 0,
        }
    
    # Filtrar apenas registros com data_entregue preenchida
    df_com_entrega = df[df['data_entregue'].notna()].copy()
    
    if df_com_entrega.empty:
        return {
            'percentual_no_prazo': 0.0,
            'lead_time_comum': 0.0,
            'lead_time_ponderado': 0.0,
            'tempo_atraso_medio': 0.0,
            'total_pedidos': len(df),
            'pedidos_no_prazo': 0,
            'pedidos_atrasados': 0,
        }
    
    # 1. % Comprado no Prazo (-2 dias)
    # Descontar 2 dias da data_entregue para considerar tempo de lançamento
    df_com_entrega['data_entregue_ajustada'] = df_com_entrega['data_entregue'] - timedelta(days=2)
    df_com_entrega['entregue_no_prazo'] = df_com_entrega['data_entregue_ajustada'] <= df_com_entrega['data_prevista']
    
    pedidos_no_prazo = df_com_entrega['entregue_no_prazo'].sum()
    total_pedidos_entregues = len(df_com_entrega)
    percentual_no_prazo = (pedidos_no_prazo / total_pedidos_entregues * 100) if total_pedidos_entregues > 0 else 0.0
    
    # 2. Lead Time Comum
    # Diferença entre data_pedido e data_entregue
    df_com_entrega['lead_time_comum'] = (df_com_entrega['data_entregue'] - df_com_entrega['data_pedido']).dt.days
    lead_time_comum_medio = df_com_entrega['lead_time_comum'].mean() if not df_com_entrega.empty else 0.0
    
    # 3. Lead Time Ponderado
    # Fórmula: SUMX(Total líquido insumo * Lead time Simples) / SUM(Total líquido insumo)
    # Assumindo que temos coluna 'total_liquido_insumo' ou similar
    if 'total_liquido_insumo' in df_com_entrega.columns:
        df_com_entrega['lead_time_ponderado_calc'] = (
            df_com_entrega['total_liquido_insumo'] * df_com_entrega['lead_time_comum']
        )
        soma_numerador = df_com_entrega['lead_time_ponderado_calc'].sum()
        soma_denominador = df_com_entrega['total_liquido_insumo'].sum()
        lead_time_ponderado = (soma_numerador / soma_denominador) if soma_denominador > 0 else 0.0
    else:
        # Se não tiver a coluna, usar lead time comum como fallback
        lead_time_ponderado = lead_time_comum_medio
        st.info("ℹ️ Coluna 'total_liquido_insumo' não encontrada. Usando lead time comum como referência.")
    
    # 4. Tempo de Atraso
    # Se não entregue no prazo: data_entregue - data_prevista
    df_atrasados = df_com_entrega[~df_com_entrega['entregue_no_prazo']].copy()
    if not df_atrasados.empty:
        df_atrasados['tempo_atraso'] = (df_atrasados['data_entregue'] - df_atrasados['data_prevista']).dt.days
        tempo_atraso_medio = df_atrasados['tempo_atraso'].mean()
    else:
        tempo_atraso_medio = 0.0
    
    return {
        'percentual_no_prazo': percentual_no_prazo,
        'lead_time_comum': lead_time_comum_medio,
        'lead_time_ponderado': lead_time_ponderado,
        'tempo_atraso_medio': tempo_atraso_medio,
        'total_pedidos': len(df),
        'pedidos_no_prazo': int(pedidos_no_prazo),
        'pedidos_atrasados': int(total_pedidos_entregues - pedidos_no_prazo),
        'total_pedidos_entregues': total_pedidos_entregues,
    }


def formatar_moeda(valor: float) -> str:
    """Formata valor como moeda brasileira."""
    if pd.isna(valor) or valor == 0:
        return "R$ 0,00"
    valor_str = f"{valor:,.2f}"
    partes = valor_str.split('.')
    parte_inteira = partes[0].replace(',', '.')
    parte_decimal = partes[1] if len(partes) > 1 else '00'
    return f"R$ {parte_inteira},{parte_decimal}"


def formatar_percentual(valor: float) -> str:
    """Formata valor como percentual."""
    return f"{valor:.2f}%"


def formatar_dias(valor: float) -> str:
    """Formata valor como dias."""
    return f"{valor:.1f} dias"


def render_leadtime_dashboard():
    """Renderiza o dashboard de Lead Time."""
    st.title("⏱️ Dashboard Lead Time - Pedidos de Compras")
    st.caption("Indicadores de lead time, tempo de atraso e % comprado no prazo | Fonte: planilhas.relacao_de_pedidos_de_compras")
    
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
            key="leadtime_data_inicio"
        )
        
        data_fim = st.date_input(
            "Data Final",
            value=default_fim,
            key="leadtime_data_fim"
        )
    
    # Carregar dados
    with st.spinner("Carregando dados de lead time..."):
        df = load_pedidos_compras_leadtime()
        
        # Aplicar filtro de período se tiver coluna data_pedido
        if not df.empty and 'data_pedido' in df.columns:
            df = df[
                (df['data_pedido'].dt.date >= data_inicio) &
                (df['data_pedido'].dt.date <= data_fim)
            ]
    
    if df.empty:
        st.warning("⚠️ Nenhum dado encontrado para os filtros selecionados.")
        st.info("💡 Verifique se a tabela 'planilhas.main.relacao_de_pedidos_de_compras' existe e possui dados.")
        return
    
    # Calcular indicadores
    indicadores = calcular_indicadores_leadtime(df)
    
    # Seção 1: KPIs Principais
    st.markdown("---")
    st.subheader("📊 Indicadores Principais")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "% Comprado no Prazo",
            formatar_percentual(indicadores['percentual_no_prazo']),
            help="Percentual de pedidos entregues no prazo (considerando -2 dias para lançamento)"
        )
    
    with col2:
        st.metric(
            "Lead Time Comum",
            formatar_dias(indicadores['lead_time_comum']),
            help="Média de dias entre data_pedido e data_entregue"
        )
    
    with col3:
        st.metric(
            "Lead Time Ponderado",
            formatar_dias(indicadores['lead_time_ponderado']),
            help="Lead time ponderado pelo total líquido insumo"
        )
    
    with col4:
        st.metric(
            "Tempo de Atraso Médio",
            formatar_dias(indicadores['tempo_atraso_medio']),
            help="Média de dias de atraso para pedidos entregues fora do prazo"
        )
    
    # Seção 2: KPIs Secundários
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Total de Pedidos",
            f"{indicadores['total_pedidos']:,}",
            help="Total de pedidos no período"
        )
    
    with col2:
        st.metric(
            "Pedidos no Prazo",
            f"{indicadores['pedidos_no_prazo']:,}",
            help="Quantidade de pedidos entregues no prazo"
        )
    
    with col3:
        st.metric(
            "Pedidos Atrasados",
            f"{indicadores['pedidos_atrasados']:,}",
            help="Quantidade de pedidos entregues fora do prazo"
        )
    
    # Seção 3: Análises Detalhadas
    st.markdown("---")
    st.subheader("📈 Análises Detalhadas")
    
    # Preparar dados para visualizações
    df_viz = df.copy()
    
    # Adicionar colunas calculadas se necessário
    if 'data_entregue' in df_viz.columns and 'data_prevista' in df_viz.columns:
        df_viz = df_viz[df_viz['data_entregue'].notna()].copy()
        if not df_viz.empty:
            df_viz['data_entregue_ajustada'] = df_viz['data_entregue'] - timedelta(days=2)
            df_viz['entregue_no_prazo'] = df_viz['data_entregue_ajustada'] <= df_viz['data_prevista']
            df_viz['lead_time'] = (df_viz['data_entregue'] - df_viz['data_pedido']).dt.days
            df_viz['tempo_atraso'] = df_viz.apply(
                lambda row: (row['data_entregue'] - row['data_prevista']).dt.days 
                if not row['entregue_no_prazo'] else 0,
                axis=1
            )
    
    # Tabs para diferentes análises
    tab1, tab2, tab3 = st.tabs([
        "📊 Distribuição Lead Time",
        "⏰ Análise de Atrasos",
        "📋 Detalhamento"
    ])
    
    with tab1:
        st.subheader("Distribuição de Lead Time")
        
        if not df_viz.empty and 'lead_time' in df_viz.columns:
            # Histograma de lead time
            fig = px.histogram(
                df_viz,
                x='lead_time',
                nbins=30,
                title='Distribuição de Lead Time (dias)',
                labels={'lead_time': 'Lead Time (dias)', 'count': 'Quantidade'}
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
            
            # Box plot
            fig2 = px.box(
                df_viz,
                y='lead_time',
                title='Box Plot - Lead Time',
                labels={'lead_time': 'Lead Time (dias)'}
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Dados de lead time não disponíveis.")
    
    with tab2:
        st.subheader("Análise de Atrasos")
        
        if not df_viz.empty and 'entregue_no_prazo' in df_viz.columns:
            # Gráfico de pizza: no prazo vs atrasado
            status_counts = df_viz['entregue_no_prazo'].value_counts()
            fig = px.pie(
                values=status_counts.values,
                names=['No Prazo' if idx else 'Atrasado' for idx in status_counts.index],
                title='Distribuição: No Prazo vs Atrasado'
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Gráfico de tempo de atraso
            if 'tempo_atraso' in df_viz.columns:
                df_atrasos = df_viz[df_viz['tempo_atraso'] > 0]
                if not df_atrasos.empty:
                    fig2 = px.histogram(
                        df_atrasos,
                        x='tempo_atraso',
                        nbins=20,
                        title='Distribuição de Tempo de Atraso (dias)',
                        labels={'tempo_atraso': 'Dias de Atraso', 'count': 'Quantidade'}
                    )
                    st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Dados de atrasos não disponíveis.")
    
    with tab3:
        st.subheader("Detalhamento de Pedidos")
        
        # Colunas para exibir
        colunas_display = [
            'data_pedido', 'data_prevista', 'data_entregue', 
            'entregue_no_prazo', 'lead_time', 'tempo_atraso'
        ]
        
        # Adicionar outras colunas se existirem
        outras_colunas = [col for col in df_viz.columns if col not in colunas_display]
        colunas_display.extend(outras_colunas[:5])  # Limitar a 5 colunas adicionais
        
        colunas_disponiveis = [col for col in colunas_display if col in df_viz.columns]
        
        df_display = df_viz[colunas_disponiveis].copy()
        
        # Formatação
        if 'entregue_no_prazo' in df_display.columns:
            df_display['entregue_no_prazo'] = df_display['entregue_no_prazo'].map({True: 'Sim', False: 'Não'})
        
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True
        )
        
        # Botão de download
        csv = df_viz.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"lead_time_pedidos_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )


def main():
    """Função principal do app."""
    render_leadtime_dashboard()


if __name__ == "__main__":
    main()

