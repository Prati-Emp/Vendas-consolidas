"""
Dashboard de Contas Pagas e a Pagar - Análise financeira de contas.
Foco em fluxo de caixa, pagamentos e contas a pagar.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.utils.md_conn import get_md_connection

def format_currency_short(value: float) -> str:
    """Formata valores monetários de forma abreviada (milhões, mil) padrão PT-BR."""
    if pd.isna(value) or value == 0:
        return "R$ 0,00"
    
    if abs(value) >= 1_000_000:
        return f"R$ {value/1_000_000:.2f} milhões".replace(".", ",")
    elif abs(value) >= 1_000:
        return f"R$ {value/1_000:.1f} mil".replace(".", ",")
    else:
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

@st.cache_data(ttl=600)
def load_contas_pagas_raw() -> pd.DataFrame:
    """Carrega os dados crus da tabela sienge_contas_pagas_e_a_pagar no MotherDuck."""
    md_conn = get_md_connection()
    
    sql = """
    SELECT 
        Titulo,
        Parcela,
        Cod_empresa,
        Empresa,
        Cod_credor,
        Credor,
        Documento,
        Numero_documento,
        Previsao_Financeira,
        Consistencia,
        Data_vencimento,
        Valor_bruto,
        Desconto,
        Valor_Imposto_Retido,
        Valor_liquido,
        Valor_baixa,
        Saldo_em_aberto,
        Valor_Saldo_Corrigido,
        Data_pagamento,
        Data_emissao,
        Indexador,
        Status_parcela,
        Dias_atraso,
        Usuario_cadastrou,
        Data_cadastro,
        Autorizacao,
        Data_Snapshot,
        fonte,
        processado_em
    FROM administracao.sienge_contas_pagas_e_a_pagar
    WHERE Titulo IS NOT NULL
    """
    
    try:
        df = md_conn.run_query(sql)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        return pd.DataFrame()


def prepare_contas_pagas(df: pd.DataFrame) -> pd.DataFrame:
    """Prepara o dataset de contas pagas e a pagar."""
    df = df.copy()
    
    # Normalizar datas
    date_cols = ["Data_vencimento", "Data_pagamento", "Data_emissao", "Data_cadastro", "Data_Snapshot"]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(
                df[col], dayfirst=True, errors="coerce"
            )
    
    # Normalizar valores monetários
    valor_cols = ["Valor_bruto", "Desconto", "Valor_Imposto_Retido", "Valor_liquido", 
                  "Valor_baixa", "Saldo_em_aberto", "Valor_Saldo_Corrigido"]
    for col in valor_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col], errors="coerce"
            ).fillna(0.0)
    
    # Normalizar Status_parcela
    if "Status_parcela" in df.columns:
        df["Status_parcela"] = df["Status_parcela"].fillna("Não informado")
    
    # Normalizar Dias_atraso
    if "Dias_atraso" in df.columns:
        df["Dias_atraso"] = pd.to_numeric(df["Dias_atraso"], errors="coerce").fillna(0)
    
    # Criar coluna de tipo (Paga ou A Pagar)
    if "Status_parcela" in df.columns:
        df["Tipo"] = df["Status_parcela"].apply(
            lambda x: "Paga" if x == "PAGA" else "A Pagar"
        )
    else:
        df["Tipo"] = "Não informado"
    
    # Criar coluna de mês/ano para agregações
    if "Data_vencimento" in df.columns:
        df["Mes_vencimento"] = df["Data_vencimento"].dt.to_period("M").dt.to_timestamp()
        df["Ano_mes_vencimento"] = df["Data_vencimento"].dt.strftime("%Y-%m")
    
    if "Data_pagamento" in df.columns:
        df["Mes_pagamento"] = df["Data_pagamento"].dt.to_period("M").dt.to_timestamp()
        df["Ano_mes_pagamento"] = df["Data_pagamento"].dt.strftime("%Y-%m")
    
    return df


def _render_status_chart(df: pd.DataFrame):
    """Helper para renderizar gráfico e tabela de status."""
    
    status_analysis = (
        df.groupby("Status_parcela")
        .agg({
            "Titulo": "nunique",
            "Valor_bruto": "sum"
        })
        .reset_index()
        .rename(columns={
            "Status_parcela": "Status",
            "Titulo": "Quantidade",
            "Valor_bruto": "Valor Total"
        })
    )
    
    # Ordenar por valor total
    status_analysis = status_analysis.sort_values("Valor Total", ascending=False)
    
    # Formatando valores para o gráfico
    status_analysis["Valor Texto"] = status_analysis["Valor Total"].apply(format_currency_short)
    
    # Gráfico Horizontal customizado
    fig = go.Figure()
    
    # Barra principal
    fig.add_trace(go.Bar(
        y=status_analysis["Status"],
        x=status_analysis["Quantidade"], 
        name="Quantidade",
        orientation='h',
        text=status_analysis["Valor Texto"], 
        textposition="inside",
        insidetextanchor="middle",
        marker_color="#002b55", 
        textfont=dict(color="white")
    ))
    
    # Adicionar anotações
    annotations = []
    max_qtd = status_analysis["Quantidade"].max() if not status_analysis.empty else 0
    
    for idx, row in status_analysis.iterrows():
        annotations.append(dict(
            x=row["Quantidade"],
            y=row["Status"],
            text=f" <b>{row['Quantidade']}</b>", 
            xanchor='left',
            yanchor='middle',
            showarrow=False,
            font=dict(color="white", size=14)
        ))
        
    fig.update_layout(
        xaxis_title="Quantidade de Títulos",
        yaxis_title=None,
        height=max(300, len(status_analysis) * 50),
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
    st.plotly_chart(fig, use_container_width=True, key="chart_status")
    
    # Tabela Detalhada
    status_analysis_table = status_analysis.copy()
    status_analysis_table["Valor"] = status_analysis_table["Valor Total"].apply(format_currency_short)
    
    st.dataframe(
        status_analysis_table[["Status", "Quantidade", "Valor"]],
        hide_index=True,
        use_container_width=True,
        key="table_status"
    )


def render_visao_geral(df: pd.DataFrame):
    """Renderiza a aba de Visão Geral (Contas Pagas e a Pagar)."""
    
    # Separar contas pagas e a pagar
    df_pagas = df[df["Status_parcela"] == "PAGA"].copy()
    df_a_pagar = df[df["Status_parcela"] != "PAGA"].copy()
    
    # KPIs Principais
    st.subheader("📊 Indicadores Financeiros")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        total_titulos = df["Titulo"].nunique() if "Titulo" in df.columns else len(df)
        st.metric("Total de Títulos", f"{total_titulos:,}")
        
    with col2:
        valor_total = df["Valor_bruto"].sum() if "Valor_bruto" in df.columns else 0.0
        st.metric(
            "Valor Total",
            format_currency_short(valor_total)
        )
        
    with col3:
        valor_pago = df_pagas["Valor_bruto"].sum() if not df_pagas.empty else 0.0
        st.metric(
            "Total Pago",
            format_currency_short(valor_pago)
        )
        
    with col4:
        valor_a_pagar = df_a_pagar["Valor_bruto"].sum() if not df_a_pagar.empty else 0.0
        st.metric(
            "Total a Pagar",
            format_currency_short(valor_a_pagar)
        )
    
    with col5:
        if valor_total > 0:
            percentual_pago = (valor_pago / valor_total) * 100
            st.metric(
                "% Pago",
                f"{percentual_pago:.1f}%"
            )
        else:
            st.metric("% Pago", "0%")
    
    st.divider()
    
    # Análise por Status
    st.subheader("📉 Distribuição por Status")
    _render_status_chart(df)
    
    st.divider()
    
    # Análise por Empresa
    if "Empresa" in df.columns:
        st.subheader("🏢 Análise por Empresa")
        
        empresa_analysis = (
            df.groupby("Empresa")
            .agg({
                "Titulo": "nunique",
                "Valor_bruto": "sum"
            })
            .reset_index()
            .rename(columns={
                "Empresa": "Empresa",
                "Titulo": "Quantidade",
                "Valor_bruto": "Valor Total"
            })
        )
        
        empresa_analysis = empresa_analysis.sort_values("Valor Total", ascending=False).head(20)
        
        # Formatar Valor
        empresa_analysis["Valor"] = empresa_analysis["Valor Total"].apply(format_currency_short)
        
        st.dataframe(
            empresa_analysis[["Empresa", "Quantidade", "Valor"]],
            hide_index=True,
            use_container_width=True,
            key="top_empresas_table"
        )
    
    st.divider()
    
    # Análise por Credor
    if "Credor" in df.columns:
        st.subheader("👥 Top Credores")
        
        credor_analysis = (
            df.groupby("Credor")
            .agg({
                "Titulo": "nunique",
                "Valor_bruto": "sum"
            })
            .reset_index()
            .rename(columns={
                "Credor": "Credor",
                "Titulo": "Quantidade",
                "Valor_bruto": "Valor Total"
            })
        )
        
        credor_analysis = credor_analysis.sort_values("Valor Total", ascending=False).head(20)
        
        # Formatar Valor
        credor_analysis["Valor"] = credor_analysis["Valor Total"].apply(format_currency_short)
        
        st.dataframe(
            credor_analysis[["Credor", "Quantidade", "Valor"]],
            hide_index=True,
            use_container_width=True,
            key="top_credores_table"
        )
    
    st.divider()
    
    # Análise de Descontos e Impostos
    if "Desconto" in df.columns or "Valor_Imposto_Retido" in df.columns:
        st.subheader("💸 Análise de Descontos e Impostos")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_descontos = df["Desconto"].sum() if "Desconto" in df.columns else 0.0
            st.metric(
                "Total de Descontos",
                format_currency_short(total_descontos)
            )
        
        with col2:
            total_impostos = df["Valor_Imposto_Retido"].sum() if "Valor_Imposto_Retido" in df.columns else 0.0
            st.metric(
                "Total de Impostos Retidos",
                format_currency_short(total_impostos)
            )
        
        with col3:
            valor_bruto_total = df["Valor_bruto"].sum() if "Valor_bruto" in df.columns else 0.0
            if valor_bruto_total > 0:
                percentual_desconto = (total_descontos / valor_bruto_total) * 100
                st.metric(
                    "% Médio de Desconto",
                    f"{percentual_desconto:.2f}%"
                )
            else:
                st.metric("% Médio de Desconto", "0%")
    
    st.divider()
    
    # Contas em Atraso
    if "Dias_atraso" in df.columns:
        st.subheader("⚠️ Análise de Atrasos")
        
        df_atrasadas = df[df["Dias_atraso"] > 0].copy()
        
        if not df_atrasadas.empty:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total_atrasadas = df_atrasadas["Titulo"].nunique()
                st.metric("Títulos em Atraso", f"{total_atrasadas:,}")
            
            with col2:
                valor_atrasado = df_atrasadas["Valor_bruto"].sum()
                st.metric(
                    "Valor em Atraso",
                    format_currency_short(valor_atrasado)
                )
            
            with col3:
                dias_medio_atraso = df_atrasadas["Dias_atraso"].mean()
                st.metric("Dias Médio de Atraso", f"{dias_medio_atraso:.1f}")
            
            with col4:
                if not df_a_pagar.empty:
                    percentual_atraso = (total_atrasadas / df_a_pagar["Titulo"].nunique()) * 100
                    st.metric("% de Títulos Atrasados", f"{percentual_atraso:.1f}%")
                else:
                    st.metric("% de Títulos Atrasados", "0%")
            
            # Gráfico de distribuição de atrasos
            fig_atraso = px.histogram(
                df_atrasadas,
                x="Dias_atraso",
                nbins=30,
                title="Distribuição de Dias de Atraso",
                labels={"Dias_atraso": "Dias de Atraso", "count": "Quantidade"}
            )
            fig_atraso.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_atraso, use_container_width=True, key="chart_atraso")
            
            # Top títulos em atraso
            if "Credor" in df_atrasadas.columns:
                # Agregar dados por credor
                def get_most_common_status(series):
                    """Retorna o status mais comum ou o primeiro se houver empate"""
                    mode_values = series.mode()
                    if len(mode_values) > 0:
                        return mode_values.iloc[0]
                    return series.iloc[0] if len(series) > 0 else "ABERTA"
                
                top_credores_agg = (
                    df_atrasadas.groupby("Credor")
                    .agg({
                        "Titulo": "nunique",
                        "Valor_bruto": "sum",
                        "Dias_atraso": "mean",
                        "Status_parcela": get_most_common_status
                    })
                    .reset_index()
                    .rename(columns={
                        "Credor": "Credor",
                        "Titulo": "Qtd Títulos",
                        "Valor_bruto": "Valor Total",
                        "Dias_atraso": "Dias Médio",
                        "Status_parcela": "Status"
                    })
                )
                
                # Mapear status para texto mais claro
                def mapear_status(status):
                    if status == "ABERTA":
                        return "Atrasada"
                    elif status == "PAGA":
                        return "Paga"
                    elif status == "PARCIAL":
                        return "Parcial"
                    else:
                        return "Atrasada"
                
                top_credores_agg["Status Parcela"] = top_credores_agg["Status"].apply(mapear_status)
                
                # Criar duas colunas para exibir as tabelas lado a lado
                col1, col2 = st.columns(2)
                
                # Tabela 1: Ordenada por Valor
                with col1:
                    st.subheader("🔴 Credores com Maior Valor Pago em Atraso")
                    
                    top_credores_valor = top_credores_agg.sort_values("Valor Total", ascending=False).head(10).copy()
                    top_credores_valor["Valor em Atraso"] = top_credores_valor["Valor Total"].apply(format_currency_short)
                    top_credores_valor["Dias Médio Atraso"] = top_credores_valor["Dias Médio"].apply(lambda x: f"{x:.1f}")
                    
                    display_df_valor = top_credores_valor[["Credor", "Qtd Títulos", "Valor em Atraso", "Dias Médio Atraso", "Status Parcela"]].copy()
                    
                    st.dataframe(
                        display_df_valor,
                        hide_index=True,
                        use_container_width=True,
                        key="top_credores_atraso_valor_table",
                        column_config={
                            "Credor": st.column_config.TextColumn(
                                "Credor",
                                help="Nome do fornecedor ou credor com contas em atraso"
                            ),
                            "Qtd Títulos": st.column_config.NumberColumn(
                                "Qtd. Títulos",
                                help="Quantidade total de títulos/documentos em atraso deste credor",
                                format="%d"
                            ),
                            "Valor em Atraso": st.column_config.TextColumn(
                                "Valor em Atraso",
                                help="Valor total (em R$) das contas em atraso deste credor, formatado em mil ou milhões"
                            ),
                            "Dias Médio Atraso": st.column_config.TextColumn(
                                "Dias Médio Atraso",
                                help="Média de dias de atraso das contas deste credor. Quanto maior, mais tempo as contas estão vencidas"
                            ),
                            "Status Parcela": st.column_config.TextColumn(
                                "Status",
                                help="Status predominante das parcelas: 'Atrasada' indica contas não pagas, 'Paga' indica que algumas foram pagas, 'Parcial' indica pagamento parcial"
                            )
                        }
                    )
                
                # Tabela 2: Ordenada por Dias de Atraso
                with col2:
                    st.subheader("⏰ Credores com Maior Tempo de Atraso")
                    
                    top_credores_dias = top_credores_agg.sort_values("Dias Médio", ascending=False).head(10).copy()
                    top_credores_dias["Valor em Atraso"] = top_credores_dias["Valor Total"].apply(format_currency_short)
                    top_credores_dias["Dias Médio Atraso"] = top_credores_dias["Dias Médio"].apply(lambda x: f"{x:.1f}")
                    
                    display_df_dias = top_credores_dias[["Credor", "Qtd Títulos", "Valor em Atraso", "Dias Médio Atraso", "Status Parcela"]].copy()
                    
                    st.dataframe(
                        display_df_dias,
                        hide_index=True,
                        use_container_width=True,
                        key="top_credores_atraso_dias_table",
                        column_config={
                            "Credor": st.column_config.TextColumn(
                                "Credor",
                                help="Nome do fornecedor ou credor com contas em atraso"
                            ),
                            "Qtd Títulos": st.column_config.NumberColumn(
                                "Qtd. Títulos",
                                help="Quantidade total de títulos/documentos em atraso deste credor",
                                format="%d"
                            ),
                            "Valor em Atraso": st.column_config.TextColumn(
                                "Valor em Atraso",
                                help="Valor total (em R$) das contas em atraso deste credor, formatado em mil ou milhões"
                            ),
                            "Dias Médio Atraso": st.column_config.TextColumn(
                                "Dias Médio Atraso",
                                help="Média de dias de atraso das contas deste credor. Quanto maior, mais tempo as contas estão vencidas"
                            ),
                            "Status Parcela": st.column_config.TextColumn(
                                "Status",
                                help="Status predominante das parcelas: 'Atrasada' indica contas não pagas, 'Paga' indica que algumas foram pagas, 'Parcial' indica pagamento parcial"
                            )
                        }
                    )
        else:
            st.info("✅ Nenhuma conta em atraso encontrada no período selecionado.")
    
    st.divider()
    
    # Análise de Vencimentos Próximos (próximos 30 dias)
    if "Data_vencimento" in df.columns and not df_a_pagar.empty:
        st.subheader("📅 Contas a Vencer (Próximos 30 dias)")
        
        hoje = pd.Timestamp.now().date()
        proximos_30_dias = hoje + timedelta(days=30)
        
        df_proximos_vencimentos = df_a_pagar[
            (df_a_pagar["Data_vencimento"].dt.date >= hoje) &
            (df_a_pagar["Data_vencimento"].dt.date <= proximos_30_dias)
        ].copy()
        
        if not df_proximos_vencimentos.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                total_proximos = df_proximos_vencimentos["Titulo"].nunique()
                st.metric("Títulos a Vencer", f"{total_proximos:,}")
            
            with col2:
                valor_proximos = df_proximos_vencimentos["Valor_bruto"].sum()
                st.metric(
                    "Valor a Vencer",
                    format_currency_short(valor_proximos)
                )
            
            # Gráfico de vencimentos por dia
            df_proximos_vencimentos["Dia"] = df_proximos_vencimentos["Data_vencimento"].dt.date
            vencimentos_diarios = (
                df_proximos_vencimentos.groupby("Dia")
                .agg({
                    "Titulo": "nunique",
                    "Valor_bruto": "sum"
                })
                .reset_index()
                .rename(columns={
                    "Titulo": "Quantidade",
                    "Valor_bruto": "Valor Total"
                })
            )
            vencimentos_diarios = vencimentos_diarios.sort_values("Dia")
            
            fig_vencimentos = go.Figure()
            fig_vencimentos.add_trace(go.Bar(
                x=vencimentos_diarios["Dia"],
                y=vencimentos_diarios["Valor Total"],
                name="Valor Total",
                marker_color="#8B0000"
            ))
            fig_vencimentos.update_layout(
                title="Valor por Dia de Vencimento (Próximos 30 dias)",
                xaxis_title="Data de Vencimento",
                yaxis_title="Valor (R$)",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_vencimentos, use_container_width=True, key="chart_vencimentos_proximos")
        else:
            st.info("ℹ️ Nenhuma conta a vencer nos próximos 30 dias.")
    
    st.divider()
    
    # Tabela Detalhada
    st.subheader("📋 Detalhamento de Contas")
    
    cols_map = {
        "Titulo": "Título",
        "Parcela": "Parcela",
        "Empresa": "Empresa",
        "Credor": "Credor",
        "Data_vencimento": "Data Vencimento",
        "Data_pagamento": "Data Pagamento",
        "Valor_bruto": "Valor Bruto",
        "Status_parcela": "Status",
        "Dias_atraso": "Dias Atraso",
        "Documento": "Documento",
        "Numero_documento": "Nº Documento"
    }
    
    # Filtrar colunas que existem no dataframe
    available_cols = [c for c in cols_map.keys() if c in df.columns]
    
    if available_cols:
        df_table = df[available_cols].rename(columns=cols_map).copy()
        
        # Formatar datas
        date_cols_display = ["Data Vencimento", "Data Pagamento"]
        for col in date_cols_display:
            if col in df_table.columns:
                df_table[col] = pd.to_datetime(df_table[col], errors="coerce")
                df_table[col] = df_table[col].dt.strftime("%d/%m/%Y")
        
        # Formatar Valor
        if "Valor Bruto" in df_table.columns:
            df_table["Valor Bruto"] = df_table["Valor Bruto"].apply(format_currency_short)
        
        st.dataframe(
            df_table,
            hide_index=True,
            use_container_width=True,
            key="detailed_contas_table"
        )
    else:
        st.info("Colunas detalhadas não disponíveis para exibição.")


def render_analise_temporal(df: pd.DataFrame):
    """Renderiza a aba de Análise Temporal."""
    
    st.subheader("📅 Evolução Temporal de Pagamentos")
    
    # Análise mensal de pagamentos
    if "Mes_pagamento" in df.columns and not df[df["Status_parcela"] == "PAGA"].empty:
        df_pagas = df[df["Status_parcela"] == "PAGA"].copy()
        
        evolucao_pagamentos = (
            df_pagas.groupby("Mes_pagamento")
            .agg({
                "Titulo": "nunique",
                "Valor_bruto": "sum"
            })
            .reset_index()
            .rename(columns={
                "Mes_pagamento": "Mês",
                "Titulo": "Quantidade",
                "Valor_bruto": "Valor Total"
            })
        )
        
        evolucao_pagamentos = evolucao_pagamentos.sort_values("Mês")
        
        # Gráfico de linha
        fig_evol = go.Figure()
        
        fig_evol.add_trace(go.Scatter(
            x=evolucao_pagamentos["Mês"],
            y=evolucao_pagamentos["Valor Total"],
            mode='lines+markers',
            name="Valor Pago",
            line=dict(color="#002b55", width=3),
            marker=dict(size=8)
        ))
        
        fig_evol.update_layout(
            title="Evolução Mensal de Pagamentos",
            xaxis_title="Mês",
            yaxis_title="Valor (R$)",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            hovermode='x unified'
        )
        
        st.plotly_chart(fig_evol, use_container_width=True, key="evol_pagamentos")
        
        # KPIs da evolução
        if len(evolucao_pagamentos) > 1:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                valor_medio_mensal = evolucao_pagamentos["Valor Total"].mean()
                st.metric(
                    "Valor Médio Mensal",
                    format_currency_short(valor_medio_mensal)
                )
            
            with col2:
                maior_mes = evolucao_pagamentos.loc[evolucao_pagamentos["Valor Total"].idxmax(), "Mês"]
                maior_valor = evolucao_pagamentos["Valor Total"].max()
                st.metric(
                    "Maior Mês",
                    f"{maior_mes.strftime('%m/%Y')}",
                    delta=format_currency_short(maior_valor)
                )
            
            with col3:
                menor_mes = evolucao_pagamentos.loc[evolucao_pagamentos["Valor Total"].idxmin(), "Mês"]
                menor_valor = evolucao_pagamentos["Valor Total"].min()
                st.metric(
                    "Menor Mês",
                    f"{menor_mes.strftime('%m/%Y')}",
                    delta=format_currency_short(menor_valor)
                )
        
        # Tabela
        evolucao_pagamentos["Valor"] = evolucao_pagamentos["Valor Total"].apply(format_currency_short)
        
        st.dataframe(
            evolucao_pagamentos[["Mês", "Quantidade", "Valor"]],
            hide_index=True,
            use_container_width=True,
            key="table_evol_pagamentos"
        )
    else:
        st.info("ℹ️ Nenhum dado de pagamento disponível para análise temporal.")
    
    st.divider()
    
    # Análise mensal de vencimentos
    if "Mes_vencimento" in df.columns:
        st.subheader("📅 Contas por Mês de Vencimento")
        
        evolucao_vencimentos = (
            df.groupby("Mes_vencimento")
            .agg({
                "Titulo": "nunique",
                "Valor_bruto": "sum"
            })
            .reset_index()
            .rename(columns={
                "Mes_vencimento": "Mês",
                "Titulo": "Quantidade",
                "Valor_bruto": "Valor Total"
            })
        )
        
        evolucao_vencimentos = evolucao_vencimentos.sort_values("Mês")
        
        # Gráfico de barras
        fig_venc = go.Figure()
        
        fig_venc.add_trace(go.Bar(
            x=evolucao_vencimentos["Mês"],
            y=evolucao_vencimentos["Valor Total"],
            name="Valor Total",
            marker_color="#8B0000"
        ))
        
        fig_venc.update_layout(
            title="Valor Total por Mês de Vencimento",
            xaxis_title="Mês",
            yaxis_title="Valor (R$)",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        
        st.plotly_chart(fig_venc, use_container_width=True, key="evol_vencimentos")
        
        # Tabela
        evolucao_vencimentos["Valor"] = evolucao_vencimentos["Valor Total"].apply(format_currency_short)
        
        st.dataframe(
            evolucao_vencimentos[["Mês", "Quantidade", "Valor"]],
            hide_index=True,
            use_container_width=True,
            key="table_evol_vencimentos"
        )


def render_contas_pagas_dashboard(
    show_title: bool = True, show_caption: bool = True
) -> None:
    """Renderiza o dashboard completo de contas pagas e a pagar."""
    
    if show_title:
        st.title("💰 Dashboard de Contas Pagas e a Pagar")
    
    if show_caption:
        st.caption(
            "Análise detalhada de fluxo de caixa e contas a pagar."
        )
    
    # Carregar dados
    with st.spinner("Carregando dados..."):
        df_raw = load_contas_pagas_raw()
        
    if df_raw.empty:
        st.warning("⚠️ Nenhum dado encontrado.")
        return
    
    # Preparar dados
    df_prep = prepare_contas_pagas(df_raw)
    
    if df_prep.empty:
        st.warning("⚠️ Nenhum dado válido encontrado após preparação.")
        return
    
    # --- FILTROS GLOBAIS ---
    with st.sidebar:
        st.header("🔧 Filtros Globais")
        
        # Calcular data mínima e máxima baseado na Data de Vencimento
        if "Data_vencimento" in df_prep.columns and not df_prep["Data_vencimento"].dropna().empty:
            min_date = df_prep["Data_vencimento"].min().date()
            max_date = df_prep["Data_vencimento"].max().date()
        else:
            min_date = date.today() - timedelta(days=365)
            max_date = date.today()
        
        # Datas padrão solicitadas: início é a menor data e fim é a maior data
        start_date = st.date_input(
            "Data inicial (Vencimento)",
            value=min_date,
            min_value=min_date,
            max_value=max_date,
            format="DD/MM/YYYY"
        )
        
        end_date = st.date_input(
            "Data final (Vencimento)",
            value=max_date,
            min_value=min_date,
            max_value=max_date,
            format="DD/MM/YYYY"
        )
        
        st.divider()
        st.subheader("Filtros Específicos")
        
        # Filtro de Empresa
        selected_empresas = []
        if "Empresa" in df_prep.columns:
            empresas = sorted(df_prep["Empresa"].dropna().unique())
            selected_empresas = st.multiselect(
                "Empresa",
                empresas,
                default=[],
                placeholder="Selecione as empresas"
            )
        
        # Filtro de Título
        selected_titulos = []
        if "Titulo" in df_prep.columns:
            titulos = sorted(df_prep["Titulo"].dropna().unique())
            selected_titulos = st.multiselect(
                "Título",
                titulos,
                default=[],
                placeholder="Selecione os títulos"
            )
        
        # Filtro de Status
        selected_status = []
        if "Status_parcela" in df_prep.columns:
            status_list = sorted(df_prep["Status_parcela"].dropna().unique())
            selected_status = st.multiselect(
                "Status",
                status_list,
                default=[],
                placeholder="Selecione os status"
            )
    
    # --- APLICAR FILTROS ---
    
    df_final = df_prep.copy()
    
    # Filtro de Data (vencimento ou pagamento)
    if start_date and end_date:
        if "Data_vencimento" in df_final.columns:
            df_final = df_final[
                (df_final["Data_vencimento"].dt.date >= start_date) &
                (df_final["Data_vencimento"].dt.date <= end_date)
            ]
        elif "Data_pagamento" in df_final.columns:
            df_final = df_final[
                (df_final["Data_pagamento"].dt.date >= start_date) &
                (df_final["Data_pagamento"].dt.date <= end_date)
            ]
    
    # Filtro de Empresa
    if selected_empresas:
        df_final = df_final[df_final["Empresa"].isin(selected_empresas)]
    
    # Filtro de Título
    if selected_titulos:
        df_final = df_final[df_final["Titulo"].isin(selected_titulos)]
    
    # Filtro de Status
    if selected_status:
        df_final = df_final[df_final["Status_parcela"].isin(selected_status)]
    
    # --- RENDERIZAÇÃO POR ABAS ---
    
    tab1, tab2 = st.tabs(["📊 Visão Geral", "📅 Análise Temporal"])
    
    with tab1:
        render_visao_geral(df_final)
        
    with tab2:
        render_analise_temporal(df_final)

