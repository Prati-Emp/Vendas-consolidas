#!/usr/bin/env python3
"""
Script para verificar se há filtros necessários
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

def verificar_filtros_necessarios(conn):
    """Verifica se há filtros necessários"""
    print("\n" + "="*60)
    print("VERIFICANDO FILTROS NECESSARIOS")
    print("="*60)
    
    try:
        # 1. Verificar se há filtros por data nas tabelas Sienge
        print("1. Verificando se há filtros por data nas tabelas Sienge...")
        try:
            # Verificar sienge_vendas_realizadas por ano
            result = conn.execute("""
                SELECT date_part('year', issueDate) as ano, COUNT(*) as total
                FROM reservas.sienge_vendas_realizadas
                GROUP BY date_part('year', issueDate)
                ORDER BY ano
            """).fetchall()
            
            print("   sienge_vendas_realizadas por ano:")
            for row in result:
                print(f"   {row[0]}: {row[1]:,} registros")
            
            # Verificar sienge_vendas_canceladas por ano
            result = conn.execute("""
                SELECT date_part('year', issueDate) as ano, COUNT(*) as total
                FROM reservas.sienge_vendas_canceladas
                GROUP BY date_part('year', issueDate)
                ORDER BY ano
            """).fetchall()
            
            print("   sienge_vendas_canceladas por ano:")
            for row in result:
                print(f"   {row[0]}: {row[1]:,} registros")
                
        except Exception as e:
            print(f"   ERRO: {e}")
        
        # 2. Verificar se há filtros por empreendimento
        print("\n2. Verificando se há filtros por empreendimento...")
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
            print(f"   ERRO: {e}")
        
        # 3. Verificar se há filtros por status
        print("\n3. Verificando se há filtros por status...")
        try:
            # Verificar sienge_vendas_realizadas por status
            result = conn.execute("""
                SELECT status, COUNT(*) as total
                FROM reservas.sienge_vendas_realizadas
                GROUP BY status
                ORDER BY status
            """).fetchall()
            
            print("   sienge_vendas_realizadas por status:")
            for row in result:
                print(f"   {row[0]}: {row[1]:,} registros")
            
            # Verificar sienge_vendas_canceladas por status
            result = conn.execute("""
                SELECT status, COUNT(*) as total
                FROM reservas.sienge_vendas_canceladas
                GROUP BY status
                ORDER BY status
            """).fetchall()
            
            print("   sienge_vendas_canceladas por status:")
            for row in result:
                print(f"   {row[0]}: {row[1]:,} registros")
                
        except Exception as e:
            print(f"   ERRO: {e}")
        
        # 4. Verificar se há filtros por tipo de venda
        print("\n4. Verificando se há filtros por tipo de venda...")
        try:
            # Verificar sienge_vendas_realizadas por tipo de venda
            result = conn.execute("""
                SELECT type, COUNT(*) as total
                FROM reservas.sienge_vendas_realizadas
                GROUP BY type
                ORDER BY type
            """).fetchall()
            
            print("   sienge_vendas_realizadas por tipo:")
            for row in result:
                print(f"   {row[0]}: {row[1]:,} registros")
            
            # Verificar sienge_vendas_canceladas por tipo de venda
            result = conn.execute("""
                SELECT type, COUNT(*) as total
                FROM reservas.sienge_vendas_canceladas
                GROUP BY type
                ORDER BY type
            """).fetchall()
            
            print("   sienge_vendas_canceladas por tipo:")
            for row in result:
                print(f"   {row[0]}: {row[1]:,} registros")
                
        except Exception as e:
            print(f"   ERRO: {e}")
        
        # 5. Verificar se há filtros por valor
        print("\n5. Verificando se há filtros por valor...")
        try:
            # Verificar sienge_vendas_realizadas por faixa de valor
            result = conn.execute("""
                SELECT 
                    CASE 
                        WHEN value < 100000 THEN '< 100k'
                        WHEN value < 500000 THEN '100k-500k'
                        WHEN value < 1000000 THEN '500k-1M'
                        ELSE '> 1M'
                    END as faixa_valor,
                    COUNT(*) as total
                FROM reservas.sienge_vendas_realizadas
                GROUP BY 
                    CASE 
                        WHEN value < 100000 THEN '< 100k'
                        WHEN value < 500000 THEN '100k-500k'
                        WHEN value < 1000000 THEN '500k-1M'
                        ELSE '> 1M'
                    END
                ORDER BY faixa_valor
            """).fetchall()
            
            print("   sienge_vendas_realizadas por faixa de valor:")
            for row in result:
                print(f"   {row[0]}: {row[1]:,} registros")
                
        except Exception as e:
            print(f"   ERRO: {e}")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao verificar filtros: {e}")
        return False

def main():
    """Funcao principal"""
    print("VERIFICANDO FILTROS NECESSARIOS")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        verificar_filtros_necessarios(conn)
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

