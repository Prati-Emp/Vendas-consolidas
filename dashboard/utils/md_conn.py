"""
Utilitário de conexão com MotherDuck para o dashboard de vendas consolidadas.
Baseado nos padrões do projeto Vendas_Consolidadas.
"""

import os
import duckdb
import pandas as pd
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
import streamlit as st

# Carregar variáveis de ambiente
import os
from pathlib import Path

# Obter o diretório do arquivo atual
current_dir = Path(__file__).parent.parent
env_path = current_dir / '.env'

# Carregar .env do diretório correto
load_dotenv(env_path)

# Fallback: definir token diretamente se não foi carregado do .env
if not os.getenv('MOTHERDUCK_TOKEN') and not os.getenv('Token_MD'):
    # Token do MotherDuck (fallback direto) - REMOVIDO POR SEGURANÇA
    # Configure MOTHERDUCK_TOKEN no arquivo .env ou secrets.toml
    pass

class MotherDuckConnection:
    """Classe para gerenciar conexões com MotherDuck."""
    
    def __init__(self):
        self.token = self._get_token()
        self.connection = None
    
    def _get_token(self) -> str:
        """Obtém o token do MotherDuck das variáveis de ambiente."""
        # Primeiro tenta st.secrets (Streamlit Cloud)
        try:
            if hasattr(st, 'secrets') and 'MOTHERDUCK_TOKEN' in st.secrets:
                return st.secrets['MOTHERDUCK_TOKEN']
        except:
            pass
        
        # Tentar diferentes nomes de variáveis conforme padrão do projeto
        token = os.getenv('MOTHERDUCK_TOKEN') or os.getenv('Token_MD')
        
        # Para teste local, usar token temporário se não encontrado
        if not token:
            st.warning("⚠️ Token do MotherDuck não encontrado. Usando modo de teste local.")
            return "test_token_local"
        
        return token
    
    def connect(self):
        """Estabelece conexão com MotherDuck."""
        if not self.connection:
            try:
                # Se for token de teste, usar DuckDB local
                if self.token == "test_token_local":
                    st.info("🔧 Modo de teste local - usando DuckDB local")
                    self.connection = duckdb.connect()
                    return
                
                connection_string = f"md:?motherduck_token={self.token}"
                self.connection = duckdb.connect(connection_string)
            except Exception as e:
                st.error(f"❌ Erro ao conectar com MotherDuck: {str(e)}")
                raise
    
    def disconnect(self):
        """Fecha a conexão com MotherDuck."""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    @st.cache_data(ttl=300)  # Cache por 5 minutos
    def run_query(_self, sql: str, params: Optional[List] = None) -> pd.DataFrame:
        """
        Executa uma consulta SQL e retorna um DataFrame.
        
        Args:
            sql: Query SQL
            params: Parâmetros para a query (opcional)
            
        Returns:
            DataFrame com os resultados
        """
        # Se for modo de teste, retornar DataFrame vazio
        if _self.token == "test_token_local":
            st.info("🔧 Modo de teste - retornando dados simulados")
            return pd.DataFrame()
        
        if not _self.connection:
            _self.connect()
        
        try:
            if params:
                return _self.connection.execute(sql, params).df()
            else:
                return _self.connection.execute(sql).df()
        except Exception as e:
            st.error(f"❌ Erro na consulta SQL: {str(e)}")
            st.error(f"SQL: {sql}")
            if params:
                st.error(f"Parâmetros: {params}")
            raise

# Instância global da conexão
@st.cache_resource
def get_md_connection():
    """Retorna uma instância singleton da conexão MotherDuck."""
    return MotherDuckConnection()

def build_date_filter(start_date: str, end_date: str) -> str:
    """
    Constrói filtro de data para consultas SQL.
    
    Args:
        start_date: Data inicial (YYYY-MM-DD)
        end_date: Data final (YYYY-MM-DD)
        
    Returns:
        String com filtro SQL
    """
    return f"contractDate BETWEEN '{start_date}' AND '{end_date}'"

