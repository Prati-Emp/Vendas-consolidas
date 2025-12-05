#!/usr/bin/env python3
"""
Script para verificar a estrutura atual da view cv_workflow_consolidado
e simplificar trazendo apenas as colunas necessárias
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
    """Verifica a estrutura atual da view"""
    print("\n" + "="*60)
    print("VERIFICANDO ESTRUTURA ATUAL DA VIEW")
    print("="*60)
    
    try:
        # 1. Usar o banco informacoes_consolidadas
        print("1. Usando banco informacoes_consolidadas...")
        conn.execute("USE informacoes_consolidadas")
        print("   Banco informacoes_consolidadas selecionado!")
        
        # 2. Verificar estrutura da view atual
        print("\n2. Estrutura atual da view cv_workflow_consolidado:")
        print("-" * 50)
        result = conn.execute("DESCRIBE cv_workflow_consolidado").fetchall()
        
        print(f"   Total de colunas: {len(result)}")
        print("\n   Colunas da view:")
        for i, row in enumerate(result, 1):
            print(f"   {i:2d}. {row[0]}: {row[1]}")
        
        # 3. Verificar algumas colunas específicas
        print(f"\n3. Verificando algumas colunas específicas:")
        print("-" * 50)
        result = conn.execute("""
            SELECT 
                idreserva,
                situacao,
                empreendimento,
                corretor,
                imobiliaria,
                referencia,
                data_cad
            FROM cv_workflow_consolidado
            LIMIT 5
        """).fetchall()
        
        print("   Exemplos de dados:")
        for row in result:
            print(f"   ID {row[0]}: {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]} | {row[6]}")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao verificar view: {e}")
        return False

def simplificar_view(conn):
    """Simplifica a view trazendo apenas as colunas necessárias"""
    print("\n" + "="*60)
    print("SIMPLIFICANDO VIEW - APENAS COLUNAS ESSENCIAIS")
    print("="*60)
    
    try:
        # 1. Remover view existente
        print("1. Removendo view existente...")
        conn.execute("DROP VIEW IF EXISTS cv_workflow_consolidado")
        print("   View existente removida!")
        
        # 2. Criar view simplificada
        print("\n2. Criando view simplificada...")
        
        sql_view = """
        CREATE VIEW cv_workflow_consolidado AS
        SELECT
            -- COLUNAS ESSENCIAIS DO WORKFLOW_ABRIL
            w.referencia,
            w.referencia_data,
            w.ativo,
            w.idtempo,
            w.idreserva,
            w.idsituacao,
            w.situacao,
            w.sigla,
            w.tempo,
            w.data_cad,
            
            -- COLUNAS SOLICITADAS DA RESERVAS_ABRIL
            r.empreendimento,
            r.corretor,
            r.imobiliaria
            
        FROM reservas.workflow_abril w
        LEFT JOIN reservas.reservas_abril r ON w.idreserva = r.idreserva
        """
        
        conn.execute(sql_view)
        print("   View simplificada criada com sucesso!")
        
        # 3. Verificar resultado
        print(f"\n3. Verificando resultado...")
        result = conn.execute("SELECT COUNT(*) FROM cv_workflow_consolidado").fetchone()
        print(f"   Total de registros: {result[0]:,}")
        
        # 4. Verificar estrutura simplificada
        print(f"\n4. Estrutura simplificada:")
        print("-" * 50)
        result = conn.execute("DESCRIBE cv_workflow_consolidado").fetchall()
        
        print(f"   Total de colunas: {len(result)}")
        print("\n   Colunas da view:")
        for i, row in enumerate(result, 1):
            print(f"   {i:2d}. {row[0]}: {row[1]}")
        
        # 5. Verificar relacionamentos
        print(f"\n5. Verificando relacionamentos...")
        result = conn.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(empreendimento) as com_empreendimento,
                COUNT(corretor) as com_corretor,
                COUNT(imobiliaria) as com_imobiliaria
            FROM cv_workflow_consolidado
        """).fetchone()
        
        print(f"   Total de registros: {result[0]:,}")
        print(f"   Com empreendimento: {result[1]:,} ({result[1]/result[0]*100:.1f}%)")
        print(f"   Com corretor: {result[2]:,} ({result[2]/result[0]*100:.1f}%)")
        print(f"   Com imobiliaria: {result[3]:,} ({result[3]/result[0]*100:.1f}%)")
        
        # 6. Verificar alguns exemplos
        print(f"\n6. Exemplos de dados simplificados:")
        print("-" * 50)
        result = conn.execute("""
            SELECT 
                idreserva,
                situacao,
                empreendimento,
                corretor,
                imobiliaria,
                referencia,
                data_cad
            FROM cv_workflow_consolidado
            WHERE empreendimento IS NOT NULL
            ORDER BY idreserva
            LIMIT 5
        """).fetchall()
        
        print("   Exemplos:")
        for row in result:
            print(f"   ID {row[0]}: {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]} | {row[6]}")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao simplificar view: {e}")
        return False

def main():
    """Funcao principal"""
    print("VERIFICANDO E SIMPLIFICANDO VIEW CV_WORKFLOW_CONSOLIDADO")
    print("="*60)
    print("Removendo colunas desnecessárias e mantendo apenas o essencial")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        # Primeiro verificar a view atual
        if not verificar_view_atual(conn):
            return False
        
        # Depois simplificar
        if not simplificar_view(conn):
            return False
        
        print("\n" + "="*60)
        print("VIEW SIMPLIFICADA COM SUCESSO!")
        print("="*60)
        print("Agora a view tem apenas as colunas essenciais:")
        print("- Colunas do workflow_abril")
        print("- empreendimento, corretor, imobiliaria da reservas_abril")
        
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


