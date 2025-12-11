"""
Dashboard Compras - Monitoramento de compras e fornecedores.
"""

import streamlit as st
import pandas as pd
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, date
import plotly.express as px
import plotly.graph_objects as go

from dashboard.utils.md_conn import get_md_connection
import duckdb
import os
from dotenv import load_dotenv

load_dotenv()


@st.cache_data(ttl=300)
def load_pedidos_compras(
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    comprador: Optional[List[str]] = None,
    empreendimento: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Carrega dados de pedidos de compras do banco reservas.
    
    Args:
        data_inicio: Data inicial (YYYY-MM-DD)
        data_fim: Data final (YYYY-MM-DD)
        comprador: Lista de compradores para filtrar
        empreendimento: Lista de empreendimentos para filtrar
        
    Returns:
        DataFrame com dados de pedidos de compras
    """
    md_conn = get_md_connection()
    
    # Construir filtros
    filters = []
    params = []
    
    if data_inicio:
        filters.append("Data_Pedido >= ?")
        params.append(data_inicio)
    
    if data_fim:
        filters.append("Data_Pedido <= ?")
        params.append(data_fim)
    
    if comprador and len(comprador) > 0:
        placeholders = ','.join(['?' for _ in comprador])
        filters.append(f"Comprador IN ({placeholders})")
        params.extend(comprador)
    
    if empreendimento and len(empreendimento) > 0:
        ids = [e for e in empreendimento if str(e).isdigit()]
        nomes = [e for e in empreendimento if not str(e).isdigit()]

        conds = []
        if ids:
            placeholders = ','.join(['?' for _ in ids])
            conds.append(f"pc.ID_Empreendimento IN ({placeholders})")
            params.extend([int(e) if isinstance(e, str) and e.isdigit() else e for e in ids])
        if nomes:
            placeholders = ','.join(['?' for _ in nomes])
            conds.append(f"re.obra IN ({placeholders})")
            params.extend(nomes)

        if conds:
            filters.append("(" + " OR ".join(conds) + ")")
    
    filter_sql = " AND ".join(filters) if filters else "1=1"
    
    # Query para obter dados com nome do empreendimento
    sql = f"""
    SELECT 
        pc.ID_Pedido,
        pc.Status,
        pc.Atrasado,
        pc.ID_Fornecedor,
        pc.ID_Empreendimento,
        COALESCE(re.obra, CAST(pc.ID_Empreendimento AS VARCHAR)) AS Empreendimento,
        pc.Comprador,
        pc.Data_Pedido::DATE AS Data_Pedido,
        pc.Notas AS Titulo,
        COALESCE(pc.Desconto, 0) AS Desconto,
        COALESCE(pc.Acrescimos, 0) AS Acrescimos,
        COALESCE(pc.Valor_Total, 0) AS Valor_Total,
        COALESCE(pc.Total_Frete, 0) AS Total_Frete
    FROM reservas.main.sienge_pedidos_compras pc
    LEFT JOIN planilhas.main.relacao_empreendimentos_pedidos_de_compras re
        ON pc.ID_Empreendimento = CAST(re.codigo_da_obra AS INT)
    WHERE {filter_sql}
    ORDER BY pc.Data_Pedido DESC
    """
    
    try:
        df = md_conn.run_query(sql, params)
        
        # Converter Data_Pedido para datetime se necessário
        if 'Data_Pedido' in df.columns and not df.empty:
            df['Data_Pedido'] = pd.to_datetime(df['Data_Pedido'], errors='coerce')
        
        return df
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados: {str(e)}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_unique_compradores(data_inicio: Optional[str] = None, data_fim: Optional[str] = None) -> List[str]:
    """Obtém lista única de compradores, opcionalmente filtrada por data."""
    md_conn = get_md_connection()
    
    filters = ["Comprador IS NOT NULL"]
    params = []
    
    if data_inicio:
        filters.append("Data_Pedido >= ?")
        params.append(data_inicio)
        
    if data_fim:
        filters.append("Data_Pedido <= ?")
        params.append(data_fim)
    
    filter_sql = " AND ".join(filters)
    
    sql = f"""
    SELECT DISTINCT Comprador
    FROM reservas.main.sienge_pedidos_compras
    WHERE {filter_sql}
    ORDER BY Comprador
    """
    df = md_conn.run_query(sql, params)
    return df['Comprador'].tolist() if not df.empty else []


@st.cache_data(ttl=300)
def get_unique_empreendimentos() -> List[Dict[str, Any]]:
    """Obtém lista única de empreendimentos (nomes) a partir da view de mapeamento."""
    md_conn = get_md_connection()
    sql = """
    SELECT DISTINCT 
        re.obra AS Empreendimento
    FROM planilhas.main.relacao_empreendimentos_pedidos_de_compras re
    WHERE re.obra IS NOT NULL
    ORDER BY re.obra
    """
    df = md_conn.run_query(sql)
    if df.empty:
        return []
    return df['Empreendimento'].astype(str).tolist()


def calcular_indicadores(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calcula indicadores principais de compras.
    
    Args:
        df: DataFrame com dados de pedidos de compras
        
    Returns:
        Dicionário com indicadores calculados
    """
    if df.empty:
        return {
            'valor_descontos': 0.0,
            'valor_pedidos': 0.0,
            'percentual_desconto': 0.0,
            'total_pedidos': 0,
            'pedidos_atrasados': 0,
            'percentual_atrasados': 0.0,
            'valor_medio_pedido': 0.0,
            'pedidos_entregues': 0,
            'pedidos_parcialmente_entregues': 0,
            'percentual_entregues': 0.0,
            'percentual_parcialmente_entregues': 0.0,
            'pedidos_no_prazo': 0,
            'percentual_no_prazo': 0.0,
        }
    
    # Filtrar pedidos cancelados (se a coluna Status existir)
    if 'Status' in df.columns:
        df_sem_cancelados = df[df['Status'] != 'CANCELED'].copy()
    else:
        df_sem_cancelados = df.copy()
    
    # Calcular indicadores
    valor_descontos = float(df_sem_cancelados['Desconto'].sum()) if 'Desconto' in df_sem_cancelados.columns else 0.0
    valor_pedidos = float(df_sem_cancelados['Valor_Total'].sum()) if 'Valor_Total' in df_sem_cancelados.columns else 0.0
    
    # % desconto = (Valor_Descontos / Valor_Pedidos_Compra) * 100
    percentual_desconto = (valor_descontos / valor_pedidos * 100) if valor_pedidos > 0 else 0.0
    
    # Contar pedidos únicos (excluindo cancelados) se a coluna existir, senão contar linhas
    if 'ID_Pedido' in df_sem_cancelados.columns:
        total_pedidos = df_sem_cancelados['ID_Pedido'].nunique()
    elif 'n_do_pedido' in df_sem_cancelados.columns:
        total_pedidos = df_sem_cancelados['n_do_pedido'].nunique()
    else:
        total_pedidos = len(df_sem_cancelados)
    
    # Lógica mutuamente exclusiva para garantir que a soma bata com o total:
    # 1. Pedidos Atrasados: todos os atrasados (independente do status)
    # 2. Pedidos Totalmente Entregues: FULLY_DELIVERED e não atrasados
    # 3. Pedidos Parcialmente Entregues: PARTIALLY_DELIVERED e não atrasados
    # 4. Pedidos no Prazo: PENDING e não atrasados (pedidos pendentes no prazo)
    
    # Identificar coluna de ID do pedido
    id_col = 'ID_Pedido' if 'ID_Pedido' in df_sem_cancelados.columns else ('n_do_pedido' if 'n_do_pedido' in df_sem_cancelados.columns else None)
    
    # Função auxiliar para contar pedidos únicos
    def contar_pedidos_unicos(df_subset):
        if df_subset.empty:
            return 0
        if id_col and id_col in df_subset.columns:
            return df_subset[id_col].nunique()
        return len(df_subset)
    
    # Verificar se temos coluna Atrasado
    tem_atrasado = 'Atrasado' in df_sem_cancelados.columns
    tem_status = 'Status' in df_sem_cancelados.columns
    
    # Preparar filtros para Atrasado
    if tem_atrasado:
        if df_sem_cancelados['Atrasado'].dtype == bool:
            filtro_atrasado = df_sem_cancelados['Atrasado'] == True
            filtro_nao_atrasado = df_sem_cancelados['Atrasado'] == False
        else:
            filtro_atrasado = df_sem_cancelados['Atrasado'] == 1
            filtro_nao_atrasado = df_sem_cancelados['Atrasado'] == 0
    else:
        # Se não tiver coluna Atrasado, considerar todos como não atrasados
        filtro_atrasado = pd.Series([False] * len(df_sem_cancelados), index=df_sem_cancelados.index)
        filtro_nao_atrasado = pd.Series([True] * len(df_sem_cancelados), index=df_sem_cancelados.index)
    
    # 1. Pedidos Atrasados (todos os atrasados, independente do status)
    if tem_atrasado:
        pedidos_atrasados_df = df_sem_cancelados[filtro_atrasado]
        pedidos_atrasados = contar_pedidos_unicos(pedidos_atrasados_df)
    else:
        pedidos_atrasados = 0
    
    # 2. Pedidos Totalmente Entregues (FULLY_DELIVERED e não atrasados)
    if tem_status:
        pedidos_entregues_df = df_sem_cancelados[
            (df_sem_cancelados['Status'] == 'FULLY_DELIVERED') & filtro_nao_atrasado
        ]
        total_entregues = contar_pedidos_unicos(pedidos_entregues_df)
    else:
        total_entregues = 0
    
    # 3. Pedidos Parcialmente Entregues (PARTIALLY_DELIVERED e não atrasados)
    if tem_status:
        pedidos_parcialmente_df = df_sem_cancelados[
            (df_sem_cancelados['Status'] == 'PARTIALLY_DELIVERED') & filtro_nao_atrasado
        ]
        total_parcialmente = contar_pedidos_unicos(pedidos_parcialmente_df)
    else:
        total_parcialmente = 0
    
    # 4. Pedidos no Prazo (Pendentes - PENDING e não atrasados)
    # Status = PENDING e Atrasado = False
    if tem_status and tem_atrasado:
        pedidos_no_prazo_df = df_sem_cancelados[
            (df_sem_cancelados['Status'] == 'PENDING') & filtro_nao_atrasado
        ]
        pedidos_no_prazo = contar_pedidos_unicos(pedidos_no_prazo_df)
    elif tem_status:
        # Se não tiver coluna Atrasado, considerar apenas PENDING
        pedidos_no_prazo_df = df_sem_cancelados[df_sem_cancelados['Status'] == 'PENDING']
        pedidos_no_prazo = contar_pedidos_unicos(pedidos_no_prazo_df)
    elif tem_atrasado:
        # Se não tiver Status, considerar apenas não atrasados
        pedidos_no_prazo_df = df_sem_cancelados[filtro_nao_atrasado]
        pedidos_no_prazo = contar_pedidos_unicos(pedidos_no_prazo_df)
    else:
        # Se não tiver nenhum dos dois, não há como determinar
        pedidos_no_prazo = 0
    
    # Validação: A soma deve bater com o total de pedidos
    # Total = Pedidos Atrasados + Pedidos Totalmente Entregues + Pedidos Parcialmente Entregues + Pedidos no Prazo
    soma_categorias = pedidos_atrasados + total_entregues + total_parcialmente + pedidos_no_prazo
    
    # Se houver diferença (devido a pedidos com outros status ou inconsistências),
    # ajustar "Pedidos no Prazo" para garantir que a soma bata
    if soma_categorias != total_pedidos and total_pedidos > 0:
        # A diferença provavelmente são pedidos com status diferente de PENDING, FULLY_DELIVERED ou PARTIALLY_DELIVERED
        # Vamos adicionar essa diferença aos "Pedidos no Prazo" se não estiverem atrasados
        diferenca = total_pedidos - soma_categorias
        # Só adicionar se a diferença for positiva (pedidos não categorizados)
        if diferenca > 0:
            pedidos_no_prazo = pedidos_no_prazo + diferenca
    
    percentual_atrasados = (pedidos_atrasados / total_pedidos * 100) if total_pedidos > 0 else 0.0
    percentual_entregues = (total_entregues / total_pedidos * 100) if total_pedidos > 0 else 0.0
    percentual_parcialmente_entregues = (total_parcialmente / total_pedidos * 100) if total_pedidos > 0 else 0.0
    percentual_no_prazo = (pedidos_no_prazo / total_pedidos * 100) if total_pedidos > 0 else 0.0
    valor_medio_pedido = (valor_pedidos / total_pedidos) if total_pedidos > 0 else 0.0
    
    return {
        'valor_descontos': valor_descontos,
        'valor_pedidos': valor_pedidos,
        'percentual_desconto': percentual_desconto,
        'total_pedidos': total_pedidos,
        'pedidos_atrasados': pedidos_atrasados,
        'percentual_atrasados': percentual_atrasados,
        'valor_medio_pedido': valor_medio_pedido,
        'pedidos_entregues': total_entregues,
        'pedidos_parcialmente_entregues': total_parcialmente,
        'percentual_entregues': percentual_entregues,
        'percentual_parcialmente_entregues': percentual_parcialmente_entregues,
        'pedidos_no_prazo': pedidos_no_prazo,
        'percentual_no_prazo': percentual_no_prazo,
    }


def formatar_moeda(valor: float) -> str:
    """Formata valor como moeda brasileira com unidades (milhões, mil, etc.)."""
    if pd.isna(valor) or valor == 0:
        return "R$ 0,00"
    
    # Valores em milhões
    if abs(valor) >= 1_000_000:
        valor_formatado = valor / 1_000_000
        # Formatar com 2 casas decimais, usando vírgula como separador decimal
        return f"R$ {valor_formatado:,.2f}M".replace(",", "X").replace(".", ",").replace("X", ".")
    # Valores em mil
    elif abs(valor) >= 1_000:
        valor_formatado = valor / 1_000
        # Formatar com 2 casas decimais, usando vírgula como separador decimal
        return f"R$ {valor_formatado:,.2f} mil".replace(",", "X").replace(".", ",").replace("X", ".")
    # Valores menores que mil
    else:
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_percentual(valor: float) -> str:
    """Formata valor como percentual."""
    return f"{valor:.2f}%"


def get_md_connection_planilhas():
    """Conecta ao banco 'planilhas' do MotherDuck"""
    token = os.getenv('MOTHERDUCK_TOKEN') or os.getenv('Token_MD')
    
    if not token:
        raise ValueError("MOTHERDUCK_TOKEN não encontrado")
    
    duckdb.sql("INSTALL motherduck")
    duckdb.sql("LOAD motherduck")
    duckdb.sql(f"SET motherduck_token='{token}'")
    return duckdb.connect("md:planilhas")


@st.cache_data(ttl=3600, show_spinner=True)  # Cache por 1 hora (dados atualizados semanalmente)
def load_contas_pagas_pmp(
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
) -> pd.DataFrame:
    """
    Carrega dados de contas pagas para cálculo de PMP (Prazo Médio de Pagamento).
    
    Filtros aplicados:
    - tipo_de_baixa IN ('ADIANTAMENTO', 'PAGAMENTO')
    - parcela_autorizada = 'sim'
    
    Args:
        data_inicio: Data inicial (YYYY-MM-DD) - filtra por data_do_pagamento
        data_fim: Data final (YYYY-MM-DD) - filtra por data_do_pagamento
        
    Returns:
        DataFrame com dados de contas pagas
    """
    try:
        conn = get_md_connection_planilhas()
        
        # Construir filtros SQL
        filters = []
        params = []
        
        # Filtros permanentes conforme especificação
        filters.append("UPPER(tipo_de_baixa) IN ('ADIANTAMENTO', 'PAGAMENTO')")
        filters.append("UPPER(parcela_autorizada) = 'SIM'")
        
        # Filtros de data (se fornecidos)
        # As datas estão como VARCHAR no formato DD/MM/YYYY, então vamos filtrar no pandas
        # Mas podemos adicionar filtro SQL se necessário
        
        filter_sql = " AND ".join(filters) if filters else "1=1"
        
        # Query para obter dados
        sql = f"""
        SELECT 
            data_do_pagamento,
            data_emiss_o,
            valor_l_quido
        FROM planilhas.main.contas_pagas
        WHERE {filter_sql}
          AND data_do_pagamento IS NOT NULL
          AND data_emiss_o IS NOT NULL
          AND valor_l_quido IS NOT NULL
        """
        
        df = conn.execute(sql, params).df()
        conn.close()
        
        if df.empty:
            return pd.DataFrame()
        
        # Converter colunas de data (formato DD/MM/YYYY)
        df['data_do_pagamento'] = pd.to_datetime(df['data_do_pagamento'], dayfirst=True, errors='coerce')
        df['data_emiss_o'] = pd.to_datetime(df['data_emiss_o'], dayfirst=True, errors='coerce')
        
        # Remover linhas com datas inválidas
        df = df[df['data_do_pagamento'].notna() & df['data_emiss_o'].notna()].copy()
        
        # Aplicar filtros de data no pandas
        if data_inicio and not df.empty:
            dt_inicio = pd.to_datetime(data_inicio)
            df = df[df['data_do_pagamento'] >= dt_inicio]
            
        if data_fim and not df.empty:
            dt_fim = pd.to_datetime(data_fim)
            # Ajustar para final do dia
            dt_fim = dt_fim + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
            df = df[df['data_do_pagamento'] <= dt_fim]
        
        # Calcular PMP simples (dias entre pagamento e emissão)
        df['pmp_simples'] = (df['data_do_pagamento'] - df['data_emiss_o']).dt.days
        
        # Remover valores negativos ou muito grandes (possíveis erros de data)
        df = df[(df['pmp_simples'] >= 0) & (df['pmp_simples'] <= 365)].copy()
        
        return df.sort_values('data_do_pagamento', ascending=False)
        
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados de contas pagas: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return pd.DataFrame()


def calcular_pmp_ponderado_mensal(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula PMP Ponderado agrupado por mês.
    
    Fórmula conforme Power BI:
    - PMP simples = Data do pagamento - Data emissão
    - PMP Ponderado = SUMX(PMP simples * Valor líquido) / SUM(Valor líquido)
    
    IMPORTANTE: Agrupa por data_do_pagamento (data de pagamento), que é a referência principal.
    
    Args:
        df: DataFrame com dados de contas pagas (deve ter colunas: data_do_pagamento, pmp_simples, valor_l_quido)
        
    Returns:
        DataFrame com colunas: Mês, Meta (38 dias), Real (PMP Ponderado)
    """
    if df.empty or 'data_do_pagamento' not in df.columns:
        return pd.DataFrame(columns=['Mês', 'Meta', 'Real'])
    
    # Criar coluna de mês/ano baseada em data_do_pagamento (data de pagamento)
    # Esta é a coluna de referência conforme especificado
    df['mes_ano'] = df['data_do_pagamento'].dt.to_period('M')
    
    # Calcular PMP ponderado por mês
    resultados = []
    
    for mes_period in sorted(df['mes_ano'].unique()):
        df_mes = df[df['mes_ano'] == mes_period].copy()
        
        if df_mes.empty:
            continue
        
        # Calcular PMP Ponderado
        # PMP Ponderado = SUMX(PMP simples * Valor líquido) / SUM(Valor líquido)
        if 'pmp_simples' in df_mes.columns and 'valor_l_quido' in df_mes.columns:
            df_mes['pmp_ponderado_calc'] = df_mes['pmp_simples'] * df_mes['valor_l_quido']
            soma_numerador = df_mes['pmp_ponderado_calc'].sum()
            soma_denominador = df_mes['valor_l_quido'].sum()
            pmp_ponderado = (soma_numerador / soma_denominador) if soma_denominador > 0 else 0.0
        else:
            pmp_ponderado = 0.0
        
        # Nome do mês em português (baseado na data de pagamento)
        data_ref = df_mes['data_do_pagamento'].iloc[0]
        meses_pt = [
            'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
            'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
        ]
        mes_nome_pt = f"{meses_pt[data_ref.month - 1]} {data_ref.year}"
        
        resultados.append({
            'Mês': mes_nome_pt,
            'Meta': 38,  # Meta fixa de 38 dias
            'Real': round(pmp_ponderado)  # Arredondar para inteiro como no Power BI
        })
    
    df_resultado = pd.DataFrame(resultados)
    
    # Ordenar por data (usando o primeiro dia do mês para ordenação)
    if not df_resultado.empty:
        df_resultado['_ordem'] = pd.to_datetime(df_resultado['Mês'], format='%B %Y', errors='coerce')
        df_resultado = df_resultado.sort_values('_ordem').drop(columns=['_ordem'])
        df_resultado = df_resultado.reset_index(drop=True)
    
    return df_resultado


@st.cache_data(ttl=3600, show_spinner=True)  # Cache por 1 hora (dados atualizados semanalmente)
def load_pedidos_compras_leadtime(
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    comprador: Optional[List[str]] = None,
    empreendimento: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Carrega dados de pedidos de compras do banco planilhas.
    
    Args:
        data_inicio: Data inicial (YYYY-MM-DD)
        data_fim: Data final (YYYY-MM-DD)
        comprador: Lista de compradores para filtrar
        empreendimento: Lista de nomes de empreendimentos para filtrar
        
    Returns:
        DataFrame com dados de pedidos de compras
    """
    try:
        conn = get_md_connection_planilhas()
        
        # Na tabela planilhas, as datas estao como STRING DD/MM/YYYY
        # Filtros de data serao aplicados no pandas apos conversao correta
        
        # Construir filtros SQL para campos de texto
        filters = []
        params = []
        
        # Filtro de data via SQL tambem para otimizar (se o formato permitir)
        # Como o formato eh DD/MM/YYYY string, melhor filtrar no pandas apos conversao
        # Mas podemos adicionar filtro se a coluna data_entregue nao for nula
        filters.append("data_entregue IS NOT NULL")
        
        if comprador and len(comprador) > 0:
            # Usar UPPER para garantir case-insensitive
            # Filtrar pela coluna c_d_comprador (login/codigo) que corresponde ao filtro lateral
            placeholders = ','.join(['UPPER(?)' for _ in comprador])
            filters.append(f"UPPER(c_d_comprador) IN ({placeholders})")
            params.extend(comprador)
            
        if empreendimento and len(empreendimento) > 0:
            # Mapear ID para Nome ou usar filtro de nome se ja vier como nome
            # O filtro principal retorna lista de strings "Nome (ID: X)"
            # Precisamos extrair o nome ou filtrar pelo ID se a tabela tiver ID
            # A tabela tem 'c_d_obra' (double) e 'obra' (varchar)
            
            ids = []
            nomes = []
            for emp in empreendimento:
                if isinstance(emp, str) and "ID:" in emp:
                    try:
                        # Extrair ID se estiver no formato "Nome (ID: X)"
                        id_val = emp.split("ID: ")[1].rstrip(")")
                        ids.append(int(id_val))
                    except:
                        nomes.append(emp)
                elif isinstance(emp, int) or (isinstance(emp, str) and emp.isdigit()):
                    ids.append(int(emp))
                else:
                    nomes.append(emp)
            
            conditions = []
            if ids:
                placeholders = ','.join(['?' for _ in ids])
                conditions.append(f"CAST(c_d_obra AS INTEGER) IN ({placeholders})")
                params.extend(ids)
            
            if nomes:
                placeholders = ','.join(['?' for _ in nomes])
                conditions.append(f"obra IN ({placeholders})")
                params.extend(nomes)
                
            if conditions:
                filters.append(f"({' OR '.join(conditions)})")
        
        filter_sql = " AND ".join(filters) if filters else "1=1"
        
        # Query para obter dados da tabela
        sql = f"""
        SELECT *
        FROM planilhas.main.relacao_de_pedidos_de_compras
        WHERE {filter_sql}
        """
        
        if params:
            df = conn.execute(sql, params).df()
        else:
            df = conn.execute(sql).df()
            
        conn.close()
        
        # Converter colunas de data
        date_columns = ['data_pedido', 'data_prevista', 'data_entregue']
        for col in date_columns:
            if col in df.columns:
                # Tentar converter com dayfirst=True para formato DD/MM/YYYY
                df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')
        
        # Aplicar filtro de data no pandas (garantido)
        # Usar data_entregue como referencia principal para Lead Time
        col_ref_data = 'data_entregue'
        
        if data_inicio and not df.empty and col_ref_data in df.columns:
            dt_inicio = pd.to_datetime(data_inicio)
            df = df[df[col_ref_data] >= dt_inicio]
            
        if data_fim and not df.empty and col_ref_data in df.columns:
            dt_fim = pd.to_datetime(data_fim)
            # Ajustar para final do dia
            dt_fim = dt_fim + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
            df = df[df[col_ref_data] <= dt_fim]
        
        # Ordenar pela data de entrega
        if col_ref_data in df.columns:
            return df.sort_values(col_ref_data, ascending=False)
        return df.sort_values('data_pedido', ascending=False)
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
            'tempo_atraso_medio_simples': 0.0,
            'total_pedidos': 0,
            'pedidos_no_prazo': 0,
            'pedidos_atrasados': 0,
        }
    
    # Garantir que temos as colunas necessárias
    required_cols = ['data_prevista', 'data_entregue', 'data_pedido']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        return {
            'percentual_no_prazo': 0.0,
            'lead_time_comum': 0.0,
            'lead_time_ponderado': 0.0,
            'tempo_atraso_medio': 0.0,
            'tempo_atraso_medio_simples': 0.0,
            'total_pedidos': len(df),
            'pedidos_no_prazo': 0,
            'pedidos_atrasados': 0,
        }
    
    # Identificar coluna de ID do pedido
    id_col = 'n_do_pedido' if 'n_do_pedido' in df.columns else None
    
    # Filtrar apenas registros com data_entregue preenchida
    df_com_entrega = df[df['data_entregue'].notna()].copy()
    
    if df_com_entrega.empty:
        return {
            'percentual_no_prazo': 0.0,
            'lead_time_comum': 0.0,
            'lead_time_ponderado': 0.0,
            'tempo_atraso_medio': 0.0,
            'tempo_atraso_medio_simples': 0.0,
            'total_pedidos': df[id_col].nunique() if id_col else len(df),
            'pedidos_no_prazo': 0,
            'pedidos_atrasados': 0,
        }
    
    # Agrupar por Pedido APENAS para contagem de pedidos unicos
    total_pedidos_geral = df[id_col].nunique() if id_col else len(df)
    
    # Analise de Lead Time e Prazo deve ser LINHA A LINHA (por item)
    # Motivo: Cada item pode ter data de entrega diferente
    df_analise = df_com_entrega
    col_valor = 'total_l_quido_insumo' if 'total_l_quido_insumo' in df_analise.columns else \
               ('total_liquido_insumo' if 'total_liquido_insumo' in df_analise.columns else None)
               
    total_itens_entregues = len(df_analise)
    
    # 1. % Comprado no Prazo
    # Compara data_entregue diretamente com data_prevista (sem desconto de dias)
    df_analise['entregue_no_prazo'] = df_analise['data_entregue'] <= df_analise['data_prevista']
    
    itens_no_prazo = df_analise['entregue_no_prazo'].sum()
    percentual_no_prazo = (itens_no_prazo / total_itens_entregues * 100) if total_itens_entregues > 0 else 0.0
    
    # 2. Lead Time Comum
    # Diferença entre data_pedido e data_entregue
    df_analise['lead_time_comum'] = (df_analise['data_entregue'] - df_analise['data_pedido']).dt.days
    lead_time_comum_medio = df_analise['lead_time_comum'].mean() if not df_analise.empty else 0.0
    
    # 3. Lead Time Ponderado
    # Fórmula: SUMX(Total líquido insumo * Lead time Simples) / SUM(Total líquido insumo)
    if col_valor and col_valor in df_analise.columns:
        df_analise['lead_time_ponderado_calc'] = (
            df_analise[col_valor] * df_analise['lead_time_comum']
        )
        soma_numerador = df_analise['lead_time_ponderado_calc'].sum()
        soma_denominador = df_analise[col_valor].sum()
        lead_time_ponderado = (soma_numerador / soma_denominador) if soma_denominador > 0 else 0.0
    else:
        # Se não tiver a coluna, usar lead time comum como fallback
        lead_time_ponderado = lead_time_comum_medio
    
    # 4. Tempo de Atraso Médio (simples e ponderado)
    # Se não entregue no prazo: data_entregue - data_prevista
    df_atrasados = df_analise[~df_analise['entregue_no_prazo']].copy()
    if not df_atrasados.empty:
        # Calcular o atraso usando data_entregue diretamente
        df_atrasados['tempo_atraso'] = (df_atrasados['data_entregue'] - df_atrasados['data_prevista']).dt.days
        # Média simples
        tempo_atraso_medio_simples = df_atrasados['tempo_atraso'].mean()
        
        # Média ponderada pelo valor
        if col_valor and col_valor in df_atrasados.columns:
            # Ponderar pelo valor: SUMX(Total líquido insumo * Tempo de Atraso) / SUM(Total líquido insumo)
            df_atrasados['tempo_atraso_ponderado_calc'] = df_atrasados[col_valor] * df_atrasados['tempo_atraso']
            soma_numerador = df_atrasados['tempo_atraso_ponderado_calc'].sum()
            soma_denominador = df_atrasados[col_valor].sum()
            tempo_atraso_medio_ponderado = (soma_numerador / soma_denominador) if soma_denominador > 0 else 0.0
        else:
            tempo_atraso_medio_ponderado = tempo_atraso_medio_simples
    else:
        tempo_atraso_medio_simples = 0.0
        tempo_atraso_medio_ponderado = 0.0
    
    # Pedidos no prazo vs atrasados (baseado em itens)
    # Se a metrica eh "Pedidos no Prazo", deveriamos olhar por pedido?
    # O usuario pediu "medidas de tempo e atraso contando linha a linha"
    # Entao vamos exibir itens nas metricas de quantidade tambem para consistencia com a %
    
    return {
        'percentual_no_prazo': percentual_no_prazo,
        'lead_time_comum': lead_time_comum_medio,
        'lead_time_ponderado': lead_time_ponderado,
        'tempo_atraso_medio': tempo_atraso_medio_ponderado,
        'tempo_atraso_medio_simples': tempo_atraso_medio_simples,
        'total_pedidos': total_pedidos_geral,
        'pedidos_no_prazo': int(itens_no_prazo),
        'pedidos_atrasados': int(total_itens_entregues - itens_no_prazo),
        'total_pedidos_entregues': total_itens_entregues,
        'df_com_entrega': df_analise,
    }


def calcular_indicadores_leadtime_mensal(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula indicadores de lead time agrupados por mês.
    
    Args:
        df: DataFrame com dados de pedidos de compras
        
    Returns:
        DataFrame com colunas: Mês, % Comprado no Prazo, Lead Time Ponderado, Tempo de Atraso Médio, Tempo Atraso Médio Ponderado
    """
    colunas_retorno = ['Mês', '% Comprado no Prazo', 'Lead Time Ponderado', 'Tempo de Atraso Médio', 'Tempo Atraso Médio Ponderado']
    
    if df.empty:
        return pd.DataFrame(columns=colunas_retorno)
    
    # Garantir que temos data_entregue
    if 'data_entregue' not in df.columns:
        return pd.DataFrame(columns=colunas_retorno)
    
    # Filtrar apenas itens com data_entregue preenchida
    df_com_entrega = df[df['data_entregue'].notna()].copy()
    
    if df_com_entrega.empty:
        return pd.DataFrame(columns=colunas_retorno)
    
    # Criar coluna de mês/ano baseada em data_entregue
    df_com_entrega['mes_ano'] = df_com_entrega['data_entregue'].dt.to_period('M')
    df_com_entrega['mes_nome'] = df_com_entrega['data_entregue'].dt.strftime('%Y-%m')
    
    # Preparar cálculos
    df_com_entrega['entregue_no_prazo'] = df_com_entrega['data_entregue'] <= df_com_entrega['data_prevista']
    df_com_entrega['lead_time_comum'] = (df_com_entrega['data_entregue'] - df_com_entrega['data_pedido']).dt.days
    
    col_valor = 'total_l_quido_insumo' if 'total_l_quido_insumo' in df_com_entrega.columns else \
               ('total_liquido_insumo' if 'total_liquido_insumo' in df_com_entrega.columns else None)
    
    # Calcular indicadores por mês
    resultados = []
    
    for mes_period in sorted(df_com_entrega['mes_ano'].unique()):
        df_mes = df_com_entrega[df_com_entrega['mes_ano'] == mes_period].copy()
        
        if df_mes.empty:
            continue
        
        # 1. % Comprado no Prazo
        total_itens = len(df_mes)
        itens_no_prazo = df_mes['entregue_no_prazo'].sum()
        percentual_no_prazo = (itens_no_prazo / total_itens * 100) if total_itens > 0 else 0.0
        
        # 2. Lead Time Ponderado
        if col_valor and col_valor in df_mes.columns:
            df_mes['lead_time_ponderado_calc'] = df_mes[col_valor] * df_mes['lead_time_comum']
            soma_numerador = df_mes['lead_time_ponderado_calc'].sum()
            soma_denominador = df_mes[col_valor].sum()
            lead_time_ponderado = (soma_numerador / soma_denominador) if soma_denominador > 0 else 0.0
        else:
            lead_time_ponderado = df_mes['lead_time_comum'].mean() if not df_mes.empty else 0.0
        
        # 3. Tempo de Atraso Médio (simples e ponderado)
        df_atrasados_mes = df_mes[~df_mes['entregue_no_prazo']].copy()
        if not df_atrasados_mes.empty:
            df_atrasados_mes['tempo_atraso'] = (df_atrasados_mes['data_entregue'] - df_atrasados_mes['data_prevista']).dt.days
            # Média simples
            tempo_atraso_medio_simples = df_atrasados_mes['tempo_atraso'].mean()
            
            # Média ponderada pelo valor
            if col_valor and col_valor in df_atrasados_mes.columns:
                df_atrasados_mes['tempo_atraso_ponderado_calc'] = df_atrasados_mes[col_valor] * df_atrasados_mes['tempo_atraso']
                soma_numerador = df_atrasados_mes['tempo_atraso_ponderado_calc'].sum()
                soma_denominador = df_atrasados_mes[col_valor].sum()
                tempo_atraso_medio_ponderado = (soma_numerador / soma_denominador) if soma_denominador > 0 else 0.0
            else:
                tempo_atraso_medio_ponderado = tempo_atraso_medio_simples
        else:
            tempo_atraso_medio_simples = 0.0
            tempo_atraso_medio_ponderado = 0.0
        
        # Nome do mês em português
        data_ref = df_mes['data_entregue'].iloc[0]
        meses_pt = [
            'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
            'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
        ]
        mes_nome_pt = f"{meses_pt[data_ref.month - 1]} {data_ref.year}"
        
        resultados.append({
            'Mês': mes_nome_pt,
            '% Comprado no Prazo': percentual_no_prazo,
            'Lead Time Ponderado': lead_time_ponderado,
            'Tempo de Atraso Médio': tempo_atraso_medio_simples,
            'Tempo Atraso Médio Ponderado': tempo_atraso_medio_ponderado
        })
    
    df_resultado = pd.DataFrame(resultados)
    
    # Ordenar por data (usando o primeiro dia do mês para ordenação)
    if not df_resultado.empty:
        df_resultado['_ordem'] = pd.to_datetime(df_resultado['Mês'], format='%B %Y', errors='coerce')
        df_resultado = df_resultado.sort_values('_ordem').drop(columns=['_ordem'])
        df_resultado = df_resultado.reset_index(drop=True)
    
    return df_resultado


def calcular_indicadores_leadtime_por(df: pd.DataFrame, group_col: str, col_label: str) -> pd.DataFrame:
    """
    Calcula indicadores de lead time agrupados por uma dimensão (ex.: obra, comprador).
    """
    if df.empty or group_col not in df.columns:
        return pd.DataFrame(columns=[col_label, '% Comprado no Prazo', 'Lead Time Ponderado', 'Tempo de Atraso Médio'])

    df_com_entrega = df[df['data_entregue'].notna()].copy()
    if df_com_entrega.empty:
        return pd.DataFrame(columns=[col_label, '% Comprado no Prazo', 'Lead Time Ponderado', 'Tempo de Atraso Médio'])

    # Preparar colunas auxiliares
    df_com_entrega['entregue_no_prazo'] = df_com_entrega['data_entregue'] <= df_com_entrega['data_prevista']
    df_com_entrega['lead_time_comum'] = (df_com_entrega['data_entregue'] - df_com_entrega['data_pedido']).dt.days

    col_valor = 'total_l_quido_insumo' if 'total_l_quido_insumo' in df_com_entrega.columns else \
               ('total_liquido_insumo' if 'total_liquido_insumo' in df_com_entrega.columns else None)

    resultados = []
    for grupo, df_grupo in df_com_entrega.groupby(group_col):
        if df_grupo.empty:
            continue

        total_itens = len(df_grupo)
        itens_no_prazo = df_grupo['entregue_no_prazo'].sum()
        percentual_no_prazo = (itens_no_prazo / total_itens * 100) if total_itens > 0 else 0.0

        if col_valor and col_valor in df_grupo.columns:
            df_grupo['lead_time_ponderado_calc'] = df_grupo[col_valor] * df_grupo['lead_time_comum']
            soma_numerador = df_grupo['lead_time_ponderado_calc'].sum()
            soma_denominador = df_grupo[col_valor].sum()
            lead_time_ponderado = (soma_numerador / soma_denominador) if soma_denominador > 0 else 0.0
        else:
            lead_time_ponderado = df_grupo['lead_time_comum'].mean() if not df_grupo.empty else 0.0

        df_atrasados = df_grupo[~df_grupo['entregue_no_prazo']].copy()
        if not df_atrasados.empty and col_valor and col_valor in df_atrasados.columns:
            df_atrasados['tempo_atraso'] = (df_atrasados['data_entregue'] - df_atrasados['data_prevista']).dt.days
            # Ponderar pelo valor
            df_atrasados['tempo_atraso_ponderado_calc'] = df_atrasados[col_valor] * df_atrasados['tempo_atraso']
            soma_numerador = df_atrasados['tempo_atraso_ponderado_calc'].sum()
            soma_denominador = df_atrasados[col_valor].sum()
            tempo_atraso_medio = (soma_numerador / soma_denominador) if soma_denominador > 0 else 0.0
        elif not df_atrasados.empty:
            # Fallback: média simples se não tiver coluna de valor
            df_atrasados['tempo_atraso'] = (df_atrasados['data_entregue'] - df_atrasados['data_prevista']).dt.days
            tempo_atraso_medio = df_atrasados['tempo_atraso'].mean()
        else:
            tempo_atraso_medio = 0.0

        resultados.append({
            col_label: grupo,
            '% Comprado no Prazo': percentual_no_prazo,
            'Lead Time Ponderado': lead_time_ponderado,
            'Tempo de Atraso Médio': tempo_atraso_medio
        })

    df_resultado = pd.DataFrame(resultados)
    if not df_resultado.empty:
        df_resultado = df_resultado.sort_values(col_label).reset_index(drop=True)
    return df_resultado


def calcular_indicadores_leadtime_por_obra_mes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula indicadores de lead time agrupados por Obra e Mês.
    """
    if df.empty or 'obra' not in df.columns or 'data_entregue' not in df.columns:
        return pd.DataFrame(columns=['Obra', 'Mês', '% Comprado no Prazo', 'Lead Time Ponderado', 'Tempo de Atraso Médio'])

    df_com_entrega = df[df['data_entregue'].notna()].copy()
    if df_com_entrega.empty:
        return pd.DataFrame(columns=['Obra', 'Mês', '% Comprado no Prazo', 'Lead Time Ponderado', 'Tempo de Atraso Médio'])

    # Colunas auxiliares
    df_com_entrega['entregue_no_prazo'] = df_com_entrega['data_entregue'] <= df_com_entrega['data_prevista']
    df_com_entrega['lead_time_comum'] = (df_com_entrega['data_entregue'] - df_com_entrega['data_pedido']).dt.days
    df_com_entrega['mes_ano'] = df_com_entrega['data_entregue'].dt.to_period('M')

    col_valor = 'total_l_quido_insumo' if 'total_l_quido_insumo' in df_com_entrega.columns else \
               ('total_liquido_insumo' if 'total_liquido_insumo' in df_com_entrega.columns else None)

    resultados = []
    for (obra, mes_period), df_g in df_com_entrega.groupby(['obra', 'mes_ano']):
        if df_g.empty:
            continue

        total_itens = len(df_g)
        itens_no_prazo = df_g['entregue_no_prazo'].sum()
        percentual_no_prazo = (itens_no_prazo / total_itens * 100) if total_itens > 0 else 0.0

        if col_valor and col_valor in df_g.columns:
            df_g['lead_time_ponderado_calc'] = df_g[col_valor] * df_g['lead_time_comum']
            soma_numerador = df_g['lead_time_ponderado_calc'].sum()
            soma_denominador = df_g[col_valor].sum()
            lead_time_ponderado = (soma_numerador / soma_denominador) if soma_denominador > 0 else 0.0
        else:
            lead_time_ponderado = df_g['lead_time_comum'].mean() if not df_g.empty else 0.0

        df_atras = df_g[~df_g['entregue_no_prazo']].copy()
        if not df_atras.empty and col_valor and col_valor in df_atras.columns:
            df_atras['tempo_atraso'] = (df_atras['data_entregue'] - df_atras['data_prevista']).dt.days
            # Ponderar pelo valor
            df_atras['tempo_atraso_ponderado_calc'] = df_atras[col_valor] * df_atras['tempo_atraso']
            soma_numerador = df_atras['tempo_atraso_ponderado_calc'].sum()
            soma_denominador = df_atras[col_valor].sum()
            tempo_atraso_medio = (soma_numerador / soma_denominador) if soma_denominador > 0 else 0.0
        elif not df_atras.empty:
            # Fallback: média simples se não tiver coluna de valor
            df_atras['tempo_atraso'] = (df_atras['data_entregue'] - df_atras['data_prevista']).dt.days
            tempo_atraso_medio = df_atras['tempo_atraso'].mean()
        else:
            tempo_atraso_medio = 0.0

        # Nome do mês em português
        data_ref = df_g['data_entregue'].iloc[0]
        meses_pt = [
            'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
            'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
        ]
        mes_nome_pt = f"{meses_pt[data_ref.month - 1]} {data_ref.year}"

        resultados.append({
            'Obra': obra,
            'Mês': mes_nome_pt,
            '% Comprado no Prazo': percentual_no_prazo,
            'Lead Time Ponderado': lead_time_ponderado,
            'Tempo de Atraso Médio': tempo_atraso_medio
        })

    df_resultado = pd.DataFrame(resultados)
    if not df_resultado.empty:
        df_resultado['_ordem'] = pd.to_datetime(df_resultado['Mês'], format='%B %Y', errors='coerce')
        df_resultado = df_resultado.sort_values(['Obra', '_ordem']).drop(columns=['_ordem']).reset_index(drop=True)
    return df_resultado

def formatar_dias(valor: float) -> str:
    """Formata valor como dias."""
    return f"{valor:.1f} dias"


@st.cache_data(ttl=3600)
def get_last_update_leadtime() -> Optional[str]:
    """Obtém data da última carga de lead time."""
    try:
        md_conn = get_md_connection_planilhas()
        # Tentar obter a maior data de ingestão se existir a coluna _ingested_at
        sql = "SELECT MAX(_ingested_at) as last_update FROM planilhas.main.relacao_de_pedidos_de_compras"
        df = md_conn.execute(sql).df()
        if not df.empty and df['last_update'].iloc[0]:
             dt = pd.to_datetime(df['last_update'].iloc[0])
             return dt.strftime("%d/%m/%Y")
    except:
        pass
    return None


@st.cache_data(ttl=3600)
def get_last_update_pmp() -> Optional[str]:
    """Obtém data da última carga de contas pagas."""
    try:
        md_conn = get_md_connection_planilhas()
        # Tentar obter a maior data de ingestão se existir a coluna _ingested_at
        sql = "SELECT MAX(_ingested_at) as last_update FROM planilhas.main.contas_pagas"
        df = md_conn.execute(sql).df()
        if not df.empty and df['last_update'].iloc[0]:
             dt = pd.to_datetime(df['last_update'].iloc[0])
             return dt.strftime("%d/%m/%Y")
    except:
        pass
    return None


def render_leadtime_tab(
    data_inicio: Optional[datetime], 
    data_fim: Optional[datetime],
    comprador: Optional[List[str]] = None,
    empreendimento: Optional[List[str]] = None
):
    """Renderiza a aba de Lead Time."""
    st.subheader("⏱️ Indicadores de Lead Time")
    
    last_update = get_last_update_leadtime()
    last_update_msg = f" Última carga conhecida: **{last_update}**." if last_update else ""
    st.info(f"Esta página é atualizada **semanalmente**.{last_update_msg}")
    
    st.caption("Análise de lead time, tempo de atraso e % comprado no prazo | Fonte: planilhas.relacao_de_pedidos_de_compras")
    
    # Carregar dados
    with st.spinner("Carregando dados de lead time..."):
        df_leadtime = load_pedidos_compras_leadtime(
            data_inicio=data_inicio.strftime('%Y-%m-%d') if data_inicio else None,
            data_fim=data_fim.strftime('%Y-%m-%d') if data_fim else None,
            comprador=comprador,
            empreendimento=empreendimento
        )
    
    if df_leadtime.empty:
        st.warning("⚠️ Nenhum dado encontrado para os filtros selecionados.")
        st.info("💡 Verifique se a tabela 'planilhas.main.relacao_de_pedidos_de_compras' existe e possui dados.")
        return
    
    # Calcular indicadores
    indicadores = calcular_indicadores_leadtime(df_leadtime)
    
    # KPIs Principais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "% Comprado no Prazo",
            formatar_percentual(indicadores['percentual_no_prazo']),
            help="Percentual de itens entregues no prazo (data_entregue <= data_prevista)"
        )
    
    with col2:
        st.metric(
            "Lead Time Ponderado",
            formatar_dias(indicadores['lead_time_ponderado']),
            help="Lead time ponderado pelo total líquido insumo"
        )
    
    with col3:
        st.metric(
            "Tempo Atraso Médio",
            formatar_dias(indicadores['tempo_atraso_medio_simples']),
            help="Média simples de dias de atraso para itens entregues fora do prazo"
        )
    
    with col4:
        st.metric(
            "Tempo Atraso Médio Ponderado",
            formatar_dias(indicadores['tempo_atraso_medio']),
            help="Tempo médio de atraso ponderado pelo valor dos itens. Fórmula: SUMX(Total líquido insumo * Tempo de Atraso) / SUM(Total líquido insumo), considerando apenas itens entregues fora do prazo"
        )
    
    # Tabela Mensal
    st.markdown("---")
    st.subheader("📅 Indicadores por Mês")
    
    df_mensal = calcular_indicadores_leadtime_mensal(df_leadtime)
    
    if not df_mensal.empty:
        # Formatar valores para exibição
        df_exibicao = df_mensal.copy()
        df_exibicao['% Comprado no Prazo'] = df_exibicao['% Comprado no Prazo'].apply(lambda x: f"{x:.2f}%")
        df_exibicao['Lead Time Ponderado'] = df_exibicao['Lead Time Ponderado'].apply(lambda x: f"{x:.1f} dias")
        if 'Tempo Atraso Médio Ponderado' in df_exibicao.columns:
            df_exibicao['Tempo Atraso Médio Ponderado'] = df_exibicao['Tempo Atraso Médio Ponderado'].apply(lambda x: f"{x:.2f} dias" if x > 0 else "-")
        if 'Tempo de Atraso Médio' in df_exibicao.columns:
            df_exibicao['Tempo de Atraso Médio'] = df_exibicao['Tempo de Atraso Médio'].apply(lambda x: f"{x:.2f} dias" if x > 0 else "-")
        
        # Ordenar colunas: Mês, % Comprado no Prazo, Lead Time Ponderado, Tempo de Atraso Médio, Tempo Atraso Médio Ponderado
        colunas_ordenadas = ['Mês', '% Comprado no Prazo', 'Lead Time Ponderado']
        if 'Tempo de Atraso Médio' in df_exibicao.columns:
            colunas_ordenadas.append('Tempo de Atraso Médio')
        if 'Tempo Atraso Médio Ponderado' in df_exibicao.columns:
            colunas_ordenadas.append('Tempo Atraso Médio Ponderado')
        
        st.dataframe(
            df_exibicao[colunas_ordenadas],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Mês": st.column_config.TextColumn("Mês", width="medium"),
                "% Comprado no Prazo": st.column_config.TextColumn("% Comprado no Prazo", width="medium"),
                "Lead Time Ponderado": st.column_config.TextColumn("Lead Time Ponderado", width="medium"),
                "Tempo Atraso Médio Ponderado": st.column_config.TextColumn("Tempo Atraso Médio Ponderado", width="medium"),
                "Tempo de Atraso Médio": st.column_config.TextColumn("Tempo de Atraso Médio", width="medium"),
            }
        )
    else:
        st.info("ℹ️ Nenhum dado mensal disponível para os filtros selecionados.")
    
    # Tabela por Obra
    st.markdown("---")
    st.subheader("🏗️ Indicadores por Obra")

    df_obra = calcular_indicadores_leadtime_por(df_leadtime, group_col='obra', col_label='Obra')
    if not df_obra.empty:
        df_exib_obra = df_obra.copy()
        df_exib_obra['% Comprado no Prazo'] = df_exib_obra['% Comprado no Prazo'].apply(lambda x: f"{x:.2f}%")
        df_exib_obra['Lead Time Ponderado'] = df_exib_obra['Lead Time Ponderado'].apply(lambda x: f"{x:.1f} dias")
        df_exib_obra['Tempo de Atraso Médio'] = df_exib_obra['Tempo de Atraso Médio'].apply(lambda x: f"{x:.2f} dias" if x > 0 else "-")

        st.dataframe(
            df_exib_obra,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Obra": st.column_config.TextColumn("Obra", width="medium"),
                "% Comprado no Prazo": st.column_config.TextColumn("% Comprado no Prazo", width="medium"),
                "Lead Time Ponderado": st.column_config.TextColumn("Lead Time Ponderado", width="medium"),
                "Tempo de Atraso Médio": st.column_config.TextColumn("Tempo de Atraso Médio", width="medium"),
            }
        )
    else:
        st.info("ℹ️ Nenhum dado por obra disponível para os filtros selecionados.")

    # Tabela por Comprador
    st.markdown("---")
    st.subheader("🛒 Indicadores por Comprador")

    df_comprador = calcular_indicadores_leadtime_por(df_leadtime, group_col='comprador', col_label='Comprador')
    if not df_comprador.empty:
        df_exib_comp = df_comprador.copy()
        df_exib_comp['% Comprado no Prazo'] = df_exib_comp['% Comprado no Prazo'].apply(lambda x: f"{x:.2f}%")
        df_exib_comp['Lead Time Ponderado'] = df_exib_comp['Lead Time Ponderado'].apply(lambda x: f"{x:.1f} dias")
        df_exib_comp['Tempo de Atraso Médio'] = df_exib_comp['Tempo de Atraso Médio'].apply(lambda x: f"{x:.2f} dias" if x > 0 else "-")

        st.dataframe(
            df_exib_comp,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Comprador": st.column_config.TextColumn("Comprador", width="medium"),
                "% Comprado no Prazo": st.column_config.TextColumn("% Comprado no Prazo", width="medium"),
                "Lead Time Ponderado": st.column_config.TextColumn("Lead Time Ponderado", width="medium"),
                "Tempo de Atraso Médio": st.column_config.TextColumn("Tempo de Atraso Médio", width="medium"),
            }
        )
    else:
        st.info("ℹ️ Nenhum dado por comprador disponível para os filtros selecionados.")

    # Tabela por Obra e Mês
    st.markdown("---")
    st.subheader("🏗️ Indicadores por Obra e Mês")

    df_obra_mes = calcular_indicadores_leadtime_por_obra_mes(df_leadtime)
    if not df_obra_mes.empty:
        # Obter lista de obras únicas para o filtro
        obras_disponiveis = sorted(df_obra_mes['Obra'].unique().tolist())
        
        # Filtro de obra (apenas para esta tabela) - estilo sutil como no Jira
        obras_opcoes = ["Todas"] + obras_disponiveis
        obra_selecionada = st.selectbox(
            "Obra:",
            options=obras_opcoes,
            key="leadtime_filtro_obra_mes"
        )
        
        # Aplicar filtro se houver seleção
        if obra_selecionada and obra_selecionada != "Todas":
            df_obra_mes_filtrado = df_obra_mes[df_obra_mes['Obra'] == obra_selecionada].copy()
        else:
            df_obra_mes_filtrado = df_obra_mes.copy()  # Se "Todas" ou vazio, mostrar todas
        
        if not df_obra_mes_filtrado.empty:
            df_exib_obra_mes = df_obra_mes_filtrado.copy()
            df_exib_obra_mes['% Comprado no Prazo'] = df_exib_obra_mes['% Comprado no Prazo'].apply(lambda x: f"{x:.2f}%")
            df_exib_obra_mes['Lead Time Ponderado'] = df_exib_obra_mes['Lead Time Ponderado'].apply(lambda x: f"{x:.1f} dias")
            df_exib_obra_mes['Tempo de Atraso Médio'] = df_exib_obra_mes['Tempo de Atraso Médio'].apply(lambda x: f"{x:.2f} dias" if x > 0 else "-")

            st.dataframe(
                df_exib_obra_mes,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Obra": st.column_config.TextColumn("Obra", width="medium"),
                    "Mês": st.column_config.TextColumn("Mês", width="medium"),
                    "% Comprado no Prazo": st.column_config.TextColumn("% Comprado no Prazo", width="medium"),
                    "Lead Time Ponderado": st.column_config.TextColumn("Lead Time Ponderado", width="medium"),
                    "Tempo de Atraso Médio": st.column_config.TextColumn("Tempo de Atraso Médio", width="medium"),
                }
            )
    else:
        st.info("ℹ️ Nenhum dado por obra e mês disponível para os filtros selecionados.")



