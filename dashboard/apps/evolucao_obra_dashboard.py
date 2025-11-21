"""
Dashboard Evolução de Obra - Monitoramento de evolução de obras.
Página em desenvolvimento - aguardando dados.
"""

import streamlit as st
from typing import Optional


def render_evolucao_obra_dashboard(
    *,
    show_title: bool = True,
    show_caption: bool = True,
):
    """
    Renderiza o dashboard de Evolução de Obra.

    Args:
        show_title: Exibe título principal.
        show_caption: Exibe legenda/logo abaixo do título.
    """
    if show_title:
        st.title("🏗️ Evolução de Obra")
        if show_caption:
            st.caption("Monitoramento de evolução de obras - Em desenvolvimento")

    st.info("📋 Esta página está em desenvolvimento. Os dados serão carregados em breve.")

    # Placeholder para futuras implementações
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Obras em Andamento", "—", "Aguardando dados")
    
    with col2:
        st.metric("Percentual Médio", "—", "Aguardando dados")
    
    with col3:
        st.metric("Prazo Médio", "—", "Aguardando dados")

    st.markdown("---")
    
    st.markdown("""
    ### 📝 Próximas funcionalidades:
    
    - Evolução percentual de obras
    - Gráficos de progresso
    - Análise de prazos
    - Comparativo entre obras
    - Indicadores de performance
    - Relatórios e exportação de dados
    """)

