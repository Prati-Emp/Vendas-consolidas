"""
Página dedicada às informações de VGV (Valor Geral de Vendas).
Reaproveita a mesma base de dados e filtros da página principal de Vendas.
"""

from datetime import datetime, date
from pathlib import Path
import sys

import streamlit as st

# Garantir acesso aos módulos compartilhados
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

# Autenticação
try:
    from advanced_auth import require_auth, require_page_access, get_current_user  # type: ignore
except Exception as e:  # pragma: no cover - fallback para ambientes sem auth
    st.error(f"Erro ao importar sistema de autenticação: {e}")
    st.stop()

from utils import display_navigation  # noqa: E402
from utils.md_conn import (  # noqa: E402
    get_date_range,
    get_kpis,
    get_metas_periodo,
    get_vgv_prosoluto_resumo,
)
from utils.formatters import format_brl, format_percent, format_compact_currency  # noqa: E402

# Reaproveitar função de VGV da página principal de Vendas
from pages.Vendas import render_vgv_section  # type: ignore  # noqa: E402


def main():
    """Renderiza a página dedicada de Informações VGV."""
    st.set_page_config(
        page_title="Informações VGV",
        page_icon="🏗️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Autenticação e permissão (mesma permissão da página de Vendas)
    require_auth()
    require_page_access("vendas")

    # Restringir acesso apenas ao usuário Odair enquanto a página está em desenvolvimento
    user = get_current_user()
    if not user or user.get("email") != "odair.santos@grupoprati.com":
        st.error("🚧 Página em desenvolvimento. Acesso restrito temporariamente.")
        st.info("Entre em contato com o administrador para mais informações.")
        st.stop()

    # Navegação global
    display_navigation()
    st.session_state["current_page"] = __file__

    st.markdown(
        '<h1 class="main-header">🏗️ Informações VGV</h1>',
        unsafe_allow_html=True,
    )

    # Sidebar – filtros principais (reutiliza lógica simplificada da página Vendas)
    st.sidebar.header("🔍 Filtros VGV")

    try:
        data_min, data_max = get_date_range()
        data_min = datetime.strptime(data_min, "%Y-%m-%d").date()
        data_max = datetime.strptime(data_max, "%Y-%m-%d").date()
    except Exception:
        data_min = date(2025, 1, 1)
        data_max = date.today()

    data_inicial_padrao = date(2026, 1, 1)
    if data_inicial_padrao < data_min:
        data_inicial_padrao = data_min

    data_inicial = st.sidebar.date_input(
        "Data Inicial",
        value=data_inicial_padrao,
        min_value=data_min,
        max_value=data_max,
    )

    data_final = st.sidebar.date_input(
        "Data Final",
        value=data_max,
        min_value=data_min,
        max_value=data_max,
    )

    data_inicial_str = data_inicial.strftime("%Y-%m-%d")
    data_final_str = data_final.strftime("%Y-%m-%d")

    # Calcular KPIs básicos e meta total do período (sem filtros adicionais)
    try:
        kpis = get_kpis(
            data_inicial_str,
            data_final_str,
            midia=None,
            tipovenda=None,
            empreendimento=None,
            corretor=None,
            imobiliaria=None,
        )
    except Exception as e:
        st.error(f"❌ Erro ao carregar KPIs para VGV: {str(e)}")
        return

    try:
        meta_total_periodo = get_metas_periodo(
            data_inicial_str,
            data_final_str,
            empreendimento="Todos",
        )
    except Exception as e:
        st.error(f"❌ Erro ao calcular meta de VGV: {str(e)}")
        meta_total_periodo = 0.0

    st.markdown("### Visão Geral de VGV no Período Selecionado")
    st.caption(
        "Esta página resume o VGV contratado e sua relação com a meta do período, "
        "sem segmentações adicionais por mídia, tipo de venda ou origem."
    )

    # Seção principal de VGV (reuso da função existente)
    render_vgv_section(kpis, meta_total_periodo, meta_ratio=1.0)

    st.markdown("---")

    # Resumo rápido numérico abaixo
    valor_vendas = float(kpis.get("total_valor", 0) or 0.0)
    st.write(
        f"**VGV Contratado (bruto)** no período: {format_compact_currency(valor_vendas)}"
    )

    st.markdown("---")
    st.markdown("### VGV x Prosoluto por Empreendimento (sem filtro de data)")
    st.caption(
        "Tabela consolidada por empreendimento usando a base de VGV (cv_vgv_empreendimentos) "
        "e a view de prosoluto antes/pós chaves. A classificação de 'VGV vendido' usa a coluna "
        "`unidades.situacao` da tabela de VGV."
    )

    with st.spinner("Carregando resumo de VGV e Prosoluto por empreendimento..."):
        df_resumo = get_vgv_prosoluto_resumo()

    if df_resumo.empty:
        st.warning("Não há dados de VGV / Prosoluto para exibir no momento.")
        return

    # Colunas numéricas para formatação
    col_valores = [
        "vgv_total",
        "vgv_vendido",
        "vgv_pendente",
        "prosoluto_antes",
        "venda_fin_antes",
        "prosoluto_pos",
        "venda_fin_pos",
    ]
    col_percentuais = ["pct_prosoluto_antes", "pct_prosoluto_pos"]

    df_display = df_resumo.copy()
    for col in col_valores:
        if col in df_display.columns:
            df_display[col] = df_display[col].fillna(0.0).apply(format_brl)

    for col in col_percentuais:
        if col in df_display.columns:
            df_display[col] = df_display[col].fillna(0.0).apply(
                lambda v: format_percent(v * 100 if 0 <= v <= 1 else v)
            )

    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
    )


if __name__ == "__main__":
    main()

