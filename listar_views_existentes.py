#!/usr/bin/env python3
"""
Script para listar todas as views existentes
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

def listar_views_existentes(conn):
    """Lista todas as views existentes"""
    print("\n" + "="*60)
    print("LISTANDO VIEWS EXISTENTES")
    print("="*60)
    
    try:
        # 1. Listar todas as views
        print("1. Listando todas as views...")
        try:
            result = conn.execute("SELECT view_name, schema_name FROM duckdb_views() ORDER BY schema_name, view_name").fetchall()
            if result:
                print(f"   Total de views encontradas: {len(result)}")
                for view in result:
                    print(f"   {view[1]}.{view[0]}")
            else:
                print("   Nenhuma view encontrada!")
        except Exception as e:
            print(f"   ERRO ao listar views: {e}")
        
        # 2. Verificar schemas disponíveis
        print("\n2. Verificando schemas disponíveis...")
        try:
            result = conn.execute("SELECT schema_name FROM duckdb_schemas() ORDER BY schema_name").fetchall()
            if result:
                print("   Schemas disponíveis:")
                for schema in result:
                    print(f"   - {schema[0]}")
            else:
                print("   Nenhum schema encontrado!")
        except Exception as e:
            print(f"   ERRO ao listar schemas: {e}")
        
        # 3. Verificar tabelas no schema informacoes_consolidadas
        print("\n3. Verificando tabelas no schema informacoes_consolidadas...")
        try:
            result = conn.execute("SELECT table_name FROM duckdb_tables() WHERE schema_name = 'informacoes_consolidadas' ORDER BY table_name").fetchall()
            if result:
                print("   Tabelas no schema informacoes_consolidadas:")
                for table in result:
                    print(f"   - {table[0]}")
            else:
                print("   Nenhuma tabela encontrada no schema informacoes_consolidadas!")
        except Exception as e:
            print(f"   ERRO ao listar tabelas: {e}")
        
        # 4. Verificar tabelas no schema reservas
        print("\n4. Verificando tabelas no schema reservas...")
        try:
            result = conn.execute("SELECT table_name FROM duckdb_tables() WHERE schema_name = 'reservas' ORDER BY table_name").fetchall()
            if result:
                print("   Tabelas no schema reservas:")
                for table in result:
                    print(f"   - {table[0]}")
            else:
                print("   Nenhuma tabela encontrada no schema reservas!")
        except Exception as e:
            print(f"   ERRO ao listar tabelas: {e}")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao listar views: {e}")
        return False

def main():
    """Funcao principal"""
    print("LISTANDO VIEWS EXISTENTES")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        listar_views_existentes(conn)
        return True
        
    except Exception as e:
        print(f"ERRO: {e}")
        return False
    
    finally:
        if conn:
            conn.close()
            print("\nConexao com MotherDuck encerrada.")

if __name__ == "__main__":
    main()

