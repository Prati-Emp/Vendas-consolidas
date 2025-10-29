import streamlit as st
import os

# Importar sistema de autenticação avançado
from advanced_auth import require_auth

# Função para obter o caminho absoluto da logo
def get_logo_path():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, "logo.png")

# Configuração da página
st.set_page_config(page_title="Relatório de Reservas", layout="wide")

# Proteger com autenticação
require_auth()

from utils import display_navigation
# Display navigation bar (includes logo)
display_navigation()

# Store current page in session state
st.session_state['current_page'] = __file__

import pandas as pd
from datetime import datetime
import re
import locale
import duckdb
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Set locale to Brazilian Portuguese silently
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
    """Format currency value to Brazilian Real format"""
    try:
        return f"R$ {value:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return f"R$ {value}"

# Situações consideradas como conversão de reserva em venda
CONVERSAO_SITUACOES = {situacao.lower() for situacao in ["Distrato", "Mútuo", "Vendida"]}

# Mapeamento de meses (2025) para as colunas da tabela de metas
MESES_COLUNAS_2025 = {
    1: "jan/25",
    2: "fev/25",
    3: "mar/25",
    4: "abr/25",
    5: "mai/25",
    6: "jun/25",
    7: "jul/25",
    8: "ago/25",
    9: "set/25",
    10: "out/25",
    11: "nov/25",
    12: "dez/25",
}

MESES_NOME_PT = {
    1: "janeiro",
    2: "fevereiro",
    3: "março",
    4: "abril",
    5: "maio",
    6: "junho",
    7: "julho",
    8: "agosto",
    9: "setembro",
    10: "outubro",
    11: "novembro",
    12: "dezembro",
}

# Sistema de autenticação removido por questões de segurança
# Para implementar autenticação segura, use:
# - Azure Active Directory
# - AWS Cognito  
# - Auth0
# - ou outro provedor de identidade confiável
# Título do aplicativo
st.title("📊 Relatório de Reservas")

def extract_days(situacao):
    # Extrai o número entre parênteses da situação
    match = re.search(r'\((\d+)\)', situacao)
    if match:
        return int(match.group(1))
    return 0

def check_time_limit(row):
    # Extrai o número entre parênteses da situação
    dias_limite = extract_days(row['situacao'])
    
    if dias_limite == 0:
        return False
        
    # Pega a data da última alteração diretamente da tabela de reservas
    data_ultima_alteracao = pd.to_datetime(row.get('data_ultima_alteracao_situacao'), errors='coerce')
    
    if pd.isna(data_ultima_alteracao):
        return False
    
    # Calcula a diferença entre agora e a última alteração em dias
    dias_decorridos = (pd.Timestamp.now() - data_ultima_alteracao).days
    
    # Verifica se o tempo desde a última alteração excede o limite
    return dias_decorridos >= dias_limite

# MotherDuck connection
@st.cache_resource
def get_motherduck_connection():
    """Create a cached connection to MotherDuck"""
    try:        
        token = os.getenv('MOTHERDUCK_TOKEN')
        
        if not token:
            load_dotenv(override=True)
            token = os.getenv('MOTHERDUCK_TOKEN')
            st.write("Token após reload do .env:", "Sim" if token else "Não")
            
            if not token:
                raise ValueError("MOTHERDUCK_TOKEN não encontrado nas variáveis de ambiente")

        # Sanitize
        token = token.strip().strip('"').strip("'")
        os.environ["MOTHERDUCK_TOKEN"] = token  
        
        conn = duckdb.connect("md:reservas")
        return conn

    except Exception as e:
        st.error(f"Erro ao configurar conexão: {str(e)}")
        raise

