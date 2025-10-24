#!/usr/bin/env python3
"""
Script para verificar a view principal em detalhes
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

def verificar_view_principal_detalhado(conn):
    """Verifica a view principal em detalhes"""
    print("\n" + "="*60)
    print("VERIFICANDO VIEW PRINCIPAL DETALHADO")
    print("="*60)
    
    try:
        # 1. Usar o banco informacoes_consolidadas
        print("1. Usando banco informacoes_consolidadas...")
        try:
            conn.execute("USE informacoes_consolidadas")
            print("   Banco informacoes_consolidadas selecionado!")
        except Exception as e:
            print(f"   ERRO ao usar banco: {e}")
            return False
        
        # 2. Verificar contagem da view principal
        print("\n2. Verificando contagem da view principal...")
        try:
            result = conn.execute("SELECT COUNT(*) FROM sienge_vendas_consolidadas").fetchone()
            print(f"   sienge_vendas_consolidadas: {result[0]:,}")
        except Exception as e:
            print(f"   ERRO: {e}")
        
        # 3. Verificar contagem por origem na view principal
        print("\n3. Verificando contagem por origem na view principal...")
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
            print(f"   ERRO: {e}")
        
        # 4. Verificar se há duplicatas na view principal
        print("\n4. Verificando duplicatas na view principal...")
        try:
            result = conn.execute("""
                SELECT COUNT(*) as total, COUNT(DISTINCT enterpriseId, cliente, value, issueDate) as unicos
                FROM sienge_vendas_consolidadas
            """).fetchone()
            
            print(f"   Total: {result[0]:,}, Únicos: {result[1]:,}")
            if result[0] != result[1]:
                print(f"   ⚠️  DUPLICATAS ENCONTRADAS: {result[0] - result[1]:,}")
        except Exception as e:
            print(f"   ERRO: {e}")
        
        # 5. Verificar se há dados de outros empreendimentos
        print("\n5. Verificando dados por empreendimento na view principal...")
        try:
            result = conn.execute("""
                SELECT enterpriseId, COUNT(*) as total
                FROM sienge_vendas_consolidadas
                GROUP BY enterpriseId
                ORDER BY enterpriseId
            """).fetchall()
            
            print("   Dados por empreendimento:")
            for row in result:
                print(f"   Enterprise {row[0]}: {row[1]:,} registros")
        except Exception as e:
            print(f"   ERRO: {e}")
        
        # 6. Verificar se há dados de outros anos/períodos
        print("\n6. Verificando dados por período na view principal...")
        try:
            result = conn.execute("""
                SELECT date_part('year', issueDate) as ano, COUNT(*) as total
                FROM sienge_vendas_consolidadas
                GROUP BY date_part('year', issueDate)
                ORDER BY ano
            """).fetchall()
            
            print("   Dados por ano:")
            for row in result:
                print(f"   {row[0]}: {row[1]:,} registros")
        except Exception as e:
            print(f"   ERRO: {e}")
        
        # 7. Verificar se há dados de outras fontes
        print("\n7. Verificando se há dados de outras fontes na view principal...")
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
            print(f"   ERRO: {e}")
        
        # 8. Verificar se há dados de outras tabelas
        print("\n8. Verificando se há dados de outras tabelas na view principal...")
        try:
            # Verificar se há dados de sienge_vendas_realizadas na view
            result = conn.execute("""
                SELECT COUNT(*) as total
                FROM sienge_vendas_consolidadas
                WHERE origem = 'Sienge Realizada'
            """).fetchone()
            
            print(f"   Dados de Sienge Realizada: {result[0]:,}")
            
            # Verificar se há dados de sienge_vendas_canceladas na view
            result = conn.execute("""
                SELECT COUNT(*) as total
                FROM sienge_vendas_consolidadas
                WHERE origem = 'Sienge Cancelada'
            """).fetchone()
            
            print(f"   Dados de Sienge Cancelada: {result[0]:,}")
            
            # Verificar se há dados de reservas na view
            result = conn.execute("""
                SELECT COUNT(*) as total
                FROM sienge_vendas_consolidadas
                WHERE origem = 'Reserva - Mútuo'
            """).fetchone()
            
            print(f"   Dados de Reserva - Mútuo: {result[0]:,}")
                
        except Exception as e:
            print(f"   ERRO: {e}")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao verificar view: {e}")
        return False

def main():
    """Funcao principal"""
    print("VERIFICANDO VIEW PRINCIPAL DETALHADO")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        verificar_view_principal_detalhado(conn)
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

