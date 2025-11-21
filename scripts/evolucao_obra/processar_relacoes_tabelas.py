#!/usr/bin/env python3
"""
FASE 1.2: Processar Relações entre Tabelas
Identifica chaves de relacionamento e cria tabela consolidada.
"""

import pandas as pd
from typing import Dict, Optional

def processar_relacoes_tabelas(tabelas: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Processa relações entre tabelas e cria tabela consolidada.
    
    Chaves de relacionamento:
    - Orcamento ↔ Apropriação: Unidade Construtiva, Célula Construtiva, Etapa, Subetapa, Serviço
    - Orcamento ↔ Medições: Unidade_Construtiva, wbsCode (se disponível)
    - Apropriação ↔ Estoque: Unidade construtiva
    """
    df_orcamento = tabelas.get('orcamento_horizont', pd.DataFrame())
    df_apropricao = tabelas.get('apropricao_horizont', pd.DataFrame())
    df_medicoes = tabelas.get('sienge_medicoes', pd.DataFrame())
    df_estoque = tabelas.get('estoque_horizont', pd.DataFrame())
    
    if df_orcamento.empty:
        print("⚠️ Tabela orcamento_horizont está vazia")
        return pd.DataFrame()
    
    # Começar com orcamento como base
    df_consolidado = df_orcamento.copy()
    
    # Normalizar nomes de colunas para matching
    def normalizar_coluna(df: pd.DataFrame, col_name: str) -> Optional[str]:
        """Encontra coluna similar (case-insensitive)"""
        for col in df.columns:
            if col.lower().replace('_', ' ').replace('-', ' ') == col_name.lower().replace('_', ' ').replace('-', ' '):
                return col
        return None
    
    # JOIN com Apropriação
    if not df_apropricao.empty:
        print("🔗 Fazendo JOIN com apropricao_horizont...")
        
        # Identificar colunas de relacionamento
        cols_relacao = [
            'Unidade construtiva', 'Célula construtiva', 'Etapa', 'Subetapa', 'Serviço'
        ]
        
        # Normalizar colunas em ambos DataFrames
        cols_orc = {}
        cols_aprop = {}
        
        for col_rel in cols_relacao:
            col_orc = normalizar_coluna(df_orcamento, col_rel)
            col_aprop = normalizar_coluna(df_apropricao, col_rel)
            
            if col_orc and col_aprop:
                cols_orc[col_rel] = col_orc
                cols_aprop[col_rel] = col_aprop
        
        if cols_orc and cols_aprop:
            # Preparar DataFrame de apropriação para merge
            df_aprop_merge = df_apropricao.copy()
            
            # Renomear colunas de apropriação para evitar conflitos
            rename_map = {}
            for col_rel, col_aprop in cols_aprop.items():
                if col_aprop in df_aprop_merge.columns:
                    rename_map[col_aprop] = f"{col_rel}_aprop"
            
            df_aprop_merge = df_aprop_merge.rename(columns=rename_map)
            
            # Criar chaves de merge
            for col_rel, col_orc in cols_orc.items():
                if col_orc in df_consolidado.columns:
                    col_aprop_renamed = f"{col_rel}_aprop"
                    if col_aprop_renamed in df_aprop_merge.columns:
                        # Normalizar valores para matching
                        df_consolidado[f"{col_rel}_key"] = df_consolidado[col_orc].astype(str).str.strip().str.upper()
                        df_aprop_merge[f"{col_rel}_key"] = df_aprop_merge[col_aprop_renamed].astype(str).str.strip().str.upper()
            
            # Fazer merge
            merge_cols = [f"{col}_key" for col in cols_relacao if f"{col}_key" in df_consolidado.columns]
            if merge_cols:
                df_consolidado = df_consolidado.merge(
                    df_aprop_merge,
                    on=merge_cols,
                    how='left',
                    suffixes=('', '_aprop')
                )
                
                # Limpar colunas auxiliares
                df_consolidado = df_consolidado.drop(columns=[col for col in df_consolidado.columns if col.endswith('_key')])
                
                print(f"   ✅ {len(df_consolidado)} registros após JOIN com apropriação")
    
    # JOIN com Medições
    if not df_medicoes.empty:
        print("🔗 Fazendo JOIN com sienge_medicoes...")
        
        # Identificar coluna de relacionamento
        col_unidade_orc = normalizar_coluna(df_consolidado, 'Unidade construtiva')
        col_unidade_med = normalizar_coluna(df_medicoes, 'Unidade_Construtiva')
        
        if col_unidade_orc and col_unidade_med:
            # Agrupar medições por Unidade_Construtiva
            df_med_agg = df_medicoes.groupby(col_unidade_med).agg({
                'Percentual_Realizado': 'mean'  # Média do percentual realizado
            }).reset_index()
            
            # Normalizar para matching
            df_consolidado['unidade_key'] = df_consolidado[col_unidade_orc].astype(str).str.strip().str.upper()
            df_med_agg['unidade_key'] = df_med_agg[col_unidade_med].astype(str).str.strip().str.upper()
            
            # Fazer merge
            df_consolidado = df_consolidado.merge(
                df_med_agg[['unidade_key', 'Percentual_Realizado']],
                on='unidade_key',
                how='left'
            )
            
            # Limpar coluna auxiliar
            df_consolidado = df_consolidado.drop(columns=['unidade_key'])
            
            print(f"   ✅ {len(df_consolidado)} registros após JOIN com medições")
    
    # JOIN com Estoque (opcional, se necessário)
    if not df_estoque.empty:
        print("🔗 Fazendo JOIN com estoque_horizont...")
        
        col_unidade_orc = normalizar_coluna(df_consolidado, 'Unidade construtiva')
        col_unidade_est = normalizar_coluna(df_estoque, 'Unidade construtiva')
        
        if col_unidade_orc and col_unidade_est:
            # Agrupar estoque por Unidade construtiva
            df_est_agg = df_estoque.groupby(col_unidade_est).agg({
                'Quantidade apropriada': 'sum',
                'Custo total': 'sum',
                'Status_Apropriacao': lambda x: 'Com Apropriação' if (x == 'Com Apropriação').any() else 'Sem Apropriação'
            }).reset_index()
            
            # Normalizar para matching
            df_consolidado['unidade_key'] = df_consolidado[col_unidade_orc].astype(str).str.strip().str.upper()
            df_est_agg['unidade_key'] = df_est_agg[col_unidade_est].astype(str).str.strip().str.upper()
            
            # Fazer merge
            df_consolidado = df_consolidado.merge(
                df_est_agg[['unidade_key', 'Quantidade apropriada', 'Custo total', 'Status_Apropriacao']],
                on='unidade_key',
                how='left'
            )
            
            # Limpar coluna auxiliar
            df_consolidado = df_consolidado.drop(columns=['unidade_key'])
            
            print(f"   ✅ {len(df_consolidado)} registros após JOIN com estoque")
    
    print(f"\n✅ Tabela consolidada criada com {len(df_consolidado)} registros")
    print(f"   Colunas: {', '.join(df_consolidado.columns.tolist()[:10])}...")
    
    return df_consolidado

if __name__ == "__main__":
    from baixar_e_tratar_tabelas import baixar_e_tratar_tabelas
    
    print("📊 Processando relações entre tabelas...\n")
    tabelas = baixar_e_tratar_tabelas()
    df_consolidado = processar_relacoes_tabelas(tabelas)
    
    if not df_consolidado.empty:
        # Salvar tabela consolidada
        from pathlib import Path
        output_dir = Path(__file__).parent.parent.parent / "dados_tratados"
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / "tabela_consolidada.csv"
        df_consolidado.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"\n💾 Tabela consolidada salva em: {output_path}")

