"""Dashboard de Repasses - Sistema Unificado"""

import streamlit as st
import pandas as pd
import duckdb
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import plotly.express as px
import plotly.graph_objects as go

# Configuração da página
st.set_page_config(
    page_title="Dashboard de Repasses",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Carregar variáveis de ambiente
load_dotenv()

# CSS personalizado
st.markdown("""
<style>
.main-header {
    background: linear-gradient(90deg, #1F3C88 0%, #3159B5 100%);
    padding: 1rem;
    border-radius: 10px;
    margin-bottom: 2rem;
    color: white;
    text-align: center;
}

.metric-card {
    background: white;
    padding: 1rem;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    border-left: 4px solid #1F3C88;
}
</style>
""", unsafe_allow_html=True)

def get_connection():
    """Conecta ao MotherDuck"""
    try:
        token = os.getenv('MOTHERDUCK_TOKEN', '').strip().strip('"').strip("'")
        if not token:
            st.error("MOTHERDUCK_TOKEN não encontrado nas variáveis de ambiente.")
            st.stop()
        
        duckdb.sql("INSTALL motherduck")
        duckdb.sql("LOAD motherduck")
        conn = duckdb.connect(f'md:reservas?motherduck_token={token}')
        return conn
    except Exception as e:
        st.error(f"Erro ao conectar ao MotherDuck: {e}")
        st.stop()

def format_currency(value):
    """Formata valor monetário"""
    try:
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return f"R$ {value}"

def format_number(value):
    """Formata número"""
    try:
        return f"{value:,.0f}".replace(",", ".")
    except:
        return str(value)

@st.cache_data
def load_repasses_data(start_date=None, end_date=None):
    """Carrega dados de repasses com filtros de data"""
    conn = get_connection()
    
    # Construir filtros de data
    where_clause = ""
    params = []
    
    if start_date:
        where_clause += " AND data_cad >= ?"
        params.append(start_date)
    if end_date:
        where_clause += " AND data_cad <= ?"
        params.append(end_date)
    
    sql = f"""
    SELECT 
        idrepasse,
        idreserva,
        empreendimento,
        Para AS para_stage,
        CAST(data_cad AS DATE) AS dt_cad_date,
        CASE 
            WHEN data_registro IS NOT NULL 
                 AND data_registro > '1900-01-01'
            THEN CAST(data_registro AS DATE) 
            ELSE NULL 
        END AS dt_registro_date,
        valor_contrato,
        banco,
        correspondente,
        CASE 
            WHEN data_registro IS NOT NULL 
                 AND data_registro > '1900-01-01'
                 AND data_cad IS NOT NULL 
                 AND data_cad > '1900-01-01'
            THEN datediff('day', CAST(data_cad AS DATE), CAST(data_registro AS DATE)) 
            ELSE NULL 
        END AS dias_cadastro_registro
    FROM cv_repasses
    WHERE 1=1 {where_clause}
    """
    
    return conn.execute(sql, params).fetch_df()

@st.cache_data
def get_date_limits():
    """Retorna os limites de data dos dados"""
    conn = get_connection()
    
    sql = """
    SELECT 
        MIN(CASE 
            WHEN data_cad IS NOT NULL 
                 AND data_cad > '1900-01-01'
            THEN CAST(data_cad AS DATE) 
            ELSE NULL 
        END) AS min_date,
        MAX(CASE 
            WHEN data_cad IS NOT NULL 
                 AND data_cad > '1900-01-01'
            THEN CAST(data_cad AS DATE) 
            ELSE NULL 
        END) AS max_date
    FROM cv_repasses
    """
    
    result = conn.execute(sql).fetch_df()
    if result.empty or result.iloc[0]['min_date'] is None:
        return None, None
    
    return result.iloc[0]['min_date'], result.iloc[0]['max_date']

def main():
    """Função principal do dashboard"""
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🏦 Dashboard de Repasses</h1>
        <p>Análise de volumes, valores e SLAs dos repasses imobiliários</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar com filtros
    with st.sidebar:
        st.header("🔧 Filtros")
        
        # Obter limites de data
        min_date, max_date = get_date_limits()
        
        if min_date and max_date:
            min_date = pd.to_datetime(min_date).date()
            max_date = pd.to_datetime(max_date).date()
            
            # Filtros de data
            start_date = st.date_input(
                "Data inicial (cadastro)",
                value=max_date - timedelta(days=90),
                min_value=min_date,
                max_value=max_date
            )
            
            end_date = st.date_input(
                "Data final (cadastro)",
                value=max_date,
                min_value=min_date,
                max_value=max_date
            )
        else:
            st.error("Não foi possível obter limites de data")
            return
        
        # Carregar dados
        try:
            df = load_repasses_data(start_date, end_date)
            
            if df.empty:
                st.warning("Nenhum dado encontrado para o período selecionado")
                return
                
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")
            return
        
        # Filtros adicionais
        st.subheader("Filtros Adicionais")
        
        # Empreendimentos
        empreendimentos = sorted(df['empreendimento'].dropna().unique())
        selected_empreendimentos = st.multiselect(
            "Empreendimentos",
            empreendimentos,
            default=empreendimentos
        )
        
        # Bancos
        bancos = sorted(df['banco'].dropna().unique())
        selected_bancos = st.multiselect(
            "Bancos",
            bancos,
            default=bancos
        )
        
        # Estágios
        estagios = sorted(df['para_stage'].dropna().unique())
        selected_estagios = st.multiselect(
            "Estágios",
            estagios,
            default=estagios
        )
        
        # Aplicar filtros
        if selected_empreendimentos:
            df = df[df['empreendimento'].isin(selected_empreendimentos)]
        if selected_bancos:
            df = df[df['banco'].isin(selected_bancos)]
        if selected_estagios:
            df = df[df['para_stage'].isin(selected_estagios)]
    
    # Métricas principais
    st.subheader("📊 Métricas Principais")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_repasses = df['idrepasse'].nunique()
        st.metric("Total de Repasses", format_number(total_repasses))
    
    with col2:
        valor_total = df['valor_contrato'].sum()
        st.metric("Valor Total", format_currency(valor_total))
    
    with col3:
        registrados = df[df['para_stage'] == 'Contrato Registrado']['idrepasse'].nunique()
        st.metric("Contratos Registrados", format_number(registrados))
    
    with col4:
        tempo_mediano = df['dias_cadastro_registro'].median()
        st.metric("Tempo Mediano (dias)", f"{tempo_mediano:.1f}" if pd.notna(tempo_mediano) else "-")
    
    st.divider()
    
    # Análise por estágio
    st.subheader("📈 Análise por Estágio")
    
    stage_analysis = df.groupby('para_stage').agg({
        'idrepasse': 'nunique',
        'valor_contrato': 'sum'
    }).reset_index()
    
    stage_analysis.columns = ['Estágio', 'Quantidade', 'Valor Total']
    stage_analysis['Valor Total'] = stage_analysis['Valor Total'].apply(format_currency)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.dataframe(stage_analysis, hide_index=True)
    
    with col2:
        # Gráfico de barras
        fig = px.bar(
            stage_analysis, 
            x='Estágio', 
            y='Quantidade',
            title='Repasses por Estágio'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # Análise por empreendimento
    st.subheader("🏢 Top 10 Empreendimentos")
    
    emp_analysis = df.groupby('empreendimento').agg({
        'idrepasse': 'nunique',
        'valor_contrato': 'sum'
    }).reset_index()
    
    emp_analysis = emp_analysis.sort_values('idrepasse', ascending=False).head(10)
    emp_analysis.columns = ['Empreendimento', 'Quantidade', 'Valor Total']
    emp_analysis['Valor Total'] = emp_analysis['Valor Total'].apply(format_currency)
    
    st.dataframe(emp_analysis, hide_index=True)
    
    st.divider()
    
    # Análise temporal
    st.subheader("📅 Análise Temporal")
    
    if 'dt_cad_date' in df.columns and not df['dt_cad_date'].isna().all():
        df['mes_ano'] = pd.to_datetime(df['dt_cad_date']).dt.to_period('M')
        temporal_analysis = df.groupby('mes_ano').agg({
            'idrepasse': 'nunique',
            'valor_contrato': 'sum'
        }).reset_index()
        
        if not temporal_analysis.empty:
            temporal_analysis['mes_ano'] = temporal_analysis['mes_ano'].astype(str)
            
            fig = px.line(
                temporal_analysis, 
                x='mes_ano', 
                y='idrepasse',
                title='Evolução Mensal de Repasses'
            )
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Não há dados temporais suficientes para análise")
    else:
        st.info("Dados de data não disponíveis para análise temporal")
    
    # Download dos dados
    st.subheader("💾 Download dos Dados")
    
    csv = df.to_csv(index=False, encoding='utf-8')
    st.download_button(
        "⬇️ Baixar dados filtrados (CSV)",
        csv,
        f"repasses_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        "text/csv"
    )

if __name__ == "__main__":
    main()
