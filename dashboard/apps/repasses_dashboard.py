"""
Dashboard de Repasses - Análise de repasses imobiliários.
Foco em quantidade, valor e tempo médio por situação.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import unicodedata

from dashboard.utils.md_conn import get_md_connection

# Ordem específica de status de repasse (Funil Lógico)
STATUS_ORDER = [
    "Em Espera",
    "Em Conformidade",
    "Em Assinatura Caixa",
    "Entrada no registro",
    "Contrato Registrado",
    "Repasse Realizado", # Mantendo caso exista
    "Cancelado",
    "Outros",
]

# Ordem específica de workflow (Funil Lógico Workflow)
STATUS_ORDER_WORKFLOW = [
    "Em Espera",
    "Espera - Sem Análise",
    "Espera - Analisando Crédito",
    "Espera - Análise Reprovada",
    "Espera - Análise Aprovada",
    "Renegociação",
    "Aprovação de Aditivo",
    "Elaboração de Aditivo",
    "Em assinatura Aditivo",
    "Aditivo Assinado",
    "Prazo de contrato - sem análise",
    "Prazo de contrato - com análise",
    "Espera - Demanda Mínima",
    "Enviado ao correspondente",
    "Aguardando projeto e Alvará",
    "Vistoria da Engenharia",
    "Validação Cohapar",
    "Aguardando Assinatura Formularios",
    "Análise de Conformidade",
    "Inconforme",
    "Conformidade Aprovada",
    "Confecção de Contrato Caixa",
    "Assinado Caixa",
    "Recolhimento de Custas",
    "Entrada no Registro",
]

# Mapeamento de colunas possíveis para nomes canônicos
COLUMN_ALIASES: Dict[str, List[str]] = {
    "referencia": ["referencia", "ref", "id", "idrepasse"],
    "empreendimento": ["empreendimento", "obra", "projeto", "nome_empreendimento"],
    "empresa": ["empresa", "emp", "enterprise", "enterpriseId"],
    "unidade": ["unidade", "unid", "un", "unidade_obra"],
    "situacao": ["Para", "situacao", "situação", "status", "estado"],
    "valor_contrato": ["valor_contrato", "valor", "valor_total", "vlr_contrato"],
    "data_cad": ["data_cad", "data_cadastro", "dt_cad", "data_criacao"],
}

def format_currency_short(value: float) -> str:
    """Formata valores monetários de forma abreviada (Mi, mil)."""
    if pd.isna(value):
        return "R$ 0"
    
    if value >= 1_000_000:
        return f"R$ {value/1_000_000:.2f} Mi".replace(".", ",")
    elif value >= 1_000:
        return f"R$ {value/1_000:.1f} mil".replace(".", ",")
    else:
        return f"R$ {value:,.0f}".replace(",", ".")

@st.cache_data(ttl=600)
def load_repasses_raw() -> pd.DataFrame:
    """Carrega os dados crus da tabela cv_repasses no MotherDuck."""
    md_conn = get_md_connection()
    # Selecionando colunas garantidas e novas colunas solicitadas
    sql = """
    SELECT 
        referencia,
        idrepasse,
        empreendimento,
        Para AS situacao_resumida,
        Situacao AS situacao_detalhada,
        valor_contrato,
        data_cad,
        unidade,
        idsituacao,
        idreserva,
        idcliente,
        cliente,
        correspondente,
        data_alteracao_status,
        data_venda
    FROM reservas.cv_repasses
    WHERE referencia IS NOT NULL
    """
    try:
        df = md_conn.run_query(sql)
    except Exception:
        # Fallback se colunas opcionais não existirem (tentativa simplificada)
        st.warning("Algumas colunas detalhadas podem não estar disponíveis. Carregando conjunto reduzido.")
        sql_fallback = """
        SELECT 
            referencia,
            idrepasse,
            empreendimento,
            Para AS situacao_resumida,
            Situacao AS situacao_detalhada,
            valor_contrato,
            data_cad
        FROM reservas.cv_repasses
        WHERE referencia IS NOT NULL
        """
        df = md_conn.run_query(sql_fallback)

    # Garantir colunas faltantes para o código não quebrar
    cols_to_ensure = ["empresa", "unidade", "cliente", "correspondente"]
    for col in cols_to_ensure:
        if col not in df.columns:
            df[col] = "Não informado"
        else:
            df[col] = df[col].fillna("Não informado")
            
    return df


@st.cache_data(ttl=600)
def load_workflow_raw() -> pd.DataFrame:
    """Carrega os dados crus da tabela cv_repasses_workflow no MotherDuck."""
    md_conn = get_md_connection()
    # Adicionando Para (situacao_resumida) e renomeando situacao (detalhada)
    sql = """
    SELECT 
        referencia,
        situacao AS situacao_detalhada,
        Para AS situacao_resumida,
        tempo,
        data_cad
    FROM reservas.cv_repasses_workflow
    WHERE referencia IS NOT NULL
    """
    try:
        return md_conn.run_query(sql)
    except Exception as e:
        # Fallback se 'Para' não existir
        sql_fallback = """
        SELECT 
            referencia,
            situacao AS situacao_detalhada,
            tempo,
            data_cad
        FROM reservas.cv_repasses_workflow
        WHERE referencia IS NOT NULL
        """
        return md_conn.run_query(sql_fallback)


def prepare_repasses(df: pd.DataFrame) -> pd.DataFrame:
    """Prepara o dataset de repasses (Visão Geral)."""
    df = df.copy()
    
    # Normalizar datas principais
    date_cols = ["data_cad", "data_venda", "data_alteracao_status"]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(
                df[col], dayfirst=True, errors="coerce"
            )

    # Normalizar valores
    if "valor_contrato" in df.columns:
        df["valor_contrato"] = pd.to_numeric(
            df["valor_contrato"], errors="coerce"
        ).fillna(0.0)

    # Normalizar situação resumida
    if "situacao_resumida" in df.columns:
        df["situacao_resumida"] = df["situacao_resumida"].fillna("Outros")
        
        # Criar coluna para ordenação
        df["situacao_resumida_ordem"] = df["situacao_resumida"].apply(
            lambda x: STATUS_ORDER.index(x) if x in STATUS_ORDER else len(STATUS_ORDER)
        )
        
    # Normalizar situação detalhada
    if "situacao_detalhada" in df.columns:
        df["situacao_detalhada"] = df["situacao_detalhada"].fillna("Outros")

    return df


def prepare_workflow(df: pd.DataFrame) -> pd.DataFrame:
    """Prepara o dataset de workflow (Análise Temporal)."""
    df = df.copy()
    
    # Normalizar datas
    if "data_cad" in df.columns:
        df["data_cad"] = pd.to_datetime(
            df["data_cad"], dayfirst=True, errors="coerce"
        )
        
    # Normalizar tempo (assumindo que o banco traz em MINUTOS, converter para DIAS)
    # Se o valor for muito alto, ajustamos. Ex: 1440 min = 1 dia.
    if "tempo" in df.columns:
        df["tempo"] = pd.to_numeric(df["tempo"], errors="coerce").fillna(0.0)
        df["tempo"] = df["tempo"] / 1440  # Converter minutos para dias
        
    # Normalizar situações
    if "situacao_resumida" in df.columns:
        df["situacao_resumida"] = df["situacao_resumida"].fillna("Outros")
        
    if "situacao_detalhada" in df.columns:
        df["situacao_detalhada"] = df["situacao_detalhada"].fillna("Outros")

    # Filtro para remover 'venda a investidor' e 'cessão' (normalizando para minúsculas para garantir)
    # Ajuste solicitado: carregar todas as situações menos "venda a investidor" e "cessão"
    # Ajuste adicional: remover 'contrato registrado' do workflow também
    
    exclusion_list = ["venda a investidor", "cessão", "cessao", "contrato registrado"]
    
    if "situacao_detalhada" in df.columns:
        # Normaliza a coluna temporariamente para filtro
        mask = ~df["situacao_detalhada"].astype(str).apply(lambda x: normalize_text(x)).isin(exclusion_list)
        df = df[mask]

    return df


def _render_situacao_chart(df: pd.DataFrame, col_name: str, order_list: Optional[List[str]] = None):
    """Helper para renderizar gráfico e tabela de situação (Visão Geral)."""
    
    situacao_analysis = (
        df.groupby(col_name)
        .agg({
            "referencia": "nunique",
            "valor_contrato": "sum"
        })
        .reset_index()
        .rename(columns={
            col_name: "Situação",
            "referencia": "Quantidade",
            "valor_contrato": "Valor Total"
        })
    )
    
    # Ordenação
    if order_list:
        # Normalizar lista de ordem para comparação
        status_order_normalized = [normalize_text(s) for s in order_list]
        
        # Aplicar normalização na coluna de situação para encontrar o índice correto
        situacao_analysis["ordem"] = situacao_analysis["Situação"].apply(
            lambda x: status_order_normalized.index(normalize_text(x)) 
            if normalize_text(x) in status_order_normalized 
            else len(status_order_normalized)
        )
        
        # Ordenar inverso para gráfico horizontal (topo = primeiro da lista)
        situacao_analysis = situacao_analysis.sort_values("ordem", ascending=False)
    else:
        # Se não houver ordem definida, ordenar por Quantidade (crescente para ficar no topo no gráfico horizontal invertido)
        # No Plotly H, o ultimo do dataframe fica no topo.
        situacao_analysis = situacao_analysis.sort_values("Quantidade", ascending=True)
    
    # Formatando valores para o gráfico
    situacao_analysis["Valor Texto"] = situacao_analysis["Valor Total"].apply(format_currency_short)
    
    # Gráfico Horizontal customizado
    fig = go.Figure()
    
    # Barra principal
    fig.add_trace(go.Bar(
        y=situacao_analysis["Situação"],
        x=situacao_analysis["Quantidade"], 
        name="Quantidade",
        orientation='h',
        text=situacao_analysis["Valor Texto"], 
        textposition="inside",
        insidetextanchor="middle",
        marker_color="#002b55", 
        textfont=dict(color="white")
    ))
    
    # Adicionar anotações
    annotations = []
    max_qtd = situacao_analysis["Quantidade"].max() if not situacao_analysis.empty else 0
    
    for idx, row in situacao_analysis.iterrows():
        annotations.append(dict(
            x=row["Quantidade"],
            y=row["Situação"],
            text=f" <b>{row['Quantidade']}</b>", 
            xanchor='left',
            yanchor='middle',
            showarrow=False,
            font=dict(color="white", size=14)
        ))
        
    fig.update_layout(
        xaxis_title="Quantidade",
        yaxis_title=None,
        height=max(400, len(situacao_analysis) * 40), # Dynamic height
        margin=dict(r=50), 
        annotations=annotations,
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(
            range=[0, max_qtd * 1.15], 
            showgrid=False 
        )
    )
    st.plotly_chart(fig, use_container_width=True, key=f"chart_{col_name}")
    
    # Tabela Detalhada
    if order_list:
        # Ordenar crescente para tabela (primeiro da lista no topo)
        # Reutilizando a lógica de ordenação normalizada já aplicada no dataframe situacao_analysis
        situacao_analysis_table = situacao_analysis.sort_values("ordem", ascending=True).copy()
    else:
        # Para tabela, queremos o maior no topo
        situacao_analysis_table = situacao_analysis.sort_values("Quantidade", ascending=False).copy()
        
    situacao_analysis_table["Valor"] = situacao_analysis_table["Valor Total"].apply(
        lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )
    
    st.dataframe(
        situacao_analysis_table[["Situação", "Quantidade", "Valor"]],
        hide_index=True,
        use_container_width=True,
        key=f"table_{col_name}"
    )


def normalize_text(text: str) -> str:
    """Remove acentos e coloca em minúsculas para comparação robusta."""
    if not isinstance(text, str):
        return str(text).lower()
    
    # Normalize unicode characters to decomposed form (NFD)
    text = unicodedata.normalize('NFD', text)
    # Filter out non-spacing mark characters (accents)
    text = "".join(c for c in text if unicodedata.category(c) != 'Mn')
    
    # Normalize whitespace
    text = " ".join(text.split())
    
    # Normalize dashes
    text = text.replace('–', '-').replace('—', '-')
    
    return text.lower().strip()


def _render_workflow_chart(df: pd.DataFrame, col_name: str, order_list: Optional[List[str]] = None, key_suffix: str = ""):
    """Helper para renderizar gráfico e tabela de tempo médio (Workflow)."""
    
    # Filtra apenas tempos válidos para média
    df_workflow_nonzero = df[df["tempo"] > 0.001]
    
    if df_workflow_nonzero.empty:
        st.warning(f"Sem dados válidos de tempo para análise ({key_suffix}).")
        return

    # Calcular contagem total (incluindo zeros) para mostrar volume real
    stats_counts = df[col_name].value_counts().reset_index()
    stats_counts.columns = ["situacao", "Ocorrências"]
    
    # Calcular média e mediana apenas para tempos > 0
    stats_times = (
        df_workflow_nonzero.groupby(col_name)["tempo"]
        .agg(["mean", "median"])
        .reset_index()
        .rename(columns={col_name: "situacao", "mean": "Média (dias)", "median": "Mediana (dias)"})
    )
    
    # Merge para ter tabela completa
    tempo_por_situacao = pd.merge(stats_counts, stats_times, on="situacao", how="left")
    tempo_por_situacao.fillna(0, inplace=True)
    
    # Ordenação
    if order_list:
        # Normalizar lista de ordem para comparação
        status_order_normalized = [normalize_text(s) for s in order_list]
        
        # Aplicar normalização na coluna de situação para encontrar o índice correto
        tempo_por_situacao["ordem"] = tempo_por_situacao["situacao"].apply(
            lambda x: status_order_normalized.index(normalize_text(x)) 
            if normalize_text(x) in status_order_normalized 
            else len(status_order_normalized)
        )
        
        # Ordenar inverso para gráfico horizontal (topo = primeiro da lista)
        tempo_por_situacao = tempo_por_situacao.sort_values("ordem", ascending=False)
    else:
        # Se não tiver ordem, ordenar por tempo médio (crescente para gráfico horizontal invertido)
        tempo_por_situacao = tempo_por_situacao.sort_values("Média (dias)", ascending=True)

    # Gráfico Customizado
    fig = go.Figure()
    
    # Formatando valores para o texto dentro da barra
    tempo_por_situacao["Texto Tempo"] = tempo_por_situacao["Média (dias)"].apply(lambda x: f"{x:.1f} dias")
    
    fig.add_trace(go.Bar(
        y=tempo_por_situacao["situacao"],
        x=tempo_por_situacao["Média (dias)"],
        name="Tempo Médio",
        orientation='h',
        text=tempo_por_situacao["Texto Tempo"],
        textposition="auto",
        marker_color="#8B0000",
        textfont=dict(color="white")
    ))
    
    max_tempo = tempo_por_situacao["Média (dias)"].max()
        
    fig.update_layout(
        xaxis_title="Tempo Médio (dias)",
        yaxis_title=None,
        height=max(500, len(tempo_por_situacao) * 40),
        margin=dict(r=50),
        bargap=0.15,
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(
            range=[0, max_tempo * 1.15],
            showgrid=False
        )
    )
    st.plotly_chart(fig, use_container_width=True, key=f"workflow_chart_{key_suffix}")
    
    # Tabela
    if order_list:
        # Normalizar lista de ordem para comparação
        status_order_normalized = [normalize_text(s) for s in order_list]
        
        # Aplicar normalização na coluna de situação para encontrar o índice correto
        tabela_ordenada = tempo_por_situacao.copy()
        tabela_ordenada["ordem"] = tabela_ordenada["situacao"].apply(
            lambda x: status_order_normalized.index(normalize_text(x)) 
            if normalize_text(x) in status_order_normalized 
            else len(status_order_normalized)
        )
        tabela_ordenada = tabela_ordenada.sort_values("ordem", ascending=True)
    else:
        # Tabela ordenada por tempo médio decrescente (piores primeiro)
        tabela_ordenada = tempo_por_situacao.sort_values("Média (dias)", ascending=False)
        
    st.dataframe(
        tabela_ordenada[["situacao", "Média (dias)", "Mediana (dias)", "Ocorrências"]].rename(columns={"situacao": "Etapa"}),
        use_container_width=True,
        hide_index=True,
        key=f"workflow_table_{key_suffix}",
        column_config={
            "Média (dias)": st.column_config.NumberColumn(
                "Média (dias)",
                format="%.2f",
                help="Média simples dos tempos desta etapa."
            ),
            "Mediana (dias)": st.column_config.NumberColumn(
                "Mediana (dias)",
                help="Representa o tempo padrão: metade dos processos (50%) terminou dentro deste prazo. É uma referência melhor que a Média, pois não é afetada por poucos casos que demoraram muito tempo.",
                format="%.2f"
            )
        }
    )


def render_visao_geral(df: pd.DataFrame):
    """Renderiza a aba de Visão Geral (Repasses)."""
    
    # KPIs Principais
    total_repasses = df["referencia"].nunique() if "referencia" in df.columns else len(df)
    valor_total = df["valor_contrato"].sum() if "valor_contrato" in df.columns else 0.0
    valor_medio = df["valor_contrato"].mean() if "valor_contrato" in df.columns else 0.0

    st.subheader("📊 Indicadores de Carteira")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Total de Repasses", 
            f"{total_repasses:,}",
            help="Quantidade total de processos de repasse na carteira filtrada (independente do status)."
        )
        
    with col2:
        st.metric(
            "Valor Total da Carteira",
            f"R$ {valor_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            help="Soma do valor de contrato de todos os repasses filtrados."
        )
        
    with col3:
        st.metric(
            "Ticket Médio",
            f"R$ {valor_medio:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            help="Valor médio dos contratos de repasse."
        )

    st.divider()

    # Análise por Situação (Funil)
    st.subheader("📉 Distribuição de Repasses por Situação")
    st.caption("Visualização do funil de vendas e distribuição dos contratos por etapa atual.")
    
    tab_resumido, tab_detalhado = st.tabs(["Resumido", "Detalhado"])
    
    with tab_resumido:
        if "situacao_resumida" in df.columns:
            _render_situacao_chart(df, "situacao_resumida", STATUS_ORDER)
        else:
            st.warning("Dados de situação resumida não disponíveis.")
            
    with tab_detalhado:
        if "situacao_detalhada" in df.columns:
            _render_situacao_chart(df, "situacao_detalhada", STATUS_ORDER_WORKFLOW)
        else:
            st.warning("Dados de situação detalhada não disponíveis.")

    st.divider()

    # Top Empreendimentos (Tabela Unificada)
    if "empreendimento" in df.columns:
        st.subheader("🏢 Top Empreendimentos (Qtd e Valor)")
        st.caption("Ranking dos empreendimentos com maior volume financeiro e quantidade de contratos.")
        
        top_empreendimentos = (
            df.groupby("empreendimento")
            .agg({
                "referencia": "nunique",
                "valor_contrato": "sum"
            })
            .reset_index()
            .rename(columns={
                "empreendimento": "Empreendimento",
                "referencia": "Quantidade",
                "valor_contrato": "Valor Total"
            })
        )
        
        # Ordenar por Valor (decrescente) e limitar (ex: top 20 para ver mais detalhes)
        top_empreendimentos = top_empreendimentos.sort_values("Valor Total", ascending=False).head(20)
        
        # Formatar Valor
        top_empreendimentos["Valor"] = top_empreendimentos["Valor Total"].apply(
            lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
        
        st.dataframe(
            top_empreendimentos[["Empreendimento", "Quantidade", "Valor"]],
            hide_index=True,
            use_container_width=True,
            key="top_empreendimentos_table"
        )
        
    st.divider()
    st.subheader("📋 Detalhamento de Repasses")
    
    # Montar tabela detalhada
    cols_map = {
        "empreendimento": "Empreendimento",
        "cliente": "Cliente",
        "valor_contrato": "Valor Contrato",
        "data_venda": "Data Venda",
        "data_cad": "Cadastro Repasse",
        "situacao_detalhada": "Situação",
        "correspondente": "Correspondente",
        "data_alteracao_status": "Última Alteração",
        "idrepasse": "ID Repasse",
        "idreserva": "ID Reserva",
        "idsituacao": "ID Situação"
    }
    
    # Filtrar colunas que existem no dataframe
    available_cols = [c for c in cols_map.keys() if c in df.columns]
    
    if available_cols:
        df_table = df[available_cols].rename(columns=cols_map).copy()
        
        # Formatar datas
        date_cols_display = ["Data Venda", "Cadastro Repasse", "Última Alteração"]
        for col in date_cols_display:
            if col in df_table.columns:
                df_table[col] = df_table[col].dt.strftime("%d/%m/%Y")
        
        # Formatar Valor
        if "Valor Contrato" in df_table.columns:
            df_table["Valor Contrato"] = df_table["Valor Contrato"].apply(
                lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            )
        
        st.dataframe(
            df_table,
            hide_index=True,
            use_container_width=True,
            key="detailed_repasses_table"
        )
    else:
        st.info("Colunas detalhadas não disponíveis para exibição.")


def render_analise_workflow(
    df_workflow_filtered: pd.DataFrame, 
    df_workflow_full: Optional[pd.DataFrame] = None, 
    df_repasses_filtered: Optional[pd.DataFrame] = None,
    df_repasses_full: Optional[pd.DataFrame] = None,
    start_date_filter: date = None, 
    end_date_filter: date = None
):
    """Renderiza a aba de Análise de Workflow (Tempo)."""
    
    st.subheader("⏱️ Análise de Tempos (SLA)")
    
    # Verificar se temos dados para trabalhar
    if (df_workflow_filtered.empty and (df_workflow_full is None or df_workflow_full.empty) and
        (df_repasses_filtered is None or df_repasses_filtered.empty) and
        (df_repasses_full is None or df_repasses_full.empty)):
        st.warning("Sem dados disponíveis para o período selecionado.")
        return
    
    # --- CÁLCULO DE SLA (Data de Registro - Data de Venda) ---
    # Usando a tabela de repasses completa para calcular o SLA
    # Filtrando apenas pela data de registro no intervalo do filtro global
    sla_medio = 0.0
    qtd_considerada = 0
    df_sla_evolucao = pd.DataFrame()
    
    # Usar df_repasses_full (dados completos) para calcular o SLA
    # Similar ao que foi feito na aba "Contratos Registrados"
    df_repasses_para_sla = df_repasses_full if df_repasses_full is not None and not df_repasses_full.empty else df_repasses_filtered
    
    if df_repasses_para_sla is not None and not df_repasses_para_sla.empty:
        # Filtrar apenas contratos registrados
        target_status = "Contrato Registrado"
        df_registrados = pd.DataFrame()
        
        if "situacao_resumida" in df_repasses_para_sla.columns:
            df_registrados = df_repasses_para_sla[df_repasses_para_sla["situacao_resumida"] == target_status].copy()
        elif "situacao_detalhada" in df_repasses_para_sla.columns:
            df_registrados = df_repasses_para_sla[df_repasses_para_sla["situacao_detalhada"] == target_status].copy()
        
        if not df_registrados.empty:
            # Verificar se temos as colunas necessárias
            if "data_alteracao_status" in df_registrados.columns and "data_venda" in df_registrados.columns:
                # Calcular SLA: diferença entre data de registro e data de venda
                df_registrados = df_registrados[
                    df_registrados["data_alteracao_status"].notna() & 
                    df_registrados["data_venda"].notna()
                ].copy()
                
                if not df_registrados.empty:
                    # Calcular diferença em dias
                    df_registrados["sla_dias"] = (
                        df_registrados["data_alteracao_status"] - df_registrados["data_venda"]
                    ).dt.days
                    
                    # Filtrar pelo período selecionado no filtro global (usando data de registro)
                    df_sla_filtrado = df_registrados.copy()
                    if start_date_filter and end_date_filter:
                        df_sla_filtrado = df_sla_filtrado[
                            (df_sla_filtrado["data_alteracao_status"].dt.date >= start_date_filter) &
                            (df_sla_filtrado["data_alteracao_status"].dt.date <= end_date_filter)
                        ]
                    
                    if not df_sla_filtrado.empty:
                        # Remover valores negativos ou muito grandes (possíveis erros de data)
                        df_sla_filtrado = df_sla_filtrado[
                            (df_sla_filtrado["sla_dias"] >= 0) & 
                            (df_sla_filtrado["sla_dias"] <= 3650)  # Máximo 10 anos
                        ]
                        
                        if not df_sla_filtrado.empty:
                            sla_medio = df_sla_filtrado["sla_dias"].mean()
                            qtd_considerada = len(df_sla_filtrado)
                            
                            # Preparar dados para gráfico de evolução
                            df_sla_evolucao = df_sla_filtrado.copy()
                            df_sla_evolucao["data_registro"] = df_sla_evolucao["data_alteracao_status"]

    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            "SLA Médio (Registro - Venda)", 
            f"{sla_medio:.1f} dias",
            help="Tempo médio decorrido entre a data de venda e a data de registro do contrato. Calculado como diferença entre Data de Registro e Data de Venda para contratos registrados no período selecionado."
        )
    
    with col2:
        st.metric(
            "Quantidade Considerada",
            f"{qtd_considerada:,}",
            help="Quantidade de contratos registrados utilizados no cálculo do SLA."
        )

    st.divider()

    # Tempo Médio por Situação (Abas Resumido e Detalhado)
    st.subheader("Tempo Médio por Etapa", help="Quanto tempo, em média, um processo permanece em cada etapa específica.")
    
    # Usamos o filtered para mostrar as etapas que ocorreram no período
    df_workflow = df_workflow_filtered
    
    tab_resumido, tab_detalhado = st.tabs(["Resumido", "Detalhado"])
    
    with tab_resumido:
        if "situacao_resumida" in df_workflow.columns:
            _render_workflow_chart(df_workflow, "situacao_resumida", STATUS_ORDER, key_suffix="resumido")
        else:
            st.warning("Dados de situação resumida não disponíveis para o Workflow.")
            
    with tab_detalhado:
        if "situacao_detalhada" in df_workflow.columns:
            _render_workflow_chart(df_workflow, "situacao_detalhada", STATUS_ORDER_WORKFLOW, key_suffix="detalhado")
        else:
            st.warning("Dados de situação detalhada não disponíveis para o Workflow.")
    
    st.divider()
    
    # Evolução Temporal do SLA
    st.subheader("Evolução do SLA Médio (Mensal)")
    st.caption("Evolução mensal do tempo médio entre data de venda e data de registro dos contratos.")
    
    if not df_sla_evolucao.empty and "data_registro" in df_sla_evolucao.columns:
        df_sla_evolucao["mes_ano"] = df_sla_evolucao["data_registro"].dt.to_period("M").dt.to_timestamp()
        
        evolucao = (
            df_sla_evolucao.groupby("mes_ano")["sla_dias"]
            .mean()
            .reset_index()
            .rename(columns={"mes_ano": "Mês", "sla_dias": "SLA Médio (dias)"})
        )
        
        fig_evol = px.line(
            evolucao,
            x="Mês",
            y="SLA Médio (dias)",
            markers=True,
            title="Evolução do SLA (Data de Registro - Data de Venda)",
            text=evolucao["SLA Médio (dias)"].apply(lambda x: f"{x:.1f}")
        )
        
        fig_evol.update_traces(
            line_color="#0EA5E9", # Azul moderno
            line_width=3,
            marker_size=8,
            marker_color="white",
            marker_line_width=2,
            marker_line_color="#0EA5E9",
            textposition="top center",
            hovertemplate="<b>%{x|%B/%Y}</b><br>SLA Médio: <b>%{y:.1f} dias</b><br>(Registro - Venda)<extra></extra>"
        )
        
        fig_evol.update_layout(
            yaxis_title="Dias", 
            xaxis_title=None,
            hovermode="x unified",
            showlegend=False,
            height=450,
            xaxis=dict(
                tickformat="%b/%Y",
                showgrid=False,
                showline=True,
                linecolor='rgba(255, 255, 255, 0.2)'
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='rgba(128, 128, 128, 0.1)',
                zeroline=False
            ),
            margin=dict(t=50, l=50, r=50, b=50)
        )
        st.plotly_chart(fig_evol, use_container_width=True, key="sla_evolution")
    else:
        st.info("Sem dados suficientes de contratos registrados no período selecionado para gerar o gráfico de evolução do SLA.")



def render_contratos_registrados(
    df_filtered_global: pd.DataFrame,
    df_prep_completo: pd.DataFrame,
    empreendimentos_filter: List[str] = None,
    start_date_global: date = None,
    end_date_global: date = None
):
    """Renderiza a aba de Contratos Registrados com filtros específicos."""
    
    st.subheader("✅ Contratos Registrados")
    st.caption("Visualização dedicada aos contratos finalizados.")
    
    # --- Filtros Opcionais para esta aba ---
    st.markdown("#### Filtro Opcional (Data de Registro)")
    st.caption(
        "**Filtro padrão:** Os contratos são filtrados pela data de cadastro conforme o filtro global selecionado.\n\n"
        "**Filtro opcional:** Ative o filtro abaixo para visualizar todos os títulos registrados no período selecionado, "
        "independente da data de cadastro. Isso permite analisar quantos contratos foram registrados em um período específico."
    )
    
    usar_filtro_registro = st.checkbox(
        "Usar filtro de data de registro (independente da data de cadastro)",
        value=False,
        key="usar_filtro_registro"
    )
    
    # Decidir qual dataframe usar baseado no filtro opcional
    if usar_filtro_registro:
        # Quando o filtro opcional está ativo, usar dados completos (antes do filtro global de data)
        # Aplicar apenas filtros de empreendimento e situação
        df_base = df_prep_completo.copy()
        
        # Aplicar filtro de empreendimento se houver
        if empreendimentos_filter:
            df_base = df_base[df_base["empreendimento"].isin(empreendimentos_filter)]
    else:
        # Quando o filtro opcional está inativo, usar dados já filtrados pelo filtro global
        df_base = df_filtered_global.copy()
        
        # Aplicar filtro de empreendimento se houver (pode já estar aplicado, mas garantindo)
        if empreendimentos_filter:
            df_base = df_base[df_base["empreendimento"].isin(empreendimentos_filter)]
    
    # Filtro de Situação (Fixo: Contrato Registrado)
    target_status = "Contrato Registrado"
    if "situacao_resumida" in df_base.columns:
        df_registrado = df_base[df_base["situacao_resumida"] == target_status]
    elif "situacao_detalhada" in df_base.columns:
        df_registrado = df_base[df_base["situacao_detalhada"] == target_status]
    else:
        df_registrado = pd.DataFrame()
    
    start_date_reg = None
    end_date_reg = None
    
    if usar_filtro_registro:
        col_filtros1, col_filtros2 = st.columns(2)
        
        # Determinar intervalo padrão para o filtro específico baseado em todos os dados
        min_date_esp = date.today()
        max_date_esp = date.today()
        
        if "data_alteracao_status" in df_prep_completo.columns:
            valid_dates = df_prep_completo["data_alteracao_status"].dropna()
            if not valid_dates.empty:
                min_date_esp = valid_dates.min().date()
                max_date_esp = valid_dates.max().date()
                
        default_start_esp = date(max_date_esp.year, 1, 1)

        with col_filtros1:
            start_date_reg = st.date_input(
                "Data Inicial (Registro)",
                value=default_start_esp,
                min_value=min_date_esp,
                max_value=max_date_esp,
                key="start_date_contratos_reg"
            )
            
        with col_filtros2:
            end_date_reg = st.date_input(
                "Data Final (Registro)",
                value=max_date_esp,
                min_value=min_date_esp,
                max_value=max_date_esp,
                key="end_date_contratos_reg"
            )
        
    st.divider()
        
    # Aplicar filtro de Data de Registro se o filtro opcional estiver ativo
    if usar_filtro_registro and "data_alteracao_status" in df_registrado.columns and start_date_reg and end_date_reg:
        df_registrado = df_registrado[
            (df_registrado["data_alteracao_status"].dt.date >= start_date_reg) &
            (df_registrado["data_alteracao_status"].dt.date <= end_date_reg)
        ]

    if df_registrado.empty:
        st.info("Nenhum contrato registrado encontrado para o período e filtros selecionados.")
        return

    # KPIs Específicos
    total_reg = df_registrado["referencia"].nunique()
    valor_total_reg = df_registrado["valor_contrato"].sum()
    valor_medio_reg = df_registrado["valor_contrato"].mean()

    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Total Registrados", 
            f"{total_reg:,}",
            help="Quantidade de contratos registrados no período filtrado."
        )
        
    with col2:
        st.metric(
            "Valor Total (Registrados)",
            f"R$ {valor_total_reg:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            help="Soma do valor de contrato dos itens registrados no período."
        )
        
    with col3:
        st.metric(
            "Ticket Médio",
            f"R$ {valor_medio_reg:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            help="Valor médio dos contratos registrados no período."
        )
    
    st.divider()
    
    # Detalhamento Específico
    st.subheader("📋 Detalhamento dos Contratos Registrados")
    
    cols_map = {
        "empreendimento": "Empreendimento",
        "cliente": "Cliente",
        "valor_contrato": "Valor Contrato",
        "data_venda": "Data Venda",
        "data_alteracao_status": "Data Registro",
        "correspondente": "Correspondente",
        "unidade": "Unidade"
    }
    
    available_cols = [c for c in cols_map.keys() if c in df_registrado.columns]
    
    if available_cols:
        df_table = df_registrado[available_cols].rename(columns=cols_map).copy()
        
        # Formatar datas
        date_cols_display = ["Data Venda", "Data Registro"]
        for col in date_cols_display:
            if col in df_table.columns:
                df_table[col] = df_table[col].dt.strftime("%d/%m/%Y")
        
        # Formatar Valor
        if "Valor Contrato" in df_table.columns:
            df_table["Valor Contrato"] = df_table["Valor Contrato"].apply(
                lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            )
        
        st.dataframe(
            df_table,
            hide_index=True,
            use_container_width=True,
            key="table_contratos_registrados"
        )


def render_repasses_dashboard(
    show_title: bool = True, show_caption: bool = True
) -> None:
    """Renderiza o dashboard completo de repasses com abas separadas."""
    if show_title:
        st.title("💰 Dashboard de Repasses")

    if show_caption:
        st.caption(
            "Análise detalhada de carteira e eficiência operacional."
        )

    # Carregar dados
    with st.spinner("Carregando dados..."):
        df_repasses = load_repasses_raw()
        df_workflow = load_workflow_raw()
        
    # Preparar dados iniciais
    df_repasses_prep = prepare_repasses(df_repasses)
    df_workflow_prep = prepare_workflow(df_workflow)

    if df_repasses_prep.empty and df_workflow_prep.empty:
        st.warning("⚠️ Nenhum dado encontrado.")
        return

    # --- FILTROS GLOBAIS ---
    with st.sidebar:
        st.header("🔧 Filtros Globais")
        
        # Calcular data mínima e máxima considerando ambas as tabelas para pegar a data mais atual
        dates_list = []
        
        if not df_repasses_prep.empty and "data_cad" in df_repasses_prep.columns:
            dates_list.extend(df_repasses_prep["data_cad"].dropna().tolist())
        
        if not df_workflow_prep.empty and "data_cad" in df_workflow_prep.columns:
            dates_list.extend(df_workflow_prep["data_cad"].dropna().tolist())
        
        if dates_list:
            min_date = pd.to_datetime(dates_list).min().date()
            max_date = pd.to_datetime(dates_list).max().date()  # Data mais atual do conjunto de dados
        else:
            min_date = date.today()
            max_date = date.today()
        
        default_start = date(max_date.year, 1, 1)

        start_date = st.date_input(
            "Data inicial",
            value=default_start,
            min_value=min_date,
            max_value=max_date,
        )

        end_date = st.date_input(
            "Data final",
            value=max_date,  # Sempre usa a data mais atual disponível
            min_value=min_date,
            max_value=max_date,
        )
        
        st.divider()
        st.subheader("Filtros da Carteira")
        
        # Filtro de Situação (apenas para Visão Geral)
        selected_situacoes = []
        if "situacao_detalhada" in df_repasses_prep.columns:
            situacoes = sorted(df_repasses_prep["situacao_detalhada"].dropna().unique())
            selected_situacoes = st.multiselect(
                "Situação",
                situacoes,
                default=[],
                placeholder="Selecione as situações"
            )
            
        # Filtro de Empreendimento (apenas para Visão Geral)
        selected_empreendimentos = []
        if "empreendimento" in df_repasses_prep.columns:
            empreendimentos = sorted(df_repasses_prep["empreendimento"].dropna().unique())
            selected_empreendimentos = st.multiselect(
                "Empreendimento",
                empreendimentos,
                default=[],
                placeholder="Selecione os empreendimentos"
            )
        
    # --- APLICAR FILTROS ---
    
    # 1. Filtros Estruturais (Empresa/Unidade) - REMOVIDOS conforme solicitação.
    # Assumimos que o usuário quer ver todos os dados, inclusive órfãos (sem vínculo de empresa).
    
    # 2. Filtro de Data e Específicos para Repasses (Visão Geral - Foco na Venda)
    df_repasses_final = df_repasses_prep.copy()
    
    # Filtro de Data
    if start_date and end_date:
        df_repasses_final = df_repasses_final[
            (df_repasses_final["data_cad"].dt.date >= start_date) &
            (df_repasses_final["data_cad"].dt.date <= end_date)
        ]
        
    # Filtro de Situação
    if selected_situacoes:
        df_repasses_final = df_repasses_final[df_repasses_final["situacao_detalhada"].isin(selected_situacoes)]
        
    # Filtro de Empreendimento
    if selected_empreendimentos:
        df_repasses_final = df_repasses_final[df_repasses_final["empreendimento"].isin(selected_empreendimentos)]
        
    # 3. Filtro de Workflow (Análise Temporal - Foco no Evento)
    # Como removemos os filtros de estrutura, mostramos TODO o workflow, 
    # filtrando apenas pela data do evento. Os filtros de Situação/Empreendimento NÃO se aplicam aqui.
    
    df_workflow_final = df_workflow_prep.copy()
    
    # Filtrar pela DATA do evento de workflow
    if start_date and end_date:
        df_workflow_final = df_workflow_final[
            (df_workflow_final["data_cad"].dt.date >= start_date) &
            (df_workflow_final["data_cad"].dt.date <= end_date)
        ]
    
    # --- RENDERIZAÇÃO POR ABAS ---
    
    tab1, tab2, tab3 = st.tabs(["📊 Visão Geral (Carteira)", "✅ Contratos Registrados", "⏱️ Análise de Workflow (Tempo)"])
    
    with tab1:
        render_visao_geral(df_repasses_final)

    with tab2:
        # Passar df_repasses_final (já filtrado pelos filtros globais) e df_repasses_prep (completo) 
        # para permitir que o filtro opcional seja independente
        render_contratos_registrados(
            df_filtered_global=df_repasses_final,
            df_prep_completo=df_repasses_prep,
            empreendimentos_filter=selected_empreendimentos,
            start_date_global=start_date,
            end_date_global=end_date
        )
        
    with tab3:
        # Passando df de repasses completo para cálculo de SLA (diferença entre data de registro e data de venda)
        # O SLA será calculado apenas para contratos registrados no intervalo do filtro global
        render_analise_workflow(
            df_workflow_filtered=df_workflow_final,
            df_workflow_full=df_workflow_prep,
            df_repasses_filtered=df_repasses_final,
            df_repasses_full=df_repasses_prep,
            start_date_filter=start_date,
            end_date_filter=end_date
        )
