import streamlit as st
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from utils import display_navigation
import pandas as pd
from datetime import datetime
import plotly.express as px
import locale
import duckdb
from dotenv import load_dotenv
import os

# Metas de vendas por mês e empreendimento
meta_vendas = {
    'Ducale': {
        '2025-01': 0.0, '2025-02': 725000.0, '2025-03': 2325000.0,
        '2025-04': 714000.0, '2025-05': 0.0, '2025-06': 29600.0,
        '2025-07': 0.0, '2025-08': 320000.0, '2025-09': 650000.0,
        '2025-10': 676400.0, '2025-11': 320000.0, '2025-12': 0.0
    },
    'Horizont': {
        '2025-01': 2473000.0, '2025-02': 5384000.0, '2025-03': 2561000.0,
        '2025-04': 579000.0, '2025-05': 74000.0, '2025-06': 348000.0,
        '2025-07': 590000.0, '2025-08': 310000.0, '2025-09': 0.0,
        '2025-10': 310000.0, '2025-11': 0.0, '2025-12': 0.0
    },
    'Gualtieri': {
        '2025-01': 1023000.0, '2025-02': 1675000.0, '2025-03': 658000.0,
        '2025-04': 918000.0, '2025-05': 742000.0, '2025-06': 511479.0,
        '2025-07': 197500.0, '2025-08': 197500.0, '2025-09': 0.0,
        '2025-10': 197500.0, '2025-11': 0.0, '2025-12': 197500.0
    },
 'Carmel': {
    '2025-01': 0.0, '2025-02': 0.0, '2025-03': 0.0,
    '2025-04': 0.0, '2025-05': 0.0, '2025-06': 0.0,
    '2025-07': 7340000.0,
    '2025-08': 11010000.0,
    '2025-09': 3670000.0,
    '2025-10': 3670000.0,
    '2025-11': 2202000.0,
    '2025-12': 2202000.0
},
    'Villa Bella I': {
        '2025-01': 0.0, '2025-02': 0.0, '2025-03': 0.0,
        '2025-04': 7982000.0, '2025-05': 10614000.0, '2025-06': 2030179.73,
        '2025-07': 1190000.0, '2025-08': 952000.0, '2025-09': 952000.0,
        '2025-10': 952000.0, '2025-11': 714000.0, '2025-12': 714000.0
    },
    'Villa Bella II': {
        '2025-01': 0.0, '2025-02': 0.0, '2025-03': 0.0,
        '2025-04': 0.0, '2025-05': 0.0, '2025-06': 9096625.17,
        '2025-07': 3570000.0, '2025-08': 1428000.0, '2025-09': 1428000.0,
        '2025-10': 1190000.0, '2025-11': 1190000.0, '2025-12': 1190000.0
    },
    'Vera Cruz': {
        '2025-01': 0.0, '2025-02': 0.0, '2025-03': 465000.0,
        '2025-04': 781000.0, '2025-05': 1245000.0, '2025-06': 395910.0,
        '2025-07': 270000.0, '2025-08': 270000.0, '2025-09': 270000.0,
        '2025-10': 270000.0, '2025-11': 945000.0, '2025-12': 1080000.0
    },
    'Canada': {
        '2025-01': 0.0, '2025-02': 0.0, '2025-03': 0.0,
        '2025-04': 0.0, '2025-05': 0.0, '2025-06': 0.0,
        '2025-07': 0.0, '2025-08': 0.0, '2025-09': 0.0,
        '2025-10': 0.0, '2025-11': 2450000.0, '2025-12': 2555000.0
    }
}

# Configuração da página
st.set_page_config(page_title="Análise de Vendas", layout="wide")

# Display navigation bar (includes logo)
display_navigation()

# Store current page in session state
st.session_state['current_page'] = "pages/Vendas.py"

# Carregar variáveis de ambiente
load_dotenv()

# Configurar locale para formato brasileiro
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except locale.Error:
        try:
            locale.setlocale(locale.LC_ALL, 'pt_BR')
        except locale.Error:
            pass