# Carregando os dados
@st.cache_data
def load_data():
    try:
        conn = get_motherduck_connection()
        
        # Usando as tabelas do MotherDuck com o esquema correto
        reservas_df = conn.sql("""
            SELECT *
            FROM reservas.main.reservas_abril
        """).df()
        
        workflow_df = conn.sql("""
            SELECT *
            FROM reservas.main.workflow_abril
        """).df()
        
        # Converter colunas de data com tratamento de erros
        for df in [reservas_df, workflow_df]:
            for col in df.select_dtypes(include=['object']).columns:
                try:
                    if 'data' in col.lower():
                        df[col] = pd.to_datetime(df[col], errors='coerce')
                except Exception as e:
                    st.warning(f"Erro ao converter coluna {col}: {str(e)}")
        
        # Remover linhas com datas inválidas apenas das colunas necessárias
        reservas_df = reservas_df.dropna(subset=['data_cad'])
        
        # Se não houver dados válidos, criar DataFrame com dados padrão
        if len(reservas_df) == 0:
            current_date = pd.Timestamp.now()
            reservas_df = pd.DataFrame({
                'data_cad': [current_date],
                'data_ultima_alteracao_situacao': [current_date],
                'empreendimento': ['Sem dados'],
                'situacao': ['Sem dados'],
                'valor_contrato': [0]
            })
            
        return reservas_df, workflow_df
        
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        current_date = pd.Timestamp.now()
        
        # Criar DataFrame com dados padrão em caso de erro
        reservas_df = pd.DataFrame({
            'data_cad': [current_date],
            'data_ultima_alteracao_situacao': [current_date],
            'empreendimento': ['Erro ao carregar dados'],
            'situacao': ['Erro'],
            'valor_contrato': [0]
        })
        workflow_df = pd.DataFrame()
        
        return reservas_df, workflow_df

reservas_df, workflow_df = load_data()

# Sidebar para filtros
st.sidebar.header("Filtros")

# Configurar valores padrão seguros para os filtros de data
default_start_date = pd.Timestamp('2025-01-01').date()
default_end_date = datetime.now().date()

try:
    # Converter datas para datetime.date
    valid_dates = reservas_df['data_cad'].dropna().dt.date
    if len(valid_dates) > 0:
        min_date = min(valid_dates)
        max_date = max(valid_dates)
    else:
        min_date = default_start_date
        max_date = default_end_date
except Exception as e:
    st.warning("Usando datas padrão devido a erro na conversão de datas")
    min_date = default_start_date
    max_date = default_end_date

# Garantir que as datas estejam em ordem correta
if min_date > max_date:
    min_date, max_date = max_date, min_date

# Garantir que temos valores válidos para o date_input
initial_value = min(max(default_start_date, min_date), max_date)

# Filtro de data com valores seguros
try:
    data_inicio = st.sidebar.date_input(
        "Data Inicial",
        value=initial_value,
        min_value=min_date,
        max_value=max_date
    )
    
    # Garantir que a data final seja posterior à inicial
    data_fim = st.sidebar.date_input(
        "Data Final",
        value=max(max_date, data_inicio),
        min_value=data_inicio,
        max_value=max_date
    )
except Exception as e:
    st.error(f"Erro ao configurar filtros de data: {str(e)}")
    data_inicio = min_date
    data_fim = max_date

# Filtro de empreendimento
empreendimentos = sorted(reservas_df['empreendimento'].unique())
empreendimento_selecionado = st.sidebar.selectbox("Empreendimento", ["Todos"] + list(empreendimentos))

# Filtro de situação
situacoes = sorted(reservas_df[~reservas_df['situacao'].isin(['Vendida', 'Distrato', 'Cancelada'])]['situacao'].unique())
situacao_selecionada = st.sidebar.selectbox("Situação", ["Todas"] + list(situacoes))

# Separador para filtros de conversão
st.sidebar.markdown("---")
st.sidebar.subheader("📊 Filtros Conversão")

# Buscar a maior data disponível no conjunto de dados
max_data_cad = pd.to_datetime('2025-12-31').date()  # Fallback padrão
try:
    conn_temp = get_motherduck_connection()
    max_date_query = conn_temp.sql("SELECT MAX(data_cad) FROM reservas.main.reservas_abril WHERE data_cad IS NOT NULL").df()
    if not max_date_query.empty and max_date_query.iloc[0, 0] is not None:
        max_data_cad = pd.to_datetime(max_date_query.iloc[0, 0]).date()
except Exception as e:
    st.sidebar.warning(f"⚠️ Não foi possível carregar a data máxima: {e}")

# Filtros específicos para a tabela de conversão
data_inicial_conversao = st.sidebar.date_input(
    "📅 Data Inicial (Conversão)",
    value=pd.to_datetime('2025-01-01').date(),
    help="Filtra reservas a partir desta data"
)

data_final_conversao = st.sidebar.date_input(
    "📅 Data Final (Conversão)",
    value=max_data_cad,
    help="Filtra reservas até esta data"
)