def build_optional_filters(midia: Optional[List[str]] = None, 
                          tipovenda: Optional[List[str]] = None,
                          empreendimento: Optional[str] = None,
                          corretor: Optional[List[str]] = None,
                          imobiliaria: Optional[List[str]] = None) -> tuple:
    """
    Constrói filtros opcionais para midia, tipovenda, empreendimento, corretor e imobiliaria.
    
    Args:
        midia: Lista de mídias para filtrar
        tipovenda: Lista de tipos de venda para filtrar
        empreendimento: Nome do empreendimento para filtrar
        corretor: Lista de corretores para filtrar
        imobiliaria: Lista de imobiliárias para filtrar
        
    Returns:
        Tuple com (filtro_sql, parametros)
    """
    filters = []
    params = []
    
    if midia and len(midia) > 0:
        placeholders = ','.join(['?' for _ in midia])
        filters.append(f"midia IN ({placeholders})")
        params.extend(midia)
    
    if tipovenda and len(tipovenda) > 0:
        placeholders = ','.join(['?' for _ in tipovenda])
        filters.append(f"tipovenda IN ({placeholders})")
        params.extend(tipovenda)
    
    if empreendimento and empreendimento != "Todos":
        filters.append("nome_empreendimento = ?")
        params.append(empreendimento)
    
    if corretor and len(corretor) > 0:
        placeholders = ','.join(['?' for _ in corretor])
        filters.append(f"COALESCE(NULLIF(TRIM(corretor), ''), '—') IN ({placeholders})")
        params.extend(corretor)
    
    if imobiliaria and len(imobiliaria) > 0:
        placeholders = ','.join(['?' for _ in imobiliaria])
        filters.append(f"COALESCE(NULLIF(TRIM(imobiliaria), ''), '—') IN ({placeholders})")
        params.extend(imobiliaria)
    
    filter_sql = " AND ".join(filters) if filters else ""
    return filter_sql, params

