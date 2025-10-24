#!/usr/bin/env python3
"""
Script para verificar a view atual e seu funcionamento
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

def verificar_view_atual(conn):
    """Verifica a view atual e seu funcionamento"""
    print("\n" + "="*60)
    print("VERIFICANDO VIEW ATUAL")
    print("="*60)
    
    try:
        # 1. Verificar se a view existe
        print("1. Verificando se a view existe...")
        try:
            result = conn.execute("SELECT COUNT(*) FROM informacoes_consolidadas.sienge_vendas_consolidadas").fetchone()
            print(f"   View existe - Total de registros: {result[0]:,}")
        except Exception as e:
            print(f"   ERRO: {e}")
            return False
        
        # 2. Verificar estrutura da view
        print("\n2. Verificando estrutura da view...")
        try:
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
            result = conn.execute("SELECT sql FROM duckdb_views() WHERE view_name = 'sienge_vendas_consolidadas'").fetchone()
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
                FROM informacoes_consolidadas.sienge_vendas_consolidadas
                GROUP BY origem
                ORDER BY origem
            """).fetchall()
            
            print("   Resultado por origem:")
            for row in result:
                print(f"   {row[0]}: {row[1]:,} registros (vpl_reserva: {row[2]:,}, vpl_tabela: {row[3]:,}, idreserva: {row[4]:,})")
                
        except Exception as e:
            print(f"   ERRO ao testar consulta: {e}")
        
        # 5. Verificar se as tabelas base existem
        print("\n5. Verificando tabelas base...")
        try:
            # Verificar sienge_vendas_realizadas
            result = conn.execute("SELECT COUNT(*) FROM reservas.sienge_vendas_realizadas").fetchone()
            print(f"   sienge_vendas_realizadas: {result[0]:,} registros")
            
            # Verificar sienge_vendas_canceladas
            result = conn.execute("SELECT COUNT(*) FROM reservas.sienge_vendas_canceladas").fetchone()
            print(f"   sienge_vendas_canceladas: {result[0]:,} registros")
            
            # Verificar cv_vendas_consolidadas_vera_cruz
            result = conn.execute("SELECT COUNT(*) FROM reservas.cv_vendas_consolidadas_vera_cruz").fetchone()
            print(f"   cv_vendas_consolidadas_vera_cruz: {result[0]:,} registros")
            
        except Exception as e:
            print(f"   ERRO ao verificar tabelas base: {e}")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao verificar view: {e}")
        return False

def main():
    """Funcao principal"""
    print("VERIFICANDO VIEW ATUAL")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        verificar_view_atual(conn)
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

