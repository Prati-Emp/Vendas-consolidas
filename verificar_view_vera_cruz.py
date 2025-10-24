#!/usr/bin/env python3
"""
Script para verificar a view cv_vendas_consolidadas_vera_cruz
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

def verificar_view_vera_cruz(conn):
    """Verifica a view cv_vendas_consolidadas_vera_cruz"""
    print("\n" + "="*60)
    print("VERIFICANDO VIEW CV_VENDAS_CONSOLIDADAS_VERA_CRUZ")
    print("="*60)
    
    try:
        # 1. Verificar se a view existe
        print("1. Verificando se a view existe...")
        try:
            result = conn.execute("SELECT COUNT(*) FROM cv_vendas_consolidadas_vera_cruz").fetchone()
            print(f"   View existe - Total de registros: {result[0]:,}")
        except Exception as e:
            print(f"   ERRO: {e}")
            return False
        
        # 2. Verificar estrutura da view
        print("\n2. Verificando estrutura da view...")
        try:
            columns = conn.execute("DESCRIBE cv_vendas_consolidadas_vera_cruz").fetchall()
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
            
            # Mostrar todas as colunas
            print(f"\n   Estrutura completa:")
            for i, col in enumerate(columns, 1):
                print(f"   {i:2d}. {col[0]} ({col[1]})")
                
        except Exception as e:
            print(f"   ERRO ao verificar estrutura: {e}")
            return False
        
        # 3. Verificar definição da view
        print("\n3. Verificando definição da view...")
        try:
            result = conn.execute("SELECT sql FROM duckdb_views() WHERE view_name = 'cv_vendas_consolidadas_vera_cruz'").fetchone()
            if result:
                print("   Definição da view encontrada!")
                # Mostrar apenas as primeiras linhas para não sobrecarregar
                sql_lines = result[0].split('\n')
                print("   Primeiras linhas da definição:")
                for i, line in enumerate(sql_lines[:10], 1):
                    print(f"   {i:2d}. {line}")
                if len(sql_lines) > 10:
                    print(f"   ... e mais {len(sql_lines) - 10} linhas")
            else:
                print("   Definição da view não encontrada!")
        except Exception as e:
            print(f"   ERRO ao verificar definição: {e}")
        
        # 4. Testar consulta simples
        print("\n4. Testando consulta simples...")
        try:
            result = conn.execute("""
                SELECT 
                    origem,
                    COUNT(*) as total,
                    COUNT(vpl_reserva) as com_vpl_reserva,
                    COUNT(vpl_tabela) as com_vpl_tabela,
                    COUNT(idreserva) as com_idreserva
                FROM cv_vendas_consolidadas_vera_cruz
                GROUP BY origem
                ORDER BY origem
            """).fetchall()
            
            print("   Resultado por origem:")
            for row in result:
                print(f"   {row[0]}: {row[1]:,} registros (vpl_reserva: {row[2]:,}, vpl_tabela: {row[3]:,}, idreserva: {row[4]:,})")
                
        except Exception as e:
            print(f"   ERRO ao testar consulta: {e}")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao verificar view: {e}")
        return False

def main():
    """Funcao principal"""
    print("VERIFICANDO VIEW CV_VENDAS_CONSOLIDADAS_VERA_CRUZ")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        verificar_view_vera_cruz(conn)
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