def format_currency(value):
    """Format currency value to Brazilian Real format with MI (millions) or MIL (thousands)"""
    try:
        if value >= 1_000_000:  # Se for 1 milhão ou mais
            return f"R$ {value/1_000_000:.1f}Mi"
        elif value >= 1_000:  # Se for 1 mil ou mais
            return f"R$ {value/1_000:.1f}Mil"
        else:
            return f"R$ {value:.1f}"
    except:
        return f"R$ {value}"

# MotherDuck connection
@st.cache_resource
def get_motherduck_connection():
    """Create a cached connection to MotherDuck"""
    try:
        token = os.getenv('MOTHERDUCK_TOKEN')
        if not token:
            raise ValueError("MOTHERDUCK_TOKEN não encontrado nas variáveis de ambiente")
        
        # Sanitize o token
        token = token.strip().strip('"').strip("'")
        
        # Conectar diretamente ao MotherDuck com o token na URL (formato para conta free)
        connection_string = f'motherduck:reservas?motherduck_token={token}'
        
        try:
            conn = duckdb.connect(connection_string)
            return conn
        except Exception as e:
            st.error(f"Erro na conexão com MotherDuck: {str(e)}")
            raise
    except Exception as e:
        st.error(f"Erro ao configurar conexão: {str(e)}")
        raise

# Carregando os dados
@st.cache_data
def load_data():
    conn = get_motherduck_connection()    # Buscar todas as reservas com tipo de venda
    reservas_df = conn.sql("""
        SELECT 
            r.*,
            COALESCE(r.tipovenda, 'Outros') as tipo_venda,
            CASE 
                WHEN r.situacao = 'Vendida' THEN CAST(r.data_ultima_alteracao_situacao AS TIMESTAMP)
                ELSE NULL 
            END as data_venda,
            CASE 
                WHEN r.situacao = 'Vendida' THEN date_part('year', CAST(r.data_ultima_alteracao_situacao AS TIMESTAMP))
                ELSE NULL 
            END as ano_venda,
            CASE 
                WHEN r.situacao = 'Vendida' THEN date_part('month', CAST(r.data_ultima_alteracao_situacao AS TIMESTAMP))
                ELSE NULL 
            END as mes_venda
        FROM reservas.main.reservas_abril r
    """).df()
    
    # Converter colunas de data
    reservas_df['data_cad'] = pd.to_datetime(reservas_df['data_cad'])
    reservas_df['data_ultima_alteracao_situacao'] = pd.to_datetime(reservas_df['data_ultima_alteracao_situacao'])
    reservas_df['data_venda'] = pd.to_datetime(reservas_df['data_venda'])
  
    
    # Calcular tempo até a venda (em dias)
    reservas_df['tempo_ate_venda'] = (reservas_df['data_ultima_alteracao_situacao'] - reservas_df['data_cad']).dt.days
    
    # Identificar vendas internas (Prati) e externas (outras imobiliárias)
    reservas_df['tipo_venda_origem'] = reservas_df['imobiliaria'].apply(
        lambda x: 'Venda Interna (Prati)' if 'PRATI' in str(x).upper() else 'Venda Externa (Imobiliárias)'
    )
    
    return reservas_df

def normalizar_nome_empreendimento(nome):
    """Remove prefixos comuns e normaliza o nome do empreendimento"""
    prefixos = ['Residencial ', 'Loteamento ']
    nome_normalizado = nome
    for prefixo in prefixos:
        if nome.startswith(prefixo):
            nome_normalizado = nome.replace(prefixo, '')
    return nome_normalizado

# Título do aplicativo
st.title("📈 Análise de Vendas")

# Carregar dados
reservas_df = load_data()

# Sidebar para filtros
st.sidebar.header("Filtros")

# Log para debug das datas disponíveis
vendas_datas = reservas_df[reservas_df['situacao'] == 'Vendida']['data_venda'].dropna()
min_data = min(vendas_datas.dt.date)
max_data = max(vendas_datas.dt.date)