def render_pmp_tab(
    data_inicio: Optional[datetime] = None,
    data_fim: Optional[datetime] = None,
):
    """Renderiza a aba de PMP (Prazo Médio de Pagamento)."""
    st.subheader("💰 Prazo Médio de Pagamento (PMP)")
    
    last_update = get_last_update_pmp()
    last_update_msg = f" Última carga conhecida: **{last_update}**." if last_update else ""
    st.info(f"Esta página é atualizada **semanalmente**.{last_update_msg}")
    st.caption("Análise de PMP ponderado por mês | Fonte: planilhas.contas_pagas")
    
    # Carregar dados
    with st.spinner("Carregando dados de contas pagas..."):
        df_pmp = load_contas_pagas_pmp(
            data_inicio=data_inicio.strftime('%Y-%m-%d') if data_inicio else None,
            data_fim=data_fim.strftime('%Y-%m-%d') if data_fim else None,
        )
    
    if df_pmp.empty:
        st.warning("⚠️ Nenhum dado encontrado para os filtros selecionados.")
        st.info("💡 Verifique se a tabela 'planilhas.main.contas_pagas' existe e possui dados.")
        return
    
    # Calcular PMP ponderado mensal
    df_pmp_mensal = calcular_pmp_ponderado_mensal(df_pmp)
    
    if df_pmp_mensal.empty:
        st.info("ℹ️ Nenhum dado mensal disponível para os filtros selecionados.")
        return
    
    # Exibir tabela simples: Meta vs Real
    st.subheader("PMP")
    
    # Formatar valores para exibição
    df_exibicao = df_pmp_mensal.copy()
    df_exibicao['Meta'] = df_exibicao['Meta'].astype(int)
    df_exibicao['Real'] = df_exibicao['Real'].apply(lambda x: f"{int(x)}" if pd.notna(x) else "-")
    
    st.dataframe(
        df_exibicao,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Mês": st.column_config.TextColumn("Mês", width="medium"),
            "Meta": st.column_config.NumberColumn("Meta", width="small", format="%d"),
            "Real": st.column_config.TextColumn("Real", width="small"),
        }
    )


