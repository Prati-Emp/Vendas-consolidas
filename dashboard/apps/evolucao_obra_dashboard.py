"""
Dashboard Evolução de Obra - Comparativo Físico-Financeiro Residencial Horizont
Replica o visual do Power BI com drill-down e todas as medidas DAX.
"""

import streamlit as st
import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Any
from pathlib import Path
import sys

# Adicionar scripts ao path
scripts_dir = Path(__file__).parent.parent.parent / "scripts" / "evolucao_obra"
if str(scripts_dir) not in sys.path:
    sys.path.append(str(scripts_dir))

# Importar funções de processamento
try:
    # Tentar importar dos scripts
    import importlib.util
    scripts_dir = Path(__file__).parent.parent.parent / "scripts" / "evolucao_obra"
    
    if scripts_dir.exists():
        spec_baixar = importlib.util.spec_from_file_location("baixar_e_tratar_tabelas", scripts_dir / "baixar_e_tratar_tabelas.py")
        spec_processar = importlib.util.spec_from_file_location("processar_relacoes_tabelas", scripts_dir / "processar_relacoes_tabelas.py")
        spec_calcular = importlib.util.spec_from_file_location("calcular_medidas_dax", scripts_dir / "calcular_medidas_dax.py")
        
        if spec_baixar and spec_baixar.loader:
            mod_baixar = importlib.util.module_from_spec(spec_baixar)
            spec_baixar.loader.exec_module(mod_baixar)
            baixar_e_tratar_tabelas = mod_baixar.baixar_e_tratar_tabelas
        else:
            baixar_e_tratar_tabelas = None
            
        if spec_processar and spec_processar.loader:
            mod_processar = importlib.util.module_from_spec(spec_processar)
            spec_processar.loader.exec_module(mod_processar)
            processar_relacoes_tabelas = mod_processar.processar_relacoes_tabelas
        else:
            processar_relacoes_tabelas = None
            
        if spec_calcular and spec_calcular.loader:
            mod_calcular = importlib.util.module_from_spec(spec_calcular)
            spec_calcular.loader.exec_module(mod_calcular)
            calcular_todas_medidas = mod_calcular.calcular_todas_medidas
            aplicar_filtros_power_bi = mod_calcular.aplicar_filtros_power_bi
        else:
            calcular_todas_medidas = None
            aplicar_filtros_power_bi = None
    else:
        baixar_e_tratar_tabelas = None
        processar_relacoes_tabelas = None
        calcular_todas_medidas = None
        aplicar_filtros_power_bi = None
except Exception as e:
    st.warning(f"⚠️ Erro ao importar módulos de processamento: {e}")
    baixar_e_tratar_tabelas = None
    processar_relacoes_tabelas = None
    calcular_todas_medidas = None
    aplicar_filtros_power_bi = None

@st.cache_data(ttl=3600)  # Cache por 1 hora
def carregar_dados_consolidados() -> pd.DataFrame:
    """
    Carrega e processa todos os dados necessários
    """
    if baixar_e_tratar_tabelas is None:
        return pd.DataFrame()
    
    try:
        # Baixar e tratar tabelas
        tabelas = baixar_e_tratar_tabelas()
        
        # Processar relações
        df_consolidado = processar_relacoes_tabelas(tabelas)
        
        if df_consolidado.empty:
            return pd.DataFrame()
        
        # Aplicar filtros do Power BI
        df_filtrado = aplicar_filtros_power_bi(df_consolidado)
        
        # Calcular medidas
        df_com_medidas = calcular_todas_medidas(df_filtrado)
        
        return df_com_medidas
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados: {e}")
        return pd.DataFrame()

def formatar_moeda(valor: float) -> str:
    """Formata valor como moeda brasileira: R$ 1.234.567,89"""
    if pd.isna(valor) or valor == 0:
        return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def formatar_percentual(valor: float, decimais: int = 2) -> str:
    """Formata valor como percentual: 45,91%"""
    if pd.isna(valor):
        return "0,00%"
    return f"{valor:,.{decimais}f}%".replace('.', ',')

def formatar_idc(valor: float) -> str:
    """Formata IDC como percentual sem decimais: 145%"""
    if pd.isna(valor):
        return "0%"
    return f"{int(round(valor))}%"