# Filtro de data - usar data_venda para vendas
data_inicio = st.sidebar.date_input(
    "Data Inicial",
    value=pd.Timestamp('2025-01-01'),
    min_value=min_data,
    max_value=max_data
)
data_fim = st.sidebar.date_input(
    "Data Final",
    value=max_data,
    min_value=min_data,
    max_value=max_data
)

# Filtro de empreendimento
empreendimentos = sorted(reservas_df['empreendimento'].unique())
empreendimento_selecionado = st.sidebar.selectbox("Empreendimento", ["Todos"] + list(empreendimentos))

# Filtro de imobiliária ordenado por vendas
vendas_por_imobiliaria = reservas_df[
    (reservas_df['situacao'] == 'Vendida')
].groupby('imobiliaria')['idreserva'].count().reset_index()
vendas_por_imobiliaria.columns = ['imobiliaria', 'total_vendas']
vendas_por_imobiliaria = vendas_por_imobiliaria.sort_values('total_vendas', ascending=False)

# Obter lista ordenada de imobiliárias por vendas
imobiliarias = vendas_por_imobiliaria['imobiliaria'].tolist()

# Adicionar imobiliárias sem vendas no período ao final da lista
todas_imobiliarias = set(reservas_df['imobiliaria'].unique())
imobiliarias.extend([i for i in todas_imobiliarias if i not in imobiliarias])

# Preparar lista de opções com destaque para Prati e mostrar contagem de vendas
options = ["Todas"] + imobiliarias
formatted_options = [
    f"{opt} ({vendas_por_imobiliaria[vendas_por_imobiliaria['imobiliaria'] == opt]['total_vendas'].iloc[0] if opt in vendas_por_imobiliaria['imobiliaria'].values else 0})" 
    if opt != "Todas" else opt for opt in options
]
formatted_options = [
    f"💠 {opt}" if "PRATI EMPREENDIMENTOS" in str(opt).upper() else opt 
    for opt in formatted_options
]
option_to_display = dict(zip(options, formatted_options))
imobiliaria_selecionada = st.sidebar.selectbox(
    "Imobiliária", 
    options,
    format_func=lambda x: option_to_display[x]
)

# Aplicar filtros básicos (não relacionados à data)
df_filtrado = reservas_df.copy()

# Aplicar filtro de empreendimento se selecionado
if empreendimento_selecionado != "Todos":
    df_filtrado = df_filtrado[df_filtrado['empreendimento'] == empreendimento_selecionado]

# Aplicar filtro de imobiliária se selecionado
if imobiliaria_selecionada != "Todas":
    df_filtrado = df_filtrado[df_filtrado['imobiliaria'] == imobiliaria_selecionada]

# Para vendas, usar data_venda no filtro - com validação de dados
vendas_2024 = df_filtrado[
    (df_filtrado['situacao'] == 'Vendida') & 
    (df_filtrado['data_venda'].dt.year == 2024)
]


# Para vendas, usar data_venda no filtro
vendas_filtradas = df_filtrado[
    (df_filtrado['situacao'] == 'Vendida') & 
    (df_filtrado['data_venda'].dt.date >= data_inicio) & 
    (df_filtrado['data_venda'].dt.date <= data_fim)
]

# Para outras situações, manter o filtro por data_cad
outras_situacoes = df_filtrado[
    (df_filtrado['situacao'] != 'Vendida') & 
    (df_filtrado['data_cad'].dt.date >= data_inicio) & 
    (df_filtrado['data_cad'].dt.date <= data_fim)
]



# Combinar os dataframes
df_filtrado = pd.concat([vendas_filtradas, outras_situacoes])

# Calcular dados do mês anterior
data_inicio_mes_anterior = pd.Timestamp('2025-01-01') if pd.Timestamp(data_inicio).strftime('%Y-%m-%d') == '2025-01-01' else pd.Timestamp(data_inicio) - pd.DateOffset(months=1)
data_fim_mes_anterior = pd.Timestamp('2025-01-01') - pd.DateOffset(days=1) if pd.Timestamp(data_inicio).strftime('%Y-%m-%d') == '2025-01-01' else pd.Timestamp(data_inicio) - pd.DateOffset(days=1)
# Filtrar vendas do mês anterior usando data_venda
vendas_mes_anterior = reservas_df[
    (reservas_df['situacao'] == 'Vendida') & 
    (reservas_df['data_venda'].dt.normalize() >= pd.Timestamp(data_inicio_mes_anterior)) & 
    (reservas_df['data_venda'].dt.normalize() <= pd.Timestamp(data_fim_mes_anterior))
]

