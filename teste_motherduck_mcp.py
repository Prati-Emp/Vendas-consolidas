#!/usr/bin/env python3
"""
Script de teste para verificar a conexão com MotherDuck usando MCP
"""

import os
import sys
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv('motherduck_config.env')

def test_motherduck_connection():
    """Testa a conexão com MotherDuck"""
    try:
        import duckdb
        
        # Obter token do MotherDuck
        token = os.getenv('MOTHERDUCK_TOKEN')
        if not token:
            print("ERRO: Token do MotherDuck nao encontrado!")
            return False
        
        print("Token do MotherDuck encontrado")
        print(f"Token: {token[:20]}...")
        
        # Configurar conexão com MotherDuck
        conn = duckdb.connect(f'md:?motherduck_token={token}')
        
        # Testar consulta simples
        print("Testando consulta simples...")
        result = conn.execute("SELECT 'Hello MotherDuck!' as message").fetchone()
        print(f"Resultado: {result[0]}")
        
        # Testar listagem de databases
        print("Listando databases...")
        databases = conn.execute("SHOW DATABASES").fetchall()
        print("Databases disponiveis:")
        for db in databases:
            print(f"  - {db[0]}")
        
        conn.close()
        print("Conexao com MotherDuck estabelecida com sucesso!")
        return True
        
    except ImportError as e:
        print(f"ERRO de importacao: {e}")
        print("Execute: pip install duckdb python-dotenv")
        return False
    except Exception as e:
        print(f"ERRO na conexao: {e}")
        return False

def test_mcp_server():
    """Testa se o servidor MCP está disponível"""
    try:
        import subprocess
        result = subprocess.run(['mcp-server-motherduck', '--help'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("Servidor MCP MotherDuck esta disponivel")
            return True
        else:
            print("Servidor MCP MotherDuck nao esta funcionando")
            return False
    except Exception as e:
        print(f"ERRO ao testar servidor MCP: {e}")
        return False

if __name__ == "__main__":
    print("Testando configuracao do MotherDuck MCP")
    print("=" * 50)
    
    # Testar servidor MCP
    print("\n1. Testando servidor MCP...")
    mcp_ok = test_mcp_server()
    
    # Testar conexão direta
    print("\n2. Testando conexao direta...")
    connection_ok = test_motherduck_connection()
    
    print("\n" + "=" * 50)
    if mcp_ok and connection_ok:
        print("Configuracao do MotherDuck MCP esta funcionando!")
    else:
        print("Alguns testes falharam. Verifique a configuracao.")
