"""Página de Contas Pagas do dashboard de Administrativo."""

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
from navigation import render_administrativo_navigation  # noqa: E402
from dashboard.apps.contas_pagas_dashboard import render_contas_pagas_dashboard  # noqa: E402

st.set_page_config(
    page_title="Administrativo - Contas Pagas",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

require_auth(dashboard_title="Dashboard Administrativo")
require_page_access("administrativo")
require_page_access("administrativo.contas_pagas")

st.title("🏛️ Dashboard Administrativo")
render_administrativo_navigation(current_key="contas_pagas")

st.markdown("---")

render_contas_pagas_dashboard(show_title=False, show_caption=False)