# Filtrar outras situações do mês anterior usando data_cad
outras_situacoes_mes_anterior = reservas_df[
    (reservas_df['situacao'] != 'Vendida') & 
    (reservas_df['data_cad'].dt.normalize() >= pd.Timestamp(data_inicio_mes_anterior)) & 
    (reservas_df['data_cad'].dt.normalize() <= pd.Timestamp(data_fim_mes_anterior))
]

# Combinar os dataframes do mês anterior
df_mes_anterior = pd.concat([vendas_mes_anterior, outras_situacoes_mes_anterior])

# Aplicar os mesmos filtros do mês atual ao mês anterior
if empreendimento_selecionado != "Todos":
    df_mes_anterior = df_mes_anterior[df_mes_anterior['empreendimento'] == empreendimento_selecionado]
if imobiliaria_selecionada != "Todas":
    df_mes_anterior = df_mes_anterior[df_mes_anterior['imobiliaria'] == imobiliaria_selecionada]

# Métricas principais em uma linha
col1, col2, col3, col4, col5 = st.columns([2, 3, 3, 2, 2])

with col1:
    # Total de vendas no período usando data_venda
    vendas_periodo = df_filtrado[
    (df_filtrado['situacao'].isin(['Vendida', 'Mútuo'])) &
    (
        (df_filtrado['data_venda'].dt.normalize().between(pd.Timestamp(data_inicio), pd.Timestamp(data_fim))) |
        (df_filtrado['data_ultima_alteracao_situacao'].dt.normalize().between(pd.Timestamp(data_inicio), pd.Timestamp(data_fim)))
    )
]
    total_vendas = len(vendas_periodo)
    
    if total_vendas == 0 and empreendimento_selecionado != "Todos":
        st.warning(f"Não há vendas registradas para {empreendimento_selecionado} no período selecionado.")
        
    st.metric("Total de Vendas", f"{total_vendas:,}")

with col2:    # Valor total atual usando data_venda
    valor_total = vendas_periodo['valor_contrato'].sum() if not vendas_periodo.empty else 0
    # Calcular valor total de Mutuo no período usando data_ultima_alteracao_situacao
    base_mutuo = reservas_df.copy()
    if empreendimento_selecionado != "Todos":
        base_mutuo = base_mutuo[base_mutuo['empreendimento'] == empreendimento_selecionado]
    if imobiliaria_selecionada != "Todas":
        base_mutuo = base_mutuo[base_mutuo['imobiliaria'] == imobiliaria_selecionada]
        
    mutuo_periodo = base_mutuo[
        (base_mutuo['situacao'] == 'Mútuo') & 
        (base_mutuo['data_ultima_alteracao_situacao'].dt.date >= data_inicio) & 
        (base_mutuo['data_ultima_alteracao_situacao'].dt.date <= data_fim)
    ]
    valor_mutuo = mutuo_periodo['valor_contrato'].sum() if not mutuo_periodo.empty else 0    # Calcular o valor total (vendas + mútuo)
    valor_total_com_mutuo = valor_total + valor_mutuo
    
    st.metric(
        "Valor Total em Vendas",
        format_currency(valor_total_com_mutuo),
        help="Soma do valor de vendas e mútuos no período"
    )

