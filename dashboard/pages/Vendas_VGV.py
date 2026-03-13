"""
Página dedicada às informações de VGV (Valor Geral de Vendas).
Exibe apenas a tabela consolidada VGV x Prosoluto por empreendimento (sem uso de data nem tabela de vendas).
"""

from pathlib import Path
import sys

import streamlit as st

# Garantir acesso aos módulos compartilhados
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

# Autenticação
try:
    from advanced_auth import require_auth, require_page_access, get_current_user  # type: ignore
except Exception as e:  # pragma: no cover - fallback para ambientes sem auth
    st.error(f"Erro ao importar sistema de autenticação: {e}")
    st.stop()

from utils import display_navigation  # noqa: E402
from utils.md_conn import get_vgv_prosoluto_resumo  # noqa: E402
from utils.formatters import format_brl, format_percent  # noqa: E402


def main():
    """Renderiza a página dedicada de Informações VGV."""
    st.set_page_config(
        page_title="Informações VGV",
        page_icon="🏗️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Autenticação e permissão (mesma permissão da página de Vendas)
    require_auth()
    require_page_access("vendas")

    # Restringir acesso apenas ao usuário Odair enquanto a página está em desenvolvimento
    user = get_current_user()
    if not user or user.get("email") != "odair.santos@grupoprati.com":
        st.error("🚧 Página em desenvolvimento. Acesso restrito temporariamente.")
        st.info("Entre em contato com o administrador para mais informações.")
        st.stop()

    # Navegação global
    display_navigation()
    st.session_state["current_page"] = __file__

    st.markdown(
        '<h1 class="main-header">🏗️ Informações VGV</h1>',
        unsafe_allow_html=True,
    )

    st.markdown("### VGV x Prosoluto por Empreendimento")
    st.caption(
        "Tabela consolidada por empreendimento usando a base de VGV (cv_vgv_empreendimentos) "
        "e a view de prosoluto antes/pós chaves. A classificação de 'VGV vendido' usa a coluna "
        "`unidades.situacao` da tabela de VGV."
    )

    with st.spinner("Carregando resumo de VGV e Prosoluto por empreendimento..."):
        df_resumo = get_vgv_prosoluto_resumo()

    if df_resumo.empty:
        st.warning("Não há dados de VGV / Prosoluto para exibir no momento.")
        return

    # Valores retornados de Prosoluto (antes e pós obra) por empreendimento
    st.markdown("#### Valor retornado de Prosoluto por empreendimento")
    st.caption(
        "Valores vindos da view **prosoluto_antes_e_pos_chaves**: valor de prosoluto **antes da obra** (vencimento ≤ data fim obra) "
        "e **pós obra** (vencimento > data fim obra), por nome do empreendimento."
    )
    col_prosoluto = ["nome_empreendimento", "prosoluto_antes", "prosoluto_pos", "pct_prosoluto_antes", "pct_prosoluto_pos"]
    df_prosoluto = df_resumo[[c for c in col_prosoluto if c in df_resumo.columns]].copy()
    if "prosoluto_antes" in df_prosoluto.columns:
        df_prosoluto["prosoluto_antes"] = df_prosoluto["prosoluto_antes"].fillna(0.0).apply(format_brl)
    if "prosoluto_pos" in df_prosoluto.columns:
        df_prosoluto["prosoluto_pos"] = df_prosoluto["prosoluto_pos"].fillna(0.0).apply(format_brl)
    for c in ["pct_prosoluto_antes", "pct_prosoluto_pos"]:
        if c in df_prosoluto.columns:
            df_prosoluto[c] = df_prosoluto[c].fillna(0.0).apply(
                lambda v: format_percent(v * 100 if 0 <= v <= 1 else v, decimal_sep_comma=True)
            )
    df_prosoluto = df_prosoluto.rename(columns={
        "nome_empreendimento": "Empreendimento",
        "prosoluto_antes": "Prosoluto antes da obra",
        "prosoluto_pos": "Prosoluto pós obra",
        "pct_prosoluto_antes": "% Prosoluto antes",
        "pct_prosoluto_pos": "% Prosoluto pós",
    })
    st.dataframe(df_prosoluto, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("#### Tabela completa (VGV + Prosoluto)")

    # Colunas numéricas para formatação
    col_valores = [
        "vgv_total",
        "vgv_vendido",
        "vgv_pendente",
        "prosoluto_antes",
        "venda_fin_antes",
        "prosoluto_pos",
        "venda_fin_pos",
    ]
    col_percentuais = ["pct_prosoluto_antes", "pct_prosoluto_pos"]

    df_display = df_resumo.copy()
    for col in col_valores:
        if col in df_display.columns:
            df_display[col] = df_display[col].fillna(0.0).apply(format_brl)

    for col in col_percentuais:
        if col in df_display.columns:
            df_display[col] = df_display[col].fillna(0.0).apply(
                lambda v: format_percent(v * 100 if 0 <= v <= 1 else v, decimal_sep_comma=True)
            )

    df_display = df_display.rename(columns={
        "id_empreendimento": "ID",
        "nome_empreendimento": "Empreendimento",
        "vgv_total": "VGV Total",
        "vgv_vendido": "VGV Vendido",
        "vgv_pendente": "VGV Pendente",
        "prosoluto_antes": "Prosoluto antes obra",
        "venda_fin_antes": "Venda financ. (antes)",
        "pct_prosoluto_antes": "% Prosoluto antes",
        "prosoluto_pos": "Prosoluto pós obra",
        "venda_fin_pos": "Venda financ. (pós)",
        "pct_prosoluto_pos": "% Prosoluto pós",
    })

    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
    )


if __name__ == "__main__":
    main()

