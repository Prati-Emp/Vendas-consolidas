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
        # Tentar diferentes nomes de variáveis conforme padrão do projeto
        token = os.getenv('MOTHERDUCK_TOKEN') or os.getenv('Token_MD')
        
        if not token:
            raise ValueError(
                "Token do MotherDuck não encontrado. "
                "Configure MOTHERDUCK_TOKEN ou Token_MD no arquivo .env"
            )
        
        return token
    
    def connect(self):
        """Estabelece conexão com MotherDuck."""
        if not self.connection:
            try:
                connection_string = f"md:?motherduck_token={self.token}"
                self.connection = duckdb.connect(connection_string)
                st.success("✅ Conectado ao MotherDuck com sucesso!")
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
    Obtém dados da tabela planilhas.metas_vendas.
    
    Returns:
        DataFrame com dados de metas
    """
    md_conn = get_md_connection()
    
    sql = "SELECT * FROM planilhas.metas_vendas"
    
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
            codigo_empreendimento,
            empreendiemento as nome_empreendimento,
            "2025_01_01_00_00_00" as meta_janeiro_25, "2025_02_01_00_00_00" as meta_fevereiro_25, "2025_03_01_00_00_00" as meta_marco_25,
            "2025_04_01_00_00_00" as meta_abril_25, "2025_05_01_00_00_00" as meta_maio_25, "2025_06_01_00_00_00" as meta_junho_25,
            "2025_07_01_00_00_00" as meta_julho_25, "2025_08_01_00_00_00" as meta_agosto_25, "2025_09_01_00_00_00" as meta_setembro_25,
            "2025_10_01_00_00_00" as meta_outubro_25, "2025_11_01_00_00_00" as meta_novembro_25, "2025_12_01_00_00_00" as meta_dezembro_25,
            "2026_01_01_00_00_00" as meta_janeiro_26, "2026_02_01_00_00_00" as meta_fevereiro_26, "2026_03_01_00_00_00" as meta_marco_26,
            "2026_04_01_00_00_00" as meta_abril_26, "2026_05_01_00_00_00" as meta_maio_26, "2026_06_01_00_00_00" as meta_junho_26,
            "2026_07_01_00_00_00" as meta_julho_26, "2026_08_01_00_00_00" as meta_agosto_26, "2026_09_01_00_00_00" as meta_setembro_26,
            "2026_10_01_00_00_00" as meta_outubro_26, "2026_11_01_00_00_00" as meta_novembro_26, "2026_12_01_00_00_00" as meta_dezembro_26
        FROM planilhas.metas_vendas
    )
    SELECT 
        v.*,
        CASE 
            WHEN v.ano = 2025 AND v.mes = 1 THEN CAST(m.meta_janeiro_25 AS VARCHAR)
            WHEN v.ano = 2025 AND v.mes = 2 THEN CAST(m.meta_fevereiro_25 AS VARCHAR)
            WHEN v.ano = 2025 AND v.mes = 3 THEN CAST(m.meta_marco_25 AS VARCHAR)
            WHEN v.ano = 2025 AND v.mes = 4 THEN CAST(m.meta_abril_25 AS VARCHAR)
            WHEN v.ano = 2025 AND v.mes = 5 THEN CAST(m.meta_maio_25 AS VARCHAR)
            WHEN v.ano = 2025 AND v.mes = 6 THEN CAST(m.meta_junho_25 AS VARCHAR)
            WHEN v.ano = 2025 AND v.mes = 7 THEN CAST(m.meta_julho_25 AS VARCHAR)
            WHEN v.ano = 2025 AND v.mes = 8 THEN CAST(m.meta_agosto_25 AS VARCHAR)
            WHEN v.ano = 2025 AND v.mes = 9 THEN CAST(m.meta_setembro_25 AS VARCHAR)
            WHEN v.ano = 2025 AND v.mes = 10 THEN CAST(m.meta_outubro_25 AS VARCHAR)
            WHEN v.ano = 2025 AND v.mes = 11 THEN CAST(m.meta_novembro_25 AS VARCHAR)
            WHEN v.ano = 2025 AND v.mes = 12 THEN CAST(m.meta_dezembro_25 AS VARCHAR)
            WHEN v.ano = 2026 AND v.mes = 1 THEN CAST(m.meta_janeiro_26 AS VARCHAR)
            WHEN v.ano = 2026 AND v.mes = 2 THEN CAST(m.meta_fevereiro_26 AS VARCHAR)
            WHEN v.ano = 2026 AND v.mes = 3 THEN CAST(m.meta_marco_26 AS VARCHAR)
            WHEN v.ano = 2026 AND v.mes = 4 THEN CAST(m.meta_abril_26 AS VARCHAR)
            WHEN v.ano = 2026 AND v.mes = 5 THEN CAST(m.meta_maio_26 AS VARCHAR)
            WHEN v.ano = 2026 AND v.mes = 6 THEN CAST(m.meta_junho_26 AS VARCHAR)
            WHEN v.ano = 2026 AND v.mes = 7 THEN CAST(m.meta_julho_26 AS VARCHAR)
            WHEN v.ano = 2026 AND v.mes = 8 THEN CAST(m.meta_agosto_26 AS VARCHAR)
            WHEN v.ano = 2026 AND v.mes = 9 THEN CAST(m.meta_setembro_26 AS VARCHAR)
            WHEN v.ano = 2026 AND v.mes = 10 THEN CAST(m.meta_outubro_26 AS VARCHAR)
            WHEN v.ano = 2026 AND v.mes = 11 THEN CAST(m.meta_novembro_26 AS VARCHAR)
            WHEN v.ano = 2026 AND v.mes = 12 THEN CAST(m.meta_dezembro_26 AS VARCHAR)
            ELSE '0'
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
    Obtém meta total para o período selecionado (suporta 2025 e 2026).
    
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
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError:
        return 0.0
    
    # Definição das colunas de metas (2025 e 2026)
    cols_metas = """
        codigo_empreendimento,
        empreendiemento as nome_empreendimento,
        "2025_01_01_00_00_00" as meta_janeiro_25, "2025_02_01_00_00_00" as meta_fevereiro_25, "2025_03_01_00_00_00" as meta_marco_25,
        "2025_04_01_00_00_00" as meta_abril_25, "2025_05_01_00_00_00" as meta_maio_25, "2025_06_01_00_00_00" as meta_junho_25,
        "2025_07_01_00_00_00" as meta_julho_25, "2025_08_01_00_00_00" as meta_agosto_25, "2025_09_01_00_00_00" as meta_setembro_25,
        "2025_10_01_00_00_00" as meta_outubro_25, "2025_11_01_00_00_00" as meta_novembro_25, "2025_12_01_00_00_00" as meta_dezembro_25,
        "2026_01_01_00_00_00" as meta_janeiro_26, "2026_02_01_00_00_00" as meta_fevereiro_26, "2026_03_01_00_00_00" as meta_marco_26,
        "2026_04_01_00_00_00" as meta_abril_26, "2026_05_01_00_00_00" as meta_maio_26, "2026_06_01_00_00_00" as meta_junho_26,
        "2026_07_01_00_00_00" as meta_julho_26, "2026_08_01_00_00_00" as meta_agosto_26, "2026_09_01_00_00_00" as meta_setembro_26,
        "2026_10_01_00_00_00" as meta_outubro_26, "2026_11_01_00_00_00" as meta_novembro_26, "2026_12_01_00_00_00" as meta_dezembro_26
    """
    
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
            {cols_metas}
        FROM planilhas.metas_vendas
        WHERE codigo_empreendimento = '{enterprise_id}'
        """
    else:
        # Construir query para somar metas do período (todos os empreendimentos)
        sql = f"""
        SELECT 
            {cols_metas}
        FROM planilhas.metas_vendas
        """
    
    result = md_conn.run_query(sql)
    
    if len(result) == 0:
        return 0.0
    
    total_meta = 0.0
    
    mes_map = {
        1: 'janeiro', 2: 'fevereiro', 3: 'marco', 4: 'abril', 5: 'maio', 6: 'junho',
        7: 'julho', 8: 'agosto', 9: 'setembro', 10: 'outubro', 11: 'novembro', 12: 'dezembro'
    }
    
    for _, row in result.iterrows():
        # Iterar mês a mês do período selecionado
        current_year = start_dt.year
        current_month = start_dt.month
        
        while (current_year < end_dt.year) or (current_year == end_dt.year and current_month <= end_dt.month):
            if current_year in [2025, 2026]:
                col_name = f"meta_{mes_map[current_month]}_{str(current_year)[-2:]}"
                if col_name in row:
                    meta_valor = row[col_name]
                    if pd.notna(meta_valor) and meta_valor != 0:
                        # Tratar formato brasileiro (vírgula como separador decimal) e converter string
                        if isinstance(meta_valor, str):
                            meta_valor = meta_valor.replace(',', '.')
                            # Remover caracteres não numéricos se necessário, mas replace deve bastar
                            try:
                                total_meta += float(meta_valor)
                            except ValueError:
                                pass # Ignorar valores inválidos
                        else:
                            total_meta += float(meta_valor)
            
            # Avançar para o próximo mês
            if current_month == 12:
                current_month = 1
                current_year += 1
            else:
                current_month += 1
    
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