with col3:# Calcular meta para o período selecionado
    valor_meta = 0
    data_inicio_ts = pd.Timestamp(data_inicio)
    data_fim_ts = pd.Timestamp(data_fim)
    
    if empreendimento_selecionado != "Todos":
        # Normaliza o nome do empreendimento selecionado
        nome_normalizado = normalizar_nome_empreendimento(empreendimento_selecionado)
        
        # Se um empreendimento específico foi selecionado
        if nome_normalizado in meta_vendas:
            metas_emp = meta_vendas[nome_normalizado]
            # Somar metas dentro do período selecionado
            for mes, valor in metas_emp.items():
                mes_ts = pd.Timestamp(f"{mes}-01")
                if valor > 0 and data_inicio_ts <= mes_ts <= data_fim_ts:
                    valor_meta += valor
    else:
        # Se nenhum empreendimento específico foi selecionado, somar todos
        for emp, metas in meta_vendas.items():
            for mes, valor in metas.items():
                mes_ts = pd.Timestamp(f"{mes}-01")  # Converter para timestamp para comparação correta
                # Só considera meses com meta > 0 e dentro do período selecionado
                if valor > 0 and data_inicio_ts <= mes_ts <= data_fim_ts:
                    valor_meta += valor
      # Calcular atingimento da meta
    atingimento = (valor_total_com_mutuo / valor_meta * 100) if valor_meta > 0 else 0
    
    st.metric(
        "Meta do Período",
        format_currency(valor_meta),
        f"{atingimento:.1f}% atingido",
        delta_color="inverse" if atingimento < 100 else "normal"
    )

with col4:    # Taxa house atual (considerando vendas e mútuos)
    vendas_e_mutuo = df_filtrado[
        ((df_filtrado['situacao'] == 'Vendida') & 
         (df_filtrado['data_venda'].dt.normalize() >= pd.Timestamp(data_inicio)) & 
         (df_filtrado['data_venda'].dt.normalize() <= pd.Timestamp(data_fim))) |
        ((df_filtrado['situacao'] == 'Mútuo') & 
         (df_filtrado['data_ultima_alteracao_situacao'].dt.normalize() >= pd.Timestamp(data_inicio)) & 
         (df_filtrado['data_ultima_alteracao_situacao'].dt.normalize() <= pd.Timestamp(data_fim)))
    ]
    transacoes_internas = len(vendas_e_mutuo[vendas_e_mutuo['tipo_venda_origem'] == 'Venda Interna (Prati)'])
    total_transacoes = len(vendas_e_mutuo)
    taxa_house = (transacoes_internas / total_transacoes * 100) if total_transacoes > 0 else 0      # Taxa house mês anterior (considerando vendas e mútuos)
    vendas_e_mutuo_anterior = df_mes_anterior[
        ((df_mes_anterior['situacao'] == 'Vendida') & 
         (df_mes_anterior['data_venda'].dt.normalize() >= pd.Timestamp(data_inicio_mes_anterior)) & 
         (df_mes_anterior['data_venda'].dt.normalize() <= pd.Timestamp(data_fim_mes_anterior))) |
        ((df_mes_anterior['situacao'] == 'Mútuo') & 
         (df_mes_anterior['data_ultima_alteracao_situacao'].dt.normalize() >= pd.Timestamp(data_inicio_mes_anterior)) & 
         (df_mes_anterior['data_ultima_alteracao_situacao'].dt.normalize() <= pd.Timestamp(data_fim_mes_anterior)))
    ]
    transacoes_internas_anterior = len(vendas_e_mutuo_anterior[vendas_e_mutuo_anterior['tipo_venda_origem'] == 'Venda Interna (Prati)'])
    total_transacoes_anterior = len(vendas_e_mutuo_anterior)
    taxa_house_anterior = (transacoes_internas_anterior / total_transacoes_anterior * 100) if total_transacoes_anterior > 0 else 0# Calcular variação em pontos percentuais
    variacao_taxa = taxa_house - taxa_house_anterior
    st.metric(
        "Taxa House",
        f"{taxa_house:.1f}%",
        f"{variacao_taxa:+.1f} P.P",
        help="Porcentagem de vendas e mútuos realizados pela Prati Empreendimentos"
    )

with col5:
    # Tempo médio apenas das vendas do período
    tempo_medio_geral = int(vendas_periodo['tempo_ate_venda'].mean().round(0)) if not vendas_periodo.empty else 0
    st.metric("Tempo Médio até a Venda", f"{tempo_medio_geral} dias", help="Tempo entre a reserva e a venda efetiva")

