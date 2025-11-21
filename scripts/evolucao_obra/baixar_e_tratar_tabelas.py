#!/usr/bin/env python3
"""
FASE 1.1: Baixar e Tratar Tabelas do MotherDuck
Conecta ao banco 'operacoes' e trata as tabelas necessárias.
"""

import os
import sys
import pandas as pd
import duckdb
from typing import Dict, Optional
from pathlib import Path

# Adicionar diretório raiz ao path
sys.path.append(str(Path(__file__).parent.parent.parent))

from scripts.config import get_api_config

def conectar_motherduck():
    """Conecta ao banco operacoes no MotherDuck"""
    try:
        # Obter token do MotherDuck
        token = os.getenv('MOTHERDUCK_TOKEN') or os.getenv('Token_MD')
        if not token:
            # Tentar via config
            try:
                config = get_api_config('motherduck')
                if config and hasattr(config, 'token'):
                    token = config.token
            except:
                pass
        
        if not token:
            raise ValueError("Token do MotherDuck não encontrado. Configure MOTHERDUCK_TOKEN ou Token_MD")
        
        # Conectar ao banco operacoes
        conn = duckdb.connect(f'md:operacoes?motherduck_token={token}')
        return conn
    except Exception as e:
        print(f"❌ Erro ao conectar ao MotherDuck: {e}")
        raise

