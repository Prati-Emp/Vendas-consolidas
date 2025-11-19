"""Aplicativo Streamlit independente para o dashboard Operações."""

import sys
from pathlib import Path

import streamlit as st

# Adicionar diretório `dashboard` ao PYTHONPATH para reutilizar módulos existentes
ROOT_DIR = Path(__file__).resolve().parents[1]
DASHBOARD_DIR = ROOT_DIR / "dashboard"
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.append(str(DASHBOARD_DIR))

from advanced_auth import require_auth, require_page_access, can_access_page  # noqa: E402
from apps.operacoes_dashboard import render_operacoes_dashboard  # noqa: E402
from apps.compras_dashboard import render_compras_dashboard  # noqa: E402

st.set_page_config(
    page_title="Operações",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Autenticação padrão do projeto
require_auth(dashboard_title="Dashboard Operações")
require_page_access("operacoes")

# Verificar acesso às subpáginas
has_jira_access = can_access_page("operacoes.jira")
has_compras_access = can_access_page("operacoes.compras")

# Verificar se o usuário tem acesso a pelo menos uma subpágina
if not has_jira_access and not has_compras_access:
    st.error("🚫 Acesso negado! Você não tem permissão para acessar nenhuma página de Operações.")
    st.info("💡 Entre em contato com o administrador para solicitar acesso.")
    st.stop()

# Título principal do dashboard
st.title("⚙️ Dashboard de Operações")
st.caption("Monitoramento integrado de operações")

# Criar lista de tabs baseado no acesso do usuário
tabs_config = []
if has_jira_access:
    tabs_config.append(("📋 Jira", "jira"))
if has_compras_access:
    tabs_config.append(("🛒 Compras", "compras"))

# Criar tabs dinamicamente
if len(tabs_config) == 1:
    # Se só tem uma tab, renderizar diretamente sem tabs
    tab_name, tab_key = tabs_config[0]
    if tab_key == "jira":
        render_operacoes_dashboard(
            show_navigation=False,
            show_title=False,
            show_caption=False,
            set_session_state=False,
            title_text="⚙️ Operações - Jira",
        )
    elif tab_key == "compras":
        render_compras_dashboard(
            show_title=False,
            show_caption=False,
        )
else:
    # Múltiplas tabs - criar normalmente
    tab_names = [tab[0] for tab in tabs_config]
    tabs = st.tabs(tab_names)
    
    for idx, (tab_name, tab_key) in enumerate(tabs_config):
        with tabs[idx]:
            if tab_key == "jira":
                render_operacoes_dashboard(
                    show_navigation=False,
                    show_title=False,
                    show_caption=False,
                    set_session_state=False,
                    title_text="⚙️ Operações - Jira",
                )
            elif tab_key == "compras":
                render_compras_dashboard(
                    show_title=False,
                    show_caption=False,
                )

