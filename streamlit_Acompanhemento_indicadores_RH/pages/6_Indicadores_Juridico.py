"""Página de Indicadores Jurídico do mini-admin RH."""

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
from dashboard.apps.indicadores_juridico_dashboard import (  # noqa: E402
    render_indicadores_juridico_dashboard,
)

st.set_page_config(
    page_title="Jurídico - Indicadores",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

require_auth(dashboard_title="Indicadores e acompanhamentos")
require_page_access("administrativo")

st.title("📊 Indicadores e acompanhamentos")
render_administrativo_navigation(current_key="indicadores_juridico")

st.markdown("---")
render_indicadores_juridico_dashboard()

