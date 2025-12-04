"""Página dedicada às solicitações de compras (placeholder inicial)."""

import sys
from pathlib import Path

import streamlit as st

PAGES_DIR = Path(__file__).resolve().parent
APP_DIR = PAGES_DIR.parent
ROOT_DIR = APP_DIR.parent
DASHBOARD_DIR = ROOT_DIR / "dashboard"

for path in (ROOT_DIR, DASHBOARD_DIR, APP_DIR):
    if str(path) not in sys.path:
        sys.path.append(str(path))

from advanced_auth import require_auth, require_page_access  # noqa: E402
from dashboard.apps.solicitacoes_dashboard import (  # noqa: E402
    render_solicitacoes_dashboard,
)
from navigation import render_operacoes_navigation  # noqa: E402

st.set_page_config(
    page_title="Operações - Solicitação de Compras",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded",
)

require_auth(dashboard_title="Dashboard Operações")
require_page_access("operacoes")
require_page_access("operacoes.solicitacoes")

st.title("⚙️ Dashboard de Operações")
render_operacoes_navigation(current_key="solicitacao_compras")

st.markdown("---")
st.subheader("📝 Solicitação de Compras")

render_solicitacoes_dashboard(
    show_title=False,
    show_caption=False,
)

