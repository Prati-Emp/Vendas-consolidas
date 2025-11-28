"""Página dedicada ao monitoramento do Jira no dashboard de Operações."""

import sys
from pathlib import Path

import streamlit as st

# Ajustar caminhos para reutilizar módulos compartilhados
PAGES_DIR = Path(__file__).resolve().parent
APP_DIR = PAGES_DIR.parent
ROOT_DIR = APP_DIR.parent
DASHBOARD_DIR = ROOT_DIR / "dashboard"

for path in (ROOT_DIR, DASHBOARD_DIR, APP_DIR):
    if str(path) not in sys.path:
        sys.path.append(str(path))

from advanced_auth import require_auth, require_page_access  # noqa: E402
from apps.operacoes_dashboard import render_operacoes_dashboard  # noqa: E402
from navigation import render_operacoes_navigation  # noqa: E402

st.set_page_config(
    page_title="Operações - Jira",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

require_auth(dashboard_title="Dashboard Operações")
require_page_access("operacoes")
require_page_access("operacoes.jira")

st.title("⚙️ Dashboard de Operações")
render_operacoes_navigation(current_key="jira")

st.markdown("---")

render_operacoes_dashboard(
    show_navigation=False,
    show_title=False,
    show_caption=False,
    set_session_state=False,
    title_text="⚙️ Operações - Jira",
)

