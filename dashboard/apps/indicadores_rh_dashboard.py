"""
Dashboard de Indicadores RH - Estrutura base para indicadores de RH.
"""

from __future__ import annotations

import streamlit as st


def render_indicadores_rh_dashboard(
    show_title: bool = True, show_caption: bool = True
) -> None:
    """Renderiza o dashboard de Indicadores RH."""
    if show_title:
        st.title("📊 Indicadores RH")

    if show_caption:
        st.caption("Indicadores consolidados de Recursos Humanos.")

    st.info("🚧 Em construção. Conteúdo em desenvolvimento.")
