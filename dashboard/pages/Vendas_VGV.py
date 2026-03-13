"""
Página dedicada às informações de VGV (Valor Geral de Vendas).
Exibe apenas a tabela consolidada VGV x Prosoluto por empreendimento (sem uso de data nem tabela de vendas).
"""

from pathlib import Path
import sys

import pandas as pd
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
from utils.md_conn import get_vgv_prosoluto_resumo, get_vgv_por_situacao  # noqa: E402
from utils.formatters import format_brl, format_percent  # noqa: E402


def _formatar_tabela_geral(df, col_valores, col_percentuais):
    """Formata e ordena a tabela da aba geral."""
    venda_fin = df["venda_fin_antes"].fillna(0.0)
    prosoluto_total = df["prosoluto_antes"].fillna(0.0) + df["prosoluto_pos"].fillna(0.0)
    df["pct_total_prosoluto"] = 0.0
    mask = venda_fin > 0
    df.loc[mask, "pct_total_prosoluto"] = (prosoluto_total[mask] / venda_fin[mask]).values

    vgv_total = df["vgv_total"].fillna(0.0)
    vgv_vendido = df["vgv_vendido"].fillna(0.0)
    df["pct_vgv_realizado"] = 0.0
    mask_vgv = vgv_total > 0
    df.loc[mask_vgv, "pct_vgv_realizado"] = (vgv_vendido[mask_vgv] / vgv_total[mask_vgv]).values

    for col in col_valores:
        if col in df.columns:
            df[col] = df[col].fillna(0.0).apply(format_brl)
    for col in col_percentuais + ["pct_total_prosoluto", "pct_vgv_realizado"]:
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
        "pct_total_prosoluto": "% total prosoluto",
        "pct_vgv_realizado": "% VGV realizado",
    })
    df = df.drop(columns=["venda_fin_pos"], errors="ignore")
    ordem = [
        "ID", "Empreendimento", "VGV Total", "VGV Vendido", "VGV Pendente",
        "% VGV realizado",
        "Prosoluto antes chaves", "Prosoluto pós chaves",
        "% Prosoluto antes chaves", "% Prosoluto pós chaves", "% total prosoluto",
        "Venda financiamento",
    ]
    return df[[c for c in ordem if c in df.columns]]


