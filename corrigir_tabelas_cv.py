#!/usr/bin/env python3
"""
Script para corrigir normalização de valores nas tabelas CV que precisam de ajuste
"""

import os
import duckdb
import pandas as pd
from dotenv import load_dotenv

def normalizar_valor_monetario_otimizado(valor):
    """
    Normalização otimizada de valores monetários
    - Se tem vírgula: já está no formato brasileiro correto
    - Se tem pontos: substitui apenas o ÚLTIMO ponto por vírgula
    - Se não tem nem pontos nem vírgulas: número simples
    """
    if pd.isna(valor) or valor is None:
        return 0.0
    
    valor_str = str(valor).replace('R$', '').replace('$', '').strip()
    
    # Se já tem vírgula, está no formato brasileiro correto
    if ',' in valor_str:
        return float(valor_str.replace(',', '.'))
    
    # Se tem pontos, substituir apenas o ÚLTIMO ponto por vírgula
    if '.' in valor_str:
        ultimo_ponto = valor_str.rfind('.')
        valor_corrigido = valor_str[:ultimo_ponto] + ',' + valor_str[ultimo_ponto+1:]
        return float(valor_corrigido.replace(',', '.'))
    
    # Número simples sem formatação
    try:
        return float(valor_str)
    except ValueError:
        return 0.0

def conectar_motherduck():
    """Conecta ao MotherDuck"""
    load_dotenv()
    
    token = os.environ.get('MOTHERDUCK_TOKEN', '').strip()
    if not token:
        raise ValueError("MOTHERDUCK_TOKEN nao encontrado")
    
    # Configurar DuckDB
    duckdb.sql("INSTALL motherduck")
    duckdb.sql("LOAD motherduck")
    duckdb.sql(f"SET motherduck_token='{token}'")
    
    # Conectar
    conn = duckdb.connect('md:reservas')
    return conn

def corrigir_tabela_cv_repasses():
    """Corrige a tabela cv_repasses"""
    print("CORRIGINDO TABELA: cv_repasses")
    print("-" * 40)
    
    conn = conectar_motherduck()
    
    try:
        # Ler dados atuais
        print("1. Lendo dados atuais...")
        df = conn.sql("SELECT * FROM main.cv_repasses").df()
        print(f"   Total de registros: {len(df)}")
        
        # Colunas de valor para corrigir
        colunas_valor = [
            'valor_previsto', 'valor_divida', 'valor_subsidio', 
            'valor_fgts', 'valor_registro', 'valor_financiado', 'valor_contrato'
        ]
        
        # Aplicar normalização
        print("2. Aplicando normalização...")
        for col in colunas_valor:
            if col in df.columns:
                print(f"   Corrigindo {col}...")
                df[col] = df[col].apply(normalizar_valor_monetario_otimizado)
        
        # Backup da tabela original
        print("3. Criando backup...")
        conn.execute("CREATE TABLE IF NOT EXISTS main.cv_repasses_backup AS SELECT * FROM main.cv_repasses")
        print("   Backup criado: main.cv_repasses_backup")
        
        # Atualizar tabela
        print("4. Atualizando tabela...")
        conn.register("df_corrigido", df)
        conn.execute("CREATE OR REPLACE TABLE main.cv_repasses AS SELECT * FROM df_corrigido")
        print("   Tabela atualizada")
        
        # Verificar contagem
        count_original = conn.sql("SELECT COUNT(*) FROM main.cv_repasses_backup").fetchone()[0]
        count_novo = conn.sql("SELECT COUNT(*) FROM main.cv_repasses").fetchone()[0]
        print(f"   Registros original: {count_original}")
        print(f"   Registros novo: {count_novo}")
        
        # Mostrar exemplos de correção
        print("5. Exemplos de correção:")
        for col in colunas_valor[:3]:  # Mostrar apenas 3 colunas
            if col in df.columns:
                stats = df[col].describe()
                print(f"   {col}: Min={stats['min']:,.2f}, Max={stats['max']:,.2f}, Mean={stats['mean']:,.2f}")
        
        conn.close()
        print("   Correção concluída com sucesso!")
        return True
        
    except Exception as e:
        print(f"   Erro na correção: {e}")
        return False

