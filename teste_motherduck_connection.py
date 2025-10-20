#!/usr/bin/env python3
"""
Script para testar a conexão com MotherDuck
"""

import os
import duckdb
from dotenv import load_dotenv

def test_motherduck_connection():
    """Testa a conexão com MotherDuck"""
    print("🧪 TESTE DE CONEXÃO MOTHERDUCK")
    print("=" * 40)
    
    try:
        # Carregar configurações
        print("1. Carregando configurações...")
        load_dotenv()
        
        # Verificar token
        token = os.environ.get('MOTHERDUCK_TOKEN', '').strip()
        if not token:
            print("❌ MOTHERDUCK_TOKEN não encontrado")
            return False
        
        print(f"✅ Token encontrado: {token[:10]}...")
        
        # Configurar DuckDB
        print("\n2. Configurando DuckDB...")
        duckdb.sql("INSTALL motherduck")
        duckdb.sql("LOAD motherduck")
        
        # Configurar token
        print("3. Configurando token...")
        duckdb.sql(f"SET motherduck_token='{token}'")
        
        # Conectar
        print("4. Conectando ao MotherDuck...")
        conn = duckdb.connect('md:reservas')
        print("✅ Conexão estabelecida")
        
        # Testar consulta
        print("\n5. Testando consulta...")
        tables = conn.sql("SHOW TABLES").fetchall()
        print(f"✅ Tabelas encontradas: {len(tables)}")
        
        for table in tables:
            table_name = table[0]
            try:
                count = conn.sql(f"SELECT COUNT(*) FROM main.{table_name}").fetchone()[0]
                print(f"   📊 {table_name}: {count:,} registros")
            except Exception as e:
                print(f"   📊 {table_name}: (erro ao contar - {e})")
        
        conn.close()
        print("\n✅ Teste de conexão bem-sucedido!")
        return True
        
    except Exception as e:
        print(f"\n❌ Erro no teste: {str(e)}")
        return False

def main():
    """Função principal"""
    print("🧪 TESTE DE CONEXÃO MOTHERDUCK")
    print("Este script testa se a conexão com MotherDuck está funcionando")
    print()
    
    try:
        sucesso = test_motherduck_connection()
        
        if sucesso:
            print("\n✅ Conexão funcionando! Você pode executar os scripts de atualização.")
        else:
            print("\n❌ Problema na conexão. Verifique o token do MotherDuck.")
            
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
    finally:
        print("\n🏁 Teste finalizado")

if __name__ == "__main__":
    main()

