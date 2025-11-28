"""Aplicativo principal do dashboard de Operações (roteador)."""

import sys
from pathlib import Path

import streamlit as st

# Adicionar diretório `dashboard` ao PYTHONPATH para reutilizar módulos existentes
APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent
DASHBOARD_DIR = ROOT_DIR / "dashboard"
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.append(str(DASHBOARD_DIR))

from advanced_auth import require_auth, require_page_access  # noqa: E402
from navigation import ensure_operacoes_access  # noqa: E402

st.set_page_config(
    page_title="Operações",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Autenticação padrão do projeto
require_auth(dashboard_title="Dashboard Operações")
require_page_access("operacoes")

# Redirecionar automaticamente para a primeira aba disponível
tabs = ensure_operacoes_access()
default_page = tabs[0]["page_path"]
st.switch_page(default_page)