def get_base_data(start_date: str, end_date: str, 
                 midia: Optional[List[str]] = None,
                 tipovenda: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Obtém dados base da tabela sienge_vendas_consolidadas com filtros aplicados.
    
    Args:
        start_date: Data inicial
        end_date: Data final
        midia: Lista de mídias (opcional)
        tipovenda: Lista de tipos de venda (opcional)
        
    Returns:
        DataFrame com dados filtrados
    """
    md_conn = get_md_connection()
    
    # Construir filtros
    date_filter = build_date_filter(start_date, end_date)
    optional_filter, params = build_optional_filters(midia, tipovenda)
    
    # SQL base
    sql = f"""
    WITH base AS (
        SELECT
            enterpriseId,
            nome_empreendimento,
            COALESCE(NULLIF(TRIM(imobiliaria), ''), '—') AS imobiliaria,
            COALESCE(NULLIF(TRIM(corretor), ''), '—') AS corretor,
            COALESCE(NULLIF(TRIM(bloco), ''), '—') AS bloco,
            COALESCE(NULLIF(TRIM(unidade), ''), '—') AS unidade,
            midia,
            tipovenda,
            contractDate::DATE AS contractDate,
            value::DOUBLE AS value,
            origem
        FROM informacoes_consolidadas.sienge_vendas_consolidadas
        WHERE value IS NOT NULL
          AND {date_filter}
    """
    
    # Adicionar filtros opcionais
    if optional_filter:
        sql += f" AND {optional_filter}"
    
    sql += """
    )
    SELECT * FROM base
    ORDER BY contractDate DESC, nome_empreendimento
    """
    
    return md_conn.run_query(sql, params)

def get_metas_data() -> pd.DataFrame:
    """
    Obtém dados da tabela meta_vendas_2025.
    
    Returns:
        DataFrame com dados de metas
    """
    md_conn = get_md_connection()
    
    sql = """
    SELECT 
        "Empreendiemento" as nome_empreendimento,
        "Codigo empreendimento" as codigo_empreendimento,
        "jan/25" as meta_janeiro,
        "fev/25" as meta_fevereiro,
        "mar/25" as meta_marco,
        "abr/25" as meta_abril,
        "mai/25" as meta_maio,
        "jun/25" as meta_junho,
        "jul/25" as meta_julho,
        "ago/25" as meta_agosto,
        "set/25" as meta_setembro,
        "out/25" as meta_outubro,
        "nov/25" as meta_novembro,
        "dez/25" as meta_dezembro
    FROM informacoes_consolidadas.meta_vendas_2025
    """
    
    return md_conn.run_query(sql)

def get_vendas_with_metas(start_date: str, end_date: str,
                         midia: Optional[List[str]] = None,
                         tipovenda: Optional[List[str]] = None,
                         empreendimento: Optional[str] = None,
                         corretor: Optional[List[str]] = None,
                         imobiliaria: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Obtém vendas com metas correspondentes.
    
    Args:
        start_date: Data inicial
        end_date: Data final
        midia: Lista de mídias (opcional)
        tipovenda: Lista de tipos de venda (opcional)
        empreendimento: Nome do empreendimento (opcional)
        corretor: Lista de corretores (opcional)
        imobiliaria: Lista de imobiliárias (opcional)
        
    Returns:
        DataFrame com vendas e metas
    """
    md_conn = get_md_connection()
    
    # Construir filtros
    date_filter = build_date_filter(start_date, end_date)
    optional_filter, params = build_optional_filters(midia, tipovenda, empreendimento, corretor, imobiliaria)
    
    sql = f"""
    WITH vendas AS (
        SELECT
            enterpriseId,
            nome_empreendimento,
            COALESCE(NULLIF(TRIM(imobiliaria), ''), '—') AS imobiliaria,
            COALESCE(NULLIF(TRIM(corretor), ''), '—') AS corretor,
            midia,
            tipovenda,
            contractDate::DATE AS contractDate,
            value::DOUBLE AS value,
            EXTRACT(YEAR FROM contractDate) as ano,
            EXTRACT(MONTH FROM contractDate) as mes
        FROM informacoes_consolidadas.sienge_vendas_consolidadas
        WHERE value IS NOT NULL
          AND {date_filter}
    """
    
    if optional_filter:
        sql += f" AND {optional_filter}"
    
    sql += """
    ),
    metas AS (
        SELECT 
            "Codigo empreendimento" as codigo_empreendimento,
            "Empreendiemento" as nome_empreendimento,
            "jan/25" as meta_janeiro,
            "fev/25" as meta_fevereiro,
            "mar/25" as meta_marco,
            "abr/25" as meta_abril,
            "mai/25" as meta_maio,
            "jun/25" as meta_junho,
            "jul/25" as meta_julho,
            "ago/25" as meta_agosto,
            "set/25" as meta_setembro,
            "out/25" as meta_outubro,
            "nov/25" as meta_novembro,
            "dez/25" as meta_dezembro
        FROM informacoes_consolidadas.meta_vendas_2025
    )
    SELECT 
        v.*,
        CASE v.mes
            WHEN 1 THEN CAST(m.meta_janeiro AS VARCHAR)
            WHEN 2 THEN CAST(m.meta_fevereiro AS VARCHAR)
            WHEN 3 THEN CAST(m.meta_marco AS VARCHAR)
            WHEN 4 THEN CAST(m.meta_abril AS VARCHAR)
            WHEN 5 THEN CAST(m.meta_maio AS VARCHAR)
            WHEN 6 THEN CAST(m.meta_junho AS VARCHAR)
            WHEN 7 THEN CAST(m.meta_julho AS VARCHAR)
            WHEN 8 THEN CAST(m.meta_agosto AS VARCHAR)
            WHEN 9 THEN CAST(m.meta_setembro AS VARCHAR)
            WHEN 10 THEN CAST(m.meta_outubro AS VARCHAR)
            WHEN 11 THEN CAST(m.meta_novembro AS VARCHAR)
            WHEN 12 THEN CAST(m.meta_dezembro AS VARCHAR)
        END as meta_mes
    FROM vendas v
    LEFT JOIN metas m ON v.enterpriseId = m.codigo_empreendimento
    ORDER BY v.contractDate DESC, v.nome_empreendimento
    """
    
    return md_conn.run_query(sql, params)

def get_timeline_data(start_date: str, end_date: str,
                     midia: Optional[List[str]] = None,
                     tipovenda: Optional[List[str]] = None,
                     empreendimento: Optional[str] = None,
                     corretor: Optional[List[str]] = None,
                     imobiliaria: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Obtém dados para timeline mensal.
    
    Args:
        start_date: Data inicial
        end_date: Data final
        midia: Lista de mídias (opcional)
        tipovenda: Lista de tipos de venda (opcional)
        empreendimento: Nome do empreendimento (opcional)
        
    Returns:
        DataFrame com dados mensais agregados
    """
    md_conn = get_md_connection()
    
    # Construir filtros
    date_filter = build_date_filter(start_date, end_date)
    optional_filter, params = build_optional_filters(midia, tipovenda, empreendimento, corretor, imobiliaria)
    
    sql = f"""
    WITH base AS (
        SELECT
            contractDate::DATE AS contractDate,
            value::DOUBLE AS value
        FROM informacoes_consolidadas.sienge_vendas_consolidadas
        WHERE value IS NOT NULL
          AND {date_filter}
    """
    
    if optional_filter:
        sql += f" AND {optional_filter}"
    
    sql += """
    )
    SELECT 
        date_trunc('month', contractDate)::DATE AS mes,
        COUNT(*) AS qtd_vendas,
        SUM(value) AS total_valor,
        AVG(value) AS ticket_medio
    FROM base
    GROUP BY date_trunc('month', contractDate)
    ORDER BY mes
    """
    
    return md_conn.run_query(sql, params)

def get_kpis(start_date: str, end_date: str,
            midia: Optional[List[str]] = None,
            tipovenda: Optional[List[str]] = None,
            empreendimento: Optional[str] = None,
            corretor: Optional[List[str]] = None,
            imobiliaria: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Obtém KPIs principais.
    
    Args:
        start_date: Data inicial
        end_date: Data final
        midia: Lista de mídias (opcional)
        tipovenda: Lista de tipos de venda (opcional)
        empreendimento: Nome do empreendimento (opcional)
        corretor: Lista de corretores (opcional)
        imobiliaria: Lista de imobiliárias (opcional)
        
    Returns:
        Dicionário com KPIs
    """
    md_conn = get_md_connection()
    
    # Construir filtros
    date_filter = build_date_filter(start_date, end_date)
    optional_filter, params = build_optional_filters(midia, tipovenda, empreendimento, corretor, imobiliaria)
    
    sql = f"""
    WITH base AS (
        SELECT
            value::DOUBLE AS value
        FROM informacoes_consolidadas.sienge_vendas_consolidadas
        WHERE value IS NOT NULL
          AND {date_filter}
    """
    
    if optional_filter:
        sql += f" AND {optional_filter}"
    
    sql += """
    )
    SELECT 
        COUNT(*) AS total_vendas,
        SUM(value) AS total_valor,
        AVG(value) AS ticket_medio,
        MIN(value) AS menor_venda,
        MAX(value) AS maior_venda
    FROM base
    """
    
    result = md_conn.run_query(sql, params)
    
    if len(result) > 0:
        return {
            'total_vendas': int(result.iloc[0]['total_vendas']),
            'total_valor': float(result.iloc[0]['total_valor']),
            'ticket_medio': float(result.iloc[0]['ticket_medio']),
            'menor_venda': float(result.iloc[0]['menor_venda']),
            'maior_venda': float(result.iloc[0]['maior_venda'])
        }
    else:
        return {
            'total_vendas': 0,
            'total_valor': 0.0,
            'ticket_medio': 0.0,
            'menor_venda': 0.0,
            'maior_venda': 0.0
        }

def get_metas_periodo(start_date: str, end_date: str, 
                     empreendimento: Optional[str] = None) -> float:
    """
    Obtém meta total para o período selecionado.
    
    Args:
        start_date: Data inicial
        end_date: Data final
        empreendimento: Nome do empreendimento (opcional)
        
    Returns:
        Valor total da meta
    """
    md_conn = get_md_connection()
    
    # Converter datas para ano/mês
    from datetime import datetime
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    
    # Se empreendimento específico foi selecionado, precisamos buscar o enterpriseId correspondente
    if empreendimento and empreendimento != "Todos":
        # Buscar o enterpriseId do empreendimento selecionado
        sql_emp = """
        SELECT DISTINCT enterpriseId 
        FROM informacoes_consolidadas.sienge_vendas_consolidadas 
        WHERE nome_empreendimento = ?
        LIMIT 1
        """
        emp_result = md_conn.run_query(sql_emp, [empreendimento])
        
        if len(emp_result) == 0:
            return 0.0
        
        enterprise_id = emp_result.iloc[0]['enterpriseId']
        
        # Construir query para somar metas do período com filtro por enterpriseId
        sql = f"""
        SELECT 
            "Codigo empreendimento" as codigo_empreendimento,
            "Empreendiemento" as nome_empreendimento,
            "jan/25" as meta_janeiro,
            "fev/25" as meta_fevereiro,
            "mar/25" as meta_marco,
            "abr/25" as meta_abril,
            "mai/25" as meta_maio,
            "jun/25" as meta_junho,
            "jul/25" as meta_julho,
            "ago/25" as meta_agosto,
            "set/25" as meta_setembro,
            "out/25" as meta_outubro,
            "nov/25" as meta_novembro,
            "dez/25" as meta_dezembro
        FROM informacoes_consolidadas.meta_vendas_2025
        WHERE "Codigo empreendimento" = '{enterprise_id}'
        """
    else:
        # Construir query para somar metas do período (todos os empreendimentos)
        sql = """
        SELECT 
            "Codigo empreendimento" as codigo_empreendimento,
            "Empreendiemento" as nome_empreendimento,
            "jan/25" as meta_janeiro,
            "fev/25" as meta_fevereiro,
            "mar/25" as meta_marco,
            "abr/25" as meta_abril,
            "mai/25" as meta_maio,
            "jun/25" as meta_junho,
            "jul/25" as meta_julho,
            "ago/25" as meta_agosto,
            "set/25" as meta_setembro,
            "out/25" as meta_outubro,
            "nov/25" as meta_novembro,
            "dez/25" as meta_dezembro
        FROM informacoes_consolidadas.meta_vendas_2025
        """
    
    result = md_conn.run_query(sql)
    
    if len(result) == 0:
        return 0.0
    
    total_meta = 0.0
    
    for _, row in result.iterrows():
        # Somar metas dos meses no período
        for mes in range(1, 13):
            if start_dt.month <= mes <= end_dt.month and start_dt.year <= 2025 <= end_dt.year:
                col_name = f"meta_{['janeiro', 'fevereiro', 'marco', 'abril', 'maio', 'junho', 
                                  'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'][mes-1]}"
                meta_valor = row[col_name]
                if pd.notna(meta_valor) and meta_valor != 0:
                    # Tratar formato brasileiro (vírgula como separador decimal)
                    if isinstance(meta_valor, str):
                        meta_valor = meta_valor.replace(',', '.')
                    total_meta += float(meta_valor)
    
    return total_meta

