"""Página para o dashboard de Evolução de Obra."""

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
from apps.evolucao_obra_dashboard import render_evolucao_obra_dashboard  # noqa: E402
from navigation import render_operacoes_navigation  # noqa: E402

st.set_page_config(
    page_title="Operações - Evolução de Obra",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

require_auth(dashboard_title="Dashboard Operações")
require_page_access("operacoes")
require_page_access("operacoes.evolucao_obra")

st.title("⚙️ Dashboard de Operações")
render_operacoes_navigation(current_key="evolucao_obra")

st.markdown("---")

render_evolucao_obra_dashboard(
    show_title=False,
    show_caption=False,
)

