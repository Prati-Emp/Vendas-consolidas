"""Portal central de acesso aos apps publicados."""

from __future__ import annotations

import html
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


st.markdown(
    """
    <style>
    .portal-hero {
        background: linear-gradient(135deg, #1e3a8a 0%, #dc2626 100%);
        border-radius: 12px;
        padding: 42px 22px;
        margin-bottom: 14px;
        border: 1px solid rgba(255,255,255,0.15);
    }
    .portal-hero h1 {
        margin: 0;
        color: #ffffff;
        font-size: 2rem;
        font-weight: 700;
        text-align: center;
    }
    .portal-hero p {
        margin: 6px 0 0 0;
        color: #f3f4f6;
        font-size: 0.95rem;
        text-align: center;
    }
    .portal-card {
        border: 1px solid rgba(128,128,128,0.35);
        border-left: 3px solid #dc2626;
        border-radius: 10px;
        padding: 14px 16px;
        margin-bottom: 12px;
        min-height: 120px;
        background: rgba(30,58,138,0.08);
        transition: all 0.2s ease;
    }
    .portal-card:hover {
        border-left-color: #1e3a8a;
        background: rgba(220,38,38,0.08);
    }
    .portal-card h4 {
        margin: 0 0 8px 0;
        color: inherit;
        text-align: center;
    }
    .portal-card p {
        margin: 0;
        opacity: 0.9;
        color: inherit;
        text-align: center;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="portal-hero">
        <h1>🧭 Portal de Dashboards Prati</h1>
    </div>
    """,
    unsafe_allow_html=True,
)

links = {**DEFAULT_PORTAL_LINKS, **_get_portal_links_from_secrets()}
allowed_apps = PORTAL_APPS

cols = st.columns(2)
for i, app in enumerate(allowed_apps):
    with cols[i % 2]:
        url = links.get(app["key"], "").strip()
        # Títulos podem ter emoji/caracteres — escapar para HTML seguro.
        title_h = html.escape(app["title"], quote=False)
        desc_h = html.escape(app["description"], quote=False)
        card_inner = (
            f'<div class="portal-card">'
            f"<h4>{title_h}</h4>"
            f"<p>{desc_h}</p>"
            f"</div>"
        )

        # Só o card em HTML; links via st.link_button (âncoras em markdown costumam não navegar no Cloud).
        st.markdown(card_inner, unsafe_allow_html=True)
        if url:
            st.link_button(
                "Abrir dashboard →",
                url.strip(),
                help=app["description"],
                use_container_width=True,
                type="primary",
                key=f"portal_open_{app['key']}",
            )
        else:
            st.caption("URL não configurada")

