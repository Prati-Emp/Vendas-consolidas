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
import time

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
            secrets = getattr(st, "secrets", None)
            if secrets:
                # Verificar chaves diretas
                for key in ("MOTHERDUCK_TOKEN", "Token_MD", "motherduck_token"):
                    token = secrets.get(key)
                    if token:
                        return token

                # Verificar estrutura em connections
                connections = secrets.get("connections")
                if isinstance(connections, dict):
                    motherduck_conn = connections.get("motherduck") or connections.get("motherduck_token")
                    if isinstance(motherduck_conn, dict):
                        token = motherduck_conn.get("token") or motherduck_conn.get("MOTHERDUCK_TOKEN")
                        if token:
                            return token
        except Exception:
            pass
        
        # Tentar diferentes nomes de variáveis conforme padrão do projeto
        token = os.getenv('MOTHERDUCK_TOKEN') or os.getenv('Token_MD')
        
        if not token:
            raise ValueError(
                "Token do MotherDuck não encontrado. "
                "Configure MOTHERDUCK_TOKEN ou Token_MD no arquivo .env"
            )
        
        return token
    
    def connect(self, max_retries: int = 3, retry_delay: float = 2.0):
        """Estabelece conexão com MotherDuck com retry automático."""
        if not self.connection:
            connection_string = f"md:?motherduck_token={self.token}"
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    self.connection = duckdb.connect(connection_string)
                    return  # Sucesso
                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        # Aguardar antes de tentar novamente (backoff exponencial)
                        wait_time = retry_delay * (2 ** attempt)
                        time.sleep(wait_time)
                    else:
                        # Última tentativa falhou
                        error_msg = str(e)
                        if "UNAVAILABLE" in error_msg or "GET_WELCOME_PACK" in error_msg:
                            st.error(
                                "❌ **Erro de conexão com MotherDuck**\n\n"
                                "O serviço MotherDuck está temporariamente indisponível. "
                                "Isso pode ser causado por:\n"
                                "- Problemas temporários de rede\n"
                                "- Manutenção do serviço MotherDuck\n"
                                "- Sobrecarga do servidor\n\n"
                                "**Solução:** Tente recarregar a página em alguns instantes. "
                                "Se o problema persistir, verifique o status do MotherDuck ou entre em contato com o suporte."
                            )
                        else:
                            st.error(f"❌ Erro ao conectar com MotherDuck: {error_msg}")
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
            error_msg = str(e)
            # Se a conexão foi perdida, tentar reconectar uma vez
            if "connection" in error_msg.lower() or "closed" in error_msg.lower():
                try:
                    _self.connection = None  # Resetar conexão
                    _self.connect()
                    # Tentar novamente após reconectar
                    if params:
                        return _self.connection.execute(sql, params).df()
                    else:
                        return _self.connection.execute(sql).df()
                except Exception as retry_error:
                    st.error(f"❌ Erro na consulta SQL após tentativa de reconexão: {str(retry_error)}")
                    st.error(f"SQL: {sql}")
                    if params:
                        st.error(f"Parâmetros: {params}")
                    raise
            else:
                st.error(f"❌ Erro na consulta SQL: {error_msg}")
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
    Obtém dados da view meta_vendas (consolidada).
    
    Returns:
        DataFrame com dados de metas (2025 e 2026)
    """
    md_conn = get_md_connection()
    
    sql = """
    SELECT 
        "Empreendiemento" as nome_empreendimento,
        "Codigo empreendimento" as codigo_empreendimento,
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
        "dez/25",
        "jan/26",
        "fev/26",
        "mar/26",
        "abr/26",
        "mai/26",
        "jun/26",
        "jul/26",
        "ago/26",
        "set/26",
        "out/26",
        "nov/26",
        "dez/26"
    FROM informacoes_consolidadas.meta_vendas
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
            "jan/25" as meta_janeiro_25, "fev/25" as meta_fevereiro_25, "mar/25" as meta_marco_25,
            "abr/25" as meta_abril_25, "mai/25" as meta_maio_25, "jun/25" as meta_junho_25,
            "jul/25" as meta_julho_25, "ago/25" as meta_agosto_25, "set/25" as meta_setembro_25,
            "out/25" as meta_outubro_25, "nov/25" as meta_novembro_25, "dez/25" as meta_dezembro_25,
            "jan/26" as meta_janeiro_26, "fev/26" as meta_fevereiro_26, "mar/26" as meta_marco_26,
            "abr/26" as meta_abril_26, "mai/26" as meta_maio_26, "jun/26" as meta_junho_26,
            "jul/26" as meta_julho_26, "ago/26" as meta_agosto_26, "set/26" as meta_setembro_26,
            "out/26" as meta_outubro_26, "nov/26" as meta_novembro_26, "dez/26" as meta_dezembro_26
        FROM informacoes_consolidadas.meta_vendas
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