def aplicar_drill_down(df: pd.DataFrame, nivel_drill: List[str]) -> pd.DataFrame:
    """
    Aplica filtros baseados no nível de drill-down atual
    """
    df_filtrado = df.copy()
    
    # Nível 0: Mostrar tudo
    if len(nivel_drill) == 0:
        return df_filtrado
    
    # Nível 1: Filtrar por Unidade Construtiva
    if len(nivel_drill) >= 1:
        col_unidade = None
        for col in df_filtrado.columns:
            if 'unidade' in col.lower() and 'construtiva' in col.lower():
                col_unidade = col
                break
        
        if col_unidade:
            df_filtrado = df_filtrado[
                df_filtrado[col_unidade].astype(str).str.strip() == nivel_drill[0]
            ]
    
    # Nível 2: Filtrar por Célula Construtiva
    if len(nivel_drill) >= 2:
        col_celula = None
        for col in df_filtrado.columns:
            if 'célula' in col.lower() or 'celula' in col.lower():
                col_celula = col
                break
        
        if col_celula:
            df_filtrado = df_filtrado[
                df_filtrado[col_celula].astype(str).str.strip() == nivel_drill[1]
            ]
    
    # Nível 3: Filtrar por Etapa
    if len(nivel_drill) >= 3:
        if 'Etapa' in df_filtrado.columns:
            df_filtrado = df_filtrado[
                df_filtrado['Etapa'].astype(str).str.strip() == nivel_drill[2]
            ]
    
    # Nível 4: Filtrar por Subetapa
    if len(nivel_drill) >= 4:
        if 'Subetapa' in df_filtrado.columns:
            df_filtrado = df_filtrado[
                df_filtrado['Subetapa'].astype(str).str.strip() == nivel_drill[3]
            ]
    
    # Nível 5: Filtrar por Serviço
    if len(nivel_drill) >= 5:
        if 'Serviço' in df_filtrado.columns:
            df_filtrado = df_filtrado[
                df_filtrado['Serviço'].astype(str).str.strip() == nivel_drill[4]
            ]
    
    return df_filtrado

def obter_valores_unicos_hierarquia(df: pd.DataFrame, nivel: int) -> List[str]:
    """
    Obtém valores únicos para um nível específico da hierarquia
    """
    df_filtrado = df.copy()
    
    # Aplicar filtros dos níveis anteriores
    if 'nivel_drill' in st.session_state:
        df_filtrado = aplicar_drill_down(df_filtrado, st.session_state['nivel_drill'])
    
    # Identificar coluna do nível
    colunas_niveis = [
        ('unidade', 'construtiva'),
        ('célula', 'construtiva'),
        ('etapa',),
        ('subetapa',),
        ('serviço',)
    ]
    
    if nivel < len(colunas_niveis):
        termos = colunas_niveis[nivel]
        for col in df_filtrado.columns:
            col_lower = col.lower()
            if all(termo in col_lower for termo in termos):
                valores = df_filtrado[col].dropna().unique().tolist()
                return sorted([str(v).strip() for v in valores if str(v).strip()])
    
    return []

def render_breadcrumb(nivel_drill: List[str]):
    """Renderiza breadcrumb mostrando caminho atual"""
    if len(nivel_drill) == 0:
        st.caption("📊 Visão Geral - Todas as Unidades Construtivas")
    else:
        caminho = " > ".join(nivel_drill)
        st.caption(f"📊 {caminho}")

