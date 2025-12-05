#!/usr/bin/env python3
"""
Script para investigar as tabelas workflow_abril e reservas_abril
antes de criar a view cv_workflow_consolidado
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

def investigar_tabelas(conn):
    """Investiga as estruturas das tabelas workflow_abril e reservas_abril"""
    print("\n" + "="*60)
    print("INVESTIGANDO ESTRUTURA DAS TABELAS")
    print("="*60)
    
    try:
        # 1. Verificar estrutura da tabela workflow_abril
        print("1. Estrutura da tabela reservas.workflow_abril:")
        print("-" * 50)
        result = conn.execute("DESCRIBE reservas.workflow_abril").fetchall()
        for row in result:
            print(f"   {row[0]}: {row[1]}")
        
        # 2. Verificar estrutura da tabela reservas_abril
        print(f"\n2. Estrutura da tabela reservas.reservas_abril:")
        print("-" * 50)
        result = conn.execute("DESCRIBE reservas.reservas_abril").fetchall()
        for row in result:
            print(f"   {row[0]}: {row[1]}")
        
        # 3. Verificar quantidade de registros
        print(f"\n3. Quantidade de registros:")
        print("-" * 50)
        
        result = conn.execute("SELECT COUNT(*) FROM reservas.workflow_abril").fetchone()
        print(f"   workflow_abril: {result[0]:,} registros")
        
        result = conn.execute("SELECT COUNT(*) FROM reservas.reservas_abril").fetchone()
        print(f"   reservas_abril: {result[0]:,} registros")
        
        # 4. Verificar relacionamento idreserva
        print(f"\n4. Verificando relacionamento idreserva:")
        print("-" * 50)
        
        # Quantos idreserva únicos em cada tabela
        result = conn.execute("SELECT COUNT(DISTINCT idreserva) FROM reservas.workflow_abril").fetchone()
        print(f"   idreserva únicos em workflow_abril: {result[0]:,}")
        
        result = conn.execute("SELECT COUNT(DISTINCT idreserva) FROM reservas.reservas_abril").fetchone()
        print(f"   idreserva únicos em reservas_abril: {result[0]:,}")
        
        # Verificar correspondências
        result = conn.execute("""
            SELECT COUNT(DISTINCT w.idreserva)
            FROM reservas.workflow_abril w
            INNER JOIN reservas.reservas_abril r ON w.idreserva = r.idreserva
        """).fetchone()
        print(f"   Correspondências encontradas: {result[0]:,}")
        
        # 5. Verificar alguns exemplos de dados
        print(f"\n5. Exemplos de dados workflow_abril:")
        print("-" * 50)
        result = conn.execute("""
            SELECT 
                idreserva,
                COUNT(*) as total_registros
            FROM reservas.workflow_abril
            GROUP BY idreserva
            ORDER BY total_registros DESC
            LIMIT 10
        """).fetchall()
        
        print("   Top 10 idreserva com mais registros:")
        for row in result:
            print(f"   - ID {row[0]}: {row[1]:,} registros")
        
        # 6. Verificar colunas específicas que vamos usar
        print(f"\n6. Verificando colunas específicas:")
        print("-" * 50)
        
        # Verificar empreendimento, corretor, imobiliaria em reservas_abril
        result = conn.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(empreendimento) as com_empreendimento,
                COUNT(corretor) as com_corretor,
                COUNT(imobiliaria) as com_imobiliaria
            FROM reservas.reservas_abril
        """).fetchone()
        
        print(f"   reservas_abril:")
        print(f"   - Total: {result[0]:,}")
        print(f"   - Com empreendimento: {result[1]:,} ({result[1]/result[0]*100:.1f}%)")
        print(f"   - Com corretor: {result[2]:,} ({result[2]/result[0]*100:.1f}%)")
        print(f"   - Com imobiliaria: {result[3]:,} ({result[3]/result[0]*100:.1f}%)")
        
        # 7. Verificar alguns exemplos de relacionamento
        print(f"\n7. Exemplos de relacionamento:")
        print("-" * 50)
        result = conn.execute("""
            SELECT 
                w.idreserva,
                r.empreendimento,
                r.corretor,
                r.imobiliaria,
                COUNT(*) as total_workflow
            FROM reservas.workflow_abril w
            INNER JOIN reservas.reservas_abril r ON w.idreserva = r.idreserva
            GROUP BY w.idreserva, r.empreendimento, r.corretor, r.imobiliaria
            ORDER BY total_workflow DESC
            LIMIT 5
        """).fetchall()
        
        print("   Exemplos de relacionamento:")
        for row in result:
            print(f"   ID {row[0]}: {row[1]} | {row[2]} | {row[3]} ({row[4]} registros)")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao investigar tabelas: {e}")
        return False

def main():
    """Funcao principal"""
    print("INVESTIGANDO TABELAS PARA CRIAR VIEW CV_WORKFLOW_CONSOLIDADO")
    print("="*60)
    print("Relacionamento: workflow_abril.idreserva = reservas_abril.idreserva")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        if not investigar_tabelas(conn):
            return False
        
        print("\n" + "="*60)
        print("INVESTIGACAO CONCLUIDA!")
        print("="*60)
        print("Pronto para criar a view cv_workflow_consolidado!")
        
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


