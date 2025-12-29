#!/usr/bin/env python3
"""
Script para procurar a tabela apropriacao_horizont em todos os schemas
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

def procurar_tabela(conn):
    """Procura a tabela apropriacao_horizont em todos os schemas"""
    print("\n" + "="*60)
    print("PROCURANDO TABELA apropriacao_horizont")
    print("="*60)
    
    try:
        # Procurar em todos os schemas
        result = conn.execute("""
            SELECT table_schema, table_name 
            FROM information_schema.tables 
            WHERE LOWER(table_name) LIKE '%apropriacao%' 
               OR LOWER(table_name) LIKE '%horizont%'
            ORDER BY table_schema, table_name
        """).fetchall()
        
        if not result:
            print("Nenhuma tabela encontrada com 'apropriacao' ou 'horizont' no nome")
            
            # Listar todas as tabelas para ajudar
            print("\nListando todas as tabelas disponiveis...")
            result_all = conn.execute("""
                SELECT table_schema, table_name 
                FROM information_schema.tables 
                WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
                ORDER BY table_schema, table_name
                LIMIT 50
            """).fetchall()
            
            print("\nPrimeiras 50 tabelas encontradas:")
            schema_atual = None
            for row in result_all:
                if schema_atual != row[0]:
                    schema_atual = row[0]
                    print(f"\n  Schema: {schema_atual}")
                print(f"    - {row[1]}")
            
            return False
        
        print(f"Tabelas encontradas: {len(result)}")
        print("\nTabelas:")
        for row in result:
            print(f"  Schema: {row[0]}, Tabela: {row[1]}")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao procurar tabela: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Funcao principal"""
    print("PROCURANDO TABELA apropriacao_horizont")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        if not procurar_tabela(conn):
            return False
        
        print("\n" + "="*60)
        print("BUSCA CONCLUIDA!")
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




























