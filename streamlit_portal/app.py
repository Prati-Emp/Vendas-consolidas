"""Portal central de acesso aos apps publicados."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict

import streamlit as st

# Reuso da autenticação central do projeto
APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent
DASHBOARD_DIR = ROOT_DIR / "dashboard"
for path in (ROOT_DIR, DASHBOARD_DIR):
    if str(path) not in sys.path:
        sys.path.append(str(path))



st.set_page_config(
    page_title="Portal de Dashboards Prati",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _get_portal_links_from_secrets() -> Dict[str, str]:
    """Lê URLs publicadas dos apps via Streamlit secrets."""
    try:
        portal_cfg = st.secrets.get("portal_links", {})
        if isinstance(portal_cfg, dict):
            return {str(k): str(v) for k, v in portal_cfg.items()}
    except Exception:
        pass
    return {}


DEFAULT_PORTAL_LINKS: Dict[str, str] = {
    "vendas": "https://painel-comercial-3an7z6klwm62m8vjgaandc.streamlit.app/",
    "operacoes": "https://operacoe-atividades-dp6rfv83mdgebtsitsvsab.streamlit.app/",
    "administrativo": "https://dashboardadm7uzra3xkjapkqfbotwba6.streamlit.app/",
    "tv_comercial": "https://tv-comercial-fe5yw6krwg6qwxntjwjkiao.streamlit.app/",
    "rh_portal": "https://acompanhamento-qjz7ssdzfrmmqyw2dcpw4f.streamlit.app/",
}


PORTAL_APPS = [
    {
        "key": "vendas",
        "title": "📊 Dashboard de Vendas",
        "description": "KPIs, análises e visão consolidada de vendas.",
        "required_permissions": ["vendas"],
    },
    {
        "key": "operacoes",
        "title": "⚙️ Dashboard de Operações",
        "description": "Jira, compras e indicadores operacionais.",
        "required_permissions": ["operacoes"],
    },
    {
        "key": "administrativo",
        "title": "🏛️ Dashboard Administrativo",
        "description": "Repasses, contas e páginas administrativas.",
        "required_permissions": ["administrativo"],
    },
    {
        "key": "tv_comercial",
        "title": "📺 TV Comercial",
        "description": "Visão simplificada para exibição comercial.",
        "required_permissions": ["tv_comercial"],
    },
    {
        "key": "rh_portal",
        "title": "👥 Acompanhamento e Indicadores de Gestão de Pessoas",
        "description": "Acompanhamento de solicitações e indicadores RH.",
        "required_permissions": [
            "administrativo.indicadores_gestao_pessoas",
            "administrativo.acompanhamento_solicitacoes",
        ],
    },
]


st.title("🧭 Portal de Dashboards Prati")
st.caption("Acesso rápido para os dashboards publicados.")

links = {**DEFAULT_PORTAL_LINKS, **_get_portal_links_from_secrets()}
allowed_apps = PORTAL_APPS

cols = st.columns(2)
for i, app in enumerate(allowed_apps):
    with cols[i % 2]:
        url = links.get(app["key"], "").strip()
        title_html = (
            f'<a href="{url}" target="_self" style="text-decoration:none; color:inherit;">{app["title"]}</a>'
            if url
            else app["title"]
        )
        st.markdown(
            f"""
            <div style="
                border: 1px solid rgba(128,128,128,0.3);
                border-radius: 10px;
                padding: 14px 16px;
                margin-bottom: 12px;
                min-height: 120px;
                background: rgba(255,255,255,0.02);
            ">
                <h4 style="margin: 0 0 8px 0;">{title_html}</h4>
                <p style="margin: 0; opacity: 0.85;">{app["description"]}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if not url:
            st.caption("URL não configurada")

st.markdown("---")
st.markdown(
    """
    **Configuração de links (Streamlit Cloud / Secrets):**
    adicione um objeto `portal_links` com as URLs dos apps.
    """.strip()
)