# Aplicar filtros
mask = (
    reservas_df['data_cad'].dt.date >= data_inicio
) & (
    reservas_df['data_cad'].dt.date <= data_fim
) & (
    reservas_df['situacao'].str.strip().str.upper() != 'MÚTUO'
)
if empreendimento_selecionado != "Todos":
    mask = mask & (reservas_df['empreendimento'] == empreendimento_selecionado)
if situacao_selecionada != "Todas":
    mask = mask & (reservas_df['situacao'] == situacao_selecionada)

df_filtrado = reservas_df[mask].copy()

# Métricas principais
df_sem_canceladas_vendidas = df_filtrado[~df_filtrado['situacao'].isin(['Cancelada', 'Vendida', 'Distrato'])].copy()

col1, col2 = st.columns(2)
with col1:
    st.metric(label="Total De Reservas", value=len(df_sem_canceladas_vendidas))
with col2:
    valor_total = df_sem_canceladas_vendidas['valor_contrato'].sum()
    st.metric(label="Valor Total", value=format_currency(valor_total))
    
    
# Reservas por Situação
st.subheader("Reservas Por Situação")

# Definir ordem do funil de vendas
ordem_situacoes = [
    'Reserva (7)',
    'Crédito (CEF) (3)',
    'Negociação (5)',
    'Mútuo',
    'Análise Diretoria',
    'Contrato - Elaboração',
    'Contrato - Assinatura',
    #'Vendida',
    # 'Distrato'
]

if df_filtrado.empty:
    st.info("Nenhuma reserva encontrada para os filtros selecionados.")
