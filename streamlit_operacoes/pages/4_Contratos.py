"""Página dedicada ao dashboard de Contratos."""

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
from apps.contratos_dashboard import render_contratos_dashboard  # noqa: E402
from navigation import render_operacoes_navigation  # noqa: E402

st.set_page_config(
    page_title="Operações - Contratos",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

require_auth(dashboard_title="Dashboard Operações")
require_page_access("operacoes")
require_page_access("operacoes.contratos")

st.title("⚙️ Dashboard de Operações")
render_operacoes_navigation(current_key="contratos")

st.markdown("---")
st.subheader("📋 Contratos")

render_contratos_dashboard(
    show_title=False,
    show_caption=False,
)

