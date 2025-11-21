#!/usr/bin/env python3
"""
FASE 2: Replicar Medidas DAX
Calcula todas as medidas necessárias para o visual.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional

def calcular_orcamento(df: pd.DataFrame) -> pd.Series:
    """
    Medida: Orçamento
    CountNonNull(Orcamento_base_horizont.Orcamento + contingência)
    """
    col_orcamento = None
    for col in df.columns:
        if 'orcamento' in col.lower() and 'contingência' in col.lower():
            col_orcamento = col
            break
        elif 'orcamento' in col.lower() and 'contingencia' in col.lower():
            col_orcamento = col
            break
    
    if col_orcamento:
        return df[col_orcamento].fillna(0)
    else:
        # Tentar encontrar coluna de orçamento
        for col in df.columns:
            if 'preço total' in col.lower() or 'preco total' in col.lower():
                return df[col].fillna(0)
    
    return pd.Series([0] * len(df))

def calcular_realizado(df: pd.DataFrame) -> pd.Series:
    """
    Medida: Realizado
    Custos_Horizont.Apropriações_Horizont
    Soma de valores da tabela apropricao_horizont
    """
    # Procurar coluna de valor da apropriação
    col_valor = None
    for col in df.columns:
        if 'valor' in col.lower() and ('aprop' in col.lower() or 'apropriacao' in col.lower()):
            col_valor = col
            break
    
    if not col_valor:
        # Tentar encontrar qualquer coluna de valor
        for col in df.columns:
            if col.lower() == 'valor':
                col_valor = col
                break
    
    if col_valor:
        # Aplicar filtros (já devem estar aplicados no tratamento, mas garantir)
        df_filtrado = df.copy()
        
        if 'Serviço' in df_filtrado.columns:
            df_filtrado = df_filtrado[~df_filtrado['Serviço'].isin(['Comissões', 'Devolução apartamentos', 'Imposto sobre vendas'])]
        
        if 'Credor/Histórico' in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado['Credor/Histórico'] != 'Pagamento - DÉBITO AMORTIZAÇÃO PJ']
        
        return df_filtrado[col_valor].fillna(0)
    else:
        return pd.Series([0] * len(df))

def calcular_conclusao_financeira(realizado: pd.Series, orcamento: pd.Series) -> pd.Series:
    """
    Medida: Conclusão Financeira
    Fórmula: (Realizado / Orçamento) * 100
    Formato: 0.00% (duas casas decimais)
    """
    # Tratar divisão por zero
    resultado = np.where(
        orcamento != 0,
        (realizado / orcamento) * 100,
        0
    )
    return pd.Series(resultado)

def calcular_conclusao_fisica(df: pd.DataFrame) -> pd.Series:
    """
    Medida: Conclusão Física
    Medicao_Horizont.Medicao_fisica_hr
    Usa Percentual_Realizado da tabela sienge_medicoes
    """
    # Procurar coluna Percentual_Realizado
    col_percentual = None
    for col in df.columns:
        if 'percentual' in col.lower() and 'realizado' in col.lower():
            col_percentual = col
            break
    
    if col_percentual:
        return df[col_percentual].fillna(0)
    else:
        return pd.Series([0] * len(df))

def calcular_idc(conclusao_financeira: pd.Series, conclusao_fisica: pd.Series) -> pd.Series:
    """
    Medida: IDC (Índice de Desvio de Custo)
    Fórmula: (Conclusão Financeira / Conclusão Física) * 100
    Formato: 0% (sem casas decimais)
    """
    # Tratar divisão por zero
    resultado = np.where(
        conclusao_fisica != 0,
        (conclusao_financeira / conclusao_fisica) * 100,
        0
    )
    return pd.Series(resultado)

def calcular_todas_medidas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula todas as medidas DAX e adiciona ao DataFrame
    """
    df_resultado = df.copy()
    
    print("📊 Calculando medidas DAX...")
    
    # 1. Orçamento
    print("   1. Orçamento...")
    df_resultado['Orçamento'] = calcular_orcamento(df_resultado)
    
    # 2. Realizado
    print("   2. Realizado...")
    df_resultado['Realizado'] = calcular_realizado(df_resultado)
    
    # 3. Conclusão Financeira
    print("   3. Conclusão Financeira...")
    df_resultado['Conclusão Financeira'] = calcular_conclusao_financeira(
        df_resultado['Realizado'],
        df_resultado['Orçamento']
    )
    
    # 4. Conclusão Física
    print("   4. Conclusão Física...")
    df_resultado['Conclusão Física'] = calcular_conclusao_fisica(df_resultado)
    
    # 5. IDC
    print("   5. IDC...")
    df_resultado['IDC'] = calcular_idc(
        df_resultado['Conclusão Financeira'],
        df_resultado['Conclusão Física']
    )
    
    print("✅ Todas as medidas foram calculadas!")
    
    return df_resultado

def aplicar_filtros_power_bi(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica filtros do Power BI conforme especificação
    """
    df_filtrado = df.copy()
    
    # 1. Célula Construtiva = 'FECHAMENTOS E ACABAMENTOS' (fixo)
    col_celula = None
    for col in df_filtrado.columns:
        if 'célula' in col.lower() or 'celula' in col.lower():
            col_celula = col
            break
    
    if col_celula:
        df_filtrado = df_filtrado[
            df_filtrado[col_celula].astype(str).str.upper().str.contains('FECHAMENTOS E ACABAMENTOS', na=False)
        ]
    
    # 2. Serviço != 'Contingência'
    if 'Serviço' in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado['Serviço'].astype(str).str.upper() != 'CONTINGÊNCIA']
    
    # 3. Unidade Construtiva != 'Administrativo'
    col_unidade = None
    for col in df_filtrado.columns:
        if 'unidade' in col.lower() and 'construtiva' in col.lower():
            col_unidade = col
            break
    
    if col_unidade:
        df_filtrado = df_filtrado[
            df_filtrado[col_unidade].astype(str).str.upper() != 'ADMINISTRATIVO'
        ]
    
    # 4. Serviço (Apropriação) != 'Comissões', 'Devolução apartamentos', 'Imposto sobre vendas'
    if 'Serviço' in df_filtrado.columns:
        df_filtrado = df_filtrado[
            ~df_filtrado['Serviço'].isin(['Comissões', 'Devolução apartamentos', 'Imposto sobre vendas'])
        ]
    
    # 5. Credor/Histórico != 'Pagamento - DÉBITO AMORTIZAÇÃO PJ'
    if 'Credor/Histórico' in df_filtrado.columns:
        df_filtrado = df_filtrado[
            df_filtrado['Credor/Histórico'] != 'Pagamento - DÉBITO AMORTIZAÇÃO PJ'
        ]
    
    return df_filtrado

if __name__ == "__main__":
    from baixar_e_tratar_tabelas import baixar_e_tratar_tabelas
    from processar_relacoes_tabelas import processar_relacoes_tabelas
    
    print("📊 Calculando medidas DAX...\n")
    tabelas = baixar_e_tratar_tabelas()
    df_consolidado = processar_relacoes_tabelas(tabelas)
    
    if not df_consolidado.empty:
        # Aplicar filtros do Power BI
        df_filtrado = aplicar_filtros_power_bi(df_consolidado)
        
        # Calcular medidas
        df_com_medidas = calcular_todas_medidas(df_filtrado)
        
        # Salvar resultado
        from pathlib import Path
        output_dir = Path(__file__).parent.parent.parent / "dados_tratados"
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / "dados_com_medidas.csv"
        df_com_medidas.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"\n💾 Dados com medidas salvos em: {output_path}")

