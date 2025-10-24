#!/usr/bin/env python3
"""
Script para verificar a view cv_vendas_consolidadas_vera_cruz em detalhes
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

def verificar_view_vera_cruz_detalhado(conn):
    """Verifica a view cv_vendas_consolidadas_vera_cruz em detalhes"""
    print("\n" + "="*60)
    print("VERIFICANDO VIEW VERA CRUZ DETALHADO")
    print("="*60)
    
    try:
        # 1. Verificar contagem da view cv_vendas_consolidadas_vera_cruz
        print("1. Verificando contagem da view cv_vendas_consolidadas_vera_cruz...")
        try:
            result = conn.execute("SELECT COUNT(*) FROM reservas.cv_vendas_consolidadas_vera_cruz").fetchone()
            print(f"   reservas.cv_vendas_consolidadas_vera_cruz: {result[0]:,}")
        except Exception as e:
            print(f"   ERRO: {e}")
        
        # 2. Verificar contagem por origem na view cv_vendas_consolidadas_vera_cruz
        print("\n2. Verificando contagem por origem na view cv_vendas_consolidadas_vera_cruz...")
        try:
            result = conn.execute("""
                SELECT origem, COUNT(*) as total
                FROM reservas.cv_vendas_consolidadas_vera_cruz
                GROUP BY origem
                ORDER BY origem
            """).fetchall()
            
            for row in result:
                print(f"   {row[0]}: {row[1]:,} registros")
        except Exception as e:
            print(f"   ERRO: {e}")
        
        # 3. Verificar se há duplicatas na view cv_vendas_consolidadas_vera_cruz
        print("\n3. Verificando duplicatas na view cv_vendas_consolidadas_vera_cruz...")
        try:
            result = conn.execute("""
                SELECT COUNT(*) as total, COUNT(DISTINCT idreserva) as unicos
                FROM reservas.cv_vendas_consolidadas_vera_cruz
            """).fetchone()
            
            print(f"   Total: {result[0]:,}, Únicos por idreserva: {result[1]:,}")
            if result[0] != result[1]:
                print(f"   ⚠️  DUPLICATAS ENCONTRADAS: {result[0] - result[1]:,}")
        except Exception as e:
            print(f"   ERRO: {e}")
        
        # 4. Verificar se a view cv_vendas_consolidadas_vera_cruz está incluindo dados de outras fontes
        print("\n4. Verificando se há dados de outras fontes na view cv_vendas_consolidadas_vera_cruz...")
        try:
            result = conn.execute("""
                SELECT origem, COUNT(*) as total
                FROM reservas.cv_vendas_consolidadas_vera_cruz
                WHERE origem NOT IN ('Reserva - Mútuo')
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
        
        # 5. Verificar se há dados de outros empreendimentos
        print("\n5. Verificando dados por empreendimento na view cv_vendas_consolidadas_vera_cruz...")
        try:
            result = conn.execute("""
                SELECT enterpriseId, COUNT(*) as total
                FROM reservas.cv_vendas_consolidadas_vera_cruz
                GROUP BY enterpriseId
                ORDER BY enterpriseId
            """).fetchall()
            
            print("   Dados por empreendimento:")
            for row in result:
                print(f"   Enterprise {row[0]}: {row[1]:,} registros")
        except Exception as e:
            print(f"   ERRO: {e}")
        
        # 6. Verificar se a view cv_vendas_consolidadas_vera_cruz está incluindo dados de outras tabelas
        print("\n6. Verificando se a view cv_vendas_consolidadas_vera_cruz está incluindo dados de outras tabelas...")
        try:
            # Verificar se há dados de sienge_vendas_realizadas na view
            result = conn.execute("""
                SELECT COUNT(*) as total
                FROM reservas.cv_vendas_consolidadas_vera_cruz
                WHERE origem = 'Sienge Realizada'
            """).fetchone()
            
            if result[0] > 0:
                print(f"   ⚠️  DADOS DE SIENGE REALIZADA ENCONTRADOS: {result[0]:,}")
            
            # Verificar se há dados de sienge_vendas_canceladas na view
            result = conn.execute("""
                SELECT COUNT(*) as total
                FROM reservas.cv_vendas_consolidadas_vera_cruz
                WHERE origem = 'Sienge Cancelada'
            """).fetchone()
            
            if result[0] > 0:
                print(f"   ⚠️  DADOS DE SIENGE CANCELADA ENCONTRADOS: {result[0]:,}")
                
        except Exception as e:
            print(f"   ERRO: {e}")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao verificar view: {e}")
        return False

def main():
    """Funcao principal"""
    print("VERIFICANDO VIEW VERA CRUZ DETALHADO")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        verificar_view_vera_cruz_detalhado(conn)
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

