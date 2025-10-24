#!/usr/bin/env python3
"""
Script para investigar por que a contagem está errada
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

def investigar_contagem_errada(conn):
    """Investiga por que a contagem está errada"""
    print("\n" + "="*60)
    print("INVESTIGANDO CONTAGEM ERRADA")
    print("="*60)
    
    try:
        # 1. Verificar contagem das tabelas base
        print("1. Verificando contagem das tabelas base...")
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
            total_esperado = 1058 + 39 + 53
            print(f"   Soma total esperada: {total_esperado:,}")
            
        except Exception as e:
            print(f"   ERRO ao verificar tabelas base: {e}")
        
        # 2. Verificar contagem da view atual
        print("\n2. Verificando contagem da view atual...")
        try:
            conn.execute("USE informacoes_consolidadas")
            result = conn.execute("SELECT COUNT(*) FROM sienge_vendas_consolidadas").fetchone()
            print(f"   informacoes_consolidadas.sienge_vendas_consolidadas: {result[0]:,}")
        except Exception as e:
            print(f"   ERRO ao verificar view: {e}")
        
        # 3. Verificar contagem por origem na view
        print("\n3. Verificando contagem por origem na view...")
        try:
            result = conn.execute("""
                SELECT origem, COUNT(*) as total
                FROM sienge_vendas_consolidadas
                GROUP BY origem
                ORDER BY origem
            """).fetchall()
            
            for row in result:
                print(f"   {row[0]}: {row[1]:,} registros")
        except Exception as e:
            print(f"   ERRO ao verificar por origem: {e}")
        
        # 4. Verificar se há duplicatas
        print("\n4. Verificando se há duplicatas...")
        try:
            result = conn.execute("""
                SELECT COUNT(*) as total, COUNT(DISTINCT *) as unicos
                FROM sienge_vendas_consolidadas
            """).fetchone()
            
            print(f"   Total de registros: {result[0]:,}")
            print(f"   Registros únicos: {result[1]:,}")
            print(f"   Diferença (possíveis duplicatas): {result[0] - result[1]:,}")
            
        except Exception as e:
            print(f"   ERRO ao verificar duplicatas: {e}")
        
        # 5. Verificar se a view está incluindo dados de outras fontes
        print("\n5. Verificando se há dados de outras fontes...")
        try:
            result = conn.execute("""
                SELECT origem, COUNT(*) as total
                FROM sienge_vendas_consolidadas
                WHERE origem NOT IN ('Sienge Realizada', 'Sienge Cancelada', 'Reserva - Mútuo')
                GROUP BY origem
                ORDER BY origem
            """).fetchall()
            
            if result:
                print("   Origens inesperadas encontradas:")
                for row in result:
                    print(f"   {row[0]}: {row[1]:,} registros")
            else:
                print("   Nenhuma origem inesperada encontrada")
                
        except Exception as e:
            print(f"   ERRO ao verificar origens: {e}")
        
        # 6. Verificar se há problemas na view cv_vendas_consolidadas_vera_cruz
        print("\n6. Verificando view cv_vendas_consolidadas_vera_cruz...")
        try:
            result = conn.execute("""
                SELECT origem, COUNT(*) as total
                FROM reservas.cv_vendas_consolidadas_vera_cruz
                GROUP BY origem
                ORDER BY origem
            """).fetchall()
            
            print("   Origens na view cv_vendas_consolidadas_vera_cruz:")
            for row in result:
                print(f"   {row[0]}: {row[1]:,} registros")
                
        except Exception as e:
            print(f"   ERRO ao verificar view vera cruz: {e}")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao investigar: {e}")
        return False

def main():
    """Funcao principal"""
    print("INVESTIGANDO CONTAGEM ERRADA")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        investigar_contagem_errada(conn)
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