else:
    if df_sem_canceladas_vendidas.empty:
        st.info("Nenhuma reserva ativa disponível para exibição por situação.")
    else:
        quantidade_por_situacao = (
            df_sem_canceladas_vendidas['situacao']
            .value_counts()
            .rename_axis('Situação')
            .reset_index(name='Quantidade')
        )

        ordem_mapping = {situacao: idx for idx, situacao in enumerate(ordem_situacoes)}
        quantidade_por_situacao['ordem'] = quantidade_por_situacao['Situação'].map(ordem_mapping)
        quantidade_por_situacao = quantidade_por_situacao.sort_values(['ordem', 'Situação']).drop(columns=['ordem'])

        df_sem_canceladas_vendidas['data_ultima_alteracao_situacao'] = pd.to_datetime(
            df_sem_canceladas_vendidas['data_ultima_alteracao_situacao'],
            errors='coerce'
        )

        df_sem_canceladas_vendidas['tempo_excedido'] = df_sem_canceladas_vendidas.apply(check_time_limit, axis=1)
        df_sem_canceladas_vendidas['dias_na_situacao'] = (
            pd.Timestamp.now() - df_sem_canceladas_vendidas['data_ultima_alteracao_situacao']
        ).dt.days
        df_sem_canceladas_vendidas['dias_na_situacao'] = df_sem_canceladas_vendidas['dias_na_situacao'].fillna(0).astype(int)

        tempo_medio = (
            df_sem_canceladas_vendidas.groupby('situacao', dropna=False)['dias_na_situacao']
            .mean()
            .round(0)
            .reset_index()
        )
        tempo_medio.columns = ['Situação', 'Tempo Médio']
        tempo_medio['Tempo Médio'] = tempo_medio['Tempo Médio'].fillna(0).astype(int)

        fora_prazo_por_situacao = (
            df_sem_canceladas_vendidas[df_sem_canceladas_vendidas['tempo_excedido']]
            .groupby('situacao')['tempo_excedido']
            .count()
            .reset_index()
        )
        fora_prazo_por_situacao.columns = ['Situação', 'Fora do Prazo']

        reservas_por_situacao = pd.merge(quantidade_por_situacao, fora_prazo_por_situacao, on='Situação', how='left')
        reservas_por_situacao = pd.merge(reservas_por_situacao, tempo_medio, on='Situação', how='left')
        reservas_por_situacao['Fora do Prazo'] = reservas_por_situacao['Fora do Prazo'].fillna(0).astype(int)
        reservas_por_situacao['Tempo Médio'] = reservas_por_situacao['Tempo Médio'].fillna(0).astype(int)

        reservas_por_situacao['Fora do Prazo'] = reservas_por_situacao.apply(
            lambda row: min(row['Fora do Prazo'], row['Quantidade']),
            axis=1
        )

        reservas_por_situacao['Dentro do Prazo'] = reservas_por_situacao['Quantidade'] - reservas_por_situacao['Fora do Prazo']

        # Reordenar as colunas mantendo os nomes originais exatos
        reservas_por_situacao = reservas_por_situacao[['Situação', 'Quantidade', 'Fora do Prazo', 'Tempo Médio', 'Dentro do Prazo']]

        # Adicionar linha de totais
        totais = pd.DataFrame([{
            'Situação': 'Total',
            'Quantidade': reservas_por_situacao['Quantidade'].sum(),
            'Fora do Prazo': reservas_por_situacao['Fora do Prazo'].sum(),
            'Tempo Médio': round(reservas_por_situacao['Tempo Médio'].mean()) if not reservas_por_situacao.empty else 0,
            'Dentro do Prazo': reservas_por_situacao['Dentro do Prazo'].sum()
        }])

        reservas_por_situacao = pd.concat([reservas_por_situacao, totais], ignore_index=True)

        st.table(reservas_por_situacao)

        # Funil de Reservas por Situação
        try:
            import plotly.graph_objects as go
            funnel_df = reservas_por_situacao[reservas_por_situacao['Situação'] != 'Total']
            if not funnel_df.empty:
                fig = go.Figure(go.Funnel(
                    y=funnel_df['Situação'],
                    x=funnel_df['Quantidade'],
                    textinfo="value+percent initial"
                ))
                fig.update_layout(
                    title="Funil de Reservas por Situação",
                    height=500
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sem dados suficientes para montar o funil com os filtros selecionados.")
        except Exception as e:
            st.warning(f"Não foi possível renderizar o funil: {str(e)}")

    st.divider()

    # Reservas por Empreendimento
    st.subheader("Reservas Por Empreendimento")

    if df_sem_canceladas_vendidas.empty:
        st.info("Nenhuma reserva ativa disponível para exibição por empreendimento.")
    else:
        quantidade_por_empreendimento = (
            df_sem_canceladas_vendidas['empreendimento']
            .value_counts()
            .rename_axis('Empreendimento')
            .reset_index(name='Quantidade')
        )

        fora_prazo_por_empreendimento = (
            df_sem_canceladas_vendidas[df_sem_canceladas_vendidas['tempo_excedido']]
            .groupby('empreendimento')['tempo_excedido']
            .count()
            .reset_index()
        )
        fora_prazo_por_empreendimento.columns = ['Empreendimento', 'Fora do Prazo']

        tempo_medio_empreendimento = (
            df_sem_canceladas_vendidas.groupby('empreendimento')['dias_na_situacao']
            .mean()
            .round(0)
            .reset_index()
        )
        tempo_medio_empreendimento.columns = ['Empreendimento', 'Tempo Médio']
        tempo_medio_empreendimento['Tempo Médio'] = tempo_medio_empreendimento['Tempo Médio'].fillna(0).astype(int)

        reservas_por_empreendimento = pd.merge(quantidade_por_empreendimento, fora_prazo_por_empreendimento, on='Empreendimento', how='left')
        reservas_por_empreendimento = pd.merge(reservas_por_empreendimento, tempo_medio_empreendimento, on='Empreendimento', how='left')
        reservas_por_empreendimento['Fora do Prazo'] = reservas_por_empreendimento['Fora do Prazo'].fillna(0).astype(int)
        reservas_por_empreendimento['Tempo Médio'] = reservas_por_empreendimento['Tempo Médio'].fillna(0).astype(int)

        # Garantir que "Fora do Prazo" não seja maior que "Quantidade"
        reservas_por_empreendimento['Fora do Prazo'] = reservas_por_empreendimento.apply(
            lambda row: min(row['Fora do Prazo'], row['Quantidade']), 
            axis=1
        )

        # Calcular "Dentro do Prazo"
        reservas_por_empreendimento['Dentro do Prazo'] = reservas_por_empreendimento['Quantidade'] - reservas_por_empreendimento['Fora do Prazo']

        # Reordenar as colunas mantendo os nomes originais exatos
        reservas_por_empreendimento = reservas_por_empreendimento[['Empreendimento', 'Quantidade', 'Fora do Prazo', 'Tempo Médio', 'Dentro do Prazo']]

        # Adicionar linha de totais
        totais_empreendimento = pd.DataFrame([{
            'Empreendimento': 'Total',
            'Quantidade': reservas_por_empreendimento['Quantidade'].sum(),
            'Fora do Prazo': reservas_por_empreendimento['Fora do Prazo'].sum(),
            'Tempo Médio': round(reservas_por_empreendimento['Tempo Médio'].mean()) if not reservas_por_empreendimento.empty else 0,
            'Dentro do Prazo': reservas_por_empreendimento['Dentro do Prazo'].sum()
        }])

        reservas_por_empreendimento = pd.concat([reservas_por_empreendimento, totais_empreendimento], ignore_index=True)

        st.table(reservas_por_empreendimento)

# =============================================================================
# NOVA TABELA: CONVERSÃO DE RESERVAS EM VENDAS
# =============================================================================

st.subheader("📊 Conversão de Reservas em Vendas")

# Caixa de informação sobre filtros e observações
st.info("""
📋 **Informações Importantes:**

• **Filtro Próprio:** Esta tabela possui filtros específicos localizados na barra lateral (sidebar) 
  sob a seção "📊 Filtros Conversão"

• ⚠️ **Importante:** Os números podem variar conforme o fechamento das vendas, pois a análise considera a data de cadastro (data_cad) da reserva. Uma venda pode ser cadastrada em um período e efetivada posteriormente, mas será contabilizada conforme a data de cadastro.

• 📌 **Total de Reservas:** A coluna contabiliza todas as situações registradas, incluindo reservas canceladas.
""")

# Dica sobre ordenação
st.write("💡 **Dica:** A primeira coluna (índice) ordena automaticamente pelo número de reservas do maior para o menor.")

# Variáveis auxiliares para o termômetro de vendas
conversao_df_base = pd.DataFrame()
taxa_conversao_geral = 0.0
total_reservas_conversao = 0
reservas_convertidas_total = 0

try:
    # Carregar dados de reservas para análise de conversão
    conn = get_motherduck_connection()
    
    # Converter datas para string no formato correto
    data_inicial_str = data_inicial_conversao.strftime('%Y-%m-%d')
    data_final_str = data_final_conversao.strftime('%Y-%m-%d')
    
    # Query para buscar dados de reservas com filtro por data_cad
    conversao_df = conn.sql("""
        SELECT 
            corretor,
            situacao,
            data_cad,
            empreendimento
        FROM reservas.main.reservas_abril
        WHERE data_cad IS NOT NULL
        AND corretor IS NOT NULL
        AND corretor != ''
        AND CAST(data_cad AS DATE) >= CAST(? AS DATE)
        AND CAST(data_cad AS DATE) <= CAST(? AS DATE)
    """, params=[data_inicial_str, data_final_str]).df()
    
    if not conversao_df.empty:
        # Normalizar campos textuais
        conversao_df['situacao'] = conversao_df['situacao'].astype(str).str.strip()
        conversao_df['empreendimento'] = conversao_df['empreendimento'].astype(str).str.strip()

        # Remover situação "Mútuo" do conjunto da tabela de conversão
        conversao_df = conversao_df[conversao_df['situacao'].str.upper() != 'MÚTUO']

        # Aplicar filtros gerais (exceto data, que já é dedicada)
        if empreendimento_selecionado != "Todos":
            empreendimento_normalizado = empreendimento_selecionado.strip().upper()
            conversao_df = conversao_df[
                conversao_df['empreendimento'].str.upper() == empreendimento_normalizado
            ]

        if conversao_df.empty:
            st.warning("⚠️ Nenhum dado de reservas encontrado com os filtros selecionados.")
        else:
            # Converter data_cad para datetime
            conversao_df['data_cad'] = pd.to_datetime(conversao_df['data_cad'], errors='coerce')
            conversao_df['situacao_normalizada'] = conversao_df['situacao'].str.lower()

            # Guardar dataframe filtrado para o termômetro
            conversao_df_base = conversao_df.copy()

            # Métricas gerais de conversão
            total_reservas_conversao = len(conversao_df_base)
            reservas_convertidas_total = (
                conversao_df_base['situacao_normalizada'].isin(CONVERSAO_SITUACOES)
            ).sum()
            taxa_conversao_geral = (
                reservas_convertidas_total / total_reservas_conversao
            ) if total_reservas_conversao > 0 else 0.0
            
            # Calcular métricas por corretor
            conversao_por_corretor = []
            
            for corretor in conversao_df_base['corretor'].unique():
                df_corretor = conversao_df_base[conversao_df_base['corretor'] == corretor]
                
                # Total de reservas
                total_reservas = len(df_corretor)
                
                # Reservas convertidas (Distrato, Mútuo, Vendida)
                reservas_convertidas = df_corretor['situacao_normalizada'].isin(CONVERSAO_SITUACOES).sum()
                
                # Calcular taxa de conversão
                taxa_conversao = (reservas_convertidas / total_reservas * 100) if total_reservas > 0 else 0
                
                conversao_por_corretor.append({
                    'Corretor': corretor,
                    'Total Reservas': total_reservas,
                    'Reservas Convertidas': reservas_convertidas,
                    'Taxa Conversão (%)': round(taxa_conversao, 2)
                })
            
            # Converter para DataFrame
            conversao_df_final = pd.DataFrame(conversao_por_corretor)
            
            if conversao_df_final.empty:
                st.warning("⚠️ Nenhum dado de reservas encontrado para análise de conversão.")
            else:
                # Ordenar por número de reservas (maior para menor)
                conversao_df_final = conversao_df_final.sort_values('Total Reservas', ascending=False)
                
                # Adicionar linha de totais
                totais_conversao = pd.DataFrame([{
                    'Corretor': 'Total',
                    'Total Reservas': conversao_df_final['Total Reservas'].sum(),
                    'Reservas Convertidas': conversao_df_final['Reservas Convertidas'].sum(),
                    'Taxa Conversão (%)': round(
                        (conversao_df_final['Reservas Convertidas'].sum() / 
                         conversao_df_final['Total Reservas'].sum() * 100) 
                        if conversao_df_final['Total Reservas'].sum() > 0 else 0, 2
                    )
                }])
                
                conversao_df_final = pd.concat([conversao_df_final, totais_conversao], ignore_index=True)
                
                # Exibir tabela
                st.dataframe(conversao_df_final, use_container_width=True)
        
    else:
        st.warning("⚠️ Nenhum dado de reservas encontrado para análise de conversão.")
        
except Exception as e:
    st.error(f"❌ Erro ao carregar dados de conversão: {str(e)}")

# =============================================================================
# INDICADOR: TERMÔMETRO DE VENDAS
# =============================================================================

st.divider()
st.subheader("🌡️ Termômetro de Vendas")

# Cálculo das reservas atuais (mesma lógica do indicador principal)
reservas_atuais_total = len(df_sem_canceladas_vendidas)
valor_total_reservas = float(df_sem_canceladas_vendidas.get('valor_contrato', pd.Series(dtype=float)).fillna(0).sum())

# Calcular metas do mês atual
meta_total = 0.0
coluna_meta_atual = MESES_COLUNAS_2025.get(datetime.now().month)
mes_referencia_label = MESES_NOME_PT.get(datetime.now().month, "mês atual")

metas_df = pd.DataFrame()
if coluna_meta_atual:
    try:
        conn_meta = get_motherduck_connection()
        metas_df = conn_meta.sql("""
            SELECT 
                "Empreendiemento" AS nome_empreendimento,
                "Codigo empreendimento" AS codigo_empreendimento,
                "jan/25",
                "fev/25",
                "mar/25",
                "abr/25",
                "mai/25",
                "jun/25",
                "jul/25",
                "ago/25",
                "set/25",
                "out/25",
                "nov/25",
                "dez/25"
            FROM informacoes_consolidadas.meta_vendas_2025
        """).df()

        if not metas_df.empty:
            metas_df['nome_empreendimento'] = metas_df['nome_empreendimento'].astype(str).str.strip()
            if empreendimento_selecionado != "Todos":
                empreendimento_meta = empreendimento_selecionado.strip().upper()
                metas_df = metas_df[metas_df['nome_empreendimento'].str.upper() == empreendimento_meta]

            if not metas_df.empty and coluna_meta_atual in metas_df.columns:
                metas_valores = metas_df[coluna_meta_atual].apply(pd.to_numeric, errors='coerce').fillna(0)
                meta_total = float(metas_valores.sum())
    except Exception as e:
        st.warning(f"⚠️ Não foi possível carregar as metas de vendas: {e}")

# Potencial de vendas usando valor total das reservas ativas e taxa de conversão
potencial_vendas_valor = valor_total_reservas * taxa_conversao_geral

if meta_total > 0:
    cobertura_percent = (potencial_vendas_valor / meta_total) * 100
else:
    cobertura_percent = 0.0

cobertura_percent = float(cobertura_percent)

if meta_total <= 0:
    status = "Sem meta cadastrada"
    interpretacao = "Não encontramos metas para o mês atual."
    acao = "Atualize os dados de metas ou verifique o cadastro do mês corrente."
    status_color = "#95a5a6"
else:
    if cobertura_percent < 70:
        status = "Frio"
        interpretacao = "Reservas insuficientes para atingir a meta."
        acao = "Intensificar prospecção e aumentar o volume de reservas."
        status_color = "#1E90FF"
    elif cobertura_percent <= 100:
        status = "Morno"
        interpretacao = "Em linha, mas ainda vulnerável."
        acao = "Focar em qualificação e follow-ups." 
        status_color = "#f1c40f"
    else:
        status = "Quente"
        interpretacao = "Carteira suficiente para atingir a meta."
        acao = "Manter ritmo e reforçar o fechamento."
        status_color = "#27ae60"

status_text_color = "#0b0b0b"
if status in {"Frio", "Quente"}:
    status_text_color = "#ffffff"

col_meta = st.columns(5)
col_meta[0].metric("Meta de Vendas", format_currency(meta_total) if meta_total > 0 else "—")
col_meta[1].metric("Reservas Atuais", f"{reservas_atuais_total}")
col_meta[2].metric("Taxa de Conversão Geral", f"{taxa_conversao_geral * 100:.1f}%")
col_meta[3].metric("Potencial de Vendas", format_currency(potencial_vendas_valor))
col_meta[4].metric("Cobertura da Meta", f"{cobertura_percent:.1f}%")

st.caption(f"Meta referente a {mes_referencia_label} de {datetime.now().year}.")
st.markdown(f"**Cobertura da meta:** {cobertura_percent:.1f}%")

status_badge_html = f"""
<div style="margin-top:0.5rem;">
  <span style="display:inline-block;padding:0.45rem 1rem;border-radius:999px;background:{status_color};color:{status_text_color};font-weight:600;">Status: {status}</span>
</div>
"""

st.markdown(status_badge_html, unsafe_allow_html=True)

escala_max = 150
indicador_percentual = max(0.0, min(cobertura_percent, escala_max))
indicador_posicao = indicador_percentual / escala_max * 100

barra_escala_html = f"""
<div style='margin-top:0.75rem; position:relative;'>
  <div style='display:flex; overflow:hidden; border-radius:14px; height:52px; box-shadow:0 0 8px rgba(0,0,0,0.15);'>
    <div style='flex:70; background:#1E90FF; display:flex; flex-direction:column; align-items:center; justify-content:center; color:#ffffff; font-weight:600; font-size:0.9rem;'>
      Frio
      <span style="font-weight:400;font-size:0.75rem;">&lt; 70%</span>
    </div>
    <div style='flex:30; background:#f1c40f; display:flex; flex-direction:column; align-items:center; justify-content:center; color:#0b0b0b; font-weight:700; font-size:0.9rem;'>
      Morno
      <span style="font-weight:500;font-size:0.75rem;">70% – 100%</span>
    </div>
    <div style='flex:50; background:#27ae60; display:flex; flex-direction:column; align-items:center; justify-content:center; color:#ffffff; font-weight:600; font-size:0.9rem;'>
      Quente
      <span style="font-weight:400;font-size:0.75rem;">&gt; 100%</span>
    </div>
  </div>
  <div style='position:absolute; top:-18px; left:{indicador_posicao}%; transform:translateX(-50%); display:flex; flex-direction:column; align-items:center;'>
    <div style='width:0;height:0;border-left:10px solid transparent;border-right:10px solid transparent;border-bottom:12px solid {status_color};'></div>
    <div style='width:14px;height:14px;border-radius:50%;background:{status_color};border:3px solid #ffffff;box-shadow:0 0 6px rgba(0,0,0,0.3);'></div>
  </div>
</div>
"""

st.markdown(barra_escala_html, unsafe_allow_html=True)

st.markdown(
    f"**Interpretação:** {interpretacao}<br>**Ação Recomendada:** {acao}",
    unsafe_allow_html=True
)

# Página Home simplificada - apenas os quadros principais