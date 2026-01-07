"""
Dashboard de Saldo Em Caixa - Análise de saldos bancários consolidados.
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
        return f"{sign}R$ {v/1_000_000:.1f}Mi"
    elif v >= 1_000:
        return f"{sign}R$ {v/1_000:.1f}Mil"
    else:
        return f"{sign}R$ {v:,.0f}".replace(",", ".")

def format_currency_full(value: float) -> str:
    """Formata valores monetários completos com separadores de milhar."""
    if pd.isna(value):
        return "R$ 0,00"
    
    # Formatar com separador de milhar e 2 casas decimais
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

@st.cache_data(ttl=600)
def load_saldos_bancarios_raw() -> pd.DataFrame:
    """Carrega os dados crus da view saldos_bancarios_consolidado no MotherDuck."""
    md_conn = get_md_connection()
    
    sql = """
    SELECT *
    FROM administracao.saldos_bancarios_consolidado
    """
    
    try:
        df = md_conn.run_query(sql)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        return pd.DataFrame()

def prepare_saldos_bancarios(df: pd.DataFrame) -> pd.DataFrame:
    """Prepara o dataset de saldos bancários."""
    df = df.copy()
    
    # Normalizar datas
    date_cols = [col for col in df.columns if 'data' in col.lower() or 'date' in col.lower()]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], dayfirst=True, errors="coerce")
    
    # Normalizar valores monetários
    valor_cols = [col for col in df.columns if 'valor' in col.lower() or 'saldo' in col.lower() or 'valor' in col.lower()]
    for col in valor_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    
    # Renomear colunas para padrão facilitado se necessário
    # Assumindo que o dataframe já tem colunas padronizadas da view, mas vamos garantir nomes
    col_map = {}
    for col in df.columns:
        if 'data' in col.lower() and 'transacao' in col.lower():
            col_map[col] = 'Data'
        elif 'categoria' in col.lower():
            col_map[col] = 'Categoria'
        elif 'banco' in col.lower():
            col_map[col] = 'Banco'
        elif 'valor' in col.lower() and 'clean' not in col.lower() and 'direct' not in col.lower():
            col_map[col] = 'Valor'
            
    if col_map:
        df = df.rename(columns=col_map)
    
    return df

def get_category_type(categoria: str) -> str:
    """Classifica a categoria em grupos macro."""
    cat = str(categoria).lower()
    if 'saldo' in cat:
        if 'investimento' in cat or 'aplicações' in cat or 'cdb' in cat:
             return 'Saldo Investimento'
        return 'Saldo Conta'
    elif 'recebimento' in cat or 'resgate' in cat:
        return 'Entrada'
    elif 'pagamento' in cat or 'aplicação' in cat:
        return 'Saída'
    return 'Outros'

def calculate_kpis(df: pd.DataFrame, start_date: date, end_date: date) -> Dict:
    """Calcula KPIs comparando com período anterior."""
    
    # Converter para datetime para comparação segura
    start_dt = pd.Timestamp(start_date)
    end_dt = pd.Timestamp(end_date)
    
    # Período Atual
    df_curr = df[(df['Data'] >= start_dt) & (df['Data'] <= end_dt)]
    
    # Período Anterior (mesma duração)
    duration = (end_dt - start_dt).days + 1
    prev_end = start_dt - timedelta(days=1)
    prev_start = prev_end - timedelta(days=duration - 1)
    df_prev = df[(df['Data'] >= prev_start) & (df['Data'] <= prev_end)]
    
    kpis = {}
    
    # 1. Saldo Atual (Último dia do período)
    # Procurar categorias de saldo
    cats_saldo = [c for c in df['Categoria'].unique() if 'Saldo Atual' in str(c) or 'Saldo Acumulado' in str(c)]
    
    # Se não tiver Saldo Atual explícito, tentar reconstruir? Melhor usar o que tem.
    # Assumindo que 'Saldo Atual' ou 'Saldo Acumulado' existe na view
    
    def get_last_balance(dframe, categories):
        if dframe.empty: return 0.0
        # Pegar a data máxima disponível no frame
        max_date = dframe['Data'].max()
        # Filtrar essa data e categorias
        val = dframe[
            (dframe['Data'] == max_date) & 
            (dframe['Categoria'].isin(categories))
        ]['Valor'].sum()
        return val

    current_balance = get_last_balance(df_curr, cats_saldo)
    # Para saldo anterior, pegamos o último dia do período anterior
    prev_balance = get_last_balance(df_prev, cats_saldo)
    
    # Se saldo anterior for 0, tenta pegar o saldo inicial do período atual (primeiro dia)
    if prev_balance == 0 and not df_curr.empty:
         min_date = df_curr['Data'].min()
         # Tenta pegar saldo ANTERIOR (categoria 'Saldo Anterior') do primeiro dia
         cats_saldo_ant = [c for c in df['Categoria'].unique() if 'Saldo Anterior' in str(c)]
         prev_balance = df_curr[
            (df_curr['Data'] == min_date) & 
            (df_curr['Categoria'].isin(cats_saldo_ant))
         ]['Valor'].sum()

    kpis['saldo_atual'] = current_balance
    kpis['saldo_atual_delta'] = ((current_balance - prev_balance) / prev_balance * 100) if prev_balance != 0 else 0
    
    # 2. Saldo Investimentos
    cats_inv = [c for c in df['Categoria'].unique() if 'investimento' in str(c).lower() or 'aplica' in str(c).lower() and 'saldo' in str(c).lower()]
    curr_inv = get_last_balance(df_curr, cats_inv)
    prev_inv = get_last_balance(df_prev, cats_inv)
    
    kpis['investimentos'] = curr_inv
    kpis['investimentos_delta'] = ((curr_inv - prev_inv) / prev_inv * 100) if prev_inv != 0 else 0
    
    # 3. Fluxo Líquido (Entradas - Saídas)
    # Entradas: Recebimentos, Resgate
    cats_in = [c for c in df['Categoria'].unique() if 'recebimento' in str(c).lower() or 'resgate' in str(c).lower()]
    # Saídas: Pagamentos, Aplicação
    cats_out = [c for c in df['Categoria'].unique() if ('pagamento' in str(c).lower() or 'aplica' in str(c).lower()) and 'saldo' not in str(c).lower()]
    
    curr_in = df_curr[df_curr['Categoria'].isin(cats_in)]['Valor'].sum()
    curr_out = df_curr[df_curr['Categoria'].isin(cats_out)]['Valor'].sum()
    
    prev_in = df_prev[df_prev['Categoria'].isin(cats_in)]['Valor'].sum()
    prev_out = df_prev[df_prev['Categoria'].isin(cats_out)]['Valor'].sum()
    
    curr_flow = curr_in - curr_out
    prev_flow = prev_in - prev_out
    
    kpis['fluxo_liquido'] = curr_flow
    kpis['fluxo_liquido_delta'] = ((curr_flow - prev_flow) / abs(prev_flow) * 100) if prev_flow != 0 else 0
    
    # 4. Cobertura de Caixa (Dias)
    # Saldo Atual / Média Diária de Pagamentos * 30 (ou projeção mensal)
    # Pagamentos apenas (excluir aplicações se possível, mas muitas vezes 'Pagamentos/Aplicações' estão juntos)
    # Vamos tentar pegar apenas 'Pagamentos' puros ou usar o total de saídas como conservadorismo
    
    total_out = curr_out
    num_days = (end_dt - start_dt).days + 1
    avg_daily_out = total_out / num_days if num_days > 0 else 0
    
    if avg_daily_out > 0:
        coverage_days = current_balance / avg_daily_out
    else:
        coverage_days = 999 # Infinito tecnicamente
        
    kpis['cobertura_dias'] = coverage_days
    
    return kpis

def render_kpi_cards(kpis: Dict):
    """Renderiza os cards de KPI no topo."""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Saldo Atual Total", 
            format_currency_short(kpis['saldo_atual']),
            delta=f"{kpis['saldo_atual_delta']:.1f}%"
        )
        
    with col2:
        st.metric(
            "Saldo Investimentos", 
            format_currency_short(kpis['investimentos']),
            delta=f"{kpis['investimentos_delta']:.1f}%"
        )
    
    with col3:
        st.metric(
            "Fluxo Líquido", 
            format_currency_short(kpis['fluxo_liquido']),
            delta=f"{kpis['fluxo_liquido_delta']:.1f}%",
            delta_color="normal" # Verde se positivo, vermelho se negativo
        )
    
    with col4:
        days = kpis['cobertura_dias']
        val_str = f"{days:.0f} dias" if days < 900 else "> 900 dias"
        st.metric(
            "Cobertura de Caixa", 
            val_str,
            help="Saldo Atual / Média Diária de Saídas"
        )

def render_charts_and_tables(df_input: pd.DataFrame, df_completo: pd.DataFrame = None, start_date: date = None):
    """Renderiza gráficos e tabelas principais."""
    
    # Criar cópia para não alterar o dataframe original
    df = df_input.copy()
    
    st.subheader("📊 Análise de Movimentações")
    
    # Preparar dados para gráfico de barras empilhadas
    # Categorias de fluxo (não saldo)
    cats_flow = [c for c in df['Categoria'].unique() if 'saldo' not in str(c).lower()]
    df_flow = df[df['Categoria'].isin(cats_flow)].copy()
    
    if not df_flow.empty:
        # Agrupar por data e categoria
        df_chart = df_flow.groupby(['Data', 'Categoria'])['Valor'].sum().reset_index()
        
        fig = px.bar(
            df_chart,
            x="Data",
            y="Valor",
            color="Categoria",
            title="Movimentações Diárias por Categoria",
            barmode="group" # Pode ser 'stack' ou 'group'. Group facilita comparar entradas vs saídas
        )
        fig.update_layout(
            xaxis_title="Data", 
            yaxis_title="Valor (R$)",
            yaxis=dict(tickformat=",.0f", tickprefix="R$ "),
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados de movimentação para o gráfico.")
        
    # Tabela Semanal
    st.subheader("📅 Resumo Semanal")
    
    if not df.empty:
        df['Semana'] = df['Data'].dt.to_period('W').apply(lambda r: r.start_time)
        
        # Identificar categorias de saldo atual (usar df_completo se disponível para ter todas as categorias)
        if df_completo is not None:
            cats_saldo = [c for c in df_completo['Categoria'].unique() if 'saldo atual' in str(c).lower()]
        else:
            cats_saldo = [c for c in df['Categoria'].unique() if 'saldo atual' in str(c).lower()]
        
        # Agrupar por semana para obter lista de semanas
        semanas_unicas = sorted(df['Semana'].unique())
        
        # Calcular saldos para cada semana
        saldos_data = []
        for sem in semanas_unicas:
            end_of_week = sem + timedelta(days=6)
            # Pegar o saldo do último dia da semana
            mask = (df['Data'] <= end_of_week) & (df['Categoria'].isin(cats_saldo))
            if mask.any():
                max_date_in_week = df[mask]['Data'].max()
                saldo_atual = df[(df['Data'] == max_date_in_week) & (df['Categoria'].isin(cats_saldo))]['Valor'].sum()
            else:
                saldo_atual = 0
            
            saldos_data.append({
                'Semana': sem,
                'Saldo Atual': saldo_atual
            })
        
        summary = pd.DataFrame(saldos_data)
        
        # Calcular Saldo Anterior (saldo de fechamento da semana anterior)
        # Para a primeira semana, buscar saldo anterior fora do período filtrado se disponível
        saldos_anteriores = []
        for idx, row in summary.iterrows():
            if idx == 0:
                # Primeira semana: buscar saldo anterior fora do período filtrado
                saldo_anterior = 0
                if df_completo is not None and start_date is not None:
                    # Calcular semana anterior
                    semana_anterior = row['Semana'] - timedelta(days=7)
                    end_semana_anterior = semana_anterior + timedelta(days=6)
                    
                    # Buscar saldo no dataframe completo (antes do filtro de data)
                    if end_semana_anterior.date() < start_date:
                        mask_anterior = (df_completo['Data'].dt.date <= end_semana_anterior.date()) & (df_completo['Categoria'].isin(cats_saldo))
                        if mask_anterior.any():
                            max_date_anterior = df_completo[mask_anterior]['Data'].max()
                            saldo_anterior = df_completo[(df_completo['Data'] == max_date_anterior) & (df_completo['Categoria'].isin(cats_saldo))]['Valor'].sum()
                saldos_anteriores.append(saldo_anterior)
            else:
                # Demais semanas: usar saldo atual da semana anterior
                saldos_anteriores.append(summary.iloc[idx - 1]['Saldo Atual'])
        
        summary['Saldo Anterior'] = saldos_anteriores
        
        # Calcular Saldo Semana (diferença entre atual e anterior)
        summary['Saldo Semana'] = summary['Saldo Atual'] - summary['Saldo Anterior']
        
        # Criar coluna de período (início e fim da semana)
        summary['Período'] = summary['Semana'].apply(
            lambda x: f"{x.strftime('%d/%m/%Y')} - {(x + timedelta(days=6)).strftime('%d/%m/%Y')}"
        )
        
        # Reordenar colunas: Período primeiro, depois os saldos
        summary = summary[['Período', 'Saldo Anterior', 'Saldo Atual', 'Saldo Semana']]
        
        # Criar cópia para formatação de exibição
        summary_display = summary.copy()
        summary_display['Saldo Anterior'] = summary_display['Saldo Anterior'].apply(format_currency_full)
        summary_display['Saldo Atual'] = summary_display['Saldo Atual'].apply(format_currency_full)
        summary_display['Saldo Semana'] = summary_display['Saldo Semana'].apply(format_currency_full)
        
        # Configurar tooltips e formatação para a tabela
        column_config = {
            "Período": st.column_config.TextColumn("Período", help="Período da semana (início - fim)"),
            "Saldo Anterior": st.column_config.TextColumn(
                "Saldo Anterior", 
                help="Saldo de fechamento da semana anterior"
            ),
            "Saldo Atual": st.column_config.TextColumn(
                "Saldo Atual", 
                help="Saldo de fechamento da semana atual"
            ),
            "Saldo Semana": st.column_config.TextColumn(
                "Saldo Semana", 
                help="Diferença entre Saldo Atual e Saldo Anterior"
            ),
        }

        st.dataframe(
            summary_display,
            column_config=column_config,
            use_container_width=True,
            hide_index=True
        )

        with st.expander("ℹ️ Entenda os Cálculos do Resumo Semanal"):
            st.markdown("""
            **Como os valores são calculados:**
            
            *   **Saldo Anterior:** Saldo de fechamento da semana anterior (último dia com movimentação da semana anterior).
            *   **Saldo Atual:** Saldo de fechamento da semana atual (último dia com movimentação da semana atual).
            *   **Saldo Semana:** Diferença entre o Saldo Atual e o Saldo Anterior (Saldo Atual - Saldo Anterior). Indica a variação do saldo na semana.
            """)

        # --- DETALHAMENTO SEMANAL ---
        st.subheader("📑 Detalhamento Semanal")
        
        if not df.empty:
            # Preparar dados: agrupar por semana
            df_detalhado = df.copy()
            df_detalhado['Semana'] = df_detalhado['Data'].dt.to_period('W').apply(lambda r: r.start_time)
            
            # Obter semanas únicas ordenadas
            semanas_detalhado = sorted(df_detalhado['Semana'].unique())
            
            # Definir ordem das categorias
            cat_order = [
                "Saldo Anterior", "Pagamentos", "Aplicação", 
                "Recebimentos", "Resgate", "Saldo Atual", 
                "Saldo de Investimentos", "Saldo Acumulado"
            ]
            
            # Encontrar categorias existentes
            existing_cats = df_detalhado['Categoria'].unique()
            sorted_cats = []
            for co in cat_order:
                matches = [c for c in existing_cats if co.lower() in str(c).lower()]
                for m in matches:
                    if m not in sorted_cats:
                        sorted_cats.append(m)
            
            # Adicionar outras categorias não mapeadas
            for c in existing_cats:
                if c not in sorted_cats:
                    sorted_cats.append(c)
            
            # Obter bancos únicos
            bancos = sorted(df_detalhado['Banco'].unique())
            
            # Criar lista de labels para as tabs
            tab_labels = []
            for semana in semanas_detalhado:
                semana_inicio = semana
                semana_fim = semana + timedelta(days=6)
                periodo_str = f"{semana_inicio.strftime('%d/%m')} - {semana_fim.strftime('%d/%m')}"
                tab_labels.append(f"📅 {periodo_str}")
            
            # Criar tabs para cada semana
            if tab_labels:
                tabs_semanas = st.tabs(tab_labels)
                
                for idx, semana in enumerate(semanas_detalhado):
                    with tabs_semanas[idx]:
                        # Preparar dados da semana
                        df_semana = df_detalhado[df_detalhado['Semana'] == semana]
                        
                        # Obter todos os dias da semana que têm dados
                        dias_semana = sorted(df_semana['Data'].dt.date.unique())
                        
                        # Construir tabela: Categorias x (Dias x Bancos)
                        rows_detalhe = []
                        for cat in sorted_cats:
                            row_detalhe = {'Categoria': cat}
                            df_cat = df_semana[df_semana['Categoria'] == cat]
                            
                            # Para cada dia da semana
                            for dia in dias_semana:
                                df_cat_dia = df_cat[df_cat['Data'].dt.date == dia]
                                
                                # Para cada banco
                                for banco in bancos:
                                    df_cat_dia_banco = df_cat_dia[df_cat_dia['Banco'] == banco]
                                    
                                    # Para saldos: pegar valor do dia (último se houver múltiplos)
                                    # Para fluxos: somar todos os valores do dia
                                    is_saldo = 'saldo' in str(cat).lower()
                                    
                                    if not df_cat_dia_banco.empty:
                                        if is_saldo:
                                            # Saldo: último valor do dia (caso haja múltiplos registros)
                                            val = df_cat_dia_banco.iloc[-1]['Valor']
                                        else:
                                            # Fluxo: soma do dia
                                            val = df_cat_dia_banco['Valor'].sum()
                                    else:
                                        val = 0
                                    
                                    # Nome da coluna: "DD/MM (Banco)"
                                    col_name = f"{dia.strftime('%d/%m')} ({banco})"
                                    row_detalhe[col_name] = val
                            
                            rows_detalhe.append(row_detalhe)
                        
                        df_tabela_semana = pd.DataFrame(rows_detalhe)
                        
                        # Formatar valores para exibição
                        df_tabela_display = df_tabela_semana.copy()
                        for col in df_tabela_display.columns:
                            if col != 'Categoria':
                                df_tabela_display[col] = df_tabela_display[col].apply(format_currency_full)
                        
                        # Configurar colunas
                        column_config_detalhe = {
                            "Categoria": st.column_config.TextColumn("Categoria", width="medium")
                        }
                        for col in df_tabela_display.columns:
                            if col != 'Categoria':
                                column_config_detalhe[col] = st.column_config.TextColumn(
                                    col,
                                    help=f"Valor do dia {col}"
                                )
                        
                        # Exibir tabela
                        st.dataframe(
                            df_tabela_display,
                            column_config=column_config_detalhe,
                            use_container_width=True,
                            hide_index=True
                        )

def render_saldo_em_caixa_dashboard(
    show_title: bool = True, show_caption: bool = True
) -> None:
    """Renderiza o dashboard completo de Saldo Em Caixa."""
    
    if show_title:
        st.title("💵 Dashboard de Saldo Em Caixa")
    
    if show_caption:
        st.caption(
            "Análise detalhada dos saldos bancários consolidados."
        )
    
    # Carregar dados
    with st.spinner("Carregando dados..."):
        df_raw = load_saldos_bancarios_raw()
        
    if df_raw.empty:
        st.warning("⚠️ Nenhum dado encontrado.")
        return
    
    # Preparar dados
    df_prep = prepare_saldos_bancarios(df_raw)
    
    if df_prep.empty:
        st.warning("⚠️ Nenhum dado válido encontrado após preparação.")
        return
    
    # --- FILTROS GLOBAIS ---
    with st.sidebar:
        st.header("🔧 Filtros Globais")
        
        # Data
        if df_prep['Data'].notna().any():
            min_date = df_prep['Data'].min().date()
            max_date = df_prep['Data'].max().date()
        else:
            min_date = date.today() - timedelta(days=365)
            max_date = date.today()
        
        # Padrão: Últimos 30 dias se possível
        default_start = max_date - timedelta(days=30)
        if default_start < min_date: default_start = min_date
        
        start_date = st.date_input("Data inicial", value=default_start, min_value=min_date, max_value=max_date, format="DD/MM/YYYY")
        end_date = st.date_input("Data final", value=max_date, min_value=min_date, max_value=max_date, format="DD/MM/YYYY")
        
        st.divider()
        
        # Banco
        bancos = sorted(df_prep['Banco'].dropna().unique())
        selected_bancos = st.multiselect("Banco/Instituição", bancos, default=[], placeholder="Todos")

    # --- PROCESSAMENTO ---
    
    # 1. Calcular KPIs (usando dados globais para comparação temporal correta)
    # Filtro de banco para KPIs deve ser aplicado ANTES
    df_for_kpi = df_prep.copy()
    if selected_bancos:
        df_for_kpi = df_for_kpi[df_for_kpi['Banco'].isin(selected_bancos)]
        
    kpis = calculate_kpis(df_for_kpi, start_date, end_date)
    
    # 2. Filtrar dados para gráficos (Período Selecionado)
    df_filtered = df_for_kpi[
        (df_for_kpi['Data'].dt.date >= start_date) &
        (df_for_kpi['Data'].dt.date <= end_date)
    ]
    
    # --- RENDERIZAÇÃO ---
    
    # KPIs no topo (Prioridade 1)
    render_kpi_cards(kpis)
    
    st.divider()
    
    tab1, tab_receb, tab_pag, tab_inv, tab2 = st.tabs([
        "📊 Visão Geral", 
        "💰 Recebimentos", 
        "💸 Pagamentos", 
        "📈 Investimentos", 
        "📅 Dados Detalhados"
    ])
    
    with tab1:
        st.subheader("Fluxo de Caixa Acumulado")
        # Waterfall simplificado ou Gráfico de Saldo
        # Vamos manter o gráfico de linha de saldo acumulado que já existia pois é útil
        cats_acum = [c for c in df_filtered['Categoria'].unique() if 'saldo acumulado' in str(c).lower()]
        if cats_acum:
            df_acum = df_filtered[df_filtered['Categoria'].isin(cats_acum)].groupby('Data')['Valor'].sum().reset_index()
            fig_acum = px.line(df_acum, x='Data', y='Valor', title='Evolução do Saldo Acumulado', markers=True)
            fig_acum.update_layout(yaxis=dict(tickformat=",.0f", tickprefix="R$ "))
            st.plotly_chart(fig_acum, use_container_width=True)
            
        render_charts_and_tables(df_filtered, df_for_kpi, start_date)
        
    with tab_receb:
        st.subheader("Evolução de Recebimentos")
        cats_receb = [c for c in df_filtered['Categoria'].unique() if 'recebimento' in str(c).lower()]
        if cats_receb:
            # Agrupar por dia para gráfico de linha
            df_receb = df_filtered[df_filtered['Categoria'].isin(cats_receb)].groupby('Data')['Valor'].sum().reset_index()
            if not df_receb.empty:
                fig_receb = px.line(df_receb, x='Data', y='Valor', title='Evolução Diária de Recebimentos', markers=True)
                fig_receb.update_layout(yaxis=dict(tickformat=",.0f", tickprefix="R$ "))
                st.plotly_chart(fig_receb, use_container_width=True)
            else:
                st.info("Sem dados de Recebimentos para o período selecionado.")
        else:
            st.info("Nenhuma categoria de Recebimentos encontrada.")

    with tab_pag:
        st.subheader("Evolução de Pagamentos")
        cats_pag = [c for c in df_filtered['Categoria'].unique() if 'pagamento' in str(c).lower()]
        if cats_pag:
            # Agrupar por dia
            df_pag = df_filtered[df_filtered['Categoria'].isin(cats_pag)].groupby('Data')['Valor'].sum().reset_index()
            if not df_pag.empty:
                fig_pag = px.line(df_pag, x='Data', y='Valor', title='Evolução Diária de Pagamentos', markers=True)
                fig_pag.update_layout(yaxis=dict(tickformat=",.0f", tickprefix="R$ "))
                st.plotly_chart(fig_pag, use_container_width=True)
            else:
                st.info("Sem dados de Pagamentos para o período selecionado.")
        else:
            st.info("Nenhuma categoria de Pagamentos encontrada.")

    with tab_inv:
        st.subheader("Análise de Investimentos")
        
        # 1. Saldo de Investimentos (Linha)
        cats_inv_saldo = [c for c in df_filtered['Categoria'].unique() if 'saldo' in str(c).lower() and ('investimento' in str(c).lower() or 'aplica' in str(c).lower())]
        if cats_inv_saldo:
            df_inv_saldo = df_filtered[df_filtered['Categoria'].isin(cats_inv_saldo)].groupby('Data')['Valor'].sum().reset_index()
            if not df_inv_saldo.empty:
                fig_inv_saldo = px.line(df_inv_saldo, x='Data', y='Valor', title='Evolução do Saldo de Investimentos', markers=True)
                fig_inv_saldo.update_layout(yaxis=dict(tickformat=",.0f", tickprefix="R$ "))
                st.plotly_chart(fig_inv_saldo, use_container_width=True)
        
        # 2. Aplicações e Resgates (Barras ou Linhas)
        st.markdown("### Movimentações de Investimento (Aplicações e Resgates)")
        cats_inv_mov = [c for c in df_filtered['Categoria'].unique() if ('aplica' in str(c).lower() or 'resgate' in str(c).lower()) and 'saldo' not in str(c).lower()]
        
        if cats_inv_mov:
            df_inv_mov = df_filtered[df_filtered['Categoria'].isin(cats_inv_mov)].groupby(['Data', 'Categoria'])['Valor'].sum().reset_index()
            if not df_inv_mov.empty:
                fig_inv_mov = px.line(df_inv_mov, x='Data', y='Valor', color='Categoria', title='Aplicações vs Resgates', markers=True)
                fig_inv_mov.update_layout(yaxis=dict(tickformat=",.0f", tickprefix="R$ "))
                st.plotly_chart(fig_inv_mov, use_container_width=True)
            else:
                st.info("Sem movimentações de investimento no período.")
        else:
            st.info("Categorias de movimentação de investimento não encontradas.")
    
    with tab2:
        st.subheader("📋 Dados em Tabela")
        st.dataframe(
            df_filtered.sort_values(['Data', 'Banco', 'Categoria']).style.format({'Valor': 'R$ {:,.2f}'}),
            use_container_width=True,
            height=500
        )
