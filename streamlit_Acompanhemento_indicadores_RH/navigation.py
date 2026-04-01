"""Utilidades de navegação (mini-admin) para Acompanhamento e Indicadores RH."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List

import streamlit as st

# Garantir acesso aos módulos compartilhados do dashboard principal
BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
DASHBOARD_DIR = ROOT_DIR / "dashboard"
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.append(str(DASHBOARD_DIR))

from advanced_auth import can_access_page  # noqa: E402


TAB_DEFINITIONS: List[Dict[str, str]] = [
    {
        "label": "📊 Indicadores Gestão de Pessoas",
        "permission": "administrativo.indicadores_gestao_pessoas",
        "page_path": "pages/6_Indicadores_Gestao_Pessoas.py",
        "key": "indicadores_gestao_pessoas",
    },
    {
        "label": "📈 Indicadores Jurídico",
        "permission": "administrativo",
        "page_path": "pages/6_Indicadores_Juridico.py",
        "key": "indicadores_juridico",
    },
    {
        "label": "🧑‍💼 Acompanhamento RH",
        # A governança de dados já bloqueia quem não está autorizado (planilhas.quadro_rh_autorizacoes).
        # Então liberamos essa página para qualquer usuário com acesso ao `administrativo`.
        "permission": "administrativo",
        "page_path": "pages/7_Acompanhamento_RH.py",
        "key": "acompanhamento_solicitacoes",
    },
    {
        "label": "⚖️ Acompanhamento Jurídico",
        "permission": "administrativo",
        "page_path": "pages/8_Acompanhamento_Juridico.py",
        "key": "acompanhamento_juridico",
    },
]


def get_accessible_administrativo_tabs() -> List[Dict[str, str]]:
    """Retorna as abas disponíveis para o usuário atual."""
    tabs: List[Dict[str, str]] = []
    for tab in TAB_DEFINITIONS:
        if can_access_page(tab["permission"]):
            tabs.append(tab)
    return tabs


def ensure_administrativo_access() -> List[Dict[str, str]]:
    """Garante que o usuário tenha acesso a pelo menos uma aba."""
    tabs = get_accessible_administrativo_tabs()
    if not tabs:
        st.error("🚫 Acesso negado! Você não tem permissão para acessar RH.")
        st.info("💡 Entre em contato com o administrador para solicitar acesso.")
        st.stop()
    return tabs


def render_administrativo_navigation(current_key: str) -> List[Dict[str, str]]:
    """Exibe a navegação horizontal entre as duas páginas disponíveis."""
    tabs = ensure_administrativo_access()

    st.markdown(
        """
        <style>
        .administrativo-nav button {
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
                key=f"mini_rh_nav_{tab['key']}",
                use_container_width=True,
                disabled=disabled,
            ):
                st.switch_page(tab["page_path"])

    return tabs

