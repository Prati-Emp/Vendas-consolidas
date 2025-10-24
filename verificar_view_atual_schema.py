#!/usr/bin/env python3
"""
Script para verificar a view atual no schema correto
"""

import os
import duckdb
from dotenv import load_dotenv
import os

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

def verificar_view_atual_schema(conn):
    """Verifica a view atual no schema correto"""
    print("\n" + "="*60)
    print("VERIFICANDO VIEW ATUAL NO SCHEMA CORRETO")
    print("="*60)
    
    try:
        # 1. Verificar se a view existe no schema informacoes_consolidadas
        print("1. Verificando view no schema informacoes_consolidadas...")
        try:
            result = conn.execute("SELECT COUNT(*) FROM informacoes_consolidadas.sienge_vendas_consolidadas").fetchone()
            print(f"   View existe - Total de registros: {result[0]:,}")
        except Exception as e:
            print(f"   ERRO: {e}")
        
        # 2. Verificar se a view existe no schema padrão
        print("\n2. Verificando view no schema padrão...")
        try:
            result = conn.execute("SELECT COUNT(*) FROM sienge_vendas_consolidadas").fetchone()
            print(f"   View existe - Total de registros: {result[0]:,}")
        except Exception as e:
            print(f"   ERRO: {e}")
        
        # 3. Verificar contagem das tabelas base
        print("\n3. Verificando contagem das tabelas base...")
        try:
            # Sienge vendas realizadas
            result = conn.execute("SELECT COUNT(*) FROM reservas.sienge_vendas_realizadas").fetchone()
            print(f"   reservas.sienge_vendas_realizadas: {result[0]:,}")
            
            # Sienge vendas canceladas
            result = conn.execute("SELECT COUNT(*) FROM reservas.sienge_vendas_canceladas").fetchone()
            print(f"   reservas.sienge_vendas_canceladas: {result[0]:,}")
            
            # CV vendas consolidadas vera cruz
            result = conn.execute("SELECT COUNT(*) FROM reservas.cv_vendas_consolidadas_vera_cruz").fetchone()
            print(f"   reservas.cv_vendas_consolidadas_vera_cruz: {result[0]:,}")
            
            # Soma total esperada
            total_esperado = 1058 + 39 + 53  # Valores conhecidos
            print(f"   Soma total esperada: {total_esperado:,}")
            
        except Exception as e:
            print(f"   ERRO ao verificar tabelas base: {e}")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao verificar view: {e}")
        return False

def main():
    """Funcao principal"""
    print("VERIFICANDO VIEW ATUAL NO SCHEMA CORRETO")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        verificar_view_atual_schema(conn)
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

