"""
Dashboard Operações - Monitoramento das tarefas do Jira.
Fonte de dados: informacoes_consolidadas.Jira_status_tarefas
"""

import sys
from pathlib import Path
from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Garantir acesso aos módulos utilitários quando importado fora do diretório dashboard
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from utils import display_navigation  # noqa: E402
from utils.md_conn import get_md_connection  # noqa: E402


def _normalize_text(value: str) -> str:
    if not isinstance(value, str):
        return ""
    value = value.strip().lower()
    import unicodedata

    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return " ".join(value.split())


@st.cache_data(ttl=600)
def load_jira_status_data() -> pd.DataFrame:
    """Carrega os dados da view Jira_status_tarefas do MotherDuck."""
    md_conn = get_md_connection()
    query = """
        SELECT
            tipo_item,
            chave,
            resumo,
            responsavel,
            prioridade,
            status,
            resolucao,
            atualizado,
            data_limite,
            projeto_name,
            data_inicio_corrigida,
            data_fim_corrigida,
            data_original_inicio,
            data_original_fim,
            start_date,
            dias_para_conclusao,
            status_tarefas,
            "chamada_Para" as chamada_para,
            indice
        FROM informacoes_consolidadas.Jira_status_tarefas
    """
    return md_conn.run_query(query)


@st.cache_data(ttl=600)
def load_calendar_mapping() -> pd.DataFrame:
    """Carrega subtarefas únicas a partir da própria view Jira_status_tarefas, usando o Indice da tabela de mapeamento."""
    md_conn = get_md_connection()

    df = md_conn.run_query(
        """
        SELECT 
            COALESCE(TRIM("chamada_Para"), '') AS chamada_para,
            MIN(indice) AS indice
        FROM informacoes_consolidadas.Jira_status_tarefas
        WHERE "chamada_Para" IS NOT NULL AND TRIM("chamada_Para") <> ''
          AND indice IS NOT NULL
        GROUP BY "chamada_Para"
        ORDER BY indice
        """
    )

    if df.empty:
        return df.assign(match_norm=[], subtarefa=[])

    df["subtarefa"] = df["chamada_para"]
    df["match_norm"] = df["chamada_para"].map(_normalize_text)
    return df


