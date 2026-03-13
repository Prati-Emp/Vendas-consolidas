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


def _formatar_tabela_geral(df, col_valores, col_percentuais):
    """Formata e ordena a tabela da aba geral."""
    for col in col_valores:
        if col in df.columns:
            df[col] = df[col].fillna(0.0).apply(format_brl)
    for col in col_percentuais:
        if col in df.columns:
            df[col] = df[col].fillna(0.0).apply(
                lambda v: format_percent(v, decimals=2, decimal_sep_comma=True)
            )
    df = df.rename(columns={
        "id_empreendimento": "ID",
        "nome_empreendimento": "Empreendimento",
        "vgv_total": "VGV Total",
        "vgv_vendido": "VGV Vendido",
        "vgv_pendente": "VGV Pendente",
        "prosoluto_antes": "Prosoluto antes chaves",
        "venda_fin_antes": "Venda financiamento",
        "pct_prosoluto_antes": "% Prosoluto antes chaves",
        "prosoluto_pos": "Prosoluto pós chaves",
        "pct_prosoluto_pos": "% Prosoluto pós chaves",
    })
    df = df.drop(columns=["venda_fin_pos"], errors="ignore")
    ordem = [
        "ID", "Empreendimento", "VGV Total", "VGV Vendido", "VGV Pendente",
        "Prosoluto antes chaves", "Prosoluto pós chaves",
        "% Prosoluto antes chaves", "% Prosoluto pós chaves",
        "Venda financiamento",
    ]
    return df[[c for c in ordem if c in df.columns]]


def _montar_tabela_analise(df):
    """Monta tabela de análise: Prosoluto antes/pós chaves e VGV realizado (valor e %)."""
    df = df.copy()
    vgv_total = df["vgv_total"].fillna(0.0)
    vgv_vendido = df["vgv_vendido"].fillna(0.0)
    df["pct_vgv_realizado"] = 0.0
    mask = vgv_total > 0
    df.loc[mask, "pct_vgv_realizado"] = (vgv_vendido[mask] / vgv_total[mask]).values

    for col in ["prosoluto_antes", "prosoluto_pos", "vgv_vendido"]:
        if col in df.columns:
            df[col] = df[col].fillna(0.0).apply(format_brl)
    for col in ["pct_prosoluto_antes", "pct_prosoluto_pos", "pct_vgv_realizado"]:
        if col in df.columns:
            df[col] = df[col].fillna(0.0).apply(
                lambda v: format_percent(v, decimals=2, decimal_sep_comma=True)
            )
    df = df.rename(columns={
        "nome_empreendimento": "Empreendimento",
        "prosoluto_antes": "Prosoluto antes chaves",
        "pct_prosoluto_antes": "% Prosoluto antes chaves",
        "prosoluto_pos": "Prosoluto pós chaves",
        "pct_prosoluto_pos": "% Prosoluto pós chaves",
        "vgv_vendido": "VGV realizado",
        "pct_vgv_realizado": "% VGV realizado",
    })
    ordem = [
        "Empreendimento",
        "Prosoluto antes chaves", "% Prosoluto antes chaves",
        "Prosoluto pós chaves", "% Prosoluto pós chaves",
        "VGV realizado", "% VGV realizado",
    ]
    return df[[c for c in ordem if c in df.columns]]


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

    with st.spinner("Carregando resumo de VGV e Prosoluto por empreendimento..."):
        df_resumo = get_vgv_prosoluto_resumo()

    if df_resumo.empty:
        st.warning("Não há dados de VGV / Prosoluto para exibir no momento.")
        return

    # Totalizador: preencher Geral Prati com a soma de VGV dos demais empreendimentos
    mask_geral = df_resumo["nome_empreendimento"].str.strip().str.lower() == "geral prati"
    if mask_geral.any():
        outros = df_resumo[~mask_geral]
        for col in ["vgv_total", "vgv_vendido", "vgv_pendente"]:
            if col in df_resumo.columns:
                total = outros[col].fillna(0.0).sum()
                df_resumo.loc[mask_geral, col] = total

    tab_geral, tab_analise = st.tabs(["Aba geral", "Analise VGV"])

    with tab_geral:
        st.markdown("### VGV x Prosoluto por Empreendimento")
        st.caption(
            "Tabela consolidada por empreendimento usando a base de VGV (cv_vgv_empreendimentos) "
            "e a view de prosoluto antes/pós chaves. A classificação de 'VGV vendido' usa a coluna "
            "`unidades.situacao` da tabela de VGV."
        )
        col_valores = [
            "vgv_total", "vgv_vendido", "vgv_pendente",
            "prosoluto_antes", "venda_fin_antes", "prosoluto_pos",
        ]
        col_percentuais = ["pct_prosoluto_antes", "pct_prosoluto_pos"]
        df_display = _formatar_tabela_geral(df_resumo.copy(), col_valores, col_percentuais)
        st.dataframe(df_display, use_container_width=True, hide_index=True)

    with tab_analise:
        st.markdown("### Análise: Prosoluto e VGV Realizado")
        st.caption(
            "Prosoluto antes e pós chaves (valor e % sobre venda financiamento) e VGV já realizado "
            "(valor e % sobre o VGV total do empreendimento)."
        )

        empreendimentos = sorted(
            df_resumo["nome_empreendimento"].dropna().astype(str).str.strip().unique()
        )
        empreendimentos_filtro = st.multiselect(
            "Filtrar por empreendimento",
            options=empreendimentos,
            default=[],
            placeholder="Selecione um ou mais empreendimentos (vazio = todos)",
            help="Filtros para tomada de decisão pela diretoria.",
        )
        df_analise_base = df_resumo.copy()
        if empreendimentos_filtro:
            df_analise_base = df_analise_base[
                df_analise_base["nome_empreendimento"].str.strip().isin(empreendimentos_filtro)
            ]
        if df_analise_base.empty:
            st.info("Nenhum empreendimento encontrado para os filtros selecionados.")
        else:
            df_analise = _montar_tabela_analise(df_analise_base)
            st.dataframe(df_analise, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()

