"""Página multipage interna para o dashboard Operações."""

import sys
from pathlib import Path

import streamlit as st

# Garantir acesso aos módulos compartilhados
sys.path.append(str(Path(__file__).parent.parent))

from advanced_auth import require_auth, require_page_access  # noqa: E402
from apps.operacoes_dashboard import render_operacoes_dashboard  # noqa: E402

st.set_page_config(
    page_title="Operações - Jira",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

require_auth()
require_page_access("operacoes")

render_operacoes_dashboard(
    show_navigation=True,
    show_title=True,
    show_caption=True,
    set_session_state=True,
)