def render_compras_dashboard(
    *,
    show_title: bool = True,
    show_caption: bool = True,
):
    """
    Renderiza o dashboard de Compras.

    Args:
        show_title: Exibe título principal.
        show_caption: Exibe legenda/logo abaixo do título.
    """
    if show_title:
        st.title("🛒 Dashboard de Compras")
        if show_caption:
            st.caption("Monitoramento de compras e fornecedores")

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
            max_value=date.today(),
            key="compras_data_inicio"
        )

        data_fim = st.date_input(
            "Data Final",
            value=default_fim,
            max_value=date.today(),
            key="compras_data_fim"
        )
        
        # Filtro de comprador
        st.subheader("Comprador")
        # Filtrar compradores com base no periodo selecionado
        data_ini_str = data_inicio.strftime('%Y-%m-%d') if data_inicio else None
        data_fim_str = data_fim.strftime('%Y-%m-%d') if data_fim else None
        
        compradores_disponiveis = get_unique_compradores(data_ini_str, data_fim_str)
        comprador_selecionado = st.multiselect(
            "Selecione o(s) comprador(es)",
            options=compradores_disponiveis,
            key="compras_comprador"
        )
        
        # Filtro de empreendimento
        st.subheader("Empreendimento")
        empreendimentos_disponiveis = get_unique_empreendimentos()
        empreendimento_selecionado = st.multiselect(
            "Selecione o(s) empreendimento(s)",
            options=empreendimentos_disponiveis,
            key="compras_empreendimento"
        )
        
        # Filtro de título (Notas)
        st.subheader("Título")
        titulo_filtro = st.text_input(
            "Buscar por título (Notas)",
            key="compras_titulo",
            placeholder="Digite parte do título..."
        )
    
    # Carregar dados
    with st.spinner("Carregando dados de compras..."):
        df = load_pedidos_compras(
            data_inicio=data_inicio.strftime('%Y-%m-%d') if data_inicio else None,
            data_fim=data_fim.strftime('%Y-%m-%d') if data_fim else None,
            comprador=comprador_selecionado if comprador_selecionado else None,
            empreendimento=empreendimento_selecionado if empreendimento_selecionado else None,
        )
        
        # Aplicar filtro de título se fornecido
        if titulo_filtro and not df.empty:
            df = df[df['Titulo'].astype(str).str.contains(titulo_filtro, case=False, na=False)]
    
    if df.empty:
        st.warning("⚠️ Nenhum dado encontrado para os filtros selecionados.")
        return
    
    # Calcular indicadores
    indicadores = calcular_indicadores(df)
    
    # Seção 1: KPIs Principais
    st.markdown("---")
    st.subheader("📊 Indicadores Principais")
    
    # Primeira linha: Valor de Compras, Total de Pedidos, Valor Médio por Pedido, Valor de Descontos
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Valor de Compras",
            formatar_moeda(indicadores['valor_pedidos']),
            help="Soma do valor total de todos os pedidos de compra"
        )
    
    with col2:
        st.metric(
            "Total de Pedidos",
            f"{indicadores['total_pedidos']:,}",
            help="Quantidade total de pedidos de compra (excluindo pedidos cancelados)"
        )
    
    with col3:
        st.metric(
            "Valor Médio por Pedido",
            formatar_moeda(indicadores['valor_medio_pedido']),
            help="Valor médio de cada pedido de compra"
        )
    
    with col4:
        st.metric(
            "Valor de Descontos",
            formatar_moeda(indicadores['valor_descontos']),
            help="Soma total de descontos aplicados"
        )
    
    # Segunda linha: % de Desconto, Pedidos Entregues, Pedidos Parcialmente Entregues, Pedidos Atrasados, Pedidos no Prazo
    col5, col6, col7, col8, col9 = st.columns(5)
    
    with col5:
        st.metric(
            "% de Desconto",
            formatar_percentual(indicadores['percentual_desconto']),
            help="Percentual de desconto em relação ao valor total dos pedidos"
        )
    
    with col6:
        st.metric(
            "Pedidos Totalmente Entregues",
            f"{indicadores['pedidos_entregues']:,}",
            f"{formatar_percentual(indicadores['percentual_entregues'])}",
            help="Quantidade e percentual de pedidos totalmente entregues e no prazo (Status: FULLY_DELIVERED e não atrasados)"
        )
    
    with col7:
        st.metric(
            "Pedidos Parcialmente Entregues",
            f"{indicadores['pedidos_parcialmente_entregues']:,}",
            f"{formatar_percentual(indicadores['percentual_parcialmente_entregues'])}",
            help="Quantidade e percentual de pedidos parcialmente entregues e no prazo (Status: PARTIALLY_DELIVERED e não atrasados)"
        )
    
    with col8:
        st.metric(
            "Pedidos Atrasados",
            f"{indicadores['pedidos_atrasados']:,}",
            f"{formatar_percentual(indicadores['percentual_atrasados'])}",
            help="Quantidade e percentual de pedidos atrasados (independente do status de entrega)"
        )
    
    with col9:
        st.metric(
            "Pedidos no Prazo",
            f"{indicadores['pedidos_no_prazo']:,}",
            f"{formatar_percentual(indicadores['percentual_no_prazo'])}",
            help="Quantidade e percentual de pedidos pendentes no prazo (Status: PENDING e Atrasado: False)"
        )
    
    # Seção 3: Análises Adicionais
    st.markdown("---")
    st.subheader("📈 Análises Detalhadas")
    
    # Tabs para diferentes análises
    tab1, tab2, tab3 = st.tabs([
        "📊 Análises Detalhadas",
        "⚠️ Pedidos Atrasados",
        "⏱️ Lead Time"
    ])
    
    with tab1:
        st.subheader("Timeline de Compras")
        
        if 'Data_Pedido' in df.columns and not df.empty:
            # Agrupar por mês
            df_timeline = df.copy()
            df_timeline['Mes'] = df_timeline['Data_Pedido'].dt.to_period('M').astype(str)
            
            timeline_agg = df_timeline.groupby('Mes').agg({
                'Valor_Total': 'sum',
                'Desconto': 'sum',
                'ID_Pedido': 'count'
            }).reset_index()
            
            timeline_agg.columns = ['Mes', 'Valor_Total', 'Total_Desconto', 'Qtd_Pedidos']
            timeline_agg = timeline_agg.sort_values('Mes')
            timeline_agg['Percentual_Desconto'] = timeline_agg.apply(
                lambda row: (row['Total_Desconto'] / row['Valor_Total'] * 100)
                if row['Valor_Total'] else 0.0,
                axis=1
            )
            
            # Gráfico de linha
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=timeline_agg['Mes'],
                y=timeline_agg['Valor_Total'],
                mode='lines+markers',
                name='Valor Total',
                line=dict(color='#1f77b4', width=2)
            ))
            fig.add_trace(go.Scatter(
                x=timeline_agg['Mes'],
                y=timeline_agg['Total_Desconto'],
                mode='lines+markers',
                name='Total Descontos',
                line=dict(color='#ff7f0e', width=2)
            ))
            
            fig.update_layout(
                title='Evolução de Compras ao Longo do Tempo',
                xaxis_title='Mês',
                yaxis_title='Valor (R$)',
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabela
            timeline_agg['Valor_Total'] = timeline_agg['Valor_Total'].apply(formatar_moeda)
            timeline_agg['Total_Desconto'] = timeline_agg['Total_Desconto'].apply(formatar_moeda)
            timeline_agg['Percentual_Desconto'] = timeline_agg['Percentual_Desconto'].apply(formatar_percentual)
            
            st.dataframe(
                timeline_agg,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Dados de data não disponíveis.")

        st.markdown("---")

        st.subheader("Análise por Empreendimento")
        
        if 'Empreendimento' in df.columns:
            analise_empreendimento = df.groupby('Empreendimento').agg({
                'Valor_Total': ['sum', 'mean', 'count'],
                'Desconto': 'sum',
            }).reset_index()
            
            analise_empreendimento.columns = ['Empreendimento', 'Valor_Total', 'Valor_Medio', 'Qtd_Pedidos', 'Total_Desconto']
            analise_empreendimento['%_Desconto'] = (analise_empreendimento['Total_Desconto'] / analise_empreendimento['Valor_Total'] * 100).fillna(0)
            analise_empreendimento = analise_empreendimento.sort_values('Valor_Total', ascending=False)
            
            # Formatação
            analise_empreendimento_display = analise_empreendimento.copy()
            analise_empreendimento_display['Valor_Total'] = analise_empreendimento_display['Valor_Total'].apply(formatar_moeda)
            analise_empreendimento_display['Valor_Medio'] = analise_empreendimento_display['Valor_Medio'].apply(formatar_moeda)
            analise_empreendimento_display['Total_Desconto'] = analise_empreendimento_display['Total_Desconto'].apply(formatar_moeda)
            analise_empreendimento_display['%_Desconto'] = analise_empreendimento_display['%_Desconto'].apply(formatar_percentual)
            
            st.dataframe(
                analise_empreendimento_display,
                use_container_width=True,
                hide_index=True
            )
            
            # Gráfico (usar valores numéricos antes da formatação)
            analise_empreendimento_num = analise_empreendimento.head(10)
            
            fig = px.bar(
                analise_empreendimento_num,
                x='Empreendimento',
                y='Valor_Total',
                title='Top 10 Empreendimentos por Valor Total',
                labels={'Valor_Total': 'Valor Total (R$)', 'Empreendimento': 'Empreendimento'}
            )
            fig.update_yaxes(tickformat='$,.2f')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Dados de empreendimento não disponíveis.")

        st.markdown("---")

        st.subheader("Análise por Comprador")
        
        if 'Comprador' in df.columns:
            analise_comprador = df.groupby('Comprador').agg({
                'Valor_Total': ['sum', 'mean', 'count'],
                'Desconto': 'sum',
            }).reset_index()
            
            analise_comprador.columns = ['Comprador', 'Valor_Total', 'Valor_Medio', 'Qtd_Pedidos', 'Total_Desconto']
            analise_comprador['%_Desconto'] = (analise_comprador['Total_Desconto'] / analise_comprador['Valor_Total'] * 100).fillna(0)
            analise_comprador = analise_comprador.sort_values('Valor_Total', ascending=False)
            
            # Formatação
            analise_comprador_display = analise_comprador.copy()
            analise_comprador_display['Valor_Total'] = analise_comprador_display['Valor_Total'].apply(formatar_moeda)
            analise_comprador_display['Valor_Medio'] = analise_comprador_display['Valor_Medio'].apply(formatar_moeda)
            analise_comprador_display['Total_Desconto'] = analise_comprador_display['Total_Desconto'].apply(formatar_moeda)
            analise_comprador_display['%_Desconto'] = analise_comprador_display['%_Desconto'].apply(formatar_percentual)
            
            st.dataframe(
                analise_comprador_display,
                use_container_width=True,
                hide_index=True
            )
            
            # Gráfico (usar valores numéricos antes da formatação)
            analise_comprador_num = analise_comprador.head(10)
            
            fig = px.bar(
                analise_comprador_num,
                x='Comprador',
                y='Valor_Total',
                title='Top 10 Compradores por Valor Total',
                labels={'Valor_Total': 'Valor Total (R$)', 'Comprador': 'Comprador'}
            )
            fig.update_yaxes(tickformat='$,.2f')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Dados de comprador não disponíveis.")
        
        st.markdown("---")
        
        # Detalhamento de Pedidos
        st.subheader("📋 Detalhamento de Pedidos")
        
        # Colunas para exibir
        colunas_display = [
            'ID_Pedido', 'Data_Pedido', 'Comprador', 'Empreendimento',
            'Status', 'Atrasado', 'Valor_Total', 'Desconto', 'Titulo'
        ]
        
        colunas_disponiveis = [col for col in colunas_display if col in df.columns]
        
        df_display = df[colunas_disponiveis].copy()
        
        # Formatação
        if 'Valor_Total' in df_display.columns:
            df_display['Valor_Total'] = df_display['Valor_Total'].apply(formatar_moeda)
        if 'Desconto' in df_display.columns:
            df_display['Desconto'] = df_display['Desconto'].apply(formatar_moeda)
        if 'Atrasado' in df_display.columns:
            df_display['Atrasado'] = df_display['Atrasado'].map({True: 'Sim', False: 'Não'})
        
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True
        )
        
        # Botão de download
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"pedidos_compras_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    with tab2:
        st.subheader("⚠️ Pedidos Atrasados")
        st.caption("Análise detalhada de pedidos com atraso na entrega")
        
        # Filtrar apenas pedidos atrasados
        if 'Atrasado' in df.columns:
            df_atrasados = df[df['Atrasado'] == True].copy() if df['Atrasado'].dtype == bool else df[df['Atrasado'] == 1].copy()
        else:
            df_atrasados = pd.DataFrame()
        
        if df_atrasados.empty:
            st.info("ℹ️ Nenhum pedido atrasado encontrado para os filtros selecionados.")
        else:
            # KPIs de Pedidos Atrasados
            total_atrasados = len(df_atrasados)
            valor_atrasados = df_atrasados['Valor_Total'].sum() if 'Valor_Total' in df_atrasados.columns else 0
            percentual_atrasados = (total_atrasados / len(df) * 100) if len(df) > 0 else 0
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(
                    "Total de Pedidos Atrasados",
                    f"{total_atrasados:,}",
                    help="Quantidade de pedidos com status atrasado"
                )
            with col2:
                st.metric(
                    "Valor Total Atrasado",
                    formatar_moeda(valor_atrasados),
                    help="Soma do valor de todos os pedidos atrasados"
                )
            with col3:
                st.metric(
                    "% do Total",
                    formatar_percentual(percentual_atrasados),
                    help="Percentual de pedidos atrasados em relação ao total"
                )
            
            st.markdown("---")
            
            # Análise por Empreendimento
            st.subheader("🏗️ Atrasados por Empreendimento")
            
            if 'Empreendimento' in df_atrasados.columns:
                atrasados_empreendimento = df_atrasados.groupby('Empreendimento').agg({
                    'ID_Pedido': 'count',
                    'Valor_Total': 'sum'
                }).reset_index()
                atrasados_empreendimento.columns = ['Empreendimento', 'Qtd_Atrasados', 'Valor_Total']
                atrasados_empreendimento = atrasados_empreendimento.sort_values('Qtd_Atrasados', ascending=False)
                
                # Formatação para exibição
                atrasados_emp_display = atrasados_empreendimento.copy()
                atrasados_emp_display['Valor_Total'] = atrasados_emp_display['Valor_Total'].apply(formatar_moeda)
                
                st.dataframe(
                    atrasados_emp_display,
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("Dados de empreendimento não disponíveis.")
            
            st.markdown("---")
            
            # Análise por Comprador
            st.subheader("🛒 Atrasados por Comprador")
            
            if 'Comprador' in df_atrasados.columns:
                atrasados_comprador = df_atrasados.groupby('Comprador').agg({
                    'ID_Pedido': 'count',
                    'Valor_Total': 'sum'
                }).reset_index()
                atrasados_comprador.columns = ['Comprador', 'Qtd_Atrasados', 'Valor_Total']
                atrasados_comprador = atrasados_comprador.sort_values('Qtd_Atrasados', ascending=False)
                
                # Formatação para exibição
                atrasados_comp_display = atrasados_comprador.copy()
                atrasados_comp_display['Valor_Total'] = atrasados_comp_display['Valor_Total'].apply(formatar_moeda)
                
                st.dataframe(
                    atrasados_comp_display,
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("Dados de comprador não disponíveis.")
            
            st.markdown("---")
            
            # Tabela detalhada dos pedidos atrasados
            st.subheader("📋 Detalhamento dos Pedidos Atrasados")
            
            # Selecionar colunas relevantes
            colunas_atrasados = ['ID_Pedido', 'Empreendimento', 'Comprador', 'Valor_Total']
            colunas_disponiveis_atrasados = [col for col in colunas_atrasados if col in df_atrasados.columns]
            
            if colunas_disponiveis_atrasados:
                df_atrasados_display = df_atrasados[colunas_disponiveis_atrasados].copy()
                df_atrasados_display = df_atrasados_display.sort_values('Valor_Total', ascending=False)
                
                # Formatação
                if 'Valor_Total' in df_atrasados_display.columns:
                    df_atrasados_display['Valor_Total'] = df_atrasados_display['Valor_Total'].apply(formatar_moeda)
                
                st.dataframe(
                    df_atrasados_display,
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("Dados detalhados não disponíveis.")
    
    with tab3:
        try:
            render_leadtime_tab(data_inicio, data_fim, comprador_selecionado, empreendimento_selecionado)
        except Exception as e:
            st.error(f"❌ Erro ao carregar dados de Lead Time: {str(e)}")
            st.info("💡 Verifique se a tabela 'planilhas.main.relacao_de_pedidos_de_compras' existe e possui dados.")
            import traceback
            with st.expander("Detalhes do erro"):
                st.code(traceback.format_exc())