def get_top_empreendimentos(start_date: str, end_date: str,
                           midia: Optional[List[str]] = None,
                           tipovenda: Optional[List[str]] = None,
                           empreendimento: Optional[str] = None,
                           corretor: Optional[List[str]] = None,
                           imobiliaria: Optional[List[str]] = None,
                           limit: int = 10) -> pd.DataFrame:
    """
    Obtém top empreendimentos por valor e quantidade.
    
    Args:
        start_date: Data inicial
        end_date: Data final
        midia: Lista de mídias (opcional)
        tipovenda: Lista de tipos de venda (opcional)
        empreendimento: Nome do empreendimento (opcional)
        limit: Limite de resultados
        
    Returns:
        DataFrame com top empreendimentos
    """
    md_conn = get_md_connection()
    
    # Construir filtros
    date_filter = build_date_filter(start_date, end_date)
    optional_filter, params = build_optional_filters(midia, tipovenda, empreendimento, corretor, imobiliaria)
    
    sql = f"""
    WITH base AS (
        SELECT
            nome_empreendimento,
            value::DOUBLE AS value
        FROM informacoes_consolidadas.sienge_vendas_consolidadas
        WHERE value IS NOT NULL
          AND {date_filter}
    """
    
    if optional_filter:
        sql += f" AND {optional_filter}"
    
    sql += f"""
    )
    SELECT 
        nome_empreendimento,
        COUNT(*) AS qtd_vendas,
        SUM(value) AS total_valor,
        AVG(value) AS ticket_medio
    FROM base
    GROUP BY nome_empreendimento
    ORDER BY total_valor DESC
    LIMIT {limit}
    """
    
    return md_conn.run_query(sql, params)