def get_vgv_prosoluto_resumo() -> pd.DataFrame:
    """
    Retorna uma tabela consolidada por empreendimento com:
    - VGV total, vendido e pendente (a partir de cv_vgv_empreendimentos)
    - Prosoluto antes e pós chaves (a partir da view prosoluto_antes_e_pos_chaves)
    - id e nome do empreendimento preenchidos a partir de dim_empreendimentos_dinamica quando vazios.

    Os valores de prosoluto e o nome do empreendimento são alinhados pela coluna nome_empreendimento
    da view administracao.prosoluto_antes_e_pos_chaves, para permitir comparação direta com a view.
    Observação: a classificação de "vendido" (VGV) é baseada na coluna unidades.situacao.
    """
    md_conn = get_md_connection()

    sql = """
    WITH vgv_base AS (
        SELECT
            id_empreendimento,
            nome_empreendimento,
            SUM(COALESCE("unidades.valor_total", 0)) AS vgv_total,
            SUM(
                CASE
                    WHEN LOWER(COALESCE("unidades.situacao", '')) IN (
                        'vendido', 'vendida', 'assinado', 'escriturado'
                    )
                    THEN COALESCE("unidades.valor_total", 0)
                    ELSE 0
                END
            ) AS vgv_vendido
        FROM reservas.cv_vgv_empreendimentos
        GROUP BY id_empreendimento, nome_empreendimento
    ),
    vgv AS (
        SELECT
            id_empreendimento,
            nome_empreendimento,
            vgv_total,
            vgv_vendido,
            vgv_total - vgv_vendido AS vgv_pendente
        FROM vgv_base
    ),
    prosoluto_pivot AS (
        SELECT
            id_empreendimento,
            nome_empreendimento,
            SUM(
                CASE WHEN periodo = 'antes_chaves' THEN COALESCE(valor_prosoluto, 0) ELSE 0 END
            ) AS prosoluto_antes,
            SUM(
                CASE WHEN periodo = 'pos_chaves' THEN COALESCE(valor_prosoluto, 0) ELSE 0 END
            ) AS prosoluto_pos,
            MAX(COALESCE(valor_venda_financiamento, 0)) AS valor_venda_financiamento
        FROM administracao.prosoluto_antes_e_pos_chaves
        GROUP BY id_empreendimento, nome_empreendimento
    ),
    base AS (
        SELECT
            p.id_empreendimento AS id_empreendimento,
            COALESCE(p.nome_empreendimento, v.nome_empreendimento) AS nome_empreendimento,
            v.vgv_total,
            v.vgv_vendido,
            v.vgv_pendente,
            p.prosoluto_antes,
            p.valor_venda_financiamento AS venda_fin_antes,
            CASE WHEN COALESCE(p.valor_venda_financiamento, 0) > 0
                 THEN p.prosoluto_antes / p.valor_venda_financiamento ELSE 0 END AS pct_prosoluto_antes,
            p.prosoluto_pos,
            p.valor_venda_financiamento AS venda_fin_pos,
            CASE WHEN COALESCE(p.valor_venda_financiamento, 0) > 0
                 THEN p.prosoluto_pos / p.valor_venda_financiamento ELSE 0 END AS pct_prosoluto_pos
        FROM prosoluto_pivot p
        FULL OUTER JOIN vgv v
            ON TRIM(COALESCE(p.nome_empreendimento, '')) = TRIM(COALESCE(v.nome_empreendimento, ''))
    ),
    dim AS (
        SELECT
            TRY_CAST(enterpriseId AS BIGINT) AS enterpriseId,
            nome_empreendimento
        FROM informacoes_consolidadas.dim_empreendimentos_dinamica
        WHERE enterpriseId IS NOT NULL
    ),
    dim_por_nome AS (
        SELECT
            TRIM(nome_empreendimento) AS nome_trim,
            MAX(enterpriseId) AS enterpriseId,
            MAX(nome_empreendimento) AS nome_empreendimento
        FROM dim
        GROUP BY TRIM(nome_empreendimento)
    )
    SELECT
        COALESCE(base.id_empreendimento, dim_nome.enterpriseId) AS id_empreendimento,
        COALESCE(
            NULLIF(TRIM(base.nome_empreendimento), ''),
            dim_id.nome_empreendimento,
            dim_nome.nome_empreendimento
        ) AS nome_empreendimento,
        base.vgv_total,
        base.vgv_vendido,
        base.vgv_pendente,
        base.prosoluto_antes,
        base.venda_fin_antes,
        base.pct_prosoluto_antes,
        base.prosoluto_pos,
        base.venda_fin_pos,
        base.pct_prosoluto_pos
    FROM base
    LEFT JOIN dim dim_id ON dim_id.enterpriseId = base.id_empreendimento
    LEFT JOIN dim_por_nome dim_nome
        ON dim_nome.nome_trim = TRIM(COALESCE(base.nome_empreendimento, ''))
        AND base.nome_empreendimento IS NOT NULL
        AND TRIM(base.nome_empreendimento) <> ''
    ORDER BY nome_empreendimento
    """

    return md_conn.run_query(sql)


