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
    """Formata valores de forma abreviada para caber em uma linha (Mi / Mil)."""
    if pd.isna(value) or value == 0:
        return "R$ 0"

    sign = "-" if value < 0 else ""
    v = abs(value)

    if v >= 1_000_000:
        # Ex.: R$ 114.3Mi
        return f"{sign}R$ {v/1_000_000:.1f}Mi"
    elif v >= 1_000:
        # Ex.: R$ 244.3Mil
        return f"{sign}R$ {v/1_000:.1f}Mil"
    else:
        return f"{sign}R$ {v:,.0f}".replace(",", ".")

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


def render_visao_geral(df: pd.DataFrame):
    """Renderiza a aba de Visão Geral (Contas Pagas e a Pagar)."""
    
    # Separar contas pagas e a pagar
    df_pagas = df[df["Status_parcela"] == "PAGA"].copy()
    df_a_pagar = df[df["Status_parcela"] != "PAGA"].copy()
    
    # KPIs Principais
    st.subheader("📊 Indicadores Financeiros")
    
    # Todos os KPIs em uma única linha
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        valor_total = df["Valor_bruto"].sum() if "Valor_bruto" in df.columns else 0.0
        st.metric("Valor Total", format_currency_short(valor_total))
        
    with col2:
        valor_pago = df_pagas["Valor_bruto"].sum() if not df_pagas.empty else 0.0
        st.metric("Total Pago", format_currency_short(valor_pago))
        
    with col3:
        valor_a_pagar = df_a_pagar["Valor_bruto"].sum() if not df_a_pagar.empty else 0.0
        st.metric("Total a Pagar", format_currency_short(valor_a_pagar))
    
    with col4:
        total_titulos = df["Titulo"].nunique() if "Titulo" in df.columns else len(df)
        st.metric("Total de Títulos", f"{total_titulos:,}")
    
    with col5:
        if valor_total > 0:
            percentual_pago = (valor_pago / valor_total) * 100
            st.metric("% Pago", f"{percentual_pago:.1f}%")
        else:
            st.metric("% Pago", "0%")
    
    st.divider()
    
    # Tabela de Títulos a Pagar
    if not df_a_pagar.empty:
        st.subheader("📋 Títulos a Pagar")
        
        # Card com total dos valores
        valor_total_tabela = df_a_pagar["Valor_bruto"].sum() if "Valor_bruto" in df_a_pagar.columns else 0.0
        st.metric(
            "Valor Total Pago e a Pagar",
            format_currency_short(valor_total_tabela),
            help="Somatório total dos valores de todos os títulos listados na tabela abaixo"
        )
        
        # Preparar dados para tabela
        df_tabela_a_pagar = df_a_pagar.copy()
        df_tabela_a_pagar = df_tabela_a_pagar.sort_values("Data_vencimento", ascending=True)
        
        # Calcular dias de atraso
        if "Data_vencimento" in df_tabela_a_pagar.columns:
            hoje = pd.Timestamp.now().date()
            df_tabela_a_pagar["Data_vencimento_dt"] = pd.to_datetime(df_tabela_a_pagar["Data_vencimento"], errors="coerce")
            df_tabela_a_pagar["Dias_atraso_tabela"] = (
                (hoje - df_tabela_a_pagar["Data_vencimento_dt"].dt.date)
                .apply(lambda x: x.days if pd.notna(x) and x.days > 0 else 0)
            )
        
        # Selecionar colunas relevantes
        cols_a_pagar = {
            "Titulo": "Título",
            "Parcela": "Parcela",
            "Empresa": "Empresa",
            "Credor": "Credor",
            "Data_vencimento": "Data Vencimento",
            "Valor_bruto": "Valor Bruto",
            "Dias_atraso_tabela": "Dias de Atraso",
            "Documento": "Documento",
            "Numero_documento": "Nº Documento",
            "Status_parcela": "Status"
        }
        
        available_cols_apagar = [c for c in cols_a_pagar.keys() if c in df_tabela_a_pagar.columns]
        
        if available_cols_apagar:
            df_display_apagar = df_tabela_a_pagar[available_cols_apagar].rename(columns=cols_a_pagar).copy()
            
            # Formatar data
            if "Data Vencimento" in df_display_apagar.columns:
                df_display_apagar["Data Vencimento"] = pd.to_datetime(df_display_apagar["Data Vencimento"], errors="coerce")
                df_display_apagar["Data Vencimento"] = df_display_apagar["Data Vencimento"].dt.strftime("%d/%m/%Y")
            
            # Formatar valor
            if "Valor Bruto" in df_display_apagar.columns:
                df_display_apagar["Valor Bruto"] = df_display_apagar["Valor Bruto"].apply(format_currency_short)
            
            # Formatar dias de atraso
            if "Dias de Atraso" in df_display_apagar.columns:
                df_display_apagar["Dias de Atraso"] = df_display_apagar["Dias de Atraso"].apply(
                    lambda x: f"{int(x)}" if pd.notna(x) and x > 0 else "-"
                )
            
            # Mapear status
            if "Status" in df_display_apagar.columns:
                def mapear_status(status):
                    if status == "ABERTA":
                        return "Aberta"
                    elif status == "PAGA":
                        return "Paga"
                    elif status == "PARCIAL":
                        return "Parcial"
                    else:
                        return str(status)
                df_display_apagar["Status"] = df_display_apagar["Status"].apply(mapear_status)
            
            st.dataframe(
                df_display_apagar,
                hide_index=True,
                use_container_width=True,
                key="tabela_titulos_a_pagar",
                column_config={
                    "Título": st.column_config.NumberColumn(
                        "Título",
                        help="Número do título/documento",
                        format="%d"
                    ),
                    "Parcela": st.column_config.NumberColumn(
                        "Parcela",
                        help="Número da parcela",
                        format="%d"
                    ),
                    "Empresa": st.column_config.TextColumn(
                        "Empresa",
                        help="Nome da empresa responsável pela conta"
                    ),
                    "Credor": st.column_config.TextColumn(
                        "Credor",
                        help="Nome do fornecedor ou credor"
                    ),
                    "Data Vencimento": st.column_config.TextColumn(
                        "Data Vencimento",
                        help="Data em que a conta vence"
                    ),
                    "Valor Bruto": st.column_config.TextColumn(
                        "Valor Bruto",
                        help="Valor bruto da conta a pagar, formatado em mil ou milhões"
                    ),
                    "Dias de Atraso": st.column_config.TextColumn(
                        "Dias de Atraso",
                        help="Quantidade de dias em atraso. Mostra '-' se a conta ainda não venceu ou está em dia"
                    ),
                    "Documento": st.column_config.TextColumn(
                        "Documento",
                        help="Tipo de documento"
                    ),
                    "Nº Documento": st.column_config.TextColumn(
                        "Nº Documento",
                        help="Número do documento"
                    ),
                    "Status": st.column_config.TextColumn(
                        "Status",
                        help="Status atual da parcela: Aberta (não paga), Paga, ou Parcial"
                    )
                }
            )
    
    st.divider()
    
    # Contas Pagas com Atraso - Análise de Credores (movido para cima)
    if "Dias_atraso" in df.columns and "Status_parcela" in df.columns:
        st.subheader("⚠️ Análise de Contas Pagas com Atraso")
        
        # Filtrar apenas contas que foram PAGAS mas tinham atraso
        df_pagas_com_atraso = df[(df["Status_parcela"] == "PAGA") & (df["Dias_atraso"] > 0)].copy()
        
        if not df_pagas_com_atraso.empty:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                total_pagas_atraso = df_pagas_com_atraso["Titulo"].nunique()
                st.metric(
                    "Títulos Pagos com Atraso",
                    f"{total_pagas_atraso:,}",
                    help="Quantidade de títulos que foram pagos, mas tiveram atraso no pagamento"
                )
            
            with col2:
                valor_pago_atraso = df_pagas_com_atraso["Valor_bruto"].sum()
                st.metric(
                    "Valor Pago com Atraso",
                    format_currency_short(valor_pago_atraso),
                    help="Valor total das contas que foram pagas com atraso"
                )
            
            with col3:
                dias_medio_atraso = df_pagas_com_atraso["Dias_atraso"].mean()
                st.metric(
                    "Dias Médio de Atraso",
                    f"{dias_medio_atraso:.1f}",
                    help="Média de dias de atraso das contas que foram pagas com atraso"
                )
            
            # Top credores com contas pagas em atraso
            if "Credor" in df_pagas_com_atraso.columns:
                # Agregar dados por credor
                top_credores_agg = (
                    df_pagas_com_atraso.groupby("Credor")
                    .agg({
                        "Titulo": "nunique",
                        "Valor_bruto": "sum",
                        "Dias_atraso": "mean"
                    })
                    .reset_index()
                    .rename(columns={
                        "Credor": "Credor",
                        "Titulo": "Qtd Títulos",
                        "Valor_bruto": "Valor Total",
                        "Dias_atraso": "Dias Médio"
                    })
                )
                
                # Criar duas colunas para exibir as tabelas lado a lado
                col_tab1, col_tab2 = st.columns(2)
                
                # Tabela 1: Ordenada por Valor
                with col_tab1:
                    st.markdown("#### 🔴 Credores Pagos com Maior **Valor de Atraso**")
                    
                    top_credores_valor = top_credores_agg.sort_values("Valor Total", ascending=False).head(10).copy()
                    top_credores_valor["Valor Pago com Atraso"] = top_credores_valor["Valor Total"].apply(format_currency_short)
                    top_credores_valor["Dias Médio Atraso"] = top_credores_valor["Dias Médio"].apply(lambda x: f"{x:.1f}")
                    
                    display_df_valor = top_credores_valor[["Credor", "Qtd Títulos", "Valor Pago com Atraso", "Dias Médio Atraso"]].copy()
                    
                    st.dataframe(
                        display_df_valor,
                        hide_index=True,
                        use_container_width=True,
                        key="top_credores_pagos_atraso_valor_table",
                        column_config={
                            "Credor": st.column_config.TextColumn(
                                "Credor",
                                help="Nome do fornecedor ou credor que teve contas pagas com atraso"
                            ),
                            "Qtd Títulos": st.column_config.NumberColumn(
                                "Qtd. Títulos",
                                help="Quantidade de títulos/documentos deste credor que foram pagos com atraso",
                                format="%d"
                            ),
                            "Valor Pago com Atraso": st.column_config.TextColumn(
                                "Valor Pago com Atraso",
                                help="Valor total (em R$) das contas deste credor que foram pagas com atraso, formatado em mil ou milhões"
                            ),
                            "Dias Médio Atraso": st.column_config.TextColumn(
                                "Dias Médio Atraso",
                                help="Média de dias de atraso das contas deste credor que foram pagas com atraso. Quanto maior, mais tempo as contas ficaram vencidas antes de serem pagas"
                            )
                        }
                    )
                
                # Tabela 2: Ordenada por Dias de Atraso
                with col_tab2:
                    st.markdown("#### ⏰ Credores Pagos com Maior **Tempo de Atraso**")
                    
                    top_credores_dias = top_credores_agg.sort_values("Dias Médio", ascending=False).head(10).copy()
                    top_credores_dias["Valor Pago com Atraso"] = top_credores_dias["Valor Total"].apply(format_currency_short)
                    top_credores_dias["Dias Médio Atraso"] = top_credores_dias["Dias Médio"].apply(lambda x: f"{x:.1f}")
                    
                    display_df_dias = top_credores_dias[["Credor", "Qtd Títulos", "Valor Pago com Atraso", "Dias Médio Atraso"]].copy()
                    
                    st.dataframe(
                        display_df_dias,
                        hide_index=True,
                        use_container_width=True,
                        key="top_credores_pagos_atraso_dias_table",
                        column_config={
                            "Credor": st.column_config.TextColumn(
                                "Credor",
                                help="Nome do fornecedor ou credor que teve contas pagas com atraso"
                            ),
                            "Qtd Títulos": st.column_config.NumberColumn(
                                "Qtd. Títulos",
                                help="Quantidade de títulos/documentos deste credor que foram pagos com atraso",
                                format="%d"
                            ),
                            "Valor Pago com Atraso": st.column_config.TextColumn(
                                "Valor Pago com Atraso",
                                help="Valor total (em R$) das contas deste credor que foram pagas com atraso, formatado em mil ou milhões"
                            ),
                            "Dias Médio Atraso": st.column_config.TextColumn(
                                "Dias Médio Atraso",
                                help="Média de dias de atraso das contas deste credor que foram pagas com atraso. Quanto maior, mais tempo as contas ficaram vencidas antes de serem pagas"
                            )
                        }
                    )
        else:
            st.info("✅ Nenhuma conta paga com atraso encontrada no período selecionado.")
    
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
            
            # Tabela detalhada de contas a vencer
            st.markdown("#### 📋 Detalhamento das Contas a Vencer")
            
            # Preparar dados para tabela
            df_tabela_vencimentos = df_proximos_vencimentos.copy()
            df_tabela_vencimentos = df_tabela_vencimentos.sort_values("Data_vencimento", ascending=True)
            
            # Selecionar colunas relevantes
            cols_vencimentos = {
                "Titulo": "Título",
                "Parcela": "Parcela",
                "Empresa": "Empresa",
                "Credor": "Credor",
                "Data_vencimento": "Data Vencimento",
                "Valor_bruto": "Valor Bruto",
                "Documento": "Documento",
                "Numero_documento": "Nº Documento"
            }
            
            available_cols_venc = [c for c in cols_vencimentos.keys() if c in df_tabela_vencimentos.columns]
            
            if available_cols_venc:
                df_display_venc = df_tabela_vencimentos[available_cols_venc].rename(columns=cols_vencimentos).copy()
                
                # Formatar data
                if "Data Vencimento" in df_display_venc.columns:
                    df_display_venc["Data Vencimento"] = pd.to_datetime(df_display_venc["Data Vencimento"], errors="coerce")
                    df_display_venc["Data Vencimento"] = df_display_venc["Data Vencimento"].dt.strftime("%d/%m/%Y")
                
                # Formatar valor
                if "Valor Bruto" in df_display_venc.columns:
                    df_display_venc["Valor Bruto"] = df_display_venc["Valor Bruto"].apply(format_currency_short)
                
                st.dataframe(
                    df_display_venc,
                    hide_index=True,
                    use_container_width=True,
                    key="tabela_vencimentos_proximos",
                    column_config={
                        "Título": st.column_config.NumberColumn(
                            "Título",
                            help="Número do título/documento",
                            format="%d"
                        ),
                        "Parcela": st.column_config.NumberColumn(
                            "Parcela",
                            help="Número da parcela",
                            format="%d"
                        ),
                        "Empresa": st.column_config.TextColumn(
                            "Empresa",
                            help="Nome da empresa responsável pela conta"
                        ),
                        "Credor": st.column_config.TextColumn(
                            "Credor",
                            help="Nome do fornecedor ou credor"
                        ),
                        "Data Vencimento": st.column_config.TextColumn(
                            "Data Vencimento",
                            help="Data em que a conta vence (próximos 30 dias)"
                        ),
                        "Valor Bruto": st.column_config.TextColumn(
                            "Valor Bruto",
                            help="Valor bruto da conta a vencer, formatado em mil ou milhões"
                        ),
                        "Documento": st.column_config.TextColumn(
                            "Documento",
                            help="Tipo de documento"
                        ),
                        "Nº Documento": st.column_config.TextColumn(
                            "Nº Documento",
                            help="Número do documento"
                        )
                    }
                )
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
    start_date = st.session_state.get("contas_filtro_inicio")
    end_date = st.session_state.get("contas_filtro_fim")
    
    st.subheader("📅 Evolução Temporal de Pagamentos")
    
    # Análise mensal de pagamentos (respeita data de pagamento)
    if "Mes_pagamento" in df.columns:
        df_pagas = df[df["Status_parcela"] == "PAGA"].copy()
        
        if start_date and end_date and "Data_pagamento" in df_pagas.columns:
            df_pagas = df_pagas[
                (df_pagas["Data_pagamento"].dt.date >= start_date)
                & (df_pagas["Data_pagamento"].dt.date <= end_date)
            ]
        
        if not df_pagas.empty:
        
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
            
            # Gráfico de linha com rótulos (elimina necessidade de tabela abaixo)
            fig_evol = go.Figure()
            
            fig_evol.add_trace(go.Scatter(
                x=evolucao_pagamentos["Mês"],
                y=evolucao_pagamentos["Valor Total"],
                mode='lines+markers+text',
                name="Valor Pago",
                line=dict(color="#002b55", width=3),
                marker=dict(size=8),
                text=evolucao_pagamentos["Valor Total"].apply(format_currency_short),
                textposition="top center",
                textfont=dict(size=12)
            ))
            
            fig_evol.update_layout(
                title="Evolução Mensal de Pagamentos",
                xaxis_title="Mês",
                yaxis_title="Valor (R$)",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                hovermode='x unified',
                yaxis=dict(tickprefix="R$ ")
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
            
            # Valores exibidos diretamente no gráfico (tabela não necessária)
        else:
            st.info("ℹ️ Nenhum dado de pagamento disponível para análise temporal no período filtrado.")
    else:
        st.info("ℹ️ Nenhum dado de pagamento disponível para análise temporal.")
    
    st.divider()
    
    # Análise mensal de vencimentos
    if "Mes_vencimento" in df.columns:
        st.subheader("📅 Contas por Mês de Vencimento")
        
        df_venc = df.copy()
        if start_date and end_date and "Data_vencimento" in df_venc.columns:
            df_venc = df_venc[
                (df_venc["Data_vencimento"].dt.date >= start_date)
                & (df_venc["Data_vencimento"].dt.date <= end_date)
            ]
        
        if not df_venc.empty:
            evolucao_vencimentos = (
                df_venc.groupby("Mes_vencimento")
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
            
            # Gráfico de barras com rótulos (elimina necessidade de tabela abaixo)
            fig_venc = go.Figure()
            
            fig_venc.add_trace(go.Bar(
                x=evolucao_vencimentos["Mês"],
                y=evolucao_vencimentos["Valor Total"],
                name="Valor Total",
                marker_color="#8B0000",
                text=evolucao_vencimentos["Valor Total"].apply(format_currency_short),
                textposition="outside",
                textfont=dict(size=12)
            ))
            
            fig_venc.update_layout(
                title="Valor Total por Mês de Vencimento",
                xaxis_title="Mês",
                yaxis_title="Valor (R$)",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                yaxis=dict(tickprefix="R$ "),
                bargap=0.25
            )
            
            st.plotly_chart(fig_venc, use_container_width=True, key="evol_vencimentos")
        else:
            st.info("ℹ️ Nenhum dado de vencimento disponível no período filtrado.")


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
        
        # Guardar intervalo para outras seções (ex.: análise temporal)
        st.session_state["contas_filtro_inicio"] = start_date
        st.session_state["contas_filtro_fim"] = end_date
        
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
        
        # Filtro de Credor
        selected_credores = []
        if "Credor" in df_prep.columns:
            credores = sorted(df_prep["Credor"].dropna().unique())
            selected_credores = st.multiselect(
                "Credor",
                credores,
                default=[],
                placeholder="Selecione os credores"
            )
        
        # Filtro de Documento
        selected_documentos = []
        if "Documento" in df_prep.columns:
            documentos = sorted(df_prep["Documento"].dropna().unique())
            selected_documentos = st.multiselect(
                "Documento",
                documentos,
                default=[],
                placeholder="Selecione os documentos"
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
    
    # Filtro de Credor
    if selected_credores:
        df_final = df_final[df_final["Credor"].isin(selected_credores)]
    
    # Filtro de Documento
    if selected_documentos:
        df_final = df_final[df_final["Documento"].isin(selected_documentos)]
    
    # --- RENDERIZAÇÃO POR ABAS ---
    
    tab1, tab2 = st.tabs(["📊 Visão Geral", "📅 Análise Temporal"])
    
    with tab1:
        render_visao_geral(df_final)
        
    with tab2:
        render_analise_temporal(df_final)

