"""Página inicial do dashboard de Administrativo."""

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

st.set_page_config(
    page_title="Administrativo - Visão Geral",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

require_auth(dashboard_title="Dashboard Administrativo")
require_page_access("administrativo")
require_page_access("administrativo.visao_geral")

st.title("🏛️ Dashboard Administrativo")
render_administrativo_navigation(current_key="visao_geral")

st.markdown("---")
st.subheader("📌 Visão Geral")
st.info(
    "Estrutura básica criada para o novo conjunto de dashboards de Administrativo. "
    "Inclua aqui os painéis e indicadores específicos conforme forem definidos."
)

st.markdown(
    """
    ### Próximos passos sugeridos
    - Definir as fontes de dados e tabelas que alimentarão os painéis de Administrativo.
    - Mapear as permissões necessárias (subpáginas) para cada área dentro de Administrativo.
    - Adicionar novas abas utilizando `navigation.py` e páginas em `pages/` conforme os temas forem criados.
    """
)