def get_vgv_por_situacao() -> pd.DataFrame:
    """
    Retorna VGV por empreendimento e situação (unidades.situacao).
    Usado para tabela de VGV por situação na aba geral.
    """
    md_conn = get_md_connection()
    sql = """
    SELECT
        id_empreendimento,
        nome_empreendimento,
        COALESCE(NULLIF(TRIM("unidades.situacao"), ''), 'Não informado') AS situacao,
        SUM(COALESCE("unidades.valor_total", 0)) AS valor
    FROM reservas.cv_vgv_empreendimentos
    GROUP BY id_empreendimento, nome_empreendimento, COALESCE(NULLIF(TRIM("unidades.situacao"), ''), 'Não informado')
    ORDER BY nome_empreendimento, situacao
    """
    return md_conn.run_query(sql)


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
            "jan/25", "fev/25", "mar/25", "abr/25", "mai/25", "jun/25",
            "jul/25", "ago/25", "set/25", "out/25", "nov/25", "dez/25",
            "jan/26", "fev/26", "mar/26", "abr/26", "mai/26", "jun/26",
            "jul/26", "ago/26", "set/26", "out/26", "nov/26", "dez/26"
        FROM informacoes_consolidadas.meta_vendas
        WHERE "Codigo empreendimento" = '{enterprise_id}'
        """
    else:
        # Construir query para somar metas do período (todos os empreendimentos)
        sql = """
        SELECT 
            "Codigo empreendimento" as codigo_empreendimento,
            "Empreendiemento" as nome_empreendimento,
            "jan/25", "fev/25", "mar/25", "abr/25", "mai/25", "jun/25",
            "jul/25", "ago/25", "set/25", "out/25", "nov/25", "dez/25",
            "jan/26", "fev/26", "mar/26", "abr/26", "mai/26", "jun/26",
            "jul/26", "ago/26", "set/26", "out/26", "nov/26", "dez/26"
        FROM informacoes_consolidadas.meta_vendas
        """
    
    result = md_conn.run_query(sql)
    
    if len(result) == 0:
        return 0.0
    
    total_meta = 0.0
    meses_abreviacoes = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 
                         'jul', 'ago', 'set', 'out', 'nov', 'dez']
    
    # Gerar todas as datas no período
    from datetime import date
    current_date = start_dt.date()
    end_date = end_dt.date()
    
    while current_date <= end_date:
        ano = current_date.year
        mes = current_date.month
        
        # Só processar se for 2025 ou 2026
        if ano in [2025, 2026]:
            col_name = f"{meses_abreviacoes[mes-1]}/{ano % 100}"
            
            for _, row in result.iterrows():
                meta_valor = row[col_name]
                if pd.notna(meta_valor) and meta_valor != 0:
                    # Tratar formato brasileiro (vírgula como separador decimal)
                    if isinstance(meta_valor, str):
                        meta_valor = meta_valor.replace(',', '.')
                    try:
                        total_meta += float(meta_valor)
                    except (ValueError, TypeError):
                        pass
        
        # Avançar para o próximo mês
        if mes == 12:
            current_date = date(ano + 1, 1, 1)
        else:
            current_date = date(ano, mes + 1, 1)
    
    return total_meta

def get_metas_periodo_internas(start_date: str, end_date: str, 
                               empreendimento: Optional[str] = None) -> float:
    """
    Obtém meta total de vendas internas para o período selecionado.
    A partir de 2026, usa a tabela específica de metas internas.
    Até dez/2025, usa a meta geral (mesma lógica de get_metas_periodo).
    
    Args:
        start_date: Data inicial
        end_date: Data final
        empreendimento: Nome do empreendimento (opcional)
        
    Returns:
        Valor total da meta
    """
    md_conn = get_md_connection()
    
    # Converter datas para ano/mês
    from datetime import datetime, date
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    
    # Verificar se há datas em 2026 ou depois
    tem_2026_ou_depois = end_dt.year >= 2026
    tem_2025_ou_antes = start_dt.year <= 2025
    
    total_meta = 0.0
    meses_abreviacoes = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 
                         'jul', 'ago', 'set', 'out', 'nov', 'dez']
    
    # Se empreendimento específico foi selecionado, precisamos buscar o enterpriseId correspondente
    enterprise_id = None
    if empreendimento and empreendimento != "Todos":
        sql_emp = """
        SELECT DISTINCT enterpriseId 
        FROM informacoes_consolidadas.sienge_vendas_consolidadas 
        WHERE nome_empreendimento = ?
        LIMIT 1
        """
        emp_result = md_conn.run_query(sql_emp, [empreendimento])
        if len(emp_result) > 0:
            enterprise_id = emp_result.iloc[0]['enterpriseId']
    
    # Processar período de 2025 ou antes (usar meta geral)
    if tem_2025_ou_antes:
        # Limitar end_date para dez/2025 se necessário
        periodo_2025_end = min(end_dt.date(), date(2025, 12, 31))
        
        # Buscar da meta geral uma única vez
        if enterprise_id:
            sql = f"""
            SELECT "jan/25", "fev/25", "mar/25", "abr/25", "mai/25", "jun/25",
                   "jul/25", "ago/25", "set/25", "out/25", "nov/25", "dez/25"
            FROM informacoes_consolidadas.meta_vendas
            WHERE "Codigo empreendimento" = '{enterprise_id}'
            """
        else:
            sql = """
            SELECT "jan/25", "fev/25", "mar/25", "abr/25", "mai/25", "jun/25",
                   "jul/25", "ago/25", "set/25", "out/25", "nov/25", "dez/25"
            FROM informacoes_consolidadas.meta_vendas
            """
        
        result = md_conn.run_query(sql)
        
        # Processar meses de 2025 no período
        current_date = start_dt.date()
        while current_date <= periodo_2025_end and current_date.year <= 2025:
            ano = current_date.year
            mes = current_date.month
            
            if ano == 2025:
                col_name = f"{meses_abreviacoes[mes-1]}/25"
                
                for _, row in result.iterrows():
                    if col_name in row.index:
                        meta_valor = row[col_name]
                        if pd.notna(meta_valor) and meta_valor != 0:
                            if isinstance(meta_valor, str):
                                meta_valor = meta_valor.replace(',', '.')
                            try:
                                # Aplicar ratio de 30% para vendas internas em 2025
                                total_meta += float(meta_valor) * 0.3
                            except (ValueError, TypeError):
                                pass
            
            # Avançar para o próximo mês
            if mes == 12:
                current_date = date(ano + 1, 1, 1)
            else:
                current_date = date(ano, mes + 1, 1)
    
    # Processar período de 2026 ou depois (usar meta específica de vendas internas)
    if tem_2026_ou_depois:
        # Limitar start_date para jan/2026 se necessário
        periodo_2026_start = max(start_dt.date(), date(2026, 1, 1))
        end_date_obj = end_dt.date()
        
        # Determinar quais anos precisamos buscar (2026, 2027, etc.)
        anos_necessarios = set()
        current_date = periodo_2026_start
        while current_date <= end_date_obj:
            if current_date.year >= 2026:
                anos_necessarios.add(current_date.year)
            if current_date.month == 12:
                current_date = date(current_date.year + 1, 1, 1)
            else:
                current_date = date(current_date.year, current_date.month + 1, 1)
        
        # Buscar dados para cada ano necessário
        for ano in sorted(anos_necessarios):
            ano_curto = ano % 100
            colunas_ano = [f'"{mes}/{ano_curto}"' for mes in meses_abreviacoes]
            colunas_str = ', '.join(colunas_ano)
            
            # Buscar da meta específica de vendas internas
            if enterprise_id:
                sql = f"""
                SELECT {colunas_str}
                FROM informacoes_consolidadas.metas_vendas_internas
                WHERE "Codigo empreendimento" = '{enterprise_id}'
                """
            else:
                sql = f"""
                SELECT {colunas_str}
                FROM informacoes_consolidadas.metas_vendas_internas
                """
            
            result = md_conn.run_query(sql)
            
            # Processar meses do ano no período
            current_date = max(periodo_2026_start, date(ano, 1, 1))
            ano_end = min(end_date_obj, date(ano, 12, 31))
            
            while current_date <= ano_end and current_date.year == ano:
                mes = current_date.month
                col_name = f"{meses_abreviacoes[mes-1]}/{ano_curto}"
                
                for _, row in result.iterrows():
                    if col_name in row.index:
                        meta_valor = row[col_name]
                        if pd.notna(meta_valor) and meta_valor != 0:
                            if isinstance(meta_valor, str):
                                meta_valor = meta_valor.replace(',', '.')
                            try:
                                total_meta += float(meta_valor)
                            except (ValueError, TypeError):
                                pass
                
                # Avançar para o próximo mês
                if mes == 12:
                    current_date = date(ano + 1, 1, 1)
                else:
                    current_date = date(ano, mes + 1, 1)
    
    return total_meta

def get_metas_periodo_externas(start_date: str, end_date: str, 
                               empreendimento: Optional[str] = None) -> float:
    """
    Obtém meta total de vendas externas para o período selecionado.
    A partir de 2026, usa a tabela específica de metas externas.
    Até dez/2025, usa a meta geral (mesma lógica de get_metas_periodo).
    
    Args:
        start_date: Data inicial
        end_date: Data final
        empreendimento: Nome do empreendimento (opcional)
        
    Returns:
        Valor total da meta
    """
    md_conn = get_md_connection()
    
    # Converter datas para ano/mês
    from datetime import datetime, date
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    
    # Verificar se há datas em 2026 ou depois
    tem_2026_ou_depois = end_dt.year >= 2026
    tem_2025_ou_antes = start_dt.year <= 2025
    
    total_meta = 0.0
    meses_abreviacoes = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 
                         'jul', 'ago', 'set', 'out', 'nov', 'dez']
    
    # Se empreendimento específico foi selecionado, precisamos buscar o enterpriseId correspondente
    enterprise_id = None
    if empreendimento and empreendimento != "Todos":
        sql_emp = """
        SELECT DISTINCT enterpriseId 
        FROM informacoes_consolidadas.sienge_vendas_consolidadas 
        WHERE nome_empreendimento = ?
        LIMIT 1
        """
        emp_result = md_conn.run_query(sql_emp, [empreendimento])
        if len(emp_result) > 0:
            enterprise_id = emp_result.iloc[0]['enterpriseId']
    
    # Processar período de 2025 ou antes (usar meta geral)
    if tem_2025_ou_antes:
        # Limitar end_date para dez/2025 se necessário
        periodo_2025_end = min(end_dt.date(), date(2025, 12, 31))
        
        # Buscar da meta geral uma única vez
        if enterprise_id:
            sql = f"""
            SELECT "jan/25", "fev/25", "mar/25", "abr/25", "mai/25", "jun/25",
                   "jul/25", "ago/25", "set/25", "out/25", "nov/25", "dez/25"
            FROM informacoes_consolidadas.meta_vendas
            WHERE "Codigo empreendimento" = '{enterprise_id}'
            """
        else:
            sql = """
            SELECT "jan/25", "fev/25", "mar/25", "abr/25", "mai/25", "jun/25",
                   "jul/25", "ago/25", "set/25", "out/25", "nov/25", "dez/25"
            FROM informacoes_consolidadas.meta_vendas
            """
        
        result = md_conn.run_query(sql)
        
        # Processar meses de 2025 no período
        current_date = start_dt.date()
        while current_date <= periodo_2025_end and current_date.year <= 2025:
            ano = current_date.year
            mes = current_date.month
            
            if ano == 2025:
                col_name = f"{meses_abreviacoes[mes-1]}/25"
                
                for _, row in result.iterrows():
                    if col_name in row.index:
                        meta_valor = row[col_name]
                        if pd.notna(meta_valor) and meta_valor != 0:
                            if isinstance(meta_valor, str):
                                meta_valor = meta_valor.replace(',', '.')
                            try:
                                # Aplicar ratio de 70% para vendas externas em 2025
                                total_meta += float(meta_valor) * 0.7
                            except (ValueError, TypeError):
                                pass
            
            # Avançar para o próximo mês
            if mes == 12:
                current_date = date(ano + 1, 1, 1)
            else:
                current_date = date(ano, mes + 1, 1)
    
    # Processar período de 2026 ou depois (usar meta específica de vendas externas)
    if tem_2026_ou_depois:
        # Limitar start_date para jan/2026 se necessário
        periodo_2026_start = max(start_dt.date(), date(2026, 1, 1))
        end_date_obj = end_dt.date()
        
        # Determinar quais anos precisamos buscar (2026, 2027, etc.)
        anos_necessarios = set()
        current_date = periodo_2026_start
        while current_date <= end_date_obj:
            if current_date.year >= 2026:
                anos_necessarios.add(current_date.year)
            if current_date.month == 12:
                current_date = date(current_date.year + 1, 1, 1)
            else:
                current_date = date(current_date.year, current_date.month + 1, 1)
        
        # Buscar dados para cada ano necessário
        for ano in sorted(anos_necessarios):
            ano_curto = ano % 100
            colunas_ano = [f'"{mes}/{ano_curto}"' for mes in meses_abreviacoes]
            colunas_str = ', '.join(colunas_ano)
            
            # Buscar da meta específica de vendas externas
            if enterprise_id:
                sql = f"""
                SELECT {colunas_str}
                FROM informacoes_consolidadas.metas_vendas_externas
                WHERE "Codigo empreendimento" = '{enterprise_id}'
                """
            else:
                sql = f"""
                SELECT {colunas_str}
                FROM informacoes_consolidadas.metas_vendas_externas
                """
            
            result = md_conn.run_query(sql)
            
            # Processar meses do ano no período
            current_date = max(periodo_2026_start, date(ano, 1, 1))
            ano_end = min(end_date_obj, date(ano, 12, 31))
            
            while current_date <= ano_end and current_date.year == ano:
                mes = current_date.month
                col_name = f"{meses_abreviacoes[mes-1]}/{ano_curto}"
                
                for _, row in result.iterrows():
                    if col_name in row.index:
                        meta_valor = row[col_name]
                        if pd.notna(meta_valor) and meta_valor != 0:
                            if isinstance(meta_valor, str):
                                meta_valor = meta_valor.replace(',', '.')
                            try:
                                total_meta += float(meta_valor)
                            except (ValueError, TypeError):
                                pass
                
                # Avançar para o próximo mês
                if mes == 12:
                    current_date = date(ano + 1, 1, 1)
                else:
                    current_date = date(ano, mes + 1, 1)
    
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
