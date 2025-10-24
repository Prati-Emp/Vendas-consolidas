#!/usr/bin/env python3
"""
Script para verificar a estrutura correta das views
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

def verificar_estrutura_correta(conn):
    """Verifica a estrutura correta das views"""
    print("\n" + "="*60)
    print("VERIFICANDO ESTRUTURA CORRETA")
    print("="*60)
    
    try:
        # 1. Verificar view cv_vendas_consolidadas_vera_cruz no schema reservas
        print("1. Verificando view cv_vendas_consolidadas_vera_cruz no schema reservas...")
        try:
            result = conn.execute("SELECT COUNT(*) FROM reservas.cv_vendas_consolidadas_vera_cruz").fetchone()
            print(f"   View existe - Total de registros: {result[0]:,}")
            
            # Verificar estrutura
            columns = conn.execute("DESCRIBE reservas.cv_vendas_consolidadas_vera_cruz").fetchall()
            print(f"   Total de colunas: {len(columns)}")
            
            # Verificar se as novas colunas existem
            colunas_existentes = [col[0] for col in columns]
            novas_colunas = ['vpl_reserva', 'vpl_tabela', 'idreserva']
            
            print(f"\n   Verificando novas colunas:")
            for coluna in novas_colunas:
                if coluna in colunas_existentes:
                    print(f"   OK {coluna} - EXISTE")
                else:
                    print(f"   X {coluna} - NAO EXISTE")
            
        except Exception as e:
            print(f"   ERRO: {e}")
        
        # 2. Verificar se existe view sienge_vendas_consolidadas no schema informacoes_consolidadas
        print("\n2. Verificando view sienge_vendas_consolidadas no schema informacoes_consolidadas...")
        try:
            result = conn.execute("SELECT COUNT(*) FROM informacoes_consolidadas.sienge_vendas_consolidadas").fetchone()
            print(f"   View existe - Total de registros: {result[0]:,}")
            
            # Verificar estrutura
            columns = conn.execute("DESCRIBE informacoes_consolidadas.sienge_vendas_consolidadas").fetchall()
            print(f"   Total de colunas: {len(columns)}")
            
            # Verificar se as novas colunas existem
            colunas_existentes = [col[0] for col in columns]
            novas_colunas = ['vpl_reserva', 'vpl_tabela', 'idreserva']
            
            print(f"\n   Verificando novas colunas:")
            for coluna in novas_colunas:
                if coluna in colunas_existentes:
                    print(f"   OK {coluna} - EXISTE")
                else:
                    print(f"   X {coluna} - NAO EXISTE")
            
        except Exception as e:
            print(f"   ERRO: {e}")
        
        # 3. Verificar tabelas base
        print("\n3. Verificando tabelas base...")
        try:
            # Verificar sienge_vendas_realizadas
            result = conn.execute("SELECT COUNT(*) FROM reservas.sienge_vendas_realizadas").fetchone()
            print(f"   reservas.sienge_vendas_realizadas: {result[0]:,} registros")
            
            # Verificar sienge_vendas_canceladas
            result = conn.execute("SELECT COUNT(*) FROM reservas.sienge_vendas_canceladas").fetchone()
            print(f"   reservas.sienge_vendas_canceladas: {result[0]:,} registros")
            
            # Verificar reservas_abril
            result = conn.execute("SELECT COUNT(*) FROM reservas.reservas_abril").fetchone()
            print(f"   reservas.reservas_abril: {result[0]:,} registros")
            
        except Exception as e:
            print(f"   ERRO ao verificar tabelas base: {e}")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao verificar estrutura: {e}")
        return False

def main():
    """Funcao principal"""
    print("VERIFICANDO ESTRUTURA CORRETA")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        verificar_estrutura_correta(conn)
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

