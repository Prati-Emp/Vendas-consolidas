"""
Página de Tabela Hierárquica com Drill-Down
Sistema de análise de vendas com expand/collapse por níveis.
"""

import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode
from typing import Dict, List, Any
import json

# Importar utilitários locais
from utils.md_conn import get_base_data
from utils.formatters import (
    fmt_brl, 
    fmt_int, 
    fmt_number,
    format_ag_grid_currency,
    format_ag_grid_number,
    format_ag_grid_decimal
)

# Configuração da página
st.set_page_config(
    page_title="Tabela Drill-Down - Vendas Consolidadas",
    page_icon="📋",
    layout="wide"
)

# CSS customizado para a página
st.markdown("""
<style>
    .drilldown-header {
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .hierarchy-info {
        background-color: #e3f2fd;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin: 1rem 0;
    }
    .export-section {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .aggrid-container {
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

def get_session_filters():
    """Obtém filtros da sessão principal."""
    return {
        'data_inicial': st.session_state.get('data_inicial'),
        'data_final': st.session_state.get('data_final'),
        'midia_selecionada': st.session_state.get('midia_selecionada', []),
        'tipovenda_selecionada': st.session_state.get('tipovenda_selecionada', [])
    }

def prepare_drilldown_data(df: pd.DataFrame, show_levels: list = [1]) -> pd.DataFrame:
    """
    Prepara dados para drill-down hierárquico com controle de níveis visíveis.
    
    Args:
        df: DataFrame com dados base
        show_levels: Lista de níveis para mostrar (1=Empreendimento, 2=Imobiliária, etc.)
        
    Returns:
        DataFrame preparado para drill-down
    """
    if df.empty:
        return pd.DataFrame()
    
    # Criar agregações hierárquicas
    agg_data = []
    
    # Nível 1: Empreendimento (sempre visível)
    empreendimento_data = df.groupby('nome_empreendimento').agg({
        'value': ['count', 'sum', 'mean']
    }).round(2)
    empreendimento_data.columns = ['qtd', 'valor_total', 'ticket_medio']
    empreendimento_data = empreendimento_data.reset_index()
    
    for _, row in empreendimento_data.iterrows():
        agg_data.append({
            'nivel': 'Empreendimento',
            'nome': row['nome_empreendimento'],
            'imobiliaria': '—',
            'corretor': '—',
            'bloco': '—',
            'unidade': '—',
            'qtd': int(row['qtd']),
            'valor_total': float(row['valor_total']),
            'ticket_medio': float(row['ticket_medio']),
            'level': 1,
            'empreendimento_id': row['nome_empreendimento']
        })
        
        # Nível 2: Imobiliária (só se solicitado)
        if 2 in show_levels:
            imobiliaria_data = df[df['nome_empreendimento'] == row['nome_empreendimento']].groupby('imobiliaria').agg({
                'value': ['count', 'sum', 'mean']
            }).round(2)
            imobiliaria_data.columns = ['qtd', 'valor_total', 'ticket_medio']
            imobiliaria_data = imobiliaria_data.reset_index()
            
            for _, imob_row in imobiliaria_data.iterrows():
                agg_data.append({
                    'nivel': 'Imobiliária',
                    'nome': f"  └─ {imob_row['imobiliaria']}",
                    'imobiliaria': imob_row['imobiliaria'],
                    'corretor': '—',
                    'bloco': '—',
                    'unidade': '—',
                    'qtd': int(imob_row['qtd']),
                    'valor_total': float(imob_row['valor_total']),
                    'ticket_medio': float(imob_row['ticket_medio']),
                    'level': 2,
                    'empreendimento_id': row['nome_empreendimento']
                })
                
                # Nível 3: Corretor (só se solicitado)
                if 3 in show_levels:
                    corretor_data = df[
                        (df['nome_empreendimento'] == row['nome_empreendimento']) & 
                        (df['imobiliaria'] == imob_row['imobiliaria'])
                    ].groupby('corretor').agg({
                        'value': ['count', 'sum', 'mean']
                    }).round(2)
                    corretor_data.columns = ['qtd', 'valor_total', 'ticket_medio']
                    corretor_data = corretor_data.reset_index()
                    
                    for _, corr_row in corretor_data.iterrows():
                        agg_data.append({
                            'nivel': 'Corretor',
                            'nome': f"    └─ {corr_row['corretor']}",
                            'imobiliaria': imob_row['imobiliaria'],
                            'corretor': corr_row['corretor'],
                            'bloco': '—',
                            'unidade': '—',
                            'qtd': int(corr_row['qtd']),
                            'valor_total': float(corr_row['valor_total']),
                            'ticket_medio': float(corr_row['ticket_medio']),
                            'level': 3,
                            'empreendimento_id': row['nome_empreendimento']
                        })
                        
                        # Nível 4: Bloco (só se solicitado)
                        if 4 in show_levels:
                            bloco_data = df[
                                (df['nome_empreendimento'] == row['nome_empreendimento']) & 
                                (df['imobiliaria'] == imob_row['imobiliaria']) &
                                (df['corretor'] == corr_row['corretor'])
                            ].groupby('bloco').agg({
                                'value': ['count', 'sum', 'mean']
                            }).round(2)
                            bloco_data.columns = ['qtd', 'valor_total', 'ticket_medio']
                            bloco_data = bloco_data.reset_index()
                            
                            for _, bloco_row in bloco_data.iterrows():
                                agg_data.append({
                                    'nivel': 'Bloco',
                                    'nome': f"      └─ {bloco_row['bloco']}",
                                    'imobiliaria': imob_row['imobiliaria'],
                                    'corretor': corr_row['corretor'],
                                    'bloco': bloco_row['bloco'],
                                    'unidade': '—',
                                    'qtd': int(bloco_row['qtd']),
                                    'valor_total': float(bloco_row['valor_total']),
                                    'ticket_medio': float(bloco_row['ticket_medio']),
                                    'level': 4,
                                    'empreendimento_id': row['nome_empreendimento']
                                })
                                
                                # Nível 5: Unidade (só se solicitado)
                                if 5 in show_levels:
                                    unidade_data = df[
                                        (df['nome_empreendimento'] == row['nome_empreendimento']) & 
                                        (df['imobiliaria'] == imob_row['imobiliaria']) &
                                        (df['corretor'] == corr_row['corretor']) &
                                        (df['bloco'] == bloco_row['bloco'])
                                    ]
                                    
                                    for _, unidade_row in unidade_data.iterrows():
                                        agg_data.append({
                                            'nivel': 'Unidade',
                                            'nome': f"        └─ {unidade_row['unidade']}",
                                            'imobiliaria': imob_row['imobiliaria'],
                                            'corretor': corr_row['corretor'],
                                            'bloco': bloco_row['bloco'],
                                            'unidade': unidade_row['unidade'],
                                            'qtd': 1,
                                            'valor_total': float(unidade_row['value']),
                                            'ticket_medio': float(unidade_row['value']),
                                            'level': 5,
                                            'empreendimento_id': row['nome_empreendimento']
                                        })
    
    return pd.DataFrame(agg_data)

def configure_aggrid_options():
    """Configura opções do AG Grid simplificado."""
    # Criar DataFrame de exemplo para configurar as colunas
    sample_df = pd.DataFrame({
        'nivel': ['Empreendimento'],
        'nome': ['Exemplo'],
        'qtd': [1],
        'valor_total': [1000.0],
        'ticket_medio': [1000.0]
    })
    
    gb = GridOptionsBuilder.from_dataframe(sample_df)
    
    # Configurar colunas específicas
    gb.configure_column('nivel', header_name='Nível', width=120, pinned='left')
    gb.configure_column('nome', header_name='Nome', width=300, pinned='left')
    gb.configure_column('qtd', header_name='Qtd', width=80, type='numericColumn')
    gb.configure_column('valor_total', header_name='Valor (R$)', width=120, type='numericColumn', pinned='right')
    gb.configure_column('ticket_medio', header_name='Ticket Médio (R$)', width=140, type='numericColumn')
    
    # Configurar colunas padrão
    gb.configure_default_column(
        groupable=True,
        sortable=True,
        filter=True,
        resizable=True
    )
    
    # Configurar seleção
    gb.configure_selection('multiple', use_checkbox=True)
    
    # Configurar paginação
    gb.configure_pagination(
        paginationAutoPageSize=True,
        paginationPageSize=100
    )
    
    # Configurar altura
    gb.configure_grid_options(
        domLayout='normal',
        suppressRowClickSelection=True,
        rowSelection='multiple',
        enableRangeSelection=True
    )
    
    return gb.build()

def render_hierarchy_info():
    """Renderiza informações sobre a hierarquia."""
    st.markdown("""
    <div class="hierarchy-info">
        <h4>📊 Hierarquia de Drill-Down</h4>
        <p><strong>Níveis disponíveis:</strong></p>
        <ol>
            <li><strong>Empreendimento</strong> - Nível principal (sem indentação)</li>
            <li><strong>Imobiliária</strong> - Agrupamento por imobiliária (└─ indentado)</li>
            <li><strong>Corretor</strong> - Agrupamento por corretor (└─ mais indentado)</li>
            <li><strong>Bloco</strong> - Agrupamento por bloco (└─ ainda mais indentado)</li>
            <li><strong>Unidade</strong> - Vendas individuais (└─ máximo indentado)</li>
        </ol>
        <p><strong>Como funciona:</strong> A hierarquia é mostrada através de indentação visual. 
        Cada nível é identificado pela coluna "Nível" e pela indentação na coluna "Nome". 
        Use os filtros de coluna para buscar dados específicos.</p>
    </div>
    """, unsafe_allow_html=True)

def render_export_section(df: pd.DataFrame):
    """Renderiza seção de exportação."""
    st.markdown("""
    <div class="export-section">
        <h4>📥 Exportar Dados</h4>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if not df.empty:
            csv_data = df.to_csv(index=False)
            st.download_button(
                label="📊 Baixar CSV Completo",
                data=csv_data,
                file_name=f"drilldown_vendas_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                help="Baixar todos os dados da tabela hierárquica"
            )
    
    with col2:
        if not df.empty:
            # Preparar dados para Excel (sem colunas de controle)
            excel_data = df.drop(['level', 'parent', 'path'], axis=1, errors='ignore')
            csv_excel = excel_data.to_csv(index=False)
            st.download_button(
                label="📈 Baixar Dados Limpos",
                data=csv_excel,
                file_name=f"dados_limpos_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                help="Baixar dados sem colunas de controle interno"
            )
    
    with col3:
        st.info(f"**Total de registros:** {len(df):,}")

def render_integrated_filters():
    """Renderiza filtros integrados na página."""
    st.markdown("## 🔍 Filtros e Controles")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 📅 Filtros de Dados")
        
        # Obter range de datas disponível
        try:
            from utils.md_conn import get_date_range
            data_min, data_max = get_date_range()
            data_min_dt = pd.to_datetime(data_min).date()
            data_max_dt = pd.to_datetime(data_max).date()
        except:
            data_min_dt = pd.to_datetime('2024-01-01').date()
            data_max_dt = pd.to_datetime('2025-12-31').date()
        
        # Filtros de data
        col1_1, col1_2 = st.columns(2)
        with col1_1:
            data_inicial = st.date_input(
                "Data Inicial",
                value=data_min_dt,
                min_value=data_min_dt,
                max_value=data_max_dt,
                key="drilldown_data_inicial"
            )
        with col1_2:
            data_final = st.date_input(
                "Data Final",
                value=data_max_dt,
                min_value=data_min_dt,
                max_value=data_max_dt,
                key="drilldown_data_final"
            )
        
        # Filtros opcionais
        col1_3, col1_4 = st.columns(2)
        with col1_3:
            try:
                from utils.md_conn import get_unique_values
                midias_disponiveis = get_unique_values('midia')
                midia_selecionada = st.multiselect(
                    "Mídia",
                    options=midias_disponiveis,
                    default=[],
                    key="drilldown_midia"
                )
            except:
                midia_selecionada = []
        
        with col1_4:
            try:
                tipos_disponiveis = get_unique_values('tipovenda')
                tipovenda_selecionada = st.multiselect(
                    "Tipo de Venda",
                    options=tipos_disponiveis,
                    default=[],
                    key="drilldown_tipovenda"
                )
            except:
                tipovenda_selecionada = []
    
    with col2:
        st.markdown("### 🎛️ Controles de Drill-Down")
        
        # Controles de níveis
        st.markdown("**Níveis a exibir:**")
        show_empreendimento = st.checkbox("Empreendimento", value=True, disabled=True)
        show_imobiliaria = st.checkbox("Imobiliária", value=False, key="show_imobiliaria")
        show_corretor = st.checkbox("Corretor", value=False, key="show_corretor")
        show_bloco = st.checkbox("Bloco", value=False, key="show_bloco")
        show_unidade = st.checkbox("Unidade", value=False, key="show_unidade")
        
        # Botão para aplicar
        if st.button("🔄 Aplicar Filtros e Atualizar", type="primary"):
            # Salvar filtros na sessão
            st.session_state.data_inicial = data_inicial.strftime('%Y-%m-%d')
            st.session_state.data_final = data_final.strftime('%Y-%m-%d')
            st.session_state.midia_selecionada = midia_selecionada
            st.session_state.tipovenda_selecionada = tipovenda_selecionada
            st.rerun()
    
    return {
        'data_inicial': data_inicial.strftime('%Y-%m-%d'),
        'data_final': data_final.strftime('%Y-%m-%d'),
        'midia_selecionada': midia_selecionada,
        'tipovenda_selecionada': tipovenda_selecionada,
        'show_levels': [1] + ([2] if show_imobiliaria else []) + ([3] if show_corretor else []) + ([4] if show_bloco else []) + ([5] if show_unidade else [])
    }

def main():
    """Função principal da página."""
    # Header
    st.markdown('<h1 class="drilldown-header">📋 Tabela Hierárquica com Drill-Down</h1>', unsafe_allow_html=True)
    
    # Renderizar filtros integrados
    filters = render_integrated_filters()
    
    # Verificar se filtros foram aplicados
    if not st.session_state.get('data_inicial'):
        st.info("👆 Configure os filtros acima e clique em 'Aplicar Filtros e Atualizar' para carregar os dados")
        return
    
    # Usar filtros da sessão
    session_filters = {
        'data_inicial': st.session_state.get('data_inicial'),
        'data_final': st.session_state.get('data_final'),
        'midia_selecionada': st.session_state.get('midia_selecionada', []),
        'tipovenda_selecionada': st.session_state.get('tipovenda_selecionada', [])
    }
    
    # Mostrar filtros aplicados
    st.markdown("### ✅ Filtros Aplicados")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.info(f"**Período:** {session_filters['data_inicial']} a {session_filters['data_final']}")
    
    with col2:
        midia_text = ", ".join(session_filters['midia_selecionada']) if session_filters['midia_selecionada'] else "Todas"
        st.info(f"**Mídia:** {midia_text}")
    
    with col3:
        tipovenda_text = ", ".join(session_filters['tipovenda_selecionada']) if session_filters['tipovenda_selecionada'] else "Todos"
        st.info(f"**Tipo Venda:** {tipovenda_text}")
    
    # Renderizar informações da hierarquia
    render_hierarchy_info()
    
    # Carregar dados
    with st.spinner("🔄 Carregando dados para drill-down..."):
        try:
            # Obter dados base
            base_data = get_base_data(
                session_filters['data_inicial'],
                session_filters['data_final'],
                session_filters['midia_selecionada'],
                session_filters['tipovenda_selecionada']
            )
            
            if base_data.empty:
                st.warning("⚠️ Nenhum dado encontrado para os filtros aplicados.")
                return
            
            # Preparar dados para drill-down com níveis selecionados
            drilldown_data = prepare_drilldown_data(base_data, filters['show_levels'])
            
            if drilldown_data.empty:
                st.warning("⚠️ Erro ao processar dados para drill-down.")
                return
            
            st.success(f"✅ Carregados {len(drilldown_data):,} registros hierárquicos")
            
        except Exception as e:
            st.error(f"❌ Erro ao carregar dados: {str(e)}")
            return
    
    # Configurar AG Grid
    grid_options = configure_aggrid_options()
    
    # Renderizar tabela
    st.markdown("### 📊 Tabela Hierárquica")
    
    try:
        # Renderizar AG Grid
        grid_response = AgGrid(
            drilldown_data,
            gridOptions=grid_options,
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            fit_columns_on_grid_load=True,
            height=600,
            width='100%',
            theme='streamlit',
            allow_unsafe_jscode=True,
            enable_enterprise_modules=False
        )
        
        # Mostrar informações da seleção
        if grid_response['selected_rows']:
            st.info(f"📋 {len(grid_response['selected_rows'])} linha(s) selecionada(s)")
            
            # Mostrar dados selecionados
            with st.expander("👁️ Ver Dados Selecionados"):
                selected_df = pd.DataFrame(grid_response['selected_rows'])
                st.dataframe(selected_df, width='stretch')
        
    except Exception as e:
        st.error(f"❌ Erro ao renderizar tabela: {str(e)}")
        
        # Fallback: mostrar dados em tabela simples
        st.markdown("### 📋 Dados (Visualização Simples)")
        display_data = drilldown_data.drop(['level', 'empreendimento_id'], axis=1, errors='ignore')
        st.dataframe(display_data, width='stretch')
    
    # Seção de exportação
    render_export_section(drilldown_data)
    
    # Estatísticas resumidas
    st.markdown("---")
    st.markdown("### 📈 Estatísticas Resumidas")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_vendas = drilldown_data[drilldown_data['level'] == 5]['qtd'].sum() if 5 in filters['show_levels'] else drilldown_data[drilldown_data['level'] == drilldown_data['level'].max()]['qtd'].sum()
        st.metric("Total de Vendas", fmt_int(total_vendas))
    
    with col2:
        valor_total = drilldown_data[drilldown_data['level'] == 5]['valor_total'].sum() if 5 in filters['show_levels'] else drilldown_data[drilldown_data['level'] == drilldown_data['level'].max()]['valor_total'].sum()
        st.metric("Valor Total", fmt_brl(valor_total))
    
    with col3:
        empreendimentos = drilldown_data[drilldown_data['level'] == 1]['nome'].nunique()
        st.metric("Empreendimentos", fmt_int(empreendimentos))
    
    with col4:
        imobiliarias = drilldown_data[drilldown_data['level'] == 2]['imobiliaria'].nunique() if 2 in filters['show_levels'] else 0
        st.metric("Imobiliárias", fmt_int(imobiliarias))
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; font-size: 0.8rem;'>
        📋 Tabela Hierárquica com Drill-Down | 
        🔗 Dados do MotherDuck | 
        ⏰ Atualizado em: {timestamp}
    </div>
    """.format(timestamp=pd.Timestamp.now().strftime('%d/%m/%Y %H:%M:%S')), unsafe_allow_html=True)

if __name__ == "__main__":
    main()
