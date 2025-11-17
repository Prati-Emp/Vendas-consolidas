"""
Dashboard Operações - Monitoramento das tarefas do Jira.
Fonte de dados: informacoes_consolidadas.Jira_status_tarefas
"""

import sys
from pathlib import Path
from typing import Optional

import pandas as pd
import plotly.express as px
import streamlit as st

# Garantir acesso aos módulos utilitários quando importado fora do diretório dashboard
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from utils import display_navigation  # noqa: E402
from utils.md_conn import get_md_connection  # noqa: E402


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
            status_tarefas
        FROM informacoes_consolidadas.Jira_status_tarefas
    """
    return md_conn.run_query(query)


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

    data["data_referencia"] = data["data_limite"].combine_first(data["atualizado"])

    hoje = pd.Timestamp.utcnow().normalize()
    data["dias_para_limite"] = (data["data_limite"] - hoje).dt.days
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
    atrasadas = int(df["esta_atrasada"].sum())
    criticas = int(df["critica_proxima"].sum())

    atraso_pct = f"{(atrasadas / abertas * 100):.1f}%" if abertas else "0%"
    abertas_pct = f"{(abertas / total * 100):.1f}%" if total else "0%"
    criticas_pct = f"{(criticas / max(abertas, 1) * 100):.1f}%" if abertas else "0%"

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Tarefas monitoradas", total)
    col2.metric("Em aberto", abertas, delta=f"{abertas_pct} do total")
    col3.metric("Atrasadas", atrasadas, delta=f"{atraso_pct} das abertas")
    col4.metric("Próximas do prazo (≤7 dias)", criticas, delta=f"{criticas_pct} das abertas")


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

    timeline = (
        df.dropna(subset=["data_referencia"])
        .assign(periodo=lambda d: d["data_referencia"].dt.to_period("W").dt.start_time)
        .groupby(["periodo", "status_tarefas"])
        .size()
        .reset_index(name="quantidade")
        .sort_values("periodo")
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

    st.subheader("Evolução semanal por status")
    if timeline.empty:
        st.info("Não há histórico suficiente para montar a timeline.")
    else:
        fig_timeline = px.area(
            timeline,
            x="periodo",
            y="quantidade",
            color="status_tarefas",
            line_group="status_tarefas",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig_timeline.update_layout(xaxis_title="Semana", yaxis_title="Tarefas", legend_title="Status")
        st.plotly_chart(fig_timeline, use_container_width=True)


def render_responsavel_section(df: pd.DataFrame):
    """Mostra desempenho e carga por responsável."""
    st.subheader("Responsáveis monitorados")

    resumo = (
        df.groupby("responsavel")
        .agg(
            tarefas=("chave", "count"),
            atrasadas=("esta_atrasada", "sum"),
            proximas=("critica_proxima", "sum"),
        )
        .reset_index()
        .sort_values("tarefas", ascending=False)
    )

    top10 = resumo.head(10)

    if resumo.empty:
        st.info("Não há responsáveis com tarefas no filtro atual.")
        return

    col1, col2 = st.columns([1.2, 1])
    with col1:
        fig_resp = px.bar(
            top10,
            y="responsavel",
            x="tarefas",
            color="atrasadas",
            orientation="h",
            color_continuous_scale="Reds",
            labels={"tarefas": "Tarefas", "responsavel": "Responsável", "atrasadas": "Atrasadas"},
        )
        fig_resp.update_layout(coloraxis_colorbar=dict(title="Atrasadas"))
        st.plotly_chart(fig_resp, use_container_width=True)

    with col2:
        st.dataframe(
            top10.assign(
                atraso_pct=lambda d: (d["atrasadas"] / d["tarefas"]).fillna(0).map(lambda v: f"{v:.0%}")
            ),
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

