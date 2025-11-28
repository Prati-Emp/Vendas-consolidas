"""Página dedicada ao dashboard de Compras."""

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
from apps.compras_dashboard import render_compras_dashboard  # noqa: E402
from navigation import render_operacoes_navigation  # noqa: E402

st.set_page_config(
    page_title="Operações - Compras",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

require_auth(dashboard_title="Dashboard Operações")
require_page_access("operacoes")
require_page_access("operacoes.compras")

st.title("⚙️ Dashboard de Operações")
render_operacoes_navigation(current_key="compras")

st.markdown("---")
st.subheader("🛒 Compras")

render_compras_dashboard(
    show_title=False,
    show_caption=False,
)

