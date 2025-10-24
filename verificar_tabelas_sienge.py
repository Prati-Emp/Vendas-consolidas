#!/usr/bin/env python3
"""
Script para verificar as tabelas Sienge
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

def verificar_tabelas_sienge(conn):
    """Verifica as tabelas Sienge"""
    print("\n" + "="*60)
    print("VERIFICANDO TABELAS SIENGE")
    print("="*60)
    
    try:
        # 1. Verificar estrutura das tabelas Sienge
        print("1. Verificando estrutura das tabelas Sienge...")
        try:
            # Sienge vendas realizadas
            columns = conn.execute("DESCRIBE reservas.sienge_vendas_realizadas").fetchall()
            print(f"   reservas.sienge_vendas_realizadas: {len(columns)} colunas")
            
            # Sienge vendas canceladas
            columns = conn.execute("DESCRIBE reservas.sienge_vendas_canceladas").fetchall()
            print(f"   reservas.sienge_vendas_canceladas: {len(columns)} colunas")
            
        except Exception as e:
            print(f"   ERRO ao verificar estrutura: {e}")
        
        # 2. Verificar contagem das tabelas Sienge
        print("\n2. Verificando contagem das tabelas Sienge...")
        try:
            # Sienge vendas realizadas
            result = conn.execute("SELECT COUNT(*) FROM reservas.sienge_vendas_realizadas").fetchone()
            print(f"   reservas.sienge_vendas_realizadas: {result[0]:,}")
            
            # Sienge vendas canceladas
            result = conn.execute("SELECT COUNT(*) FROM reservas.sienge_vendas_canceladas").fetchone()
            print(f"   reservas.sienge_vendas_canceladas: {result[0]:,}")
            
        except Exception as e:
            print(f"   ERRO ao verificar contagem: {e}")
        
        # 3. Verificar se há dados duplicados nas tabelas Sienge
        print("\n3. Verificando duplicatas nas tabelas Sienge...")
        try:
            # Verificar duplicatas em sienge_vendas_realizadas
            result = conn.execute("""
                SELECT COUNT(*) as total, COUNT(DISTINCT id) as unicos
                FROM reservas.sienge_vendas_realizadas
            """).fetchone()
            
            print(f"   sienge_vendas_realizadas - Total: {result[0]:,}, Únicos: {result[1]:,}")
            if result[0] != result[1]:
                print(f"   ⚠️  DUPLICATAS ENCONTRADAS: {result[0] - result[1]:,}")
            
            # Verificar duplicatas em sienge_vendas_canceladas
            result = conn.execute("""
                SELECT COUNT(*) as total, COUNT(DISTINCT id) as unicos
                FROM reservas.sienge_vendas_canceladas
            """).fetchone()
            
            print(f"   sienge_vendas_canceladas - Total: {result[0]:,}, Únicos: {result[1]:,}")
            if result[0] != result[1]:
                print(f"   ⚠️  DUPLICATAS ENCONTRADAS: {result[0] - result[1]:,}")
                
        except Exception as e:
            print(f"   ERRO ao verificar duplicatas: {e}")
        
        # 4. Verificar se as tabelas têm dados de outros empreendimentos
        print("\n4. Verificando dados por empreendimento...")
        try:
            # Verificar sienge_vendas_realizadas por empreendimento
            result = conn.execute("""
                SELECT enterpriseId, COUNT(*) as total
                FROM reservas.sienge_vendas_realizadas
                GROUP BY enterpriseId
                ORDER BY enterpriseId
            """).fetchall()
            
            print("   sienge_vendas_realizadas por empreendimento:")
            for row in result:
                print(f"   Enterprise {row[0]}: {row[1]:,} registros")
            
            # Verificar sienge_vendas_canceladas por empreendimento
            result = conn.execute("""
                SELECT enterpriseId, COUNT(*) as total
                FROM reservas.sienge_vendas_canceladas
                GROUP BY enterpriseId
                ORDER BY enterpriseId
            """).fetchall()
            
            print("   sienge_vendas_canceladas por empreendimento:")
            for row in result:
                print(f"   Enterprise {row[0]}: {row[1]:,} registros")
                
        except Exception as e:
            print(f"   ERRO ao verificar por empreendimento: {e}")
        
        # 5. Verificar se há dados de outros anos/períodos
        print("\n5. Verificando dados por período...")
        try:
            # Verificar sienge_vendas_realizadas por ano
            result = conn.execute("""
                SELECT EXTRACT(YEAR FROM issueDate) as ano, COUNT(*) as total
                FROM reservas.sienge_vendas_realizadas
                GROUP BY EXTRACT(YEAR FROM issueDate)
                ORDER BY ano
            """).fetchall()
            
            print("   sienge_vendas_realizadas por ano:")
            for row in result:
                print(f"   {row[0]}: {row[1]:,} registros")
            
            # Verificar sienge_vendas_canceladas por ano
            result = conn.execute("""
                SELECT EXTRACT(YEAR FROM issueDate) as ano, COUNT(*) as total
                FROM reservas.sienge_vendas_canceladas
                GROUP BY EXTRACT(YEAR FROM issueDate)
                ORDER BY ano
            """).fetchall()
            
            print("   sienge_vendas_canceladas por ano:")
            for row in result:
                print(f"   {row[0]}: {row[1]:,} registros")
                
        except Exception as e:
            print(f"   ERRO ao verificar por período: {e}")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao verificar tabelas: {e}")
        return False

def main():
    """Funcao principal"""
    print("VERIFICANDO TABELAS SIENGE")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        verificar_tabelas_sienge(conn)
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