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
    sql = """
    SELECT 
        referencia,
        idrepasse,
        empreendimento,
        Para AS situacao,
        valor_contrato,
        data_cad,
        unidade
    FROM reservas.cv_repasses
    WHERE referencia IS NOT NULL
    """
    try:
        df = md_conn.run_query(sql)
    except Exception:
        # Fallback se 'unidade' também não existir
        sql_fallback = """
        SELECT 
            referencia,
            idrepasse,
            empreendimento,
            Para AS situacao,
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

    # Normalizar situação
    df["situacao"] = df["situacao"].fillna("Outros")
    
    # Criar coluna para ordenação
    df["situacao_ordem"] = df["situacao"].apply(
        lambda x: STATUS_ORDER.index(x) if x in STATUS_ORDER else len(STATUS_ORDER)
    )

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
    
    if "situacao" in df.columns:
        situacao_analysis = (
            df.groupby("situacao")
            .agg({
                "referencia": "nunique",
                "valor_contrato": "sum"
            })
            .reset_index()
            .rename(columns={
                "referencia": "Quantidade",
                "valor_contrato": "Valor Total"
            })
        )
        
        # Ordenação customizada
        situacao_analysis["ordem"] = situacao_analysis["situacao"].apply(
            lambda x: STATUS_ORDER.index(x) if x in STATUS_ORDER else len(STATUS_ORDER)
        )
        
        # Ordenar inverso para gráfico horizontal (topo = primeiro da lista)
        # No Plotly horizontal, o primeiro item aparece embaixo por padrão, então invertemos.
        situacao_analysis = situacao_analysis.sort_values("ordem", ascending=False)
        
        # Formatando valores para o gráfico
        situacao_analysis["Valor Texto"] = situacao_analysis["Valor Total"].apply(format_currency_short)
        
        # Gráfico Horizontal customizado
        fig = go.Figure()
        
        # Barra principal
        fig.add_trace(go.Bar(
            y=situacao_analysis["situacao"],
            x=situacao_analysis["Quantidade"], # Tamanho da barra baseado na quantidade?
            # O usuário pediu: "valor dentro e qtd fora". Mas geralmente o tamanho da barra representa uma métrica.
            # Se a barra representa QUANTIDADE:
            name="Quantidade",
            orientation='h',
            text=situacao_analysis["Valor Texto"], # Valor monetário DENTRO
            textposition="inside",
            insidetextanchor="middle",
            marker_color="#002b55", # Azul escuro corporativo
            textfont=dict(color="white")
        ))
        
        # Adicionar anotações para a Quantidade APÓS a barra (à direita)
        annotations = []
        max_qtd = situacao_analysis["Quantidade"].max()
        
        for idx, row in situacao_analysis.iterrows():
            annotations.append(dict(
                x=row["Quantidade"],
                y=row["situacao"],
                text=f" <b>{row['Quantidade']}</b>", # Espaço antes do número para afastar da barra
                xanchor='left',  # Alinha o texto à esquerda do ponto (começa após a barra)
                yanchor='middle',
                showarrow=False,
                font=dict(color="white", size=14) # Texto branco para tema escuro
            ))
            
        fig.update_layout(
            xaxis_title="Quantidade",
            yaxis_title=None,
            height=400,
            margin=dict(r=50), # Margem direita para os números
            annotations=annotations,
            showlegend=False,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(
                range=[0, max_qtd * 1.15], # Estender eixo X para direita (15% margem)
                showgrid=False # Remover grid vertical para limpar visual
            )
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Tabela Detalhada
        situacao_analysis_table = situacao_analysis.sort_values("ordem", ascending=True).copy()
        situacao_analysis_table["Valor"] = situacao_analysis_table["Valor Total"].apply(
            lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
        
        st.dataframe(
            situacao_analysis_table[["situacao", "Quantidade", "Valor"]].rename(
                columns={"situacao": "Situação"}
            ),
            hide_index=True,
            use_container_width=True
        )

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
    
    # KPI Geral de Tempo
    tempo_medio_geral = df_workflow["tempo"].mean()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Tempo Médio Geral (todas as etapas)", f"{tempo_medio_geral:.1f} dias")

    st.divider()

    # Tempo Médio por Situação
    st.subheader("Tempo Médio por Etapa")
    
    tempo_por_situacao = (
        df_workflow.groupby("situacao")["tempo"]
        .agg(["mean", "count", "median"])
        .reset_index()
        .rename(columns={
            "mean": "Média (dias)",
            "median": "Mediana (dias)",
            "count": "Ocorrências"
        })
    )
    
    # Ordenar por tempo médio decrescente
    tempo_por_situacao = tempo_por_situacao.sort_values("Média (dias)", ascending=False)
    
    # Gráfico
    fig = px.bar(
        tempo_por_situacao.head(15), # Top 15 mais demorados
        x="Média (dias)",
        y="situacao",
        orientation='h',
        title="Top 15 Etapas com Maior Tempo Médio",
        text_auto='.1f',
        color="Média (dias)",
        color_continuous_scale="Reds"
    )
    fig.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig, use_container_width=True)
    
    # Tabela
    st.dataframe(
        tempo_por_situacao.style.format({
            "Média (dias)": "{:.1f}",
            "Mediana (dias)": "{:.1f}"
        }),
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
        
        # Filtro de Empresa
        selected_empresas = []
        if "empresa" in df_repasses_prep.columns:
            empresas = sorted(df_repasses_prep["empresa"].dropna().unique())
            selected_empresas = st.multiselect(
                "Empresa",
                empresas,
                default=empresas if len(empresas) <= 10 else [],
            )

        # Filtro de Unidade
        selected_unidades = []
        if "unidade" in df_repasses_prep.columns:
            unidades = sorted(df_repasses_prep["unidade"].dropna().unique())
            selected_unidades = st.multiselect(
                "Unidade",
                unidades,
                default=unidades if len(unidades) <= 10 else [],
            )

    # --- APLICAR FILTROS ---
    
    # 1. Filtros em Repasses
    if start_date and end_date:
        df_repasses_prep = df_repasses_prep[
            (df_repasses_prep["data_cad"].dt.date >= start_date) &
            (df_repasses_prep["data_cad"].dt.date <= end_date)
        ]
        
    if selected_empresas:
        df_repasses_prep = df_repasses_prep[df_repasses_prep["empresa"].isin(selected_empresas)]
        
    if selected_unidades:
        df_repasses_prep = df_repasses_prep[df_repasses_prep["unidade"].isin(selected_unidades)]
        
    # 2. Filtros em Workflow (Aplicamos Data. Empresa/Unidade não existem na tabela workflow por padrão, 
    # a menos que fizéssemos join. Por enquanto, filtraremos workflow apenas por data para manter simples
    # conforme solicitado "separar as analises", mas idealmente filtraríamos pelos IDs filtrados de repasses)
    
    # Filtrar Workflow pelos IDs que sobraram em Repasses (consistência de filtro)
    ids_validos = df_repasses_prep["referencia"].unique()
    df_workflow_prep = df_workflow_prep[df_workflow_prep["referencia"].isin(ids_validos)]
    
    # --- RENDERIZAÇÃO POR ABAS ---
    
    tab1, tab2 = st.tabs(["📊 Visão Geral (Carteira)", "⏱️ Análise de Workflow (Tempo)"])
    
    with tab1:
        render_visao_geral(df_repasses_prep)
        
    with tab2:
        render_analise_workflow(df_workflow_prep)