def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Padroniza tipos e cria colunas derivadas."""
    if df.empty:
        return df

    data = df.copy()

    def _parse_datetime(series: pd.Series) -> pd.Series:
        parsed = pd.to_datetime(series, errors="coerce", dayfirst=True, utc=True)
        return parsed.dt.tz_convert(None)

    date_columns = [
        "atualizado",
        "data_limite",
        "data_inicio_corrigida",
        "data_fim_corrigida",
        "data_original_inicio",
        "data_original_fim",
        "start_date",
    ]
    for col in date_columns:
        data[col] = _parse_datetime(data[col])

    data["responsavel"] = data["responsavel"].fillna("—")
    data["prioridade"] = data["prioridade"].replace("", pd.NA).fillna("Sem prioridade")
    data["status_tarefas"] = data["status_tarefas"].fillna("Em Andamento")
    data["dias_para_conclusao"] = pd.to_numeric(data["dias_para_conclusao"], errors="coerce")
    data["resumo_norm"] = data["resumo"].fillna("").map(_normalize_text)

    data["data_referencia"] = data["data_limite"].combine_first(data["atualizado"])

    hoje = pd.Timestamp.utcnow().tz_localize(None).normalize()
    limite_series = pd.to_datetime(data["data_limite"], errors="coerce")
    data["dias_para_limite"] = (limite_series - hoje).dt.days
    data["esta_em_aberto"] = data["status_tarefas"].isin(["A iniciar", "Em Andamento", "Atrasada"])
    data["esta_atrasada"] = data["status_tarefas"].eq("Atrasada")
    data["critica_proxima"] = data["esta_em_aberto"] & data["dias_para_limite"].between(0, 7, inclusive="both")

    return data


def build_filters(data: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Aplica filtros escolhidos no sidebar e retorna dataframe filtrado e metadados."""
    if data.empty:
        return data, {}

    with st.sidebar:
        st.header("🔍 Filtros")

        min_date = data["data_referencia"].min()
        max_date = data["data_referencia"].max()

        if pd.notna(min_date) and pd.notna(max_date):
            st.caption(
                f"📅 Período disponível: {min_date.strftime('%Y-%m-%d')} — "
                f"{max_date.strftime('%Y-%m-%d')}"
            )
        else:
            st.caption("📅 Período disponível: dados sem data de referência registrada.")

        status_options = sorted(data["status_tarefas"].dropna().unique().tolist())
        status_selected = st.multiselect(
            "Status operacional",
            options=status_options,
            default=status_options,
        )

        projetos = sorted(data["projeto_name"].dropna().unique().tolist())
        projeto_selected = st.multiselect(
            "Projetos",
            options=projetos,
        )

        tipo_item_options = sorted(data["tipo_item"].dropna().unique().tolist())
        # Remover "Delay" da lista de opções
        tipo_item_options = [item for item in tipo_item_options if item != "Delay"]
        tipo_item_selected = st.multiselect(
            "Tipo de item",
            options=tipo_item_options,
        )

        responsaveis = sorted(data["responsavel"].dropna().unique().tolist())
        responsavel_selected = st.multiselect(
            "Responsáveis",
            options=responsaveis,
        )

        prioridades = sorted(data["prioridade"].dropna().unique().tolist())
        prioridade_selected = st.multiselect(
            "Prioridade",
            options=prioridades,
        )

        apenas_abertas = st.checkbox("Mostrar apenas tarefas em aberto", value=True)
        texto_busca = st.text_input("Busca por chave ou resumo").strip()

    filtered = data.copy()

    if status_selected:
        filtered = filtered[filtered["status_tarefas"].isin(status_selected)]

    if projeto_selected:
        filtered = filtered[filtered["projeto_name"].isin(projeto_selected)]

    if tipo_item_selected:
        filtered = filtered[filtered["tipo_item"].isin(tipo_item_selected)]

    if responsavel_selected:
        filtered = filtered[filtered["responsavel"].isin(responsavel_selected)]

    if prioridade_selected:
        filtered = filtered[filtered["prioridade"].isin(prioridade_selected)]

    if apenas_abertas:
        filtered = filtered[filtered["esta_em_aberto"]]

    if texto_busca:
        texto_busca = texto_busca.lower()
        filtered = filtered[
            filtered["chave"].astype(str).str.lower().str.contains(texto_busca, na=False)
            | filtered["resumo"].astype(str).str.lower().str.contains(texto_busca, na=False)
        ]

    if pd.notna(min_date) and pd.notna(max_date):
        periodo_texto = f"{min_date.strftime('%Y-%m-%d')} — {max_date.strftime('%Y-%m-%d')}"
    else:
        periodo_texto = "Dados sem data de referência definida"

    metadata = {
        "periodo_texto": periodo_texto,
        "status": status_selected,
        "projetos": projeto_selected,
        "tipo_item": tipo_item_selected,
        "responsaveis": responsavel_selected,
        "prioridades": prioridade_selected,
        "apenas_abertas": apenas_abertas,
        "busca": texto_busca,
    }

    return filtered, metadata


def render_kpis(df: pd.DataFrame):
    """Exibe indicadores principais."""
    total = int(len(df))
    abertas = int(df["esta_em_aberto"].sum())
    a_iniciar = int((df["status_tarefas"] == "A iniciar").sum())
    em_andamento = int((df["status_tarefas"] == "Em Andamento").sum())
    atrasadas = int(df["esta_atrasada"].sum())
    criticas = int(df["critica_proxima"].sum())

    atraso_pct = f"{(atrasadas / total * 100):.1f}% do total" if total else "0%"
    andamento_pct = f"{(em_andamento / total * 100):.1f}% do total" if total else "0%"
    criticas_pct = f"{(criticas / total * 100):.1f}% do total" if total else "0%"

    col1, col2, col3, col4, col5 = st.columns(5)
    tooltip_monitoradas = (
        "Atividades monitoradas são tarefas com status diferente de 'Finalizada' "
        "e atividades que estão 'A iniciar' (status 'Backlog' no Jira). "
        "Essas são as tarefas que estão sendo acompanhadas no dashboard."
    )
    col1.metric("Tarefas monitoradas", total, help=tooltip_monitoradas)
    col2.metric("A iniciar", a_iniciar, delta=f"{(a_iniciar / total * 100):.1f}% do total" if total else "0%")
    col3.metric("Em andamento", em_andamento, delta=andamento_pct)
    col4.metric("Atrasadas", atrasadas, delta=atraso_pct)
    col5.metric("Próximas do prazo (≤7 dias)", criticas, delta=criticas_pct)