def _montar_tabela_analise(df):
    """Monta tabela de análise: Prosoluto (apenas %) e % VGV realizado."""
    df = df.copy()
    vgv_total = df["vgv_total"].fillna(0.0)
    vgv_vendido = df["vgv_vendido"].fillna(0.0)
    df["pct_vgv_realizado"] = 0.0
    mask = vgv_total > 0
    df.loc[mask, "pct_vgv_realizado"] = (vgv_vendido[mask] / vgv_total[mask]).values

    venda_fin = df["venda_fin_antes"].fillna(0.0)
    prosoluto_total = df["prosoluto_antes"].fillna(0.0) + df["prosoluto_pos"].fillna(0.0)
    df["pct_total_prosoluto"] = 0.0
    mask_vf = venda_fin > 0
    df.loc[mask_vf, "pct_total_prosoluto"] = (prosoluto_total[mask_vf] / venda_fin[mask_vf]).values

    pct_pos = df["pct_prosoluto_pos"].fillna(0.0)
    pct_antes = df["pct_prosoluto_antes"].fillna(0.0)
    mask_pós_maior = pct_pos > pct_antes
    mask_pós_menor = pct_pos < pct_antes
    for col in ["pct_prosoluto_antes", "pct_prosoluto_pos", "pct_vgv_realizado", "pct_total_prosoluto"]:
        if col in df.columns:
            df[col] = df[col].fillna(0.0).apply(
                lambda v: format_percent(v, decimals=2, decimal_sep_comma=True)
            )
    df = df.rename(columns={
        "nome_empreendimento": "Empreendimento",
        "pct_prosoluto_antes": "% Prosoluto antes chaves",
        "pct_prosoluto_pos": "% Prosoluto pós chaves",
        "pct_total_prosoluto": "% total prosoluto",
        "pct_vgv_realizado": "% VGV realizado",
    })
    ordem = [
        "Empreendimento",
        "% total prosoluto",
        "% Prosoluto antes chaves", "% Prosoluto pós chaves",
        "% VGV realizado",
    ]
    df_out = df[[c for c in ordem if c in df.columns]]
    def _cor_celula(i):
        if mask_pós_maior.iloc[i]:
            return "color: #d97706; font-weight: 500"  # âmbar (atenção) - só o valor
        if mask_pós_menor.iloc[i]:
            return "color: #60a5fa; font-weight: 500"  # azul suave - só o valor
        return ""

    colunas_centro = ["% total prosoluto", "% Prosoluto antes chaves", "% Prosoluto pós chaves", "% VGV realizado"]
    styled = (
        df_out.style.apply(
            lambda s: [_cor_celula(i) for i in range(len(s))],
            subset=["% Prosoluto pós chaves"],
        )
        .set_properties(subset=colunas_centro, **{"text-align": "center"})
    )
    try:
        styled = styled.hide(axis="index")
    except AttributeError:
        try:
            styled = styled.hide_index()
        except AttributeError:
            pass
    return styled


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

    tab_analise, tab_geral = st.tabs(["Analise VGV", "Aba geral"])

    with tab_geral:
        st.markdown("### VGV por Situação")
        df_vgv_sit = get_vgv_por_situacao()
        if not df_vgv_sit.empty:
            mask_geral_sit = df_vgv_sit["nome_empreendimento"].str.strip().str.lower() == "geral prati"
            if mask_geral_sit.any():
                outros_sit = df_vgv_sit[~mask_geral_sit]
                agg_outros = outros_sit.groupby("situacao", as_index=False)["valor"].sum()
                agg_outros["nome_empreendimento"] = "Geral Prati"
                agg_outros = agg_outros[["nome_empreendimento", "situacao", "valor"]]
                df_vgv_sit = pd.concat([
                    df_vgv_sit[~mask_geral_sit],
                    agg_outros,
                ], ignore_index=True)
            situacoes_vendido = {"vendido", "vendida", "assinado", "escriturado"}
            pivot = df_vgv_sit.pivot_table(
                index=["nome_empreendimento"],
                columns="situacao",
                values="valor",
                aggfunc="sum",
                fill_value=0.0,
            ).reset_index()
            vgv_total_col = pivot.drop(columns=["nome_empreendimento"]).sum(axis=1)
            cols_vendido = [
                c for c in pivot.columns
                if c != "nome_empreendimento" and str(c).strip().lower() in situacoes_vendido
            ]
            vgv_vendido_col = (
                pivot[cols_vendido].sum(axis=1)
                if cols_vendido
                else pd.Series(0.0, index=pivot.index)
            )
            pivot.insert(1, "VGV Total", vgv_total_col)
            pivot.insert(2, "VGV Vendido", vgv_vendido_col)
            cols_situacao = [c for c in pivot.columns if c not in ("nome_empreendimento", "VGV Total", "VGV Vendido")]
            for c in cols_situacao:
                pivot = pivot.rename(columns={c: f"VGV {c}"})
            pivot = pivot.rename(columns={"nome_empreendimento": "Empreendimento"})
            for col in ["VGV Total", "VGV Vendido"] + [c for c in pivot.columns if c.startswith("VGV ") and c not in ("VGV Total", "VGV Vendido")]:
                pivot[col] = pivot[col].fillna(0.0).apply(format_brl)
            st.dataframe(pivot, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum dado de VGV por situação disponível.")

        st.markdown("---")
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

        df_com_prosoluto = df_resumo[
            (df_resumo["pct_prosoluto_antes"].fillna(0) != 0)
            | (df_resumo["pct_prosoluto_pos"].fillna(0) != 0)
        ]
        empreendimentos = sorted(
            df_com_prosoluto["nome_empreendimento"].dropna().astype(str).str.strip().unique()
        )
        empreendimentos_filtro = st.multiselect(
            "Filtrar por empreendimento",
            options=empreendimentos,
            default=[],
            placeholder="Selecione um ou mais empreendimentos (vazio = todos)",
        )
        df_analise_base = df_resumo.copy()
        if empreendimentos_filtro:
            df_analise_base = df_analise_base[
                df_analise_base["nome_empreendimento"].str.strip().isin(empreendimentos_filtro)
            ]
        df_analise_base = df_analise_base[
            (df_analise_base["pct_prosoluto_antes"].fillna(0) != 0)
            | (df_analise_base["pct_prosoluto_pos"].fillna(0) != 0)
        ]
        mask_geral_analise = df_analise_base["nome_empreendimento"].str.strip().str.lower() == "geral prati"
        if mask_geral_analise.any():
            outros_analise = df_analise_base[~mask_geral_analise]
            for col in ["vgv_total", "vgv_vendido"]:
                if col in df_analise_base.columns:
                    total = outros_analise[col].fillna(0.0).sum()
                    df_analise_base.loc[mask_geral_analise, col] = total
        if df_analise_base.empty:
            st.info(
                "Nenhum empreendimento encontrado. Esta aba exibe apenas empreendimentos com "
                "% Prosoluto antes ou pós chaves diferente de zero."
            )
        else:
            df_analise = _montar_tabela_analise(df_analise_base)
            # st.dataframe não aplica text-align do Styler; st.markdown com to_html() preserva
            st.markdown(
                '<div style="overflow-x: auto; width: 100%;">' + df_analise.to_html() + "</div>",
                unsafe_allow_html=True,
            )
            st.caption(
                "💡 % VGV realizado: valor realizado apenas das incorporações, sem loteamentos."
            )

            vgv_total_sum = df_analise_base["vgv_total"].fillna(0.0).sum()
            vgv_vendido_sum = df_analise_base["vgv_vendido"].fillna(0.0).sum()
            pct_bar = (vgv_vendido_sum / vgv_total_sum * 100) if vgv_total_sum > 0 else 0.0
            label_bar = "Geral Prati" if not empreendimentos_filtro else (
                empreendimentos_filtro[0] if len(empreendimentos_filtro) == 1
                else f"{len(empreendimentos_filtro)} empreendimentos selecionados"
            )
            _render_barra_vgv(label_bar, pct_bar, vgv_vendido_sum, vgv_total_sum)


def _render_barra_vgv(label: str, pct: float, vgv_vendido: float, vgv_total: float):
    """Renderiza barra de evolução do VGV realizado (adaptada para tema claro e escuro)."""
    pct_clamped = min(100.0, max(0.0, pct))
    st.markdown(
        """
        <style>
        .vgv-bar-container {
            margin-top: 1.5rem; padding: 0.75rem 1rem; border-radius: 8px;
            background: #f0f2f6; border: 1px solid #e5e7eb;
        }
        .vgv-bar-label { font-size: 0.9rem; margin-bottom: 0.4rem; color: #6b7280; }
        .vgv-bar-value { font-weight: 600; min-width: 4rem; color: #1f2937; }
        .vgv-bar-track { flex: 1; height: 20px; border-radius: 10px; overflow: hidden; background: #e5e7eb; }
        .vgv-bar-fill { height: 100%; border-radius: 10px; transition: width 0.3s; background: linear-gradient(90deg, #10b981, #059669); }
        .vgv-bar-caption { font-size: 0.8rem; margin-top: 0.35rem; color: #6b7280; }
        @media (prefers-color-scheme: dark) {
            .vgv-bar-container {
                background: rgba(49,51,63,0.6); border-color: rgba(75,85,99,0.5);
            }
            .vgv-bar-label { color: #9ca3af; }
            .vgv-bar-value { color: #e5e7eb; }
            .vgv-bar-track { background: #374151; }
            .vgv-bar-caption { color: #6b7280; }
        }
        </style>
        """
        f"""
        <div class="vgv-bar-container">
            <div class="vgv-bar-label">{label}</div>
            <div style="display: flex; align-items: center; gap: 0.75rem;">
                <div class="vgv-bar-track">
                    <div class="vgv-bar-fill" style="width: {pct_clamped:.1f}%;"></div>
                </div>
                <span class="vgv-bar-value">{pct_clamped:.1f}%</span>
            </div>
            <div class="vgv-bar-caption">VGV realizado / VGV total</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()

