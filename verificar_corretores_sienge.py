#!/usr/bin/env python3
"""
Script para verificar corretores que realmente estão no Sienge
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

def verificar_corretores_sienge(conn):
    """Verifica corretores que estão realmente no Sienge"""
    print("\n" + "="*60)
    print("VERIFICANDO CORRETORES DO SIENGE")
    print("="*60)
    
    try:
        # 1. Verificar corretores que estão nas tabelas Sienge
        print("1. Verificando corretores que estão nas tabelas Sienge...")
        
        # Top corretores Sienge Vendas Realizadas
        result = conn.execute("""
            SELECT 
                s.brokers[1].name as corretor,
                COUNT(*) as total
            FROM reservas.sienge_vendas_realizadas s
            WHERE s.brokers[1].name IS NOT NULL
            GROUP BY s.brokers[1].name
            ORDER BY total DESC
            LIMIT 10
        """).fetchall()
        
        print("   Top 10 corretores Sienge Vendas Realizadas:")
        for row in result:
            print(f"   - {row[0]}: {row[1]:,} registros")
        
        # Top corretores Sienge Vendas Canceladas
        result = conn.execute("""
            SELECT 
                s.brokers[1].name as corretor,
                COUNT(*) as total
            FROM reservas.sienge_vendas_canceladas s
            WHERE s.brokers[1].name IS NOT NULL
            GROUP BY s.brokers[1].name
            ORDER BY total DESC
            LIMIT 10
        """).fetchall()
        
        print("\n   Top 10 corretores Sienge Vendas Canceladas:")
        for row in result:
            print(f"   - {row[0]}: {row[1]:,} registros")
        
        # 2. Verificar se esses corretores aparecem na view
        print("\n2. Verificando se esses corretores aparecem na view...")
        
        # Pegar um corretor específico do Sienge
        result = conn.execute("""
            SELECT 
                s.brokers[1].name as corretor,
                COUNT(*) as total
            FROM reservas.sienge_vendas_realizadas s
            WHERE s.brokers[1].name IS NOT NULL
            GROUP BY s.brokers[1].name
            ORDER BY total DESC
            LIMIT 1
        """).fetchone()
        
        if result:
            corretor_teste = result[0]
            print(f"   Testando corretor: {corretor_teste}")
            
            # Verificar na view
            result_view = conn.execute(f"""
                SELECT 
                    corretor,
                    origem,
                    COUNT(*) as total
                FROM informacoes_consolidadas.sienge_vendas_consolidadas
                WHERE corretor LIKE '%{corretor_teste.split()[0]}%'
                GROUP BY corretor, origem
                ORDER BY total DESC
            """).fetchall()
            
            print(f"   Na view:")
            for row in result_view:
                print(f"   - {row[0]} ({row[1]}): {row[2]:,} registros")
        
        # 3. Verificar corretores que aparecem na view mas não estão no Sienge
        print("\n3. Verificando corretores que aparecem na view mas não estão no Sienge...")
        
        result = conn.execute("""
            SELECT 
                corretor,
                origem,
                COUNT(*) as total
            FROM informacoes_consolidadas.sienge_vendas_consolidadas
            WHERE origem IN ('Sienge Realizada', 'Sienge Cancelada')
            GROUP BY corretor, origem
            ORDER BY total DESC
            LIMIT 10
        """).fetchall()
        
        print("   Top 10 corretores na view (Sienge):")
        for row in result:
            print(f"   - {row[0]} ({row[1]}): {row[2]:,} registros")
        
        # 4. Verificar se há corretores que estão no Sienge mas não aparecem na view
        print("\n4. Verificando se há corretores que estão no Sienge mas não aparecem na view...")
        
        # Pegar alguns corretores do Sienge
        result_sienge = conn.execute("""
            SELECT DISTINCT s.brokers[1].name as corretor
            FROM reservas.sienge_vendas_realizadas s
            WHERE s.brokers[1].name IS NOT NULL
            LIMIT 5
        """).fetchall()
        
        print("   Verificando alguns corretores do Sienge:")
        for row in result_sienge:
            corretor = row[0]
            if corretor:
                # Verificar se aparece na view
                result_view = conn.execute(f"""
                    SELECT COUNT(*) as total
                    FROM informacoes_consolidadas.sienge_vendas_consolidadas
                    WHERE corretor = '{corretor}'
                """).fetchone()
                
                print(f"   - {corretor}: {result_view[0]:,} registros na view")
        
        # 5. Verificar total de corretores únicos
        print("\n5. Verificando total de corretores únicos...")
        
        # Sienge Vendas Realizadas
        result = conn.execute("""
            SELECT COUNT(DISTINCT s.brokers[1].name) as total
            FROM reservas.sienge_vendas_realizadas s
            WHERE s.brokers[1].name IS NOT NULL
        """).fetchone()
        print(f"   Corretores únicos Sienge Vendas Realizadas: {result[0]:,}")
        
        # Sienge Vendas Canceladas
        result = conn.execute("""
            SELECT COUNT(DISTINCT s.brokers[1].name) as total
            FROM reservas.sienge_vendas_canceladas s
            WHERE s.brokers[1].name IS NOT NULL
        """).fetchone()
        print(f"   Corretores únicos Sienge Vendas Canceladas: {result[0]:,}")
        
        # View atual
        result = conn.execute("""
            SELECT COUNT(DISTINCT corretor) as total
            FROM informacoes_consolidadas.sienge_vendas_consolidadas
            WHERE origem IN ('Sienge Realizada', 'Sienge Cancelada')
        """).fetchone()
        print(f"   Corretores únicos na view (Sienge): {result[0]:,}")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao verificar corretores: {e}")
        return False

def main():
    """Funcao principal"""
    print("VERIFICANDO CORRETORES DO SIENGE")
    print("="*60)
    print("Verificando se os corretores do Sienge estão aparecendo corretamente na view")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        if not verificar_corretores_sienge(conn):
            return False
        
        print("\n" + "="*60)
        print("VERIFICACAO CONCLUIDA!")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"ERRO na execucao: {e}")
        return False
    
    finally:
        if conn:
            conn.close()
            print("\nConexao com MotherDuck encerrada.")

if __name__ == "__main__":
    main()
