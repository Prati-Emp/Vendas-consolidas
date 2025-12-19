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
    "Em espera",
    "Espera - sem análise",
    "Espera - Analisando Credito",
    "Espera - Analise reprovada",
    "Espera - Analise Aprovada",
    "Renegociação",
    "Aprovação de Aditivo",
    "Elaboração de Aditivo",
    "Aditivo Assinado",
    "Prazo de contrato - sem análise",
    "Espera - Demanda mínima",
    "Enviado ao correspondente",
    "Aguardando projeto e alvará",
    "vistoria da engenharia",
    "validação cohapar",
    "aguardando assinatura formulários",
    "inconforme",
    "conformidade aprovada",
    "confecção de contrato caixa",
    "assinatura caixa",
    "recolhimento de custas",
    "Entrada no registro",
    "venda investidor",
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
    # Selecionando colunas garantidas. 'empresa' e 'unidade' podem não existir na tabela base.
    # 'unidade' parece existir na amostra, mas 'empresa' não.
    # Atualizado para buscar 'Para' (Resumido) e 'Situacao' (Detalhado)
    sql = """
    SELECT 
        referencia,
        idrepasse,
        empreendimento,
        Para AS situacao_resumida,
        Situacao AS situacao_detalhada,
        valor_contrato,
        data_cad,
        unidade
    FROM reservas.cv_repasses
    WHERE referencia IS NOT NULL
    """
    try:
        df = md_conn.run_query(sql)
    except Exception:
        # Fallback se 'unidade' também não existir ou erro na query principal
        # Tentamos sem unidade, mas mantendo as duas situações
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
    if "empresa" not in df.columns:
        df["empresa"] = "Não informado"
    else:
        df["empresa"] = df["empresa"].fillna("Não informado")
    
    if "unidade" not in df.columns:
        df["unidade"] = "Não informado"
    else:
        df["unidade"] = df["unidade"].fillna("Não informado")
        
    return df


@st.cache_data(ttl=600)
def load_workflow_raw() -> pd.DataFrame:
    """Carrega os dados crus da tabela cv_repasses_workflow no MotherDuck."""
    md_conn = get_md_connection()
    sql = """
    SELECT 
        referencia,
        situacao,
        tempo,
        data_cad
    FROM reservas.cv_repasses_workflow
    WHERE referencia IS NOT NULL
      AND situacao IS NOT NULL
    """
    try:
        return md_conn.run_query(sql)
    except Exception as e:
        st.error(f"Erro ao carregar cv_repasses_workflow: {e}")
        return pd.DataFrame()