def render_status_section(df: pd.DataFrame):
    """Visualizações gerais de status e prioridades."""
    status_counts = (
        df.groupby("status_tarefas")
        .size()
        .reset_index(name="quantidade")
        .sort_values("quantidade", ascending=False)
    )

    prioridade_counts = (
        df.groupby("prioridade")
        .size()
        .reset_index(name="quantidade")
        .sort_values("quantidade", ascending=True)
    )

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Distribuição por status")
        if status_counts.empty:
            st.info("Sem dados para o período selecionado.")
        else:
            fig_status = px.bar(
                status_counts,
                x="status_tarefas",
                y="quantidade",
                text_auto=True,
                color="status_tarefas",
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig_status.update_layout(showlegend=False, xaxis_title="", yaxis_title="Tarefas")
            st.plotly_chart(fig_status, use_container_width=True)

    with col2:
        st.subheader("Prioridade declarada")
        if prioridade_counts.empty:
            st.info("Sem prioridades registradas.")
        else:
            fig_prioridade = px.bar(
                prioridade_counts,
                y="prioridade",
                x="quantidade",
                text_auto=True,
                orientation="h",
                color="quantidade",
                color_continuous_scale="Blues",
            )
            fig_prioridade.update_layout(showlegend=False, xaxis_title="Tarefas", yaxis_title="")
            st.plotly_chart(fig_prioridade, use_container_width=True)

    st.subheader("Calendário de projetos")
    render_project_calendar(df)


def render_project_calendar(df: pd.DataFrame):
    """Tabela calendário com base em subtarefas mapeadas."""
    mapping = load_calendar_mapping()
    projetos = sorted(df["projeto_name"].dropna().unique().tolist())

    if not projetos:
        st.info("Nenhum projeto disponível para montar o calendário.")
        return

    projeto_sel = st.selectbox("Projeto para calendário", projetos, key="calendar_project")
    df_proj = df[df["projeto_name"] == projeto_sel].copy()

    if df_proj.empty:
        st.warning("Projeto selecionado sem tarefas correspondentes nos filtros atuais.")
        return

    if mapping.empty:
        st.warning("Tabela de mapeamento de subtarefas não encontrada.")
        return

    # Verificar se a coluna chamada_para existe (pode ter variações de case)
    col_chamada = None
    for col in df_proj.columns:
        if col.lower() == "chamada_para":
            col_chamada = col
            break
    
    if col_chamada is None:
        st.warning("Coluna 'chamada_para' não encontrada nos dados. Verifique se a view está atualizada.")
        return

    linhas = []
    # Normalizar chamada_para para matching
    df_proj["chamada_para_norm"] = df_proj[col_chamada].fillna("").map(_normalize_text)

    for _, row in mapping.sort_values("indice").iterrows():
        termo_match = row.get("match_norm") or _normalize_text(row.get("chamada_para", ""))
        if not termo_match:
            continue
        # Fazer match direto pela coluna chamada_para normalizada (match exato)
        mask = df_proj["chamada_para_norm"] == termo_match
        # Se não encontrar match exato, tentar busca flexível como fallback
        if not mask.any():
            mask = df_proj["chamada_para_norm"].str.contains(termo_match, na=False, regex=False)
        if not mask.any():
            continue

        tarefa = df_proj.loc[mask].sort_values("data_limite").iloc[0]
        data_original = tarefa["data_original_fim"]
        if pd.isna(data_original):
            data_original = tarefa["data_original_inicio"]
        if pd.isna(data_original):
            data_original = tarefa["data_limite"]

        data_corrigida = tarefa["data_fim_corrigida"]
        if pd.isna(data_corrigida):
            data_corrigida = tarefa["data_limite"]

        status = "sem_dado"
        if pd.notna(data_corrigida) and pd.notna(data_original):
            status = "adiantado" if data_corrigida <= data_original else "atrasado"

        linhas.append(
            {
                "Subtarefa": row["subtarefa"],
                "Data Original": data_original,
                "Data Corrigida": data_corrigida,
                "status_cor": status,
            }
        )

    if not linhas:
        st.info("Nenhuma subtarefa da tabela de referência encontrada para este projeto.")
        return

    calendario_df = pd.DataFrame(linhas)
    display_df = calendario_df.copy()
    for col in ["Data Original", "Data Corrigida"]:
        display_df[col] = display_df[col].dt.strftime("%d/%m/%Y")
        display_df[col] = display_df[col].fillna("—")

    status_series = calendario_df["status_cor"]

    def highlight(row):
        idx = row.name
        base_styles = [""] * len(row)
        status_row = status_series.iloc[idx]
        if status_row == "adiantado":
            base_styles[1] = "background-color:#065f46;color:white;font-weight:bold"
            base_styles[2] = "background-color:#065f46;color:white;font-weight:bold"
        elif status_row == "atrasado":
            base_styles[1] = "background-color:#7f1d1d;color:white;font-weight:bold"
            base_styles[2] = "background-color:#7f1d1d;color:white;font-weight:bold"
        return base_styles

    st.dataframe(
        display_df[["Subtarefa", "Data Original", "Data Corrigida"]].style.apply(highlight, axis=1),
        use_container_width=True,
        hide_index=True,
    )
    st.caption("Data Original = primeira previsão | Verde = dentro do prazo | Vermelho = replanejado após a data original")


def render_responsavel_section(df: pd.DataFrame):
    """Mostra desempenho e carga por responsável."""
    st.subheader("Responsáveis monitorados")

    # Filtrar apenas tarefas "Em Andamento" para calcular "no_prazo"
    df_em_andamento = df[df["status_tarefas"] == "Em Andamento"].copy()
    
    # Garantir que responsáveis vazios ou "—" sejam tratados como "Sem responsável"
    df["responsavel"] = df["responsavel"].replace("—", "Sem responsável")
    df.loc[
        (df["responsavel"].isna()) | (df["responsavel"].str.strip() == ""),
        "responsavel"
    ] = "Sem responsável"
    
    df_em_andamento["responsavel"] = df_em_andamento["responsavel"].replace("—", "Sem responsável")
    df_em_andamento.loc[
        (df_em_andamento["responsavel"].isna()) | (df_em_andamento["responsavel"].str.strip() == ""),
        "responsavel"
    ] = "Sem responsável"
    
    resumo = (
        df.groupby("responsavel")
        .agg(
            tarefas=("chave", "count"),
            atrasadas=("esta_atrasada", "sum"),  # Todas as tarefas atrasadas (status "Atrasada")
            proximas=("critica_proxima", "sum"),
        )
        .reset_index()
    )
    
    # Calcular "no_prazo" apenas para tarefas "Em Andamento" que não estão atrasadas
    resumo_em_andamento = (
        df_em_andamento.groupby("responsavel")
        .agg(
            em_andamento_total=("chave", "count"),
        )
        .reset_index()
    )
    # "no_prazo" = todas as tarefas "Em Andamento" (pois quando atrasam, mudam para status "Atrasada")
    resumo_em_andamento["no_prazo"] = resumo_em_andamento["em_andamento_total"]
    
    # Mesclar com o resumo principal
    resumo = resumo.merge(
        resumo_em_andamento[["responsavel", "no_prazo"]],
        on="responsavel",
        how="left"
    )
    resumo["no_prazo"] = resumo["no_prazo"].fillna(0).astype(int)
    
    # Filtrar apenas responsáveis que tenham tarefas "Em Andamento" ou "Atrasada" (atividades atribuídas)
    # Ou seja, no_prazo + atrasadas > 0
    resumo["total_atividades_atribuidas"] = resumo["no_prazo"] + resumo["atrasadas"]
    resumo_filtrado = resumo[resumo["total_atividades_atribuidas"] > 0].copy()
    
    # Ordenar por total de tarefas e mostrar TODOS os responsáveis com atividades atribuídas
    resumo_ordenado = resumo_filtrado.sort_values("tarefas", ascending=False)

    if resumo_ordenado.empty:
        st.info("Não há responsáveis com tarefas no filtro atual.")
        return

    chart_data = resumo_ordenado.copy()
    # Calcular total para o gráfico: no_prazo (Em Andamento) + atrasadas (status "Atrasada")
    chart_data["total_grafico"] = chart_data["no_prazo"] + chart_data["atrasadas"]
    max_total = max(chart_data["total_grafico"].max(), 1)

    # Criar gráfico de barras empilhadas
    fig = go.Figure()

    # Barra de Atrasadas (Vermelho) - tarefas com status "Atrasada"
    fig.add_trace(go.Bar(
        name="Atrasadas",
        y=resumo_ordenado["responsavel"],
        x=resumo_ordenado["atrasadas"],
        orientation="h",
        marker_color="#dc2626",  # Vermelho
        text=resumo_ordenado["atrasadas"].apply(lambda x: str(x) if x > 0 else ""), # Só mostra número se > 0
        textposition="auto",
        insidetextanchor="middle",
        textfont=dict(color="white")
    ))

    # Barra No Prazo (Azul Escuro) - tarefas "Em Andamento" (que não estão atrasadas)
    fig.add_trace(go.Bar(
        name="No prazo",
        y=resumo_ordenado["responsavel"],
        x=resumo_ordenado["no_prazo"],
        orientation="h",
        marker_color="#1e3a8a",  # Azul escuro
        text=resumo_ordenado["no_prazo"].apply(lambda x: str(x) if x > 0 else ""),
        textposition="auto",
        insidetextanchor="middle",
        textfont=dict(color="white")
    ))

    # Adicionar totais ao lado direito das barras
    for _, row in chart_data.iterrows():
        total_grafico = row["no_prazo"] + row["atrasadas"]
        fig.add_annotation(
            x=total_grafico + max_total * 0.02,
            y=row["responsavel"],
            text=str(total_grafico),
            xanchor="left",
            yanchor="middle",
            showarrow=False,
            xshift=5,
        )

    # Ajustar altura do gráfico baseado no número de responsáveis
    num_responsaveis = len(resumo_ordenado)
    altura_grafico = max(400, num_responsaveis * 40)  # Mínimo 400px, 40px por responsável
    
    fig.update_layout(
        barmode="stack",
        yaxis=dict(
            title=None,  # Remove título do eixo Y conforme solicitado
            autorange="reversed",  # Maior no topo
        ),
        xaxis=dict(visible=False, range=[0, max_total * 1.15]),  # Remove eixo X e garante espaço para o total
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(r=50, l=0),
        height=altura_grafico
    )

    st.plotly_chart(fig, use_container_width=True)

    # Preparar dados para exibição na tabela (aplicar o mesmo filtro do gráfico)
    df_tabela = chart_data[["responsavel", "tarefas", "atrasadas", "no_prazo", "proximas"]].copy()
    df_tabela["total_grafico"] = df_tabela["no_prazo"] + df_tabela["atrasadas"]
    df_tabela["atraso_pct"] = (
        (df_tabela["atrasadas"] / df_tabela["total_grafico"])
        .fillna(0)
        .map(lambda v: f"{v:.0%}" if v > 0 else "0%")
    )
    
    # A tabela já está filtrada porque usa chart_data que vem de resumo_ordenado (já filtrado)
    st.dataframe(
        df_tabela[["responsavel", "tarefas", "atrasadas", "no_prazo", "proximas", "atraso_pct"]],
        hide_index=True,
        use_container_width=True,
    )


def render_alerts(df: pd.DataFrame):
    """Lista tarefas críticas (atrasadas ou próximas do prazo)."""
    criticas = df[df["esta_atrasada"] | df["critica_proxima"]].copy()
    criticas = criticas.sort_values(
        by=["esta_atrasada", "dias_para_limite", "data_limite"], ascending=[False, True, True]
    )

    st.subheader("⚠️ Tarefas críticas")
    if criticas.empty:
        st.success("Nenhuma tarefa atrasada ou próxima do prazo nas condições atuais 🎉")
        return

    display_cols = [
        "chave",
        "tipo_item",
        "resumo",
        "responsavel",
        "prioridade",
        "status_tarefas",
        "data_limite",
        "dias_para_limite",
    ]

    st.dataframe(
        criticas[display_cols].head(20),
        hide_index=True,
        use_container_width=True,
    )


def render_detailed_table(df: pd.DataFrame):
    """Tabela detalhada e botão de download."""
    st.subheader("📋 Detalhamento das tarefas")

    if df.empty:
        st.info("Sem registros com os filtros aplicados.")
        return

    display_df = df.copy()
    for col in [
        "atualizado",
        "data_limite",
        "data_inicio_corrigida",
        "data_fim_corrigida",
        "data_original_inicio",
        "data_original_fim",
        "start_date",
    ]:
        if col in display_df.columns:
            if "hora" in col or col in ["atualizado", "start_date"]:
                display_df[col] = display_df[col].dt.strftime("%d/%m/%Y %H:%M")
            else:
                display_df[col] = display_df[col].dt.strftime("%d/%m/%Y")

    st.dataframe(
        display_df[
            [
                "chave",
                "resumo",
                "projeto_name",
                "responsavel",
                "prioridade",
                "status",
                "status_tarefas",
                "data_inicio_corrigida",
                "data_fim_corrigida",
                "data_original_inicio",
                "data_original_fim",
                "start_date",
                "data_limite",
                "dias_para_limite",
                "atualizado",
                "dias_para_conclusao",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )

    csv_bytes = display_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Baixar CSV filtrado",
        data=csv_bytes,
        file_name="operacoes_jira_status_tarefas.csv",
        mime="text/csv",
        use_container_width=True,
    )


def render_operacoes_dashboard(
    *,
    show_navigation: bool = True,
    show_title: bool = True,
    show_caption: bool = True,
    set_session_state: bool = True,
    title_text: str = "⚙️ Dashboard de Operações",
    caption_text: str = "Monitoramento das tarefas Jira - Fonte: informacoes_consolidadas.Jira_status_tarefas",
    session_state_page: Optional[str] = __file__,
):
    """
    Renderiza o dashboard de Operações.

    Args:
        show_navigation: Mostra barra de navegação global.
        show_title: Exibe título principal.
        show_caption: Exibe legenda/logo abaixo do título.
        set_session_state: Atualiza `st.session_state['current_page']`.
        title_text: Texto do título.
        caption_text: Texto da legenda.
        session_state_page: Valor armazenado em `st.session_state['current_page']`.
    """
    if show_navigation:
        display_navigation()

    if set_session_state and session_state_page:
        st.session_state["current_page"] = session_state_page

    if show_title and title_text:
        st.title(title_text)
        if show_caption and caption_text:
            st.caption(caption_text)
    elif show_caption and caption_text:
        st.caption(caption_text)

    raw_df = load_jira_status_data()
    if raw_df.empty:
        st.info("A view Jira_status_tarefas ainda não possui registros disponíveis.")
        return

    base_df = prepare_dataframe(raw_df)
    filtered_df, filters_meta = build_filters(base_df)
    filters_meta = filters_meta or {}

    status_filtros = filters_meta.get("status") or []
    status_text = ", ".join(status_filtros) if status_filtros else "Todos"
    projetos_filtro = filters_meta.get("projetos") or []
    projetos_text = ", ".join(projetos_filtro) if projetos_filtro else "Todos"
    apenas_abertas = filters_meta.get("apenas_abertas", False)

    st.markdown(
        f"""
        **Período disponível:** {filters_meta.get('periodo_texto', 'N/D')} | 
        **Status filtrados:** {status_text} |
        **Projetos filtrados:** {projetos_text} |
        **Somente abertas:** {"Sim" if apenas_abertas else "Não"}
        """
    )

    if filtered_df.empty:
        st.warning("Nenhuma tarefa encontrada com os filtros selecionados.")
        return

    render_kpis(filtered_df)

    tab1, tab2, tab3 = st.tabs(["Visão Geral", "Responsáveis", "Detalhamento"])

    with tab1:
        render_status_section(filtered_df)
        render_alerts(filtered_df)

    with tab2:
        render_responsavel_section(filtered_df)

    with tab3:
        render_detailed_table(filtered_df)


def main():
    """Permite executar o módulo isoladamente."""
    st.set_page_config(
        page_title="Operações - Jira",
        page_icon="⚙️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    render_operacoes_dashboard()


if __name__ == "__main__":
    main()

