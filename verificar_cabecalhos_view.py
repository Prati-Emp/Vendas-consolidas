#!/usr/bin/env python3
"""
Script para verificar os cabeçalhos da view apropriacao_horizont_tratada
"""

import os
import duckdb
from dotenv import load_dotenv

def conectar_motherduck():
    """Conecta ao MotherDuck"""
    try:
        load_dotenv('.env')
        token = os.getenv('MOTHERDUCK_TOKEN')
        if not token:
            print("ERRO: Token do MotherDuck nao encontrado!")
            return None
        
        print("Conectando ao MotherDuck...")
        conn = duckdb.connect(f'md:?motherduck_token={token}')
        print("Conexao estabelecida com sucesso!")
        return conn
        
    except Exception as e:
        print(f"ERRO na conexao: {e}")
        return None

def verificar_view(conn):
    """Verifica a estrutura e dados da view"""
    print("\n" + "="*60)
    print("VERIFICANDO VIEW apropriacao_horizont_tratada")
    print("="*60)
    
    try:
        # 1. Verificar estrutura da view
        print("1. Estrutura da view (cabeçalhos):")
        print("-" * 50)
        result = conn.execute("DESCRIBE planilhas.apropriacao_horizont_tratada").fetchall()
        
        colunas_view = []
        for row in result:
            colunas_view.append(row[0])
            print(f"   {row[0]}: {row[1]}")
        
        print(f"\n   Total de colunas: {len(colunas_view)}")
        
        # 2. Verificar primeira linha da view
        print("\n2. Primeira linha de dados da view:")
        print("-" * 50)
        result = conn.execute("SELECT * FROM planilhas.apropriacao_horizont_tratada LIMIT 1").fetchone()
        
        if result:
            print("   Valores da primeira linha:")
            for i, (col, val) in enumerate(zip(colunas_view[:15], result[:15])):
                val_str = str(val)[:50] if val is not None else "NULL"
                print(f"   {col}: {val_str}")
        
        # 3. Comparar com tabela original
        print("\n3. Comparando com tabela original:")
        print("-" * 50)
        
        # Primeira linha da tabela original (cabeçalho)
        print("   Primeira linha da tabela original (cabeçalho):")
        result_orig = conn.execute("SELECT * FROM planilhas.apropriacao_horizont LIMIT 1").fetchone()
        result_orig_desc = conn.execute("DESCRIBE planilhas.apropriacao_horizont").fetchall()
        colunas_orig = [row[0] for row in result_orig_desc]
        
        if result_orig:
            print("   Valores da primeira linha original:")
            for i, (col, val) in enumerate(zip(colunas_orig[:15], result_orig[:15])):
                val_str = str(val)[:50] if val is not None else "NULL"
                print(f"   {col}: {val_str}")
        
        # Segunda linha da tabela original (primeira linha de dados)
        print("\n   Segunda linha da tabela original (primeira linha de dados):")
        result_orig2 = conn.execute("SELECT * FROM planilhas.apropriacao_horizont LIMIT 1 OFFSET 1").fetchone()
        
        if result_orig2:
            print("   Valores da segunda linha original:")
            for i, (col, val) in enumerate(zip(colunas_orig[:15], result_orig2[:15])):
                val_str = str(val)[:50] if val is not None else "NULL"
                print(f"   {col}: {val_str}")
        
        # 4. Verificar se os nomes das colunas da view correspondem aos valores da primeira linha original
        print("\n4. Verificando correspondencia entre cabeçalhos:")
        print("-" * 50)
        print("   Comparacao:")
        for i in range(min(len(colunas_view), len(result_orig) if result_orig else 0)):
            col_view = colunas_view[i]
            val_orig = result_orig[i] if result_orig and i < len(result_orig) else None
            val_orig_str = str(val_orig) if val_orig is not None else "NULL"
            print(f"   View col[{i}]: '{col_view}' <- Original linha1[{i}]: '{val_orig_str}'")
        
        # 5. Verificar se há problemas com nomes de colunas
        print("\n5. Verificando problemas com nomes de colunas:")
        print("-" * 50)
        problemas = []
        for col in colunas_view:
            if col.startswith('unnamed_') or col.startswith('col_'):
                problemas.append(col)
        
        if problemas:
            print(f"   ATENCAO: {len(problemas)} colunas com nomes genericos encontradas:")
            for prob in problemas:
                print(f"     - {prob}")
        else:
            print("   Nenhum problema encontrado com nomes de colunas")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao verificar: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Funcao principal"""
    print("VERIFICANDO CABECALHOS DA VIEW")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        if not verificar_view(conn):
            return False
        
        print("\n" + "="*60)
        print("VERIFICACAO CONCLUIDA!")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"ERRO na execucao: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if conn:
            conn.close()
            print("\nConexao com MotherDuck encerrada.")

if __name__ == "__main__":
    main()




