def get_analytics_by_dimension(start_date: str, end_date: str,
                              dimension: str,
                              midia: Optional[List[str]] = None,
                              tipovenda: Optional[List[str]] = None,
                              limit: int = 20) -> pd.DataFrame:
    """
    Obtém análises por dimensão específica (midia, tipovenda, imobiliaria, corretor).
    
    Args:
        start_date: Data inicial
        end_date: Data final
        dimension: Dimensão para análise
        midia: Lista de mídias (opcional)
        tipovenda: Lista de tipos de venda (opcional)
        limit: Limite de resultados
        
    Returns:
        DataFrame com análises por dimensão
    """
    md_conn = get_md_connection()
    
    # Construir filtros
    date_filter = build_date_filter(start_date, end_date)
    optional_filter, params = build_optional_filters(midia, tipovenda)
    
    # Validar dimensão
    valid_dimensions = ['midia', 'tipovenda', 'imobiliaria', 'corretor']
    if dimension not in valid_dimensions:
        raise ValueError(f"Dimensão inválida. Use uma das: {valid_dimensions}")
    
    # Tratar campos que podem ser nulos
    if dimension in ['imobiliaria', 'corretor']:
        dimension_field = f"COALESCE(NULLIF(TRIM({dimension}), ''), '—') AS {dimension}"
    else:
        dimension_field = dimension
    
    sql = f"""
    WITH base AS (
        SELECT
            {dimension_field},
            value::DOUBLE AS value
        FROM informacoes_consolidadas.sienge_vendas_consolidadas
        WHERE value IS NOT NULL
          AND {date_filter}
    """
    
    if optional_filter:
        sql += f" AND {optional_filter}"
    
    sql += f"""
    )
    SELECT 
        {dimension},
        COUNT(*) AS qtd_vendas,
        SUM(value) AS total_valor,
        AVG(value) AS ticket_medio
    FROM base
    GROUP BY {dimension}
    ORDER BY total_valor DESC
    LIMIT {limit}
    """
    
    return md_conn.run_query(sql, params)

