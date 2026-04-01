"""Utilidades de navegação para o dashboard de Administrativo."""

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


TAB_DEFINITIONS = [
    {
        "label": "💰 Repasses",
        "permission": "administrativo.repasses",
        "page_path": "pages/2_Repasses.py",
        "key": "repasses",
    },
    {
        "label": "💳 Contas Pagas",
        "permission": "administrativo.contas_pagas",
        "page_path": "pages/3_Contas_Pagas.py",
        "key": "contas_pagas",
    },
    {
        "label": "💵 Saldo Em Caixa",
        "permission": "administrativo.saldo_em_caixa",
        "page_path": "pages/4_Saldo_Em_Caixa.py",
        "key": "saldo_em_caixa",
    },
    {
        "label": "👥 RH",
        "permission": "administrativo.rh",
        "page_path": "pages/5_RH.py",
        "key": "rh",
    },
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
        "permission": "administrativo.acompanhamento_solicitacoes",
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
    """Retorna as abas de Administrativo às quais o usuário atual tem acesso."""
    tabs: List[Dict[str, str]] = []
    for tab in TAB_DEFINITIONS:
        if can_access_page(tab["permission"]):
            tabs.append(tab)
    return tabs


def ensure_administrativo_access() -> List[Dict[str, str]]:
    """Garante que o usuário tenha acesso a pelo menos uma aba de Administrativo."""
    tabs = get_accessible_administrativo_tabs()
    if not tabs:
        st.error("🚫 Acesso negado! Você não tem permissão para acessar Administrativo.")
        st.info("💡 Entre em contato com o administrador para solicitar acesso.")
        st.stop()
    return tabs


def render_administrativo_navigation(current_key: str) -> List[Dict[str, str]]:
    """Exibe a navegação horizontal entre as abas disponíveis."""
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
                key=f"administrativo_nav_{tab['key']}",
                use_container_width=True,
                disabled=disabled,
            ):
                st.switch_page(tab["page_path"])

    return tabs

