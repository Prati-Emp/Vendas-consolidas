#!/usr/bin/env python3
"""
Script para investigar e criar a view cv_leads_workflow_consolidado
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

def investigar_tabelas_leads(conn):
    """Investiga as estruturas das tabelas cv_leads_workflow_tempo e cv_leads"""
    print("\n" + "="*60)
    print("INVESTIGANDO ESTRUTURA DAS TABELAS DE LEADS")
    print("="*60)
    
    try:
        # 1. Verificar estrutura da tabela cv_leads_workflow_tempo
        print("1. Estrutura da tabela reservas.cv_leads_workflow_tempo:")
        print("-" * 50)
        result = conn.execute("DESCRIBE reservas.cv_leads_workflow_tempo").fetchall()
        for row in result:
            print(f"   {row[0]}: {row[1]}")
        
        # 2. Verificar estrutura da tabela cv_leads
        print(f"\n2. Estrutura da tabela reservas.cv_leads:")
        print("-" * 50)
        result = conn.execute("DESCRIBE reservas.cv_leads").fetchall()
        for row in result:
            print(f"   {row[0]}: {row[1]}")
        
        # 3. Verificar quantidade de registros
        print(f"\n3. Quantidade de registros:")
        print("-" * 50)
        
        result = conn.execute("SELECT COUNT(*) FROM reservas.cv_leads_workflow_tempo").fetchone()
        print(f"   cv_leads_workflow_tempo: {result[0]:,} registros")
        
        result = conn.execute("SELECT COUNT(*) FROM reservas.cv_leads").fetchone()
        print(f"   cv_leads: {result[0]:,} registros")
        
        # 4. Verificar relacionamento idlead
        print(f"\n4. Verificando relacionamento idlead:")
        print("-" * 50)
        
        # Quantos idlead únicos em cada tabela
        result = conn.execute("SELECT COUNT(DISTINCT idlead) FROM reservas.cv_leads_workflow_tempo").fetchone()
        print(f"   idlead únicos em cv_leads_workflow_tempo: {result[0]:,}")
        
        result = conn.execute("SELECT COUNT(DISTINCT idlead) FROM reservas.cv_leads").fetchone()
        print(f"   idlead únicos em cv_leads: {result[0]:,}")
        
        # Verificar correspondências
        result = conn.execute("""
            SELECT COUNT(DISTINCT w.idlead)
            FROM reservas.cv_leads_workflow_tempo w
            INNER JOIN reservas.cv_leads l ON w.idlead = l.idlead
        """).fetchone()
        print(f"   Correspondências encontradas: {result[0]:,}")
        
        # 5. Verificar alguns exemplos de dados
        print(f"\n5. Exemplos de dados cv_leads_workflow_tempo:")
        print("-" * 50)
        result = conn.execute("""
            SELECT 
                idlead,
                COUNT(*) as total_registros
            FROM reservas.cv_leads_workflow_tempo
            GROUP BY idlead
            ORDER BY total_registros DESC
            LIMIT 10
        """).fetchall()
        
        print("   Top 10 idlead com mais registros:")
        for row in result:
            print(f"   - ID {row[0]}: {row[1]:,} registros")
        
        # 6. Verificar colunas específicas que vamos usar
        print(f"\n6. Verificando colunas específicas:")
        print("-" * 50)
        
        # Verificar corretor_consolidado, imobiliária, empreendimento_primeiro, Data_cad em cv_leads
        result = conn.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(corretor_consolidado) as com_corretor_consolidado,
                COUNT(imobiliaria) as com_imobiliaria,
                COUNT(empreendimento_primeiro) as com_empreendimento_primeiro,
                COUNT(Data_cad) as com_data_cad
            FROM reservas.cv_leads
        """).fetchone()
        
        print(f"   cv_leads:")
        print(f"   - Total: {result[0]:,}")
        print(f"   - Com corretor_consolidado: {result[1]:,} ({result[1]/result[0]*100:.1f}%)")
        print(f"   - Com imobiliaria: {result[2]:,} ({result[2]/result[0]*100:.1f}%)")
        print(f"   - Com empreendimento_primeiro: {result[3]:,} ({result[3]/result[0]*100:.1f}%)")
        print(f"   - Com Data_cad: {result[4]:,} ({result[4]/result[0]*100:.1f}%)")
        
        # 7. Verificar alguns exemplos de relacionamento
        print(f"\n7. Exemplos de relacionamento:")
        print("-" * 50)
        result = conn.execute("""
            SELECT 
                w.idlead,
                l.corretor_consolidado,
                l.imobiliaria,
                l.empreendimento_primeiro,
                l.Data_cad,
                COUNT(*) as total_workflow
            FROM reservas.cv_leads_workflow_tempo w
            INNER JOIN reservas.cv_leads l ON w.idlead = l.idlead
            GROUP BY w.idlead, l.corretor_consolidado, l.imobiliaria, l.empreendimento_primeiro, l.Data_cad
            ORDER BY total_workflow DESC
            LIMIT 5
        """).fetchall()
        
        print("   Exemplos de relacionamento:")
        for row in result:
            print(f"   ID {row[0]}: {row[1]} | {row[2]} | {row[3]} | {row[4]} ({row[5]} registros)")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao investigar tabelas: {e}")
        return False

