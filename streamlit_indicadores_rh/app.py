"""
Aplicativo principal do Indicadores RH.
Projeto standalone baseado na estrutura do dashboard administrativo.
"""

import sys
from pathlib import Path

import streamlit as st

# Adicionar diretórios necessários ao PYTHONPATH
APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent
DASHBOARD_DIR = ROOT_DIR / "dashboard"

for path in (ROOT_DIR, DASHBOARD_DIR):
    if str(path) not in sys.path:
        sys.path.append(str(path))

from advanced_auth import require_auth, require_page_access  # noqa: E402
from dashboard.apps.indicadores_rh_dashboard import render_indicadores_rh_dashboard  # noqa: E402

st.set_page_config(
    page_title="Indicadores RH",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

require_auth(dashboard_title="Indicadores RH")
require_page_access("administrativo")

st.title("📊 Indicadores RH")
st.markdown("---")

render_indicadores_rh_dashboard(show_title=False, show_caption=False)
