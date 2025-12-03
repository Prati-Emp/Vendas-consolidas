"""Utilidades de navegação para o dashboard de Operações."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Dict

import streamlit as st

# Garantir acesso aos módulos compartilhados do dashboard principal
BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
DASHBOARD_DIR = ROOT_DIR / "dashboard"
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.append(str(DASHBOARD_DIR))

from advanced_auth import can_access_page  # noqa: E402


TAB_DEFINITIONS = [
    {
        "label": "📋 Jira",
        "permission": "operacoes.jira",
        "page_path": "pages/1_Jira.py",
        "key": "jira",
    },
    {
        "label": "🛒 Compras",
        "permission": "operacoes.compras",
        "page_path": "pages/2_Compras.py",
        "key": "compras",
    },
]


def get_accessible_operacoes_tabs() -> List[Dict[str, str]]:
    """Retorna as abas de Operações às quais o usuário atual tem acesso."""
    tabs: List[Dict[str, str]] = []
    for tab in TAB_DEFINITIONS:
        if can_access_page(tab["permission"]):
            tabs.append(tab)
    return tabs


def ensure_operacoes_access() -> List[Dict[str, str]]:
    """Garante que o usuário tenha acesso a pelo menos uma aba de Operações."""
    tabs = get_accessible_operacoes_tabs()
    if not tabs:
        st.error("🚫 Acesso negado! Você não tem permissão para acessar Operações.")
        st.info("💡 Entre em contato com o administrador para solicitar acesso.")
        st.stop()
    return tabs


def render_operacoes_navigation(current_key: str) -> List[Dict[str, str]]:
    """Exibe a navegação horizontal entre as abas disponíveis."""
    tabs = ensure_operacoes_access()

    # CSS simples para destacar a navegação
    st.markdown(
        """
        <style>
        .operacoes-nav button {
            border-radius: 6px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(len(tabs))
    for col, tab in zip(cols, tabs):
        with col:
            disabled = tab["key"] == current_key
            if st.button(
                tab["label"],
                key=f"operacoes_nav_{tab['key']}",
                use_container_width=True,
                disabled=disabled,
            ):
                st.switch_page(tab["page_path"])

    return tabs