def get_date_range() -> tuple:
    """
    Obtém o range de datas disponível na tabela.
    
    Returns:
        Tuple com (data_min, data_max)
    """
    md_conn = get_md_connection()
    
    sql = """
    SELECT 
        MIN(contractDate) AS data_min,
        MAX(contractDate) AS data_max
    FROM informacoes_consolidadas.sienge_vendas_consolidadas
    WHERE value IS NOT NULL
    """
    
    result = md_conn.run_query(sql)
    
    if len(result) > 0:
        return (
            result.iloc[0]['data_min'].strftime('%Y-%m-%d'),
            result.iloc[0]['data_max'].strftime('%Y-%m-%d')
        )
    else:
        # Fallback para datas padrão
        return ('2024-01-01', '2025-12-31')

def get_unique_values(column: str) -> List[str]:
    """
    Obtém valores únicos de uma coluna para filtros.
    
    Args:
        column: Nome da coluna
        
    Returns:
        Lista de valores únicos
    """
    md_conn = get_md_connection()
    
    # Tratar campos que podem ser nulos
    if column in ['imobiliaria', 'corretor']:
        column_field = f"COALESCE(NULLIF(TRIM({column}), ''), '—')"
    else:
        column_field = column
    
    sql = f"""
    SELECT DISTINCT {column_field} AS value
    FROM informacoes_consolidadas.sienge_vendas_consolidadas
    WHERE value IS NOT NULL
      AND {column_field} IS NOT NULL
    ORDER BY value
    """
    
    result = md_conn.run_query(sql)
    return result['value'].tolist()