def prepare_repasses(df: pd.DataFrame) -> pd.DataFrame:
    """Prepara o dataset de repasses (Visão Geral)."""
    df = df.copy()
    
    # Normalizar datas
    if "data_cad" in df.columns:
        df["data_cad"] = pd.to_datetime(
            df["data_cad"], dayfirst=True, errors="coerce"
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

    return df


def _render_situacao_chart(df: pd.DataFrame, col_name: str, order_list: Optional[List[str]] = None):
    """Helper para renderizar gráfico e tabela de situação."""
    
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
        situacao_analysis["ordem"] = situacao_analysis["Situação"].apply(
            lambda x: order_list.index(x) if x in order_list else len(order_list)
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


def render_visao_geral(df: pd.DataFrame):
    """Renderiza a aba de Visão Geral (Repasses)."""
    
    # KPIs Principais
    total_repasses = df["referencia"].nunique() if "referencia" in df.columns else len(df)
    valor_total = df["valor_contrato"].sum() if "valor_contrato" in df.columns else 0.0
    valor_medio = df["valor_contrato"].mean() if "valor_contrato" in df.columns else 0.0

    st.subheader("📊 Indicadores de Carteira")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total de Repasses", f"{total_repasses:,}")
        
    with col2:
        st.metric(
            "Valor Total da Carteira",
            f"R$ {valor_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
        
    with col3:
        st.metric(
            "Ticket Médio",
            f"R$ {valor_medio:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )

    st.divider()

    # Análise por Situação (Funil)
    st.subheader("📉 Distribuição de Repasses por Situação")
    
    tab_resumido, tab_detalhado = st.tabs(["Resumido", "Detalhado"])
    
    with tab_resumido:
        if "situacao_resumida" in df.columns:
            _render_situacao_chart(df, "situacao_resumida", STATUS_ORDER)
        else:
            st.warning("Dados de situação resumida não disponíveis.")
            
    with tab_detalhado:
        if "situacao_detalhada" in df.columns:
            _render_situacao_chart(df, "situacao_detalhada")
        else:
            st.warning("Dados de situação detalhada não disponíveis.")

    st.divider()

    # Top Empreendimentos (Tabela Unificada)
    if "empreendimento" in df.columns:
        st.subheader("🏢 Top Empreendimentos (Qtd e Valor)")
        
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
            use_container_width=True
        )


def render_analise_workflow(df_workflow: pd.DataFrame):
    """Renderiza a aba de Análise de Workflow (Tempo)."""
    
    if df_workflow.empty:
        st.warning("Sem dados de workflow para o período selecionado.")
        return

    st.subheader("⏱️ Análise de Tempos (SLA)")
    
    # KPI Geral de Tempo (Considerando apenas tempos > 0 para evitar distorção por registros instantâneos/erros)
    df_workflow_nonzero = df_workflow[df_workflow["tempo"] > 0.001]
    
    if not df_workflow_nonzero.empty:
        tempo_medio_geral = df_workflow_nonzero["tempo"].mean()
    else:
        tempo_medio_geral = 0.0
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Tempo Médio Geral (etapas com espera)", f"{tempo_medio_geral:.1f} dias")

    st.divider()

    # Tempo Médio por Situação
    st.subheader("Tempo Médio por Etapa")
    
    # Calcular contagem total (incluindo zeros) para mostrar volume real
    stats_counts = df_workflow["situacao"].value_counts().reset_index()
    stats_counts.columns = ["situacao", "Ocorrências"]
    
    # Calcular média e mediana apenas para tempos > 0 (SLA real de quem esperou)
    stats_times = (
        df_workflow_nonzero.groupby("situacao")["tempo"]
        .agg(["mean", "median"])
        .reset_index()
        .rename(columns={"mean": "Média (dias)", "median": "Mediana (dias)"})
    )
    
    # Merge para ter tabela completa
    tempo_por_situacao = pd.merge(stats_counts, stats_times, on="situacao", how="left")
    tempo_por_situacao.fillna(0, inplace=True)
    
    # Criar coluna para ordenação baseada no STATUS_ORDER_WORKFLOW (insensível a case)
    status_order_normalized = [s.lower().strip() for s in STATUS_ORDER_WORKFLOW]
    tempo_por_situacao["ordem"] = tempo_por_situacao["situacao"].apply(
        lambda x: status_order_normalized.index(x.lower().strip()) if x.lower().strip() in status_order_normalized else len(status_order_normalized)
    )
    
    # Ordenar pela ordem definida (inverso para gráfico horizontal Plotly)
    tempo_por_situacao = tempo_por_situacao.sort_values("ordem", ascending=False)
    
    # Gráfico Customizado (Igual Visão Geral)
    fig = go.Figure()
    
    # Formatando valores para o texto dentro da barra (tempo médio)
    tempo_por_situacao["Texto Tempo"] = tempo_por_situacao["Média (dias)"].apply(lambda x: f"{x:.1f} dias")
    
    fig.add_trace(go.Bar(
        y=tempo_por_situacao["situacao"],
        x=tempo_por_situacao["Média (dias)"],
        name="Tempo Médio",
        orientation='h',
        text=tempo_por_situacao["Texto Tempo"],
        textposition="auto", # Ajusta automaticamente dentro ou fora da barra
        marker_color="#8B0000", # Vermelho escuro para diferenciar
        textfont=dict(color="white")
    ))
    
    max_tempo = tempo_por_situacao["Média (dias)"].max()
        
    fig.update_layout(
        xaxis_title="Tempo Médio (dias)",
        yaxis_title=None,
        height=max(500, len(tempo_por_situacao) * 40), # Altura dinâmica aumentada para barras mais largas
        margin=dict(r=50),
        bargap=0.15, # Menor gap = barras mais largas
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(
            range=[0, max_tempo * 1.15], # Margem extra para o texto se ficar fora
            showgrid=False
        )
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Tabela (ordenada pela ordem do fluxo para leitura lógica)
    tabela_ordenada = tempo_por_situacao.sort_values("ordem", ascending=True)
    st.dataframe(
        tabela_ordenada[["situacao", "Média (dias)", "Mediana (dias)", "Ocorrências"]].rename(columns={"situacao": "Etapa"}),
        use_container_width=True,
        hide_index=True
    )
    
    st.divider()
    
    # Evolução Temporal dos Tempos
    if "data_cad" in df_workflow.columns:
        st.subheader("Evolução do Tempo Médio (Mensal)")
        df_workflow["mes_ano"] = df_workflow["data_cad"].dt.to_period("M").dt.to_timestamp()
        
        evolucao = (
            df_workflow.groupby("mes_ano")["tempo"]
            .mean()
            .reset_index()
            .rename(columns={"mes_ano": "Mês", "tempo": "Tempo Médio (dias)"})
        )
        
        fig_evol = px.line(
            evolucao,
            x="Mês",
            y="Tempo Médio (dias)",
            markers=True,
            title="Tendência de Tempo Médio de Processamento"
        )
        st.plotly_chart(fig_evol, use_container_width=True)


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
    
    tab1, tab2 = st.tabs(["📊 Visão Geral (Carteira)", "⏱️ Análise de Workflow (Tempo)"])
    
    with tab1:
        render_visao_geral(df_repasses_final)
        
    with tab2:
        render_analise_workflow(df_workflow_final)