def criar_view_leads_workflow(conn):
    """Cria a view cv_leads_workflow_consolidado"""
    print("\n" + "="*60)
    print("CRIANDO VIEW CV_LEADS_WORKFLOW_CONSOLIDADO")
    print("="*60)
    
    try:
        # 1. Usar o banco informacoes_consolidadas
        print("1. Usando banco informacoes_consolidadas...")
        conn.execute("USE informacoes_consolidadas")
        print("   Banco informacoes_consolidadas selecionado!")
        
        # 2. Remover view existente se houver
        print("\n2. Removendo view existente se houver...")
        conn.execute("DROP VIEW IF EXISTS cv_leads_workflow_consolidado")
        print("   View existente removida!")
        
        # 3. Criar view consolidada
        print("\n3. Criando view cv_leads_workflow_consolidado...")
        
        sql_view = """
        CREATE VIEW cv_leads_workflow_consolidado AS
        SELECT
            -- COLUNAS DA TABELA CV_LEADS_WORKFLOW_TEMPO
            w.referencia,
            w.referencia_data,
            w.ativo,
            w.idtempo,
            w.idlead,
            w.idsituacao,
            w.situacao,
            w.sigla,
            w.tempo,
            -- RENOMEANDO data_cad para data_ultima_alteracao
            w.data_cad as data_ultima_alteracao,
            
            -- COLUNAS DA TABELA CV_LEADS (usando idlead como chave)
            l.corretor_consolidado,
            l.imobiliaria,
            l.empreendimento_primeiro,
            l.Data_cad
            
        FROM reservas.cv_leads_workflow_tempo w
        INNER JOIN reservas.cv_leads l ON w.idlead = l.idlead
        """
        
        conn.execute(sql_view)
        print("   View cv_leads_workflow_consolidado criada com sucesso!")
        
        # 4. Verificar resultado
        print(f"\n4. Verificando resultado...")
        result = conn.execute("SELECT COUNT(*) FROM cv_leads_workflow_consolidado").fetchone()
        print(f"   Total de registros: {result[0]:,}")
        
        # 5. Verificar registros com e sem relacionamento
        print(f"\n5. Verificando relacionamentos...")
        result = conn.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(corretor_consolidado) as com_corretor_consolidado,
                COUNT(imobiliaria) as com_imobiliaria,
                COUNT(empreendimento_primeiro) as com_empreendimento_primeiro,
                COUNT(Data_cad) as com_data_cad
            FROM cv_leads_workflow_consolidado
        """).fetchone()
        
        print(f"   Total de registros: {result[0]:,}")
        print(f"   Com corretor_consolidado: {result[1]:,} ({result[1]/result[0]*100:.1f}%)")
        print(f"   Com imobiliaria: {result[2]:,} ({result[2]/result[0]*100:.1f}%)")
        print(f"   Com empreendimento_primeiro: {result[3]:,} ({result[3]/result[0]*100:.1f}%)")
        print(f"   Com Data_cad: {result[4]:,} ({result[4]/result[0]*100:.1f}%)")
        
        # 6. Verificar alguns exemplos
        print(f"\n6. Exemplos de dados consolidados:")
        print("-" * 50)
        result = conn.execute("""
            SELECT 
                idlead,
                situacao,
                corretor_consolidado,
                imobiliaria,
                empreendimento_primeiro,
                data_ultima_alteracao,
                Data_cad,
                COUNT(*) as total_registros
            FROM cv_leads_workflow_consolidado
            WHERE corretor_consolidado IS NOT NULL
            GROUP BY idlead, situacao, corretor_consolidado, imobiliaria, empreendimento_primeiro, data_ultima_alteracao, Data_cad
            ORDER BY total_registros DESC
            LIMIT 5
        """).fetchall()
        
        print("   Top 5 exemplos:")
        for row in result:
            print(f"   ID {row[0]}: {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]} | {row[6]} ({row[7]} registros)")
        
        # 7. Verificar situações únicas
        print(f"\n7. Verificando situações únicas:")
        print("-" * 50)
        result = conn.execute("""
            SELECT 
                situacao,
                COUNT(*) as total
            FROM cv_leads_workflow_consolidado
            GROUP BY situacao
            ORDER BY total DESC
            LIMIT 10
        """).fetchall()
        
        print("   Top 10 situações:")
        for row in result:
            print(f"   - {row[0]}: {row[1]:,} registros")
        
        # 8. Verificar corretores únicos
        print(f"\n8. Verificando corretores únicos:")
        print("-" * 50)
        result = conn.execute("""
            SELECT 
                corretor_consolidado,
                COUNT(*) as total
            FROM cv_leads_workflow_consolidado
            WHERE corretor_consolidado IS NOT NULL
            GROUP BY corretor_consolidado
            ORDER BY total DESC
            LIMIT 10
        """).fetchall()
        
        print("   Top 10 corretores:")
        for row in result:
            print(f"   - {row[0]}: {row[1]:,} registros")
        
        # 9. Verificar empreendimentos únicos
        print(f"\n9. Verificando empreendimentos únicos:")
        print("-" * 50)
        result = conn.execute("""
            SELECT 
                empreendimento_primeiro,
                COUNT(*) as total
            FROM cv_leads_workflow_consolidado
            WHERE empreendimento_primeiro IS NOT NULL
            GROUP BY empreendimento_primeiro
            ORDER BY total DESC
            LIMIT 10
        """).fetchall()
        
        print("   Top 10 empreendimentos:")
        for row in result:
            print(f"   - {row[0]}: {row[1]:,} registros")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao criar view: {e}")
        return False

def main():
    """Funcao principal"""
    print("CRIANDO VIEW CV_LEADS_WORKFLOW_CONSOLIDADO")
    print("="*60)
    print("Relacionamento: cv_leads_workflow_tempo.idlead = cv_leads.idlead")
    print("Colunas adicionadas: corretor_consolidado, imobiliaria, empreendimento_primeiro, Data_cad")
    print("Renomeando: data_cad -> data_ultima_alteracao")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        # Primeiro investigar as tabelas
        if not investigar_tabelas_leads(conn):
            return False
        
        # Depois criar a view
        if not criar_view_leads_workflow(conn):
            return False
        
        print("\n" + "="*60)
        print("VIEW CV_LEADS_WORKFLOW_CONSOLIDADO CRIADA COM SUCESSO!")
        print("="*60)
        print("A view une cv_leads_workflow_tempo com cv_leads usando idlead!")
        print("Colunas principais: corretor_consolidado, imobiliaria, empreendimento_primeiro, Data_cad")
        print("Coluna renomeada: data_cad -> data_ultima_alteracao")
        
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