def render_evolucao_obra_dashboard(
    *,
    show_title: bool = True,
    show_caption: bool = True,
):
    """
    Renderiza o dashboard de Evolução de Obra com drill-down.
    """
    if show_title:
        st.title("🏗️ Evolução de Obra")
        if show_caption:
            st.caption("COMPARATIVO FÍSICO - FINANCEIRO RESIDENCIAL HORIZONT")
    
    # Inicializar estado do drill-down
    if 'nivel_drill' not in st.session_state:
        st.session_state['nivel_drill'] = []
    
    # Carregar dados
    with st.spinner("📥 Carregando dados..."):
        df = carregar_dados_consolidados()
    
    if df.empty:
        st.warning("⚠️ Nenhum dado encontrado. Verifique a conexão com o banco de dados.")
        return
    
    # Sidebar - Controles
    with st.sidebar:
        st.header("🔍 Filtros")
        
        # Botão para voltar um nível
        if len(st.session_state['nivel_drill']) > 0:
            if st.button("⬅️ Voltar", use_container_width=True):
                st.session_state['nivel_drill'] = st.session_state['nivel_drill'][:-1]
                st.rerun()
        
        # Seleção de Unidade Construtiva (se no nível 0)
        if len(st.session_state['nivel_drill']) == 0:
            unidades = obter_valores_unicos_hierarquia(df, 0)
            if unidades:
                unidade_selecionada = st.selectbox(
                    "Unidade Construtiva",
                    options=["Todas"] + unidades
                )
                if unidade_selecionada != "Todas":
                    st.session_state['nivel_drill'] = [unidade_selecionada]
                    st.rerun()
    
    # Breadcrumb
    render_breadcrumb(st.session_state['nivel_drill'])
    
    # Aplicar drill-down
    df_filtrado = aplicar_drill_down(df, st.session_state['nivel_drill'])
    
    if df_filtrado.empty:
        st.info("ℹ️ Nenhum dado encontrado para os filtros selecionados.")
        return
    
    # Calcular métricas resumidas
    total_orcamento = df_filtrado['Orçamento'].sum() if 'Orçamento' in df_filtrado.columns else 0
    total_realizado = df_filtrado['Realizado'].sum() if 'Realizado' in df_filtrado.columns else 0
    
    conclusao_financeira_geral = (total_realizado / total_orcamento * 100) if total_orcamento > 0 else 0
    conclusao_fisica_geral = df_filtrado['Conclusão Física'].mean() if 'Conclusão Física' in df_filtrado.columns else 0
    idc_geral = (conclusao_financeira_geral / conclusao_fisica_geral * 100) if conclusao_fisica_geral > 0 else 0
    
    # Cards com métricas principais
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Orçamento", formatar_moeda(total_orcamento))
    
    with col2:
        st.metric("Total Realizado", formatar_moeda(total_realizado))
    
    with col3:
        st.metric("Conclusão Financeira", formatar_percentual(conclusao_financeira_geral))
    
    with col4:
        st.metric("Conclusão Física", formatar_percentual(conclusao_fisica_geral))
    
    with col5:
        st.metric("IDC", formatar_idc(idc_geral))
    
    st.markdown("---")
    
    # Tabela principal
    st.subheader("📊 Tabela Detalhada")
    
    # Preparar colunas para exibição
    colunas_exibicao = []
    colunas_hierarquia = [
        ('unidade', 'construtiva'),
        ('célula', 'construtiva'),
        ('etapa',),
        ('subetapa',),
        ('serviço',)
    ]
    
    # Adicionar colunas de hierarquia
    for termos in colunas_hierarquia:
        for col in df_filtrado.columns:
            col_lower = col.lower()
            if all(termo in col_lower for termo in termos):
                if col not in colunas_exibicao:
                    colunas_exibicao.append(col)
                break
    
    # Adicionar colunas de medidas
    if 'Orçamento' in df_filtrado.columns:
        colunas_exibicao.append('Orçamento')
    if 'Realizado' in df_filtrado.columns:
        colunas_exibicao.append('Realizado')
    if 'Conclusão Financeira' in df_filtrado.columns:
        colunas_exibicao.append('Conclusão Financeira')
    if 'Conclusão Física' in df_filtrado.columns:
        colunas_exibicao.append('Conclusão Física')
    if 'IDC' in df_filtrado.columns:
        colunas_exibicao.append('IDC')
    
    # Filtrar apenas colunas que existem
    colunas_exibicao = [col for col in colunas_exibicao if col in df_filtrado.columns]
    
    if not colunas_exibicao:
        st.warning("⚠️ Nenhuma coluna disponível para exibição.")
        return
    
    df_exibicao = df_filtrado[colunas_exibicao].copy()
    
    # Formatar valores
    if 'Orçamento' in df_exibicao.columns:
        df_exibicao['Orçamento'] = df_exibicao['Orçamento'].apply(formatar_moeda)
    if 'Realizado' in df_exibicao.columns:
        df_exibicao['Realizado'] = df_exibicao['Realizado'].apply(formatar_moeda)
    if 'Conclusão Financeira' in df_exibicao.columns:
        df_exibicao['Conclusão Financeira'] = df_exibicao['Conclusão Financeira'].apply(
            lambda x: formatar_percentual(x) if isinstance(x, (int, float)) else x
        )
    if 'Conclusão Física' in df_exibicao.columns:
        df_exibicao['Conclusão Física'] = df_exibicao['Conclusão Física'].apply(
            lambda x: formatar_percentual(x) if isinstance(x, (int, float)) else x
        )
    if 'IDC' in df_exibicao.columns:
        df_exibicao['IDC'] = df_exibicao['IDC'].apply(
            lambda x: formatar_idc(x) if isinstance(x, (int, float)) else x
        )
    
    # Exibir tabela
    st.dataframe(
        df_exibicao,
        use_container_width=True,
        hide_index=True,
        height=400
    )
    
    # Botão de exportação
    col1, col2 = st.columns([1, 4])
    with col1:
        csv = df_filtrado.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 Exportar CSV",
            data=csv,
            file_name="evolucao_obra.csv",
            mime="text/csv"
        )