st.divider()

# Análise por tipo de venda (Interna vs Externa)
st.subheader("Análise Vendas House x Imobiliárias")

# Filtrar vendas e mútuos do período
df_vendas = df_filtrado[
    (
        ((df_filtrado['situacao'] == 'Vendida') & 
         (df_filtrado['data_venda'].dt.normalize() >= pd.Timestamp(data_inicio)) & 
         (df_filtrado['data_venda'].dt.normalize() <= pd.Timestamp(data_fim))) |
        ((df_filtrado['situacao'] == 'Mútuo') & 
         (df_filtrado['data_ultima_alteracao_situacao'].dt.normalize() >= pd.Timestamp(data_inicio)) & 
         (df_filtrado['data_ultima_alteracao_situacao'].dt.normalize() <= pd.Timestamp(data_fim)))
    )
]

# Agrupamento por tipo de venda sem o campo 'tempo_ate_venda'
analise_origem = df_vendas.groupby('tipo_venda_origem').agg({
    'idreserva': 'count',
    'valor_contrato': 'sum'
}).reset_index()

# Ajustando os nomes das colunas
analise_origem.columns = ['Origem', 'Quantidade', 'Valor Total']
analise_origem['Valor Total'] = analise_origem['Valor Total'].apply(format_currency)

# Exibindo tabela final sem a coluna "Tempo Médio (dias)"
st.table(analise_origem)

st.divider()

# Análise estratificada por empreendimento e tipo de venda
st.subheader("Vendas House x Imobiliárias por Empreendimento")

# Criar DataFrames separados para cada métrica
# Usar apenas vendas efetivas
df_vendas = df_filtrado[df_filtrado['situacao'] == 'Vendida']

quantidade = df_vendas.pivot_table(
    index='empreendimento',
    columns='tipo_venda_origem',
    values='idreserva',
    aggfunc='count',
    fill_value=0
).reset_index()

valor = df_vendas.pivot_table(
    index='empreendimento',
    columns='tipo_venda_origem',
    values='valor_contrato',
    aggfunc='sum',
    fill_value=0
).reset_index()

tempo = df_vendas.pivot_table(
    index='empreendimento',
    columns='tipo_venda_origem',
    values='tempo_ate_venda',
    aggfunc='mean',
    fill_value=0
).reset_index()

# Criar DataFrame final
estratificacao = pd.DataFrame()
estratificacao['Empreendimento'] = quantidade['empreendimento']

# Adicionar colunas com tratamento para colunas que podem não existir
estratificacao['Quantidade (Interna)'] = quantidade['Venda Interna (Prati)'] if 'Venda Interna (Prati)' in quantidade.columns else 0
estratificacao['Quantidade (Externa)'] = quantidade['Venda Externa (Imobiliárias)'] if 'Venda Externa (Imobiliárias)' in quantidade.columns else 0
estratificacao['Valor Total (Interna)'] = valor['Venda Interna (Prati)'] if 'Venda Interna (Prati)' in valor.columns else 0
estratificacao['Valor Total (Externa)'] = valor['Venda Externa (Imobiliárias)'] if 'Venda Externa (Imobiliárias)' in valor.columns else 0
estratificacao['Tempo Médio (Interna)'] = tempo['Venda Interna (Prati)'] if 'Venda Interna (Prati)' in tempo.columns else 0
estratificacao['Tempo Médio (Externa)'] = tempo['Venda Externa (Imobiliárias)'] if 'Venda Externa (Imobiliárias)' in tempo.columns else 0

# Formatar valores
estratificacao['Valor Total (Interna)'] = estratificacao['Valor Total (Interna)'].apply(format_currency)
estratificacao['Valor Total (Externa)'] = estratificacao['Valor Total (Externa)'].apply(format_currency)
estratificacao['Tempo Médio (Interna)'] = estratificacao['Tempo Médio (Interna)'].round(0).astype(int)
estratificacao['Tempo Médio (Externa)'] = estratificacao['Tempo Médio (Externa)'].round(0).astype(int)

