"""Aplicativo Streamlit independente para o dashboard Operações."""

import sys
from pathlib import Path

import streamlit as st

# Adicionar diretório `dashboard` ao PYTHONPATH para reutilizar módulos existentes
ROOT_DIR = Path(__file__).resolve().parents[1]
DASHBOARD_DIR = ROOT_DIR / "dashboard"
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.append(str(DASHBOARD_DIR))

from advanced_auth import require_auth, require_page_access  # noqa: E402
from apps.operacoes_dashboard import render_operacoes_dashboard  # noqa: E402

st.set_page_config(
    page_title="Operações - Jira",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Autenticação padrão do projeto
require_auth()
require_page_access("operacoes")

render_operacoes_dashboard(
    show_navigation=False,  # App independente não usa menu global
    show_title=True,
    show_caption=True,
    set_session_state=False,
    title_text="⚙️ Operações - Jira",
)

