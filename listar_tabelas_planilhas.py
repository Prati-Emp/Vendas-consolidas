#!/usr/bin/env python3
"""
Script para listar todas as tabelas do banco planilhas
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

def listar_tabelas(conn):
    """Lista todas as tabelas do banco planilhas"""
    print("\n" + "="*60)
    print("LISTANDO TABELAS DO BANCO planilhas")
    print("="*60)
    
    try:
        # Listar tabelas
        result = conn.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'planilhas'
            ORDER BY table_name
        """).fetchall()
        
        if not result:
            print("Nenhuma tabela encontrada no schema 'planilhas'")
            
            # Tentar listar todos os schemas
            print("\nListando todos os schemas disponiveis...")
            result = conn.execute("""
                SELECT DISTINCT table_schema 
                FROM information_schema.tables 
                ORDER BY table_schema
            """).fetchall()
            
            print("Schemas encontrados:")
            for row in result:
                print(f"  - {row[0]}")
            
            return False
        
        print(f"Total de tabelas encontradas: {len(result)}")
        print("\nTabelas:")
        for row in result:
            print(f"  - {row[0]}")
            
            # Verificar se o nome é similar
            if 'apropriacao' in row[0].lower() or 'horizont' in row[0].lower():
                print(f"    *** POSSIVEL TABELA PROCURADA ***")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao listar tabelas: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Funcao principal"""
    print("LISTANDO TABELAS DO BANCO planilhas")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        if not listar_tabelas(conn):
            return False
        
        print("\n" + "="*60)
        print("LISTAGEM CONCLUIDA!")
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




























