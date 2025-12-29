#!/usr/bin/env python3
"""
Script para investigar a tabela relacao_de_pedidos_de_compras
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

def investigar_tabela(conn):
    """Investiga a estrutura e dados da tabela"""
    print("\n" + "="*60)
    print("INVESTIGANDO TABELA relacao_de_pedidos_de_compras")
    print("="*60)
    
    try:
        # 1. Verificar estrutura
        print("\n1. Estrutura da tabela:")
        print("-" * 50)
        result = conn.execute("DESCRIBE planilhas.relacao_de_pedidos_de_compras").fetchall()
        colunas = [row[0] for row in result]
        for row in result:
            print(f"   {row[0]}: {row[1]}")
        
        # 2. Verificar se as colunas existem
        print("\n2. Verificando colunas necessarias:")
        print("-" * 50)
        tem_cd_obra = 'c_d_obra' in colunas or 'C_d_obra' in colunas or any('c_d_obra' in c.lower() for c in colunas)
        tem_obra = 'obra' in colunas or 'Obra' in colunas or any('obra' in c.lower() for c in colunas)
        
        # Buscar nomes exatos
        col_cd_obra = None
        col_obra = None
        
        for col in colunas:
            if col.lower() == 'c_d_obra' or col.lower() == 'código_da_obra':
                col_cd_obra = col
            if col.lower() == 'obra':
                col_obra = col
        
        print(f"   Coluna c_d_obra encontrada: {col_cd_obra if col_cd_obra else 'NAO ENCONTRADA'}")
        print(f"   Coluna obra encontrada: {col_obra if col_obra else 'NAO ENCONTRADA'}")
        
        if not col_cd_obra or not col_obra:
            print("\n   ATENCAO: Verificando variacoes de nomes...")
            for col in colunas:
                print(f"     - {col}")
        
        # 3. Verificar total de registros
        print("\n3. Total de registros:")
        print("-" * 50)
        result = conn.execute("SELECT COUNT(*) FROM planilhas.relacao_de_pedidos_de_compras").fetchone()
        print(f"   Total: {result[0]:,}")
        
        # 4. Verificar registros únicos por c_d_obra
        if col_cd_obra:
            print(f"\n4. Registros unicos por {col_cd_obra}:")
            print("-" * 50)
            result = conn.execute(f"""
                SELECT COUNT(DISTINCT "{col_cd_obra}") as unicos
                FROM planilhas.relacao_de_pedidos_de_compras
                WHERE "{col_cd_obra}" IS NOT NULL
            """).fetchone()
            print(f"   Total de obras unicas: {result[0]:,}")
        
        # 5. Amostra de dados
        print("\n5. Amostra de dados (primeiras 10 linhas):")
        print("-" * 50)
        if col_cd_obra and col_obra:
            result = conn.execute(f"""
                SELECT "{col_cd_obra}", "{col_obra}"
                FROM planilhas.relacao_de_pedidos_de_compras
                LIMIT 10
            """).fetchall()
            print(f"   {col_cd_obra:30} | {col_obra}")
            print("   " + "-" * 70)
            for row in result:
                cd_obra = str(row[0])[:30] if row[0] is not None else "NULL"
                obra = str(row[1])[:35] if row[1] is not None else "NULL"
                print(f"   {cd_obra:30} | {obra}")
        
        return col_cd_obra, col_obra
        
    except Exception as e:
        print(f"ERRO ao investigar: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def main():
    """Funcao principal"""
    print("INVESTIGANDO TABELA relacao_de_pedidos_de_compras")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        col_cd_obra, col_obra = investigar_tabela(conn)
        
        if not col_cd_obra or not col_obra:
            print("\n" + "="*60)
            print("ERRO: Colunas necessarias nao encontradas!")
            print("="*60)
            return False
        
        print("\n" + "="*60)
        print("INVESTIGACAO CONCLUIDA!")
        print("="*60)
        print(f"Coluna c_d_obra: {col_cd_obra}")
        print(f"Coluna obra: {col_obra}")
        
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

