def corrigir_tabela_cv_vendas():
    """Corrige a tabela cv_vendas"""
    print("\nCORRIGINDO TABELA: cv_vendas")
    print("-" * 40)
    
    conn = conectar_motherduck()
    
    try:
        # Ler dados atuais
        print("1. Lendo dados atuais...")
        df = conn.sql("SELECT * FROM main.cv_vendas").df()
        print(f"   Total de registros: {len(df)}")
        
        # Coluna de valor para corrigir
        coluna_valor = 'valor_contrato'
        
        if coluna_valor in df.columns:
            # Mostrar exemplos antes da correção
            print("2. Exemplos ANTES da correção:")
            exemplos_antes = df[coluna_valor].dropna().head(5).tolist()
            for exemplo in exemplos_antes:
                print(f"   {exemplo}")
            
            # Aplicar normalização
            print("3. Aplicando normalização...")
            df[coluna_valor] = df[coluna_valor].apply(normalizar_valor_monetario_otimizado)
            
            # Mostrar exemplos depois da correção
            print("4. Exemplos DEPOIS da correção:")
            exemplos_depois = df[coluna_valor].dropna().head(5).tolist()
            for exemplo in exemplos_depois:
                print(f"   {exemplo:,.2f}")
            
            # Backup da tabela original
            print("5. Criando backup...")
            conn.execute("CREATE TABLE IF NOT EXISTS main.cv_vendas_backup AS SELECT * FROM main.cv_vendas")
            print("   Backup criado: main.cv_vendas_backup")
            
            # Atualizar tabela
            print("6. Atualizando tabela...")
            conn.register("df_corrigido", df)
            conn.execute("CREATE OR REPLACE TABLE main.cv_vendas AS SELECT * FROM df_corrigido")
            print("   Tabela atualizada")
            
            # Verificar contagem
            count_original = conn.sql("SELECT COUNT(*) FROM main.cv_vendas_backup").fetchone()[0]
            count_novo = conn.sql("SELECT COUNT(*) FROM main.cv_vendas").fetchone()[0]
            print(f"   Registros original: {count_original}")
            print(f"   Registros novo: {count_novo}")
            
            # Estatísticas finais
            stats = df[coluna_valor].describe()
            print(f"   Estatísticas finais: Min={stats['min']:,.2f}, Max={stats['max']:,.2f}, Mean={stats['mean']:,.2f}")
            
            conn.close()
            print("   Correção concluída com sucesso!")
            return True
        else:
            print(f"   Coluna {coluna_valor} não encontrada")
            return False
        
    except Exception as e:
        print(f"   Erro na correção: {e}")
        return False

def main():
    """Função principal"""
    print("CORRECAO DE NORMALIZACAO - TABELAS CV")
    print("=" * 50)
    print("Este script corrige a normalização de valores monetários")
    print("nas tabelas CV que precisam de ajuste.")
    print()
    
    try:
        # Corrigir cv_repasses
        sucesso_repasses = corrigir_tabela_cv_repasses()
        
        # Corrigir cv_vendas
        sucesso_vendas = corrigir_tabela_cv_vendas()
        
        # Resumo final
        print("\n" + "=" * 50)
        print("RESUMO DAS CORRECOES:")
        print("=" * 50)
        
        if sucesso_repasses:
            print("✅ cv_repasses: Correção aplicada com sucesso")
        else:
            print("❌ cv_repasses: Erro na correção")
        
        if sucesso_vendas:
            print("✅ cv_vendas: Correção aplicada com sucesso")
        else:
            print("❌ cv_vendas: Erro na correção")
        
        print("\nNOTAS IMPORTANTES:")
        print("- Backups foram criados para todas as tabelas corrigidas")
        print("- Se houver problemas, você pode restaurar os dados originais")
        print("- As correções serão aplicadas na próxima atualização do sistema")
        
    except Exception as e:
        print(f"Erro durante a correção: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