def get_analytics_corretor(start_date: str, end_date: str,
                          midia: Optional[List[str]] = None,
                          tipovenda: Optional[List[str]] = None,
                          empreendimento: Optional[str] = None,
                          corretor: Optional[List[str]] = None,
                          imobiliaria: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Obtém análise por corretor.
    
    Args:
        start_date: Data inicial
        end_date: Data final
        midia: Lista de mídias (opcional)
        tipovenda: Lista de tipos de venda (opcional)
        empreendimento: Nome do empreendimento (opcional)
        corretor: Lista de corretores (opcional)
        imobiliaria: Lista de imobiliárias (opcional)
        
    Returns:
        DataFrame com análise por corretor
    """
    md_conn = get_md_connection()
    
    # Construir filtros
    date_filter = build_date_filter(start_date, end_date)
    optional_filter, params = build_optional_filters(midia, tipovenda, empreendimento, corretor, imobiliaria)
    
    sql = f"""
    WITH base AS (
        SELECT 
            COALESCE(NULLIF(TRIM(corretor), ''), '—') AS corretor,
            COALESCE(NULLIF(TRIM(imobiliaria), ''), '—') AS imobiliaria,
            nome_empreendimento,
            value::DOUBLE AS value
        FROM informacoes_consolidadas.sienge_vendas_consolidadas
        WHERE value IS NOT NULL
          AND {date_filter}
    """
    
    if optional_filter:
        sql += f" AND {optional_filter}"
    
    sql += """
    ),
    imob_rank AS (
        SELECT
            corretor,
            imobiliaria,
            COUNT(*) AS qtd,
            ROW_NUMBER() OVER (PARTITION BY corretor ORDER BY COUNT(*) DESC) AS rn
        FROM base
        GROUP BY corretor, imobiliaria
    ),
    agg AS (
        SELECT
            corretor,
            COUNT(*) AS total_vendas,
            SUM(value) AS total_valor,
            AVG(value) AS ticket_medio,
            MIN(value) AS menor_venda,
            MAX(value) AS maior_venda,
            COUNT(DISTINCT nome_empreendimento) AS empreendimentos_unicos
        FROM base
        GROUP BY corretor
    )
    SELECT 
        a.corretor,
        COALESCE(ir.imobiliaria, '—') AS imobiliaria_principal,
        a.total_vendas,
        a.total_valor,
        a.ticket_medio,
        a.menor_venda,
        a.maior_venda,
        a.empreendimentos_unicos
    FROM agg a
    LEFT JOIN imob_rank ir
      ON ir.corretor = a.corretor AND ir.rn = 1
    ORDER BY a.total_valor DESC
    """
    
    return md_conn.run_query(sql, params)

def get_analytics_imobiliaria(start_date: str, end_date: str,
                             midia: Optional[List[str]] = None,
                             tipovenda: Optional[List[str]] = None,
                             empreendimento: Optional[str] = None,
                             corretor: Optional[List[str]] = None,
                             imobiliaria: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Obtém análise por imobiliária.
    
    Args:
        start_date: Data inicial
        end_date: Data final
        midia: Lista de mídias (opcional)
        tipovenda: Lista de tipos de venda (opcional)
        empreendimento: Nome do empreendimento (opcional)
        corretor: Lista de corretores (opcional)
        imobiliaria: Lista de imobiliárias (opcional)
        
    Returns:
        DataFrame com análise por imobiliária
    """
    md_conn = get_md_connection()
    
    # Construir filtros
    date_filter = build_date_filter(start_date, end_date)
    optional_filter, params = build_optional_filters(midia, tipovenda, empreendimento, corretor, imobiliaria)
    
    sql = f"""
    SELECT 
        COALESCE(NULLIF(TRIM(imobiliaria), ''), '—') AS imobiliaria,
        COUNT(*) AS total_vendas,
        SUM(value) AS total_valor,
        AVG(value) AS ticket_medio,
        MIN(value) AS menor_venda,
        MAX(value) AS maior_venda,
        COUNT(DISTINCT nome_empreendimento) AS empreendimentos_unicos,
        COUNT(DISTINCT COALESCE(NULLIF(TRIM(corretor), ''), '—')) AS corretores_unicos
    FROM informacoes_consolidadas.sienge_vendas_consolidadas
    WHERE value IS NOT NULL
      AND {date_filter}
    """
    
    if optional_filter:
        sql += f" AND {optional_filter}"
    
    sql += """
    GROUP BY COALESCE(NULLIF(TRIM(imobiliaria), ''), '—')
    ORDER BY total_valor DESC
    """
    
    return md_conn.run_query(sql, params)
