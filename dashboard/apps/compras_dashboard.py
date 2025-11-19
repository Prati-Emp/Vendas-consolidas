"""
Dashboard Compras - Monitoramento de compras e fornecedores.
Página em desenvolvimento - aguardando dados.
"""

import streamlit as st
from typing import Optional


def render_compras_dashboard(
    *,
    show_title: bool = True,
    show_caption: bool = True,
):
    """
    Renderiza o dashboard de Compras.

    Args:
        show_title: Exibe título principal.
        show_caption: Exibe legenda/logo abaixo do título.
    """
    if show_title:
        st.title("🛒 Dashboard de Compras")
        if show_caption:
            st.caption("Monitoramento de compras e fornecedores - Em desenvolvimento")

    st.info("📋 Esta página está em desenvolvimento. Os dados serão carregados em breve.")

    # Placeholder para futuras implementações
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total de Compras", "—", "Aguardando dados")
    
    with col2:
        st.metric("Fornecedores", "—", "Aguardando dados")
    
    with col3:
        st.metric("Valor Total", "—", "Aguardando dados")

    st.markdown("---")
    
    st.markdown("""
    ### 📝 Próximas funcionalidades:
    
    - Lista de compras e pedidos
    - Análise de fornecedores
    - Controle de prazos e entregas
    - Indicadores de performance
    - Relatórios e exportação de dados
    """)