def tratar_orcamento_horizont(df: pd.DataFrame) -> pd.DataFrame:
    """
    Trata tabela orcamento_horizont
    
    - Converte 'Preço total' de VARCHAR para numérico (formato brasileiro)
    - Cria coluna 'Orcamento + contingência' = Preço total
    - Padroniza nomes de colunas
    """
    df = df.copy()
    
    # Converter 'Preço total' para numérico
    if 'Preço total' in df.columns:
        # Remover pontos (milhares) e substituir vírgula por ponto (decimal)
        df['Preço total'] = df['Preço total'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        df['Preço total'] = pd.to_numeric(df['Preço total'], errors='coerce')
    
    # Criar coluna 'Orcamento + contingência'
    df['Orcamento + contingência'] = df.get('Preço total', 0)
    
    # Padronizar nomes de colunas (remover espaços, normalizar)
    df.columns = df.columns.str.strip()
    
    return df

def tratar_apropricao_horizont(df: pd.DataFrame) -> pd.DataFrame:
    """
    Trata tabela apropricao_horizont
    
    - Identifica e remove cabeçalhos (linhas 0 e 1)
    - Renomeia colunas genéricas baseado na linha 1
    - Converte valores para numérico
    - Aplica filtros
    """
    df = df.copy()
    
    # Remover primeira linha (cabeçalho de período)
    if len(df) > 0:
        primeira_valor = str(df.iloc[0]['column00']) if 'column00' in df.columns else ''
        if 'período' in primeira_valor.lower() or 'periodo' in primeira_valor.lower():
            df = df.iloc[1:].reset_index(drop=True)
    
    # Remover segunda linha (cabeçalho real) e usar para renomear colunas
    if len(df) > 0:
        # Mapeamento baseado na estrutura real:
        # Linha 1 contém: Obra, Unidade construtiva, Célula construtiva, Etapa, Subetapa, Serviço, Credor/Histórico, Valor
        col_mapping = {
            'column00': 'Obra',
            'column03': 'Unidade construtiva',
            'column05': 'Célula construtiva',
            'column07': 'Etapa',
            'column08': 'Subetapa',
            'column09': 'Serviço',
            'column15': 'Credor/Histórico',
            'column17': 'Valor'
        }
        
        # Renomear colunas
        df = df.rename(columns=col_mapping)
        
        # Remover linha de cabeçalho (agora é a primeira linha após remover a anterior)
        if len(df) > 0:
            # Verificar se primeira linha ainda é cabeçalho
            primeira_obra = str(df.iloc[0].get('Obra', '')) if 'Obra' in df.columns else ''
            primeira_unidade = str(df.iloc[0].get('Unidade construtiva', '')) if 'Unidade construtiva' in df.columns else ''
            
            # Se contém "Obra" e "Unidade construtiva" como texto literal, é cabeçalho
            if primeira_obra.lower() == 'obra' or primeira_unidade.lower() == 'unidade construtiva':
                df = df.iloc[1:].reset_index(drop=True)
    
    # Converter 'Valor' para numérico (formato brasileiro)
    if 'Valor' in df.columns:
        # Tratar valores None/NaN antes de converter
        df['Valor'] = df['Valor'].fillna('0').astype(str)
        df['Valor'] = df['Valor'].str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce').fillna(0)
    
    # Aplicar filtros (tratando valores None)
    if 'Serviço' in df.columns:
        df['Serviço'] = df['Serviço'].fillna('').astype(str)
        df = df[~df['Serviço'].isin(['Comissões', 'Devolução apartamentos', 'Imposto sobre vendas'])]
    
    if 'Credor/Histórico' in df.columns:
        df['Credor/Histórico'] = df['Credor/Histórico'].fillna('').astype(str)
        df = df[df['Credor/Histórico'] != 'Pagamento - DÉBITO AMORTIZAÇÃO PJ']
    
    return df

def tratar_sienge_medicoes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Trata tabela sienge_medicoes
    
    - Filtra para ID_Empreendimento = 21 (Horizont)
    - Usa Percentual_Realizado para Conclusão Física
    - Agrupa por Unidade_Construtiva e hierarquia
    """
    df = df.copy()
    
    # Filtrar para ID_Empreendimento = 21
    if 'ID_Empreendimento' in df.columns:
        df = df[df['ID_Empreendimento'] == 21]
    
    # Garantir que Percentual_Realizado está numérico
    if 'Percentual_Realizado' in df.columns:
        df['Percentual_Realizado'] = pd.to_numeric(df['Percentual_Realizado'], errors='coerce')
    
    return df

def tratar_estoque_horizont(df: pd.DataFrame) -> pd.DataFrame:
    """
    Trata tabela estoque_horizont
    
    - Converte 'Quantidade apropriada' e 'Custo total' para numérico
    - Cria coluna condicional 'Status_Apropriacao'
    """
    df = df.copy()
    
    # Converter 'Quantidade apropriada' para numérico
    if 'Quantidade apropriada' in df.columns:
        df['Quantidade apropriada'] = df['Quantidade apropriada'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        df['Quantidade apropriada'] = pd.to_numeric(df['Quantidade apropriada'], errors='coerce')
    
    # Converter 'Custo total' para numérico
    if 'Custo total' in df.columns:
        df['Custo total'] = df['Custo total'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        df['Custo total'] = pd.to_numeric(df['Custo total'], errors='coerce')
    
    # Criar coluna condicional 'Status_Apropriacao'
    if 'Quantidade apropriada' in df.columns:
        df['Status_Apropriacao'] = df['Quantidade apropriada'].apply(
            lambda x: "Com Apropriação" if pd.notna(x) and x > 0 else "Sem Apropriação"
        )
    
    return df

def baixar_e_tratar_tabelas() -> Dict[str, pd.DataFrame]:
    """
    Baixa e trata todas as tabelas necessárias do banco operacoes
    """
    print("📥 Conectando ao banco operacoes...")
    conn = conectar_motherduck()
    
    tabelas_tratadas = {}
    
    try:
        # 1. orcamento_horizont
        print("\n1. Baixando e tratando orcamento_horizont...")
        try:
            df_orcamento = conn.execute("SELECT * FROM orcamento_horizont").df()
            df_orcamento = tratar_orcamento_horizont(df_orcamento)
            tabelas_tratadas['orcamento_horizont'] = df_orcamento
            print(f"   ✅ {len(df_orcamento)} registros tratados")
        except Exception as e:
            print(f"   ⚠️ Erro ao processar orcamento_horizont: {e}")
            tabelas_tratadas['orcamento_horizont'] = pd.DataFrame()
        
        # 2. apropricao_horizont
        print("\n2. Baixando e tratando apropricao_horizont...")
        try:
            df_apropricao = conn.execute("SELECT * FROM apropricao_horizont").df()
            df_apropricao = tratar_apropricao_horizont(df_apropricao)
            tabelas_tratadas['apropricao_horizont'] = df_apropricao
            print(f"   ✅ {len(df_apropricao)} registros tratados")
        except Exception as e:
            print(f"   ⚠️ Erro ao processar apropricao_horizont: {e}")
            tabelas_tratadas['apropricao_horizont'] = pd.DataFrame()
        
        # 3. sienge_medicoes
        print("\n3. Baixando e tratando sienge_medicoes...")
        try:
            df_medicoes = conn.execute("SELECT * FROM sienge_medicoes WHERE ID_Empreendimento = 21").df()
            df_medicoes = tratar_sienge_medicoes(df_medicoes)
            tabelas_tratadas['sienge_medicoes'] = df_medicoes
            print(f"   ✅ {len(df_medicoes)} registros tratados")
        except Exception as e:
            print(f"   ⚠️ Erro ao processar sienge_medicoes: {e}")
            tabelas_tratadas['sienge_medicoes'] = pd.DataFrame()
        
        # 4. estoque_horizont
        print("\n4. Baixando e tratando estoque_horizont...")
        try:
            df_estoque = conn.execute("SELECT * FROM estoque_horizont").df()
            df_estoque = tratar_estoque_horizont(df_estoque)
            tabelas_tratadas['estoque_horizont'] = df_estoque
            print(f"   ✅ {len(df_estoque)} registros tratados")
        except Exception as e:
            print(f"   ⚠️ Erro ao processar estoque_horizont: {e}")
            tabelas_tratadas['estoque_horizont'] = pd.DataFrame()
        
        print("\n✅ Todas as tabelas foram baixadas e tratadas!")
        
    finally:
        conn.close()
    
    return tabelas_tratadas

if __name__ == "__main__":
    tabelas = baixar_e_tratar_tabelas()
    
    # Salvar tabelas tratadas (opcional)
    output_dir = Path(__file__).parent.parent.parent / "dados_tratados"
    output_dir.mkdir(exist_ok=True)
    
    for nome, df in tabelas.items():
        if not df.empty:
            output_path = output_dir / f"{nome}_tratado.csv"
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
            print(f"💾 Salvo: {output_path}")

