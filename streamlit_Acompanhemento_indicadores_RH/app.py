"""Aplicativo principal (mini-admin) do Acompanhamento e Indicadores RH."""

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
from navigation import ensure_administrativo_access  # noqa: E402


st.set_page_config(
    page_title="Acompanhamento e Indicadores RH",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

require_auth(dashboard_title="Acompanhamento e Indicadores RH")
require_page_access("administrativo")

# Redirecionar automaticamente para a primeira aba disponível
tabs = ensure_administrativo_access()
default_page = tabs[0]["page_path"]
st.switch_page(default_page)

