#!/usr/bin/env python3
"""
Script para criar a view relacao_empreendimentos_pedidos_de_compras
com base na tabela relacao_de_pedidos_de_compras
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

def criar_view(conn):
    """Cria a view com obras únicas"""
    print("\n" + "="*60)
    print("CRIANDO VIEW relacao_empreendimentos_pedidos_de_compras")
    print("="*60)
    
    try:
        # Verificar se a view já existe
        print("\n1. Verificando se a view ja existe...")
        try:
            result = conn.execute("""
                SELECT COUNT(*) 
                FROM planilhas.relacao_empreendimentos_pedidos_de_compras
            """).fetchone()
            print("   View ja existe. Será substituída.")
        except:
            print("   View nao existe. Será criada.")
        
        # Criar a view
        print("\n2. Criando view...")
        sql_view = """
        CREATE OR REPLACE VIEW planilhas.relacao_empreendimentos_pedidos_de_compras AS
        SELECT DISTINCT
            c_d_obra as codigo_da_obra,
            obra
        FROM planilhas.relacao_de_pedidos_de_compras
        WHERE c_d_obra IS NOT NULL
        ORDER BY codigo_da_obra
        """
        
        conn.execute(sql_view)
        print("   View criada com sucesso!")
        
        # Verificar resultado
        print("\n3. Verificando view criada...")
        result = conn.execute("""
            SELECT COUNT(*) 
            FROM planilhas.relacao_empreendimentos_pedidos_de_compras
        """).fetchone()
        print(f"   Total de registros (obras unicas): {result[0]:,}")
        
        # Mostrar estrutura
        print("\n4. Estrutura da view:")
        print("-" * 50)
        result = conn.execute("DESCRIBE planilhas.relacao_empreendimentos_pedidos_de_compras").fetchall()
        for row in result:
            print(f"   {row[0]}: {row[1]}")
        
        # Mostrar amostra
        print("\n5. Amostra de dados (primeiras 10 linhas):")
        print("-" * 50)
        result = conn.execute("""
            SELECT codigo_da_obra, obra
            FROM planilhas.relacao_empreendimentos_pedidos_de_compras
            LIMIT 10
        """).fetchall()
        print(f"   {'codigo_da_obra':<20} | {'obra':<40}")
        print("   " + "-" * 65)
        for row in result:
            codigo = str(row[0]) if row[0] is not None else "NULL"
            obra = str(row[1])[:40] if row[1] is not None else "NULL"
            print(f"   {codigo:<20} | {obra}")
        
        # Verificar se há duplicatas
        print("\n6. Verificando duplicatas...")
        result = conn.execute("""
            SELECT codigo_da_obra, COUNT(*) as total
            FROM planilhas.relacao_empreendimentos_pedidos_de_compras
            GROUP BY codigo_da_obra
            HAVING COUNT(*) > 1
        """).fetchall()
        
        if result:
            print(f"   ATENCAO: {len(result)} codigos com duplicatas encontrados:")
            for row in result:
                print(f"     - codigo_da_obra {row[0]}: {row[1]} registros")
        else:
            print("   Nenhuma duplicata encontrada. Todos os codigos sao unicos!")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao criar view: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Funcao principal"""
    print("CRIANDO VIEW relacao_empreendimentos_pedidos_de_compras")
    print("="*60)
    print("Base: planilhas.relacao_de_pedidos_de_compras")
    print("Colunas: c_d_obra (-> codigo_da_obra), obra")
    print("Filtro: Obras unicas baseadas em c_d_obra")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        if not criar_view(conn):
            return False
        
        print("\n" + "="*60)
        print("VIEW CRIADA COM SUCESSO!")
        print("="*60)
        print("View: planilhas.relacao_empreendimentos_pedidos_de_compras")
        print("Colunas:")
        print("  - codigo_da_obra (renomeado de c_d_obra)")
        print("  - obra")
        print("Filtro: Apenas obras unicas baseadas em codigo_da_obra")
        
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

























