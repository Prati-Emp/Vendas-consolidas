#!/usr/bin/env python3
"""
Script para verificar a estrutura da tabela reservas_abril
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

def verificar_estrutura_reservas(conn):
    """Verifica a estrutura da tabela reservas_abril"""
    print("\n" + "="*60)
    print("ESTRUTURA DA TABELA RESERVAS_ABRIL")
    print("="*60)
    
    try:
        # Verificar estrutura da tabela
        print("Colunas da tabela reservas_abril:")
        columns = conn.execute("DESCRIBE reservas.reservas_abril").fetchall()
        for col in columns:
            print(f"   - {col[0]} ({col[1]})")
        
        # Verificar se as colunas que precisamos existem
        colunas_necessarias = ['vpl_reserva', 'vpl_tabela', 'idreserva', 'codigointerno']
        colunas_existentes = [col[0] for col in columns]
        
        print(f"\nVerificando colunas necessarias:")
        for coluna in colunas_necessarias:
            if coluna in colunas_existentes:
                print(f"   OK {coluna} - EXISTE")
            else:
                print(f"   X {coluna} - NAO EXISTE")
        
        # Verificar amostra de dados
        print(f"\nAmostra de dados (5 registros):")
        result = conn.execute("SELECT * FROM reservas.reservas_abril LIMIT 5").fetchall()
        for i, row in enumerate(result, 1):
            print(f"   Registro {i}: {row[:5]}...")  # Primeiras 5 colunas
        
        return True
        
    except Exception as e:
        print(f"ERRO ao verificar estrutura: {e}")
        return False

def main():
    """Funcao principal"""
    print("VERIFICACAO DA ESTRUTURA DA TABELA RESERVAS_ABRIL")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        verificar_estrutura_reservas(conn)
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

