"""
Dashboard Streamlit - Vendas com Dados Sienge
Sistema de analytics de vendas conectado ao MotherDuck com análise de metas.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
from typing import List, Optional, Tuple
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

# Importar sistema de autenticação avançado
try:
    from advanced_auth import require_auth, require_page_access
    
    # Proteger com autenticação
    require_auth()
    
    # Proteger acesso à página específica
    require_page_access("vendas")
except ImportError as e:
    st.error(f"Erro ao importar sistema de autenticação: {e}")
    st.stop()

# Importar utilitários locais
from utils.md_conn import (
    get_md_connection, 
    get_date_range, 
    get_kpis, 
    get_timeline_data,
    get_top_empreendimentos,
    get_unique_values,
    get_vendas_with_metas,
    get_metas_periodo,
    get_metas_periodo_internas,
    get_metas_periodo_externas,
    get_analytics_by_dimension,
    get_analytics_corretor,
    get_analytics_imobiliaria,
    build_optional_filters,
)
from utils.formatters import (
    format_currency, 
    format_int, 
    format_percent, 
    format_compact_currency,
    format_kpi_value,
    normalizar_nome_empreendimento
)
from utils import display_navigation

# Configuração da página
st.set_page_config(
    page_title="Dashboard de Vendas",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Display navigation bar (includes logo)
display_navigation()

# Store current page in session state
st.session_state['current_page'] = __file__

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


def split_imobiliarias_por_origem(imobiliarias: List[str]) -> Tuple[List[str], List[str]]:
    """Classifica imobiliárias em internas (Prati) e externas."""
    internas, externas = [], []
    for nome in imobiliarias:
        nome_normalizado = str(nome or "").upper()
        if "PRATI" in nome_normalizado:
            internas.append(nome)
        else:
            externas.append(nome)
    return internas, externas


def resolve_imobiliaria_filter(
    selecionadas: List[str],
    origem_lista: Optional[List[str]]
) -> Optional[List[str]]:
    """
    Determina a lista final a ser usada no filtro de imobiliárias.

    Retorna:
        - None quando não há filtro a aplicar.
        - Lista vazia quando não existem imobiliárias compatíveis com a origem.
        - Lista com os nomes que devem ser filtrados.
    """
    if origem_lista is None:
        return selecionadas if selecionadas else None

    origem_set = {item for item in origem_lista if item not in (None, "")}
    if not origem_set:
        return []

    if selecionadas:
        filtradas = [item for item in selecionadas if item in origem_set]
        return filtradas

    return list(origem_set)


def initialize_session_state():
    """Inicializa o estado da sessão."""
    if 'kpis' not in st.session_state:
        st.session_state.kpis = {}
    if 'timeline_data' not in st.session_state:
        st.session_state.timeline_data = pd.DataFrame()
    if 'top_empreendimentos' not in st.session_state:
        st.session_state.top_empreendimentos = pd.DataFrame()

def render_kpis(kpis: dict):
    """Renderiza os KPIs principais."""
    st.subheader("📈 Métricas Principais")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            "Total de Vendas",
            format_int(kpis.get('total_vendas', 0)),
            help="Quantidade total de vendas no período"
        )
    
    with col2:
        st.metric(
            "Valor Total",
            format_compact_currency(kpis.get('total_valor', 0)),
            help="Valor total em vendas no período"
        )
    
    with col3:
        st.metric(
            "Ticket Médio",
            format_compact_currency(kpis.get('ticket_medio', 0)),
            help="Valor médio por venda"
        )
    
    with col4:
        st.metric(
            "Maior Venda",
            format_compact_currency(kpis.get('maior_venda', 0)),
            help="Maior valor de venda individual"
        )
    
    with col5:
        st.metric(
            "Menor Venda",
            format_compact_currency(kpis.get('menor_venda', 0)),
            help="Menor valor de venda individual"
        )

def render_metas_section(kpis: dict, meta_total: float, meta_ratio: float = 1.0):
    """Renderiza seção de metas considerando o rateio configurado."""
    st.subheader("🎯 Análise de Metas")

    meta_periodo = (meta_total or 0.0) * meta_ratio
    meta_display = format_compact_currency(meta_periodo) if meta_periodo else "R$ 0"
    ratio_pct = int(meta_ratio * 100)
    ratio_caption = (
        f"Meta ajustada para {ratio_pct}% do total do período."
        if meta_ratio != 1.0 else None
    )
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Meta do Período",
            meta_display,
            help="Meta de vendas para o período selecionado"
        )
        if ratio_caption:
            st.caption(ratio_caption)
    
    with col2:
        valor_vendas = kpis.get('total_valor', 0)
        atingimento = (valor_vendas / meta_periodo * 100) if meta_periodo > 0 else 0
        
        # Determinar seta e texto baseado no atingimento
        if meta_periodo == 0:
            # Quando meta é zero, exibir sem seta e texto "Sem meta"
            valor_display = f"{atingimento:.1f}%"
            delta_display = "Sem meta"
            delta_color = "off"  # Sem cor
        elif atingimento >= 100:
            # Meta atingida - seta para cima no card principal, texto verde embaixo
            valor_display = f"↗ {atingimento:.1f}%"
            delta_display = "Meta batida"
            delta_color = "normal"  # Verde
        else:
            # Meta não atingida - seta para baixo no card principal, texto vermelho embaixo
            valor_display = f"↘ {atingimento:.1f}%"
            delta_display = "Meta não batida"
            delta_color = "inverse"  # Vermelho
        
        st.metric(
            "Atingimento",
            valor_display,
            delta=delta_display,
            delta_color=delta_color,
            help="Percentual de atingimento da meta"
        )
    
    with col3:
        diferenca = valor_vendas - meta_periodo
        # Formatar diferença corretamente, incluindo valores negativos
        if diferenca >= 0:
            diferenca_display = format_compact_currency(diferenca)
        else:
            # Para valores negativos, usar o sinal de menos
            diferenca_display = f"-{format_compact_currency(abs(diferenca))}"
        
        st.metric(
            "Diferença para Meta",
            diferenca_display,
            help="Diferença entre vendas realizadas e meta"
        )

def render_timeline(timeline_data: pd.DataFrame, key_suffix: str = ""):
    """Renderiza gráfico de timeline."""
    if timeline_data.empty:
        st.warning("Nenhum dado disponível para o período selecionado.")
        return
    
    st.subheader("📅 Evolução Mensal")
    
    # Gráfico de linha
    fig = px.line(
        timeline_data, 
        x='mes', 
        y='total_valor',
        title='Evolução do Valor Total por Mês',
        labels={'mes': 'Mês', 'total_valor': 'Valor Total (R$)'}
    )
    
    fig.update_layout(
        xaxis_title="Mês",
        yaxis_title="Valor Total (R$)",
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True, key=f"timeline_chart_{key_suffix}")
    
    # Tabela resumo
    st.subheader("📊 Resumo Mensal")
    
    # Formatar dados para exibição
    timeline_display = timeline_data.copy()
    timeline_display['mes'] = pd.to_datetime(timeline_display['mes']).dt.strftime('%Y-%m')
    timeline_display['total_valor'] = timeline_display['total_valor'].apply(format_currency)
    timeline_display['ticket_medio'] = timeline_display['ticket_medio'].apply(format_currency)
    timeline_display['qtd_vendas'] = timeline_display['qtd_vendas'].apply(format_int)
    
    timeline_display.columns = ['Mês', 'Quantidade', 'Valor Total', 'Ticket Médio']
    
    st.dataframe(timeline_display, use_container_width=True, key=f"timeline_table_{key_suffix}")

def render_top_empreendimentos(top_empreendimentos: pd.DataFrame, key_suffix: str = ""):
    """Renderiza top empreendimentos."""
    if top_empreendimentos.empty:
        st.warning("Nenhum dado disponível para o período selecionado.")
        return
    
    st.subheader("🏆 Top Empreendimentos")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Por Valor Total**")
        top_valor = top_empreendimentos.copy()
        top_valor['total_valor'] = top_valor['total_valor'].apply(format_currency)
        top_valor['ticket_medio'] = top_valor['ticket_medio'].apply(format_currency)
        top_valor['qtd_vendas'] = top_valor['qtd_vendas'].apply(format_int)
        
        st.dataframe(
            top_valor[['nome_empreendimento', 'qtd_vendas', 'total_valor', 'ticket_medio']],
            use_container_width=True,
            key=f"top_empreendimentos_table_{key_suffix}"
        )
    
    with col2:
        # Gráfico de barras
        fig = px.bar(
            top_empreendimentos.head(10),
            x='total_valor',
            y='nome_empreendimento',
            orientation='h',
            title='Top 10 Empreendimentos por Valor',
            labels={'total_valor': 'Valor Total (R$)', 'nome_empreendimento': 'Empreendimento'}
        )
        
        fig.update_layout(
            yaxis={'categoryorder': 'total ascending'},
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True, key=f"top_empreendimentos_chart_{key_suffix}")

def render_house_analysis(data_inicial: str, data_final: str, 
                         midia_selecionada: List[str], tipovenda_selecionada: List[str],
                         empreendimento_selecionado: str, corretor_selecionado: List[str],
                         imobiliaria_selecionada: List[str], key_suffix: str = ""):
    """Renderiza análise House vs Imobiliárias."""
    st.subheader("🏠 Análise Vendas House x Imobiliárias")
    
    # Obter dados com análise de origem
    vendas_data = get_vendas_with_metas(data_inicial, data_final, midia_selecionada, tipovenda_selecionada, empreendimento_selecionado, corretor_selecionado, imobiliaria_selecionada)
    
    if vendas_data.empty:
        st.warning("Nenhum dado disponível para o período selecionado.")
        return
    
    # Classificar vendas como House (Prati) ou Externa
    vendas_data['tipo_venda_origem'] = vendas_data['imobiliaria'].apply(
        lambda x: 'Venda Interna (Prati)' if 'PRATI' in str(x).upper() else 'Venda Externa (Imobiliárias)'
    )
    
    # Análise agregada
    analise_origem = vendas_data.groupby('tipo_venda_origem').agg({
        'value': ['count', 'sum', 'mean']
    }).round(2)
    
    analise_origem.columns = ['Quantidade', 'Valor Total', 'Ticket Médio']
    analise_origem['Valor Total'] = analise_origem['Valor Total'].apply(format_currency)
    analise_origem['Ticket Médio'] = analise_origem['Ticket Médio'].apply(format_currency)
    analise_origem['Quantidade'] = analise_origem['Quantidade'].apply(format_int)
    
    st.dataframe(analise_origem, use_container_width=True, key=f"house_analysis_table_{key_suffix}")
    
    # Gráfico de pizza
    col1, col2 = st.columns(2)
    
    with col1:
        fig_pizza = px.pie(
            vendas_data,
            values='value',
            names='tipo_venda_origem',
            title='Distribuição por Origem (Valor)'
        )
        st.plotly_chart(fig_pizza, use_container_width=True, key=f"house_analysis_pie_{key_suffix}")
    
    with col2:
        # Taxa House (calculada por valor, não por quantidade)
        total_valor = vendas_data['value'].sum()
        valor_house = vendas_data[vendas_data['tipo_venda_origem'] == 'Venda Interna (Prati)']['value'].sum()
        taxa_house = (valor_house / total_valor * 100) if total_valor > 0 else 0
        
        st.metric(
            "Taxa House",
            f"{taxa_house:.1f}%",
            help=f"Percentual de vendas e mútuos realizados pela Prati: {taxa_house:.1f}%\n\nRegra: Calculado pelo valor das vendas"
        )

def render_empreendimentos_estratificados(data_inicial: str, data_final: str,
                                         midia_selecionada: List[str], tipovenda_selecionada: List[str],
                                         empreendimento_selecionado: str, corretor_selecionado: List[str],
                                         imobiliaria_selecionada: List[str], key_suffix: str = ""):
    """Renderiza tabela estratificada por empreendimento."""
    st.subheader("🏢 Vendas por Empreendimento (House x Externa)")
    
    # Obter dados
    vendas_data = get_vendas_with_metas(data_inicial, data_final, midia_selecionada, tipovenda_selecionada, empreendimento_selecionado, corretor_selecionado, imobiliaria_selecionada)
    
    if vendas_data.empty:
        st.warning("Nenhum dado disponível para o período selecionado.")
        return
    
    # Classificar vendas
    vendas_data['tipo_venda_origem'] = vendas_data['imobiliaria'].apply(
        lambda x: 'Venda Interna (Prati)' if 'PRATI' in str(x).upper() else 'Venda Externa (Imobiliárias)'
    )
    
    # Criar pivot table
    quantidade = vendas_data.pivot_table(
        index='nome_empreendimento',
        columns='tipo_venda_origem',
        values='value',
        aggfunc='count',
        fill_value=0
    ).reset_index()
    
    valor = vendas_data.pivot_table(
        index='nome_empreendimento',
        columns='tipo_venda_origem',
        values='value',
        aggfunc='sum',
        fill_value=0
    ).reset_index()
    
    # Combinar dados
    estratificacao = pd.DataFrame()
    estratificacao['Empreendimento'] = quantidade['nome_empreendimento']
    
    # Adicionar colunas com tratamento para colunas que podem não existir
    estratificacao['Quantidade (Interna)'] = quantidade.get('Venda Interna (Prati)', 0)
    estratificacao['Quantidade (Externa)'] = quantidade.get('Venda Externa (Imobiliárias)', 0)
    valor_interno = valor.get('Venda Interna (Prati)', 0)
    valor_externo = valor.get('Venda Externa (Imobiliárias)', 0)
    estratificacao['Valor Total (Interna)'] = valor_interno
    estratificacao['Valor Total (Externa)'] = valor_externo

    # Calcular Taxa House por empreendimento (base valor)
    soma_valores = (valor_interno + valor_externo)
    taxa_house_pct = (valor_interno / soma_valores) * 100
    # Tratar divisões por zero e NaN/Inf
    taxa_house_pct = taxa_house_pct.replace([float('inf'), float('-inf')], 0).fillna(0).round(1)
    estratificacao['Taxa House (%)'] = taxa_house_pct
    
    # Formatar valores monetários (manter % numérico até montar totais)
    estratificacao['Valor Total (Interna)'] = estratificacao['Valor Total (Interna)'].apply(format_currency)
    estratificacao['Valor Total (Externa)'] = estratificacao['Valor Total (Externa)'].apply(format_currency)
    # Formatar percentual
    estratificacao['Taxa House (%)'] = estratificacao['Taxa House (%)'].apply(lambda v: f"{v:.1f}%")
    
    # Calcular totais
    total_valor_interno = vendas_data[vendas_data['tipo_venda_origem'] == 'Venda Interna (Prati)']['value'].sum()
    total_valor_externo = vendas_data[vendas_data['tipo_venda_origem'] == 'Venda Externa (Imobiliárias)']['value'].sum()
    taxa_house_total = (total_valor_interno / (total_valor_interno + total_valor_externo) * 100) if (total_valor_interno + total_valor_externo) > 0 else 0

    totais = pd.DataFrame([{
        'Empreendimento': 'Total',
        'Quantidade (Interna)': vendas_data[vendas_data['tipo_venda_origem'] == 'Venda Interna (Prati)']['value'].count(),
        'Quantidade (Externa)': vendas_data[vendas_data['tipo_venda_origem'] == 'Venda Externa (Imobiliárias)']['value'].count(),
        'Valor Total (Interna)': format_currency(total_valor_interno),
        'Valor Total (Externa)': format_currency(total_valor_externo),
        'Taxa House (%)': f"{taxa_house_total:.1f}%"
    }])
    
    estratificacao = pd.concat([estratificacao, totais], ignore_index=True)
    
    # Reordenar colunas para incluir a nova taxa ao final
    cols_ordem = [
        'Empreendimento',
        'Quantidade (Interna)', 'Quantidade (Externa)',
        'Valor Total (Interna)', 'Valor Total (Externa)',
        'Taxa House (%)'
    ]
    estratificacao = estratificacao[cols_ordem]

    st.dataframe(estratificacao, use_container_width=True, key=f"empreendimentos_estratificados_{key_suffix}")


def render_vendas_tab(
    titulo_tab: str,
    data_inicial: str,
    data_final: str,
    midia_selecionada: List[str],
    tipovenda_selecionada: List[str],
    empreendimento_selecionado: str,
    corretor_selecionado: List[str],
    imobiliaria_selecionada: List[str],
    meta_total_periodo: float,
    imobiliarias_override: Optional[List[str]] = None,
    meta_ratio: float = 1.0,
    mostrar_analise_imobiliaria: bool = True,
    mostrar_house_analysis: bool = True,
    mostrar_vpl_imobiliaria: bool = True,
):
    """Renderiza o conteúdo completo de uma aba (geral, interna ou externa)."""
    imobiliaria_filter = resolve_imobiliaria_filter(imobiliaria_selecionada, imobiliarias_override)

    if imobiliarias_override is not None and not imobiliarias_override:
        st.info(f"Não existem imobiliárias classificadas para {titulo_tab.lower()}.")
        return

    if isinstance(imobiliaria_filter, list) and len(imobiliaria_filter) == 0:
        st.info(f"Os filtros atuais não retornam dados para {titulo_tab.lower()}. Ajuste a seleção e tente novamente.")
        return

    imobiliaria_param = imobiliaria_filter if isinstance(imobiliaria_filter, list) else None

    try:
        with st.spinner(f"🔄 Carregando dados ({titulo_tab})..."):
            kpis = get_kpis(
                data_inicial, data_final,
                midia_selecionada, tipovenda_selecionada,
                empreendimento_selecionado, corretor_selecionado,
                imobiliaria_param
            )
            top_empreendimentos = get_top_empreendimentos(
                data_inicial, data_final,
                midia_selecionada, tipovenda_selecionada,
                empreendimento_selecionado, corretor_selecionado,
                imobiliaria_param, limit=10
            )
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados de {titulo_tab}: {str(e)}")
        return

    # Criar key_suffix único baseado no título da aba
    key_suffix = titulo_tab.lower().replace(" ", "_")
    
    render_kpis(kpis)
    st.markdown("---")

    render_metas_section(kpis, meta_total_periodo, meta_ratio)
    st.markdown("---")

    render_top_empreendimentos(top_empreendimentos, key_suffix=key_suffix)
    st.markdown("---")

    imobiliaria_list = imobiliaria_param if isinstance(imobiliaria_param, list) else []

    if mostrar_house_analysis:
        render_house_analysis(
            data_inicial, data_final,
            midia_selecionada, tipovenda_selecionada,
            empreendimento_selecionado, corretor_selecionado,
            imobiliaria_list,
            key_suffix=key_suffix
        )
        st.markdown("---")

    render_empreendimentos_estratificados(
        data_inicial, data_final,
        midia_selecionada, tipovenda_selecionada,
        empreendimento_selecionado, corretor_selecionado,
        imobiliaria_list,
        key_suffix=key_suffix
    )
    st.markdown("---")

    render_analytics_corretor(
        data_inicial, data_final,
        midia_selecionada, tipovenda_selecionada,
        empreendimento_selecionado, corretor_selecionado,
        imobiliaria_list,
        mostrar_vpl_imobiliaria=mostrar_vpl_imobiliaria,
        key_suffix=key_suffix
    )
    st.markdown("---")

    if mostrar_analise_imobiliaria:
        render_analytics_imobiliaria(
            data_inicial, data_final,
            midia_selecionada, tipovenda_selecionada,
            empreendimento_selecionado, corretor_selecionado,
            imobiliaria_list,
            key_suffix=key_suffix
        )


def main():
    """Função principal do app."""
    initialize_session_state()
    
    # Header
    st.markdown('<h1 class="main-header">📊 Dashboard de Vendas</h1>', unsafe_allow_html=True)
    
    # Sidebar para filtros
    st.sidebar.header("🔍 Filtros")
    
    # Obter range de datas disponível
    try:
        data_min, data_max = get_date_range()
        data_min = datetime.strptime(data_min, '%Y-%m-%d').date()
        data_max = datetime.strptime(data_max, '%Y-%m-%d').date()
    except:
        # Fallback para datas padrão
        data_min = date(2025, 1, 1)
        data_max = date.today()
    
    # Data inicial mínima travada em 2026/01/01
    data_inicial_minima = date(2026, 1, 1)
    # Garantir que o mínimo seja pelo menos 2026/01/01
    if data_min < data_inicial_minima:
        data_min = data_inicial_minima
    
    # Filtros
    data_inicial = st.sidebar.date_input(
        "Data Inicial",
        value=data_inicial_minima,
        min_value=data_inicial_minima,
        max_value=data_max
    )
    
    data_final = st.sidebar.date_input(
        "Data Final",
        value=data_max,
        min_value=data_min,
        max_value=data_max
    )
    
    # CSS customizado para melhorar a aparência do filtro de empreendimento
    st.markdown("""
    <style>
    /* Estilo para o selectbox de empreendimento */
    div[data-testid="stSelectbox"] > div > div {
        background-color: #262730 !important;
        border: 1px solid #4a4a4a !important;
        border-radius: 0.5rem !important;
    }
    
    div[data-testid="stSelectbox"] > div > div > div {
        color: #ffffff !important;
    }
    
    /* Estilo para quando está selecionado */
    div[data-testid="stSelectbox"] > div > div[aria-expanded="false"] {
        background-color: #1e1e2e !important;
        border: 2px solid #00d4aa !important;
    }
    
    /* Estilo para o dropdown */
    div[data-testid="stSelectbox"] > div > div[aria-expanded="true"] {
        background-color: #262730 !important;
        border: 2px solid #00d4aa !important;
    }
    
    /* Estilo para as opções do dropdown */
    div[data-testid="stSelectbox"] ul {
        background-color: #262730 !important;
        border: 1px solid #4a4a4a !important;
    }
    
    div[data-testid="stSelectbox"] li {
        color: #ffffff !important;
    }
    
    div[data-testid="stSelectbox"] li:hover {
        background-color: #4a4a4a !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Filtro de empreendimento
    empreendimentos = ["Todos"] + get_unique_values('nome_empreendimento')
    empreendimento_selecionado = st.sidebar.selectbox("Empreendimento", empreendimentos)
    
    # Filtros opcionais
    st.sidebar.subheader("Filtros Opcionais")
    
    midias_disponiveis = get_unique_values('midia')
    midia_selecionada = st.sidebar.multiselect("Mídia", midias_disponiveis)
    
    tipos_venda_disponiveis = get_unique_values('tipovenda')
    tipovenda_selecionada = st.sidebar.multiselect("Tipo de Venda", tipos_venda_disponiveis)
    
    # Filtros adicionais
    st.sidebar.subheader("Filtros Adicionais")
    
    corretores_disponiveis = get_unique_values('corretor')
    corretor_selecionado = st.sidebar.multiselect("Corretor", corretores_disponiveis)
    
    imobiliarias_disponiveis = get_unique_values('imobiliaria')
    imobiliaria_selecionada = st.sidebar.multiselect("Imobiliária", imobiliarias_disponiveis)
    
    # Converter datas para string
    data_inicial_str = data_inicial.strftime('%Y-%m-%d')
    data_final_str = data_final.strftime('%Y-%m-%d')

    # Calcular metas para cada aba
    try:
        meta_total_periodo = get_metas_periodo(data_inicial_str, data_final_str, empreendimento_selecionado)
    except Exception as e:
        st.error(f"❌ Erro ao calcular metas gerais: {str(e)}")
        meta_total_periodo = 0.0
    
    try:
        meta_total_periodo_internas = get_metas_periodo_internas(data_inicial_str, data_final_str, empreendimento_selecionado)
    except Exception as e:
        st.error(f"❌ Erro ao calcular metas internas: {str(e)}")
        meta_total_periodo_internas = 0.0
    
    try:
        meta_total_periodo_externas = get_metas_periodo_externas(data_inicial_str, data_final_str, empreendimento_selecionado)
    except Exception as e:
        st.error(f"❌ Erro ao calcular metas externas: {str(e)}")
        meta_total_periodo_externas = 0.0

    imobiliarias_internas, imobiliarias_externas = split_imobiliarias_por_origem(imobiliarias_disponiveis)

    tab_geral, tab_interna, tab_externa = st.tabs(["Vendas Geral", "Vendas Internas", "Vendas Externas"])

    with tab_geral:
        render_vendas_tab(
            "Vendas Geral",
            data_inicial_str, data_final_str,
            midia_selecionada, tipovenda_selecionada,
            empreendimento_selecionado, corretor_selecionado,
            imobiliaria_selecionada,
            meta_total_periodo,
            meta_ratio=1.0
        )

    with tab_interna:
        render_vendas_tab(
            "Vendas Internas",
            data_inicial_str, data_final_str,
            midia_selecionada, tipovenda_selecionada,
            empreendimento_selecionado, corretor_selecionado,
            imobiliaria_selecionada,
            meta_total_periodo_internas,
            imobiliarias_override=imobiliarias_internas,
            meta_ratio=1.0,  # Meta já vem calculada corretamente (30% em 2025, 100% da meta específica em 2026+)
            mostrar_analise_imobiliaria=False,
            mostrar_house_analysis=False,
            mostrar_vpl_imobiliaria=False
        )

    with tab_externa:
        render_vendas_tab(
            "Vendas Externas",
            data_inicial_str, data_final_str,
            midia_selecionada, tipovenda_selecionada,
            empreendimento_selecionado, corretor_selecionado,
            imobiliaria_selecionada,
            meta_total_periodo_externas,
            imobiliarias_override=imobiliarias_externas,
            meta_ratio=1.0,  # Meta já vem calculada corretamente (70% em 2025, 100% da meta específica em 2026+)
            mostrar_house_analysis=False
        )

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; font-size: 0.8rem;'>
        📊 Dashboard de Vendas | 
        🔗 Conectado ao MotherDuck | 
        ⏰ Atualizado em: {data_atual}
    </div>
    """.format(data_atual=datetime.now().strftime('%d/%m/%Y %H:%M:%S')), unsafe_allow_html=True)

def render_analytics_corretor(data_inicial: str, data_final: str, 
                             midia_selecionada: List[str], tipovenda_selecionada: List[str],
                             empreendimento_selecionado: str, corretor_selecionado: List[str],
                             imobiliaria_selecionada: List[str],
                             mostrar_vpl_imobiliaria: bool = True,
                             key_suffix: str = ""):
    """Renderiza quadro analítico por corretor."""
    st.subheader("👨‍💼 Análise por Corretor")
    
    filtro_sql, filtro_params = build_optional_filters(
        midia_selecionada,
        tipovenda_selecionada,
        empreendimento_selecionado,
        corretor_selecionado,
        imobiliaria_selecionada
    )
    
    # Obter dados
    try:
        analytics_data = get_analytics_corretor(data_inicial, data_final, midia_selecionada, tipovenda_selecionada, empreendimento_selecionado, corretor_selecionado, imobiliaria_selecionada)
        
        if analytics_data.empty:
            st.warning("Nenhum dado disponível para análise por corretor.")
            return
        
        # Métricas principais
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total de Corretores",
                len(analytics_data),
                help="Número total de corretores com vendas no período"
            )
        
        with col2:
            total_vendas = analytics_data['total_vendas'].sum()
            st.metric(
                "Total de Vendas",
                format_int(total_vendas),
                help="Soma de todas as vendas dos corretores"
            )
        
        with col3:
            total_valor = analytics_data['total_valor'].sum()
            st.metric(
                "Valor Total",
                format_currency(total_valor),
                help="Valor total das vendas dos corretores"
            )
        
        with col4:
            ticket_medio_geral = total_valor / total_vendas if total_vendas > 0 else 0
            st.metric(
                "Ticket Médio Geral",
                format_currency(ticket_medio_geral),
                help="Ticket médio geral de todos os corretores"
            )
        
        # Tabela detalhada
        st.subheader("📊 Ranking de Corretores")
        st.write("💡 **Dica:** A primeira coluna (índice) ordena automaticamente pelo Valor Total do maior para o menor.")
        
        # Preparar dados para exibição
        display_data = analytics_data.copy()
        
        # Ordenar por Valor Total (maior para menor) e criar índice
        display_data = display_data.sort_values('total_valor', ascending=False).reset_index(drop=True)
        display_data['Índice'] = range(1, len(display_data) + 1)
        
        # Renomear coluna de imobiliária principal se existir
        if 'imobiliaria_principal' in display_data.columns:
            # Colocar a coluna após 'corretor'
            cols = display_data.columns.tolist()
            # Garantir ordem desejada incluindo o índice
            desired = ['Índice', 'corretor', 'imobiliaria_principal', 'total_vendas', 'total_valor', 'ticket_medio', 'menor_venda', 'maior_venda', 'empreendimentos_unicos']
            display_data = display_data[desired]
        else:
            # Garantir ordem desejada incluindo o índice
            desired = ['Índice', 'corretor', 'total_vendas', 'total_valor', 'ticket_medio', 'menor_venda', 'maior_venda', 'empreendimentos_unicos']
            display_data = display_data[desired]
        
        # Formatar valores
        display_data['total_valor'] = display_data['total_valor'].apply(format_currency)
        display_data['ticket_medio'] = display_data['ticket_medio'].apply(format_currency)
        display_data['menor_venda'] = display_data['menor_venda'].apply(format_currency)
        display_data['maior_venda'] = display_data['maior_venda'].apply(format_currency)
        display_data['total_vendas'] = display_data['total_vendas'].apply(format_int)
        display_data['empreendimentos_unicos'] = display_data['empreendimentos_unicos'].apply(format_int)
        
        # Renomear colunas
        if 'imobiliaria_principal' in analytics_data.columns:
            display_data.columns = [
                'Índice', 'Corretor', 'Imobiliária', 'Total Vendas', 'Valor Total', 'Ticket Médio',
                'Menor Venda', 'Maior Venda', 'Empreendimentos Únicos'
            ]
        else:
            display_data.columns = [
                'Índice', 'Corretor', 'Total Vendas', 'Valor Total', 'Ticket Médio',
                'Menor Venda', 'Maior Venda', 'Empreendimentos Únicos'
            ]
        
        st.dataframe(
            display_data,
            use_container_width=True,
            hide_index=True,
            key=f"analytics_corretor_table_{key_suffix}"
        )
        
        # Gráfico de barras - Top 10 corretores por valor
        st.subheader("📈 Top 10 Corretores por Valor")
        top_10 = analytics_data.head(10)
        
        fig = px.bar(
            top_10,
            x='corretor',
            y='total_valor',
            title="Top 10 Corretores por Valor Total",
            labels={'corretor': 'Corretor', 'total_valor': 'Valor Total (R$)'},
            color='total_valor',
            color_continuous_scale='Blues'
        )
        fig.update_layout(
            xaxis_tickangle=-45,
            height=500,
            showlegend=False
        )
        fig.update_traces(
            texttemplate='R$ %{y:,.0f}',
            textposition='outside'
        )
        
        st.plotly_chart(fig, use_container_width=True, key=f"analytics_corretor_chart_{key_suffix}")
        
        # =============================================================================
        # ANÁLISE DE VPL - EXPANDERS
        # =============================================================================
        
        def calcular_vpl_por_corretor(df):
            """Calcula VPL por corretor com % VPL"""
            # Filtrar apenas linhas que têm tanto vpl_reserva quanto vpl_tabela
            df_vpl = df[(df['vpl_reserva'].notna()) & (df['vpl_tabela'].notna()) & 
                        (df['vpl_reserva'] != 0) & (df['vpl_tabela'] != 0)]
            
            if df_vpl.empty:
                return pd.DataFrame()
            
            # Agrupar por corretor
            vpl_por_corretor = df_vpl.groupby('corretor').agg({
                'vpl_reserva': 'sum',
                'vpl_tabela': 'sum'
            }).reset_index()
            
            # Calcular % VPL: (VPL_reserva / VPL_tabela) - 1
            vpl_por_corretor['% VPL'] = ((vpl_por_corretor['vpl_reserva'] / vpl_por_corretor['vpl_tabela']) - 1)
            
            # Ordenar por VPL Tabela (maior para menor) e criar índice
            vpl_por_corretor = vpl_por_corretor.sort_values('vpl_tabela', ascending=False).reset_index(drop=True)
            vpl_por_corretor['Índice'] = range(1, len(vpl_por_corretor) + 1)
            
            # Formatar valores (usar mesma lógica da tabela de corretores)
            vpl_por_corretor['vpl_reserva'] = vpl_por_corretor['vpl_reserva'].apply(format_currency)
            vpl_por_corretor['vpl_tabela'] = vpl_por_corretor['vpl_tabela'].apply(format_currency)
            vpl_por_corretor['% VPL'] = vpl_por_corretor['% VPL'].apply(lambda x: f"{x * 100:.2f}")
            
            # Reordenar colunas para colocar Índice primeiro
            vpl_por_corretor = vpl_por_corretor[['Índice', 'corretor', 'vpl_reserva', 'vpl_tabela', '% VPL']]
            
            # Renomear colunas
            vpl_por_corretor.columns = ['Índice', 'Corretor', 'VPL Reserva', 'VPL Tabela', '% VPL']
            
            return vpl_por_corretor

        def calcular_vpl_por_imobiliaria(df):
            """Calcula VPL por imobiliária com % VPL"""
            # Filtrar apenas linhas que têm tanto vpl_reserva quanto vpl_tabela
            df_vpl = df[(df['vpl_reserva'].notna()) & (df['vpl_tabela'].notna()) & 
                        (df['vpl_reserva'] != 0) & (df['vpl_tabela'] != 0)]
            
            if df_vpl.empty:
                return pd.DataFrame()
            
            # Agrupar por imobiliária
            vpl_por_imobiliaria = df_vpl.groupby('imobiliaria').agg({
                'vpl_reserva': 'sum',
                'vpl_tabela': 'sum'
            }).reset_index()
            
            # Calcular % VPL: (VPL_reserva / VPL_tabela) - 1
            vpl_por_imobiliaria['% VPL'] = ((vpl_por_imobiliaria['vpl_reserva'] / vpl_por_imobiliaria['vpl_tabela']) - 1)
            
            # Ordenar por VPL Tabela (maior para menor) e criar índice
            vpl_por_imobiliaria = vpl_por_imobiliaria.sort_values('vpl_tabela', ascending=False).reset_index(drop=True)
            vpl_por_imobiliaria['Índice'] = range(1, len(vpl_por_imobiliaria) + 1)
            
            # Formatar valores (usar mesma lógica da tabela de corretores)
            vpl_por_imobiliaria['vpl_reserva'] = vpl_por_imobiliaria['vpl_reserva'].apply(format_currency)
            vpl_por_imobiliaria['vpl_tabela'] = vpl_por_imobiliaria['vpl_tabela'].apply(format_currency)
            vpl_por_imobiliaria['% VPL'] = vpl_por_imobiliaria['% VPL'].apply(lambda x: f"{x * 100:.2f}")
            
            # Reordenar colunas para colocar Índice primeiro
            vpl_por_imobiliaria = vpl_por_imobiliaria[['Índice', 'imobiliaria', 'vpl_reserva', 'vpl_tabela', '% VPL']]
            
            # Renomear colunas
            vpl_por_imobiliaria.columns = ['Índice', 'Imobiliária', 'VPL Reserva', 'VPL Tabela', '% VPL']
            
            return vpl_por_imobiliaria

        # Expander 1: VPL por Corretor
        with st.expander("📊 Ver Detalhes do VPL por Corretor", expanded=False):
            try:
                # Carregar dados de vendas
                conn = get_md_connection()
                sql_vpl_corretor = """
                    SELECT 
                        COALESCE(NULLIF(TRIM(corretor), ''), '—') AS corretor,
                        COALESCE(NULLIF(TRIM(imobiliaria), ''), '—') AS imobiliaria,
                        vpl_reserva,
                        vpl_tabela
                    FROM informacoes_consolidadas.sienge_vendas_consolidadas
                    WHERE contractDate >= ? AND contractDate <= ?
                """
                params_vpl = [data_inicial, data_final]
                if filtro_sql:
                    sql_vpl_corretor += f" AND {filtro_sql}"
                    params_vpl.extend(filtro_params)

                vendas_df = conn.run_query(sql_vpl_corretor, params_vpl)
                
                if not vendas_df.empty:
                    vpl_corretor = calcular_vpl_por_corretor(vendas_df)
                    
                    if not vpl_corretor.empty:
                        st.subheader("📈 VPL por Corretor")
                        st.write("💡 **Dica:** A primeira coluna (índice) ordena automaticamente pelo VPL Tabela do maior para o menor.")
                        st.dataframe(
                            vpl_corretor,
                            use_container_width=True,
                            hide_index=True,
                            key=f"vpl_corretor_table_{key_suffix}"
                        )
                    else:
                        st.info("ℹ️ Nenhum dado de VPL encontrado para corretores no período selecionado.")
                else:
                    st.warning("⚠️ Nenhum dado de vendas encontrado no período selecionado.")
                    
            except Exception as e:
                st.error(f"❌ Erro ao carregar VPL por corretor: {str(e)}")

        if mostrar_vpl_imobiliaria:
            # Expander 2: VPL por Imobiliária
            with st.expander("📊 Ver Detalhes do VPL por Imobiliária", expanded=False):
                try:
                    # Carregar dados de vendas
                    conn = get_md_connection()
                    sql_vpl_imob = """
                        SELECT 
                            COALESCE(NULLIF(TRIM(imobiliaria), ''), '—') AS imobiliaria,
                            vpl_reserva,
                            vpl_tabela
                        FROM informacoes_consolidadas.sienge_vendas_consolidadas
                        WHERE contractDate >= ? AND contractDate <= ?
                    """
                    params_vpl_imob = [data_inicial, data_final]
                    if filtro_sql:
                        sql_vpl_imob += f" AND {filtro_sql}"
                        params_vpl_imob.extend(filtro_params)

                    vendas_df = conn.run_query(sql_vpl_imob, params_vpl_imob)
                    
                    if not vendas_df.empty:
                        vpl_imobiliaria = calcular_vpl_por_imobiliaria(vendas_df)
                        
                        if not vpl_imobiliaria.empty:
                            st.subheader("📈 VPL por Imobiliária")
                            st.write("💡 **Dica:** A primeira coluna (índice) ordena automaticamente pelo VPL Tabela do maior para o menor.")
                            st.dataframe(
                                vpl_imobiliaria,
                                use_container_width=True,
                                hide_index=True,
                                key=f"vpl_imobiliaria_table_{key_suffix}"
                            )
                        else:
                            st.info("ℹ️ Nenhum dado de VPL encontrado para imobiliárias no período selecionado.")
                    else:
                        st.warning("⚠️ Nenhum dado de vendas encontrado no período selecionado.")
                        
                except Exception as e:
                    st.error(f"❌ Erro ao carregar VPL por imobiliária: {str(e)}")
        
    except Exception as e:
        st.error(f"❌ Erro ao carregar análise por corretor: {str(e)}")

 

def render_analytics_imobiliaria(data_inicial: str, data_final: str,
                                 midia_selecionada: List[str], tipovenda_selecionada: List[str],
                                 empreendimento_selecionado: str, corretor_selecionado: List[str],
                                 imobiliaria_selecionada: List[str],
                                 key_suffix: str = ""):
    """Renderiza quadro analítico por imobiliária."""
    st.subheader("🏢 Análise por Imobiliária")
    
    # Obter dados
    try:
        analytics_data = get_analytics_imobiliaria(data_inicial, data_final, midia_selecionada, tipovenda_selecionada, empreendimento_selecionado, corretor_selecionado, imobiliaria_selecionada)
        
        if analytics_data.empty:
            st.warning("Nenhum dado disponível para análise por imobiliária.")
            return
        
        # Métricas principais
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total de Imobiliárias",
                len(analytics_data),
                help="Número total de imobiliárias com vendas no período"
            )
        
        with col2:
            total_vendas = analytics_data['total_vendas'].sum()
            st.metric(
                "Total de Vendas",
                format_int(total_vendas),
                help="Soma de todas as vendas das imobiliárias"
            )
        
        with col3:
            total_valor = analytics_data['total_valor'].sum()
            st.metric(
                "Valor Total",
                format_currency(total_valor),
                help="Valor total das vendas das imobiliárias"
            )
        
        with col4:
            ticket_medio_geral = total_valor / total_vendas if total_vendas > 0 else 0
            st.metric(
                "Ticket Médio Geral",
                format_currency(ticket_medio_geral),
                help="Ticket médio geral de todas as imobiliárias"
            )
        
        # Tabela detalhada
        st.subheader("📊 Ranking de Imobiliárias")
        st.write("💡 **Dica:** A primeira coluna (índice) ordena automaticamente pelo Valor Total do maior para o menor.")
        
        # Preparar dados para exibição
        display_data = analytics_data.copy()
        
        # Ordenar por Valor Total (maior para menor) e criar índice
        display_data = display_data.sort_values('total_valor', ascending=False).reset_index(drop=True)
        display_data['Índice'] = range(1, len(display_data) + 1)
        
        # Formatar valores
        display_data['total_valor'] = display_data['total_valor'].apply(format_currency)
        display_data['ticket_medio'] = display_data['ticket_medio'].apply(format_currency)
        display_data['menor_venda'] = display_data['menor_venda'].apply(format_currency)
        display_data['maior_venda'] = display_data['maior_venda'].apply(format_currency)
        display_data['total_vendas'] = display_data['total_vendas'].apply(format_int)
        display_data['empreendimentos_unicos'] = display_data['empreendimentos_unicos'].apply(format_int)
        display_data['corretores_unicos'] = display_data['corretores_unicos'].apply(format_int)
        
        # Reordenar colunas para colocar Índice primeiro
        display_data = display_data[['Índice', 'imobiliaria', 'total_vendas', 'total_valor', 'ticket_medio',
                                   'menor_venda', 'maior_venda', 'empreendimentos_unicos', 'corretores_unicos']]
        
        # Renomear colunas
        display_data.columns = [
            'Índice', 'Imobiliária', 'Total Vendas', 'Valor Total', 'Ticket Médio',
            'Menor Venda', 'Maior Venda', 'Empreendimentos Únicos', 'Corretores Únicos'
        ]
        
        st.dataframe(
            display_data,
            use_container_width=True,
            hide_index=True
        )
        
        # Gráfico de barras - Top 10 imobiliárias por valor
        st.subheader("📈 Top 10 Imobiliárias por Valor")
        top_10 = analytics_data.head(10)
        
        fig = px.bar(
            top_10,
            x='imobiliaria',
            y='total_valor',
            title="Top 10 Imobiliárias por Valor Total",
            labels={'imobiliaria': 'Imobiliária', 'total_valor': 'Valor Total (R$)'},
            color='total_valor',
            color_continuous_scale='Greens'
        )
        fig.update_layout(
            xaxis_tickangle=-45,
            height=500,
            showlegend=False
        )
        fig.update_traces(
            texttemplate='R$ %{y:,.0f}',
            textposition='outside'
        )
        
        st.plotly_chart(fig, use_container_width=True, key=f"analytics_imobiliaria_chart_{key_suffix}")
        
    except Exception as e:
        st.error(f"❌ Erro ao carregar análise por imobiliária: {str(e)}")


if __name__ == "__main__":
    main()