# Calcular e adicionar linha de totais
vendas_internas = df_vendas[df_vendas['tipo_venda_origem'] == 'Venda Interna (Prati)']
vendas_externas = df_vendas[df_vendas['tipo_venda_origem'] == 'Venda Externa (Imobiliárias)']

totais = pd.DataFrame([{
    'Empreendimento': 'Total',
    'Quantidade (Interna)': vendas_internas['idreserva'].count(),
    'Quantidade (Externa)': vendas_externas['idreserva'].count(),
    'Valor Total (Interna)': format_currency(vendas_internas['valor_contrato'].sum()),
    'Valor Total (Externa)': format_currency(vendas_externas['valor_contrato'].sum()),
    'Tempo Médio (Interna)': int(vendas_internas['tempo_ate_venda'].mean()) if not vendas_internas.empty else 0,
    'Tempo Médio (Externa)': int(vendas_externas['tempo_ate_venda'].mean()) if not vendas_externas.empty else 0
}])

estratificacao = pd.concat([estratificacao, totais], ignore_index=True)

# Remover a ordenação para manter a ordem original dos empreendimentos
estratificacao = estratificacao.copy()

st.table(estratificacao)

st.divider()

# Análise de conversão de reservas em vendas
st.subheader("Taxa de Conversão de Vendas")

# Calcular taxas de conversao para vendas internas e externas
def calcular_taxa_conversao(df, df_reservas, tipo_venda, data_inicio, data_fim, empreendimento=None, imobiliaria=None):
    # Aplicar os mesmos filtros de empreendimento e imobiliária nas reservas
    df_reservas_filtrado = df_reservas.copy()
    if empreendimento and empreendimento != "Todos":
        df_reservas_filtrado = df_reservas_filtrado[df_reservas_filtrado['empreendimento'] == empreendimento]
    if imobiliaria and imobiliaria != "Todas":
        df_reservas_filtrado = df_reservas_filtrado[df_reservas_filtrado['imobiliaria'] == imobiliaria]

    # Total de reservas no período com filtros aplicados
    reservas_periodo = df_reservas_filtrado[
        (df_reservas_filtrado['tipo_venda_origem'] == tipo_venda) &
        (df_reservas_filtrado['data_cad'].dt.date >= data_inicio) &
        (df_reservas_filtrado['data_cad'].dt.date <= data_fim)
    ]
    total_reservas = len(reservas_periodo)
    
    # Total de vendas no período (usando data_venda)
    vendas_periodo = df[
        (df['tipo_venda_origem'] == tipo_venda) &
        (df['situacao'] == 'Vendida') &
        (df['data_venda'].dt.date >= data_inicio) &
        (df['data_venda'].dt.date <= data_fim)
    ]
    total_vendas = len(vendas_periodo)
    
    taxa = (total_vendas / total_reservas * 100) if total_reservas > 0 else 0
    return pd.Series({
        'Total Reservas': total_reservas,
        'Total Vendas': total_vendas,
        'Taxa de Conversão': taxa
    })

# Criar DataFrame de conversão usando data_venda para o período
conversao_interna = calcular_taxa_conversao(df_filtrado, reservas_df, 'Venda Interna (Prati)', data_inicio, data_fim, 
                                          empreendimento_selecionado, imobiliaria_selecionada)
conversao_externa = calcular_taxa_conversao(df_filtrado, reservas_df, 'Venda Externa (Imobiliárias)', data_inicio, data_fim,
                                          empreendimento_selecionado, imobiliaria_selecionada)

conversao_df = pd.DataFrame({
    'Métricas': ['Total Reservas', 'Total Vendas', 'Taxa de Conversão'],
    'Venda Interna': [
        f"{conversao_interna['Total Reservas']:,}",
        f"{conversao_interna['Total Vendas']:,}",
        f"{conversao_interna['Taxa de Conversão']:.1f}%"
    ],
    'Venda Externa': [
        f"{conversao_externa['Total Reservas']:,}",
        f"{conversao_externa['Total Vendas']:,}",
        f"{conversao_externa['Taxa de Conversão']:.1f}%"
    ]
})
