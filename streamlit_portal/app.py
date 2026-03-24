"""Portal central de acesso aos apps publicados."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List

import streamlit as st

# Reuso da autenticação central do projeto
APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent
DASHBOARD_DIR = ROOT_DIR / "dashboard"
for path in (ROOT_DIR, DASHBOARD_DIR):
    if str(path) not in sys.path:
        sys.path.append(str(path))

from advanced_auth import can_access_page, get_current_user, require_auth  # noqa: E402


st.set_page_config(
    page_title="Portal de Dashboards Prati",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

require_auth(dashboard_title="Portal de Dashboards Prati")


def _get_portal_links_from_secrets() -> Dict[str, str]:
    """Lê URLs publicadas dos apps via Streamlit secrets."""
    try:
        portal_cfg = st.secrets.get("portal_links", {})
        if isinstance(portal_cfg, dict):
            return {str(k): str(v) for k, v in portal_cfg.items()}
    except Exception:
        pass
    return {}


def _is_allowed(required_permissions: List[str]) -> bool:
    """Verifica se usuário pode visualizar um card do portal."""
    return any(can_access_page(p) for p in required_permissions)


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
user = get_current_user() or {}
user_name = user.get("name", "Usuário")
st.caption(f"Bem-vindo, {user_name}. Aqui você vê apenas os apps aos quais tem acesso.")

links = _get_portal_links_from_secrets()
allowed_apps = [app for app in PORTAL_APPS if _is_allowed(app["required_permissions"])]

if not allowed_apps:
    st.warning("Nenhum app disponível para o seu perfil no momento.")
    st.stop()

cols = st.columns(2)
for i, app in enumerate(allowed_apps):
    with cols[i % 2]:
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
                <h4 style="margin: 0 0 8px 0;">{app["title"]}</h4>
                <p style="margin: 0; opacity: 0.85;">{app["description"]}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        url = links.get(app["key"], "").strip()
        if url:
            st.link_button("Abrir app", url, use_container_width=True)
        else:
            st.button(
                "URL não configurada",
                key=f"portal_missing_{app['key']}",
                disabled=True,
                use_container_width=True,
            )

st.markdown("---")
st.markdown(
    """
    **Configuração de links (Streamlit Cloud / Secrets):**
    adicione um objeto `portal_links` com as URLs dos apps.
    """.strip()
)

