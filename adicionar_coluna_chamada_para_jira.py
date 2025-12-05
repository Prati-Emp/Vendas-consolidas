#!/usr/bin/env python3
"""
Script para adicionar a coluna chamada_Para à view Jira_status_tarefas
Baseado na tabela de_para_situacoes_operacoes_jira
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

def investigar_tabela_de_para(conn):
    """Investiga a estrutura da tabela de_para_situacoes_operacoes_jira"""
    print("\n" + "="*60)
    print("INVESTIGANDO TABELA DE_PARA_SITUACOES_OPERACOES_JIRA")
    print("="*60)
    
    try:
        # Verificar se a tabela existe e em qual banco
        print("1. Verificando localizacao da tabela...")
        
        # Tentar diferentes schemas
        schemas = ['reservas', 'informacoes_consolidadas', 'main']
        tabela_encontrada = None
        schema_encontrado = None
        
        for schema in schemas:
            try:
                result = conn.execute(f"DESCRIBE {schema}.de_para_situacoes_operacoes_jira").fetchall()
                tabela_encontrada = result
                schema_encontrado = schema
                print(f"   Tabela encontrada no schema: {schema}")
                break
            except:
                continue
        
        if not tabela_encontrada:
            print("   ERRO: Tabela nao encontrada em nenhum schema!")
            return None
        
        # 2. Verificar estrutura da tabela
        print(f"\n2. Estrutura da tabela {schema_encontrado}.de_para_situacoes_operacoes_jira:")
        print("-" * 50)
        for row in tabela_encontrada:
            print(f"   {row[0]}: {row[1]}")
        
        # 3. Verificar quantidade de registros
        print(f"\n3. Quantidade de registros:")
        print("-" * 50)
        result = conn.execute(f"SELECT COUNT(*) FROM {schema_encontrado}.de_para_situacoes_operacoes_jira").fetchone()
        print(f"   Total: {result[0]:,} registros")
        
        # 4. Verificar valores únicos da coluna resumo
        print(f"\n4. Verificando coluna 'resumo':")
        print("-" * 50)
        result = conn.execute(f"""
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT resumo) as resumos_unicos,
                COUNT(resumo) as com_resumo
            FROM {schema_encontrado}.de_para_situacoes_operacoes_jira
        """).fetchone()
        
        print(f"   Total de registros: {result[0]:,}")
        print(f"   Resumos unicos: {result[1]:,}")
        print(f"   Com resumo preenchido: {result[2]:,}")
        
        # 5. Verificar colunas subtarefa e indice
        print(f"\n5. Verificando colunas subtarefa e indice:")
        print("-" * 50)
        
        # Verificar se existe coluna subtarefa
        colunas = [row[0] for row in tabela_encontrada]
        tem_subtarefa = 'subtarefa' in [c.lower() for c in colunas]
        tem_indice = 'indice' in [c.lower() for c in colunas]
        
        print(f"   Coluna 'subtarefa' existe: {tem_subtarefa}")
        print(f"   Coluna 'indice' existe: {tem_indice}")
        
        if tem_subtarefa:
            result = conn.execute(f"""
                SELECT 
                    COUNT(*) as total,
                    COUNT(subtarefa) as com_subtarefa
                FROM {schema_encontrado}.de_para_situacoes_operacoes_jira
            """).fetchone()
            print(f"   Total: {result[0]:,}")
            print(f"   Com subtarefa: {result[1]:,} ({result[1]/result[0]*100:.1f}%)")
        
        if tem_indice:
            result = conn.execute(f"""
                SELECT 
                    COUNT(*) as total,
                    COUNT(indice) as com_indice,
                    MIN(indice) as indice_min,
                    MAX(indice) as indice_max
                FROM {schema_encontrado}.de_para_situacoes_operacoes_jira
            """).fetchone()
            print(f"   Total: {result[0]:,}")
            print(f"   Com indice: {result[1]:,} ({result[1]/result[0]*100:.1f}%)")
            print(f"   Indice min: {result[2]}")
            print(f"   Indice max: {result[3]}")
        
        # 6. Verificar alguns exemplos de relacionamento
        print(f"\n6. Exemplos de dados:")
        print("-" * 50)
        result = conn.execute(f"""
            SELECT 
                resumo,
                subtarefa,
                indice
            FROM {schema_encontrado}.de_para_situacoes_operacoes_jira
            WHERE resumo IS NOT NULL
            LIMIT 10
        """).fetchall()
        
        print("   Exemplos de registros:")
        for row in result:
            resumo_curto = row[0][:50] + "..." if row[0] and len(row[0]) > 50 else (row[0] or "")
            print(f"   - Resumo: {resumo_curto}")
            print(f"     Subtarefa: {row[1]} | Indice: {row[2]}")
        
        # 7. Verificar correspondências com a view atual
        print(f"\n7. Verificando correspondencias com a view Jira_status_tarefas:")
        print("-" * 50)
        result = conn.execute(f"""
            SELECT 
                COUNT(DISTINCT j.resumo) as resumos_unicos_view,
                COUNT(DISTINCT d.resumo) as resumos_unicos_de_para,
                COUNT(DISTINCT CASE WHEN j.resumo = d.resumo THEN j.resumo END) as correspondencias
            FROM informacoes_consolidadas.Jira_status_tarefas j
            LEFT JOIN {schema_encontrado}.de_para_situacoes_operacoes_jira d 
                ON j.resumo = d.resumo
        """).fetchone()
        
        print(f"   Resumos unicos na view: {result[0]:,}")
        print(f"   Resumos unicos na tabela de_para: {result[1]:,}")
        print(f"   Correspondencias encontradas: {result[2]:,}")
        
        return {
            'schema': schema_encontrado,
            'tem_subtarefa': tem_subtarefa,
            'tem_indice': tem_indice,
            'colunas': colunas
        }
        
    except Exception as e:
        print(f"ERRO ao investigar tabela: {e}")
        import traceback
        traceback.print_exc()
        return None

def atualizar_view_com_chamada_para(conn, info_tabela):
    """Atualiza a view adicionando a coluna chamada_Para"""
    print("\n" + "="*60)
    print("ATUALIZANDO VIEW COM COLUNA CHAMADA_PARA")
    print("="*60)
    
    try:
        # 1. Usar o banco informacoes_consolidadas
        print("1. Usando banco informacoes_consolidadas...")
        conn.execute("USE informacoes_consolidadas")
        print("   Banco informacoes_consolidadas selecionado!")
        
        # 2. Remover view existente
        print("\n2. Removendo view existente...")
        conn.execute("DROP VIEW IF EXISTS Jira_status_tarefas")
        print("   View existente removida!")
        
        # 3. Criar view atualizada
        print("\n3. Criando view atualizada com coluna chamada_Para...")
        
        schema_de_para = info_tabela['schema']
        
        # Mapeamento das colunas da tabela jira_issues
        colunas = {
            'A': '"A - Tipo de item"',
            'B': '"B - Chave"',
            'C': '"C - Resumo"',
            'D': '"D - Responsável"',
            'F': '"F - Prioridade"',
            'G': '"G - Status"',
            'H': '"H - Resolução"',
            'J': '"J - Atualizado(a)"',
            'K': '"K - Data limite"',
            'Projeto': '"Z - Projeto.name"',
            'T': '"T - Data Início corrigida"',
            'U': '"U - Data Fim corrigida"',
            'V': '"V - Data original início"',
            'W': '"W - Data original fim"',
            'X': '"X - Start date"',
            'Y': '"Y - Dias para conclusão de Tarefa"'
        }
        
        # Construir SQL para JOIN com de_para
        colunas_select_de_para = []
        if info_tabela['tem_subtarefa']:
            colunas_select_de_para.append('d.subtarefa as para_subtarefa')
        if info_tabela['tem_indice']:
            colunas_select_de_para.append('d.indice')
        
        colunas_de_para_sql = ', ' + ', '.join(colunas_select_de_para) if colunas_select_de_para else ''
        
        sql_view = f"""
        CREATE VIEW Jira_status_tarefas AS
        WITH dados_base AS (
            SELECT
                -- COLUNAS PRINCIPAIS
                {colunas['A']} as tipo_item,
                {colunas['B']} as chave,
                {colunas['C']} as resumo,
                {colunas['D']} as responsavel,
                {colunas['F']} as prioridade,
                {colunas['G']} as status,
                {colunas['H']} as resolucao,
                {colunas['J']} as atualizado,
                {colunas['K']} as data_limite,
                {colunas['Projeto']} as projeto_name,
                
                -- COLUNAS DE DATAS
                {colunas['T']} as data_inicio_corrigida,
                {colunas['U']} as data_fim_corrigida,
                {colunas['V']} as data_original_inicio,
                {colunas['W']} as data_original_fim,
                {colunas['X']} as start_date,
                {colunas['Y']} as dias_para_conclusao,
                
                -- COLUNA CALCULADA: status_tarefas
                CASE
                    -- A iniciar = Coluna G = "Backlog"
                    WHEN {colunas['G']} = 'Backlog' THEN 'A iniciar'
                    
                    -- Finalizada = Coluna G = "Concluído"
                    WHEN {colunas['G']} = 'Concluído' THEN 'Finalizada'
                    
                    -- Atrasada = Coluna G <> "Backlog" E <> "Concluído" E K - Data limite < hoje
                    WHEN {colunas['G']} NOT IN ('Backlog', 'Concluído')
                         AND {colunas['K']} IS NOT NULL
                         AND {colunas['K']} != ''
                         AND TRY_CAST(
                             SUBSTR({colunas['K']}, 7, 4) || '-' || 
                             SUBSTR({colunas['K']}, 4, 2) || '-' || 
                             SUBSTR({colunas['K']}, 1, 2) 
                             AS DATE
                         ) < CURRENT_DATE
                    THEN 'Atrasada'
                    
                    -- Em Andamento = Coluna G <> "Backlog", "Concluído" e "Atrasada"
                    WHEN {colunas['G']} NOT IN ('Backlog', 'Concluído') THEN 'Em Andamento'
                    
                    -- Caso padrão (não deveria acontecer)
                    ELSE 'Em Andamento'
                END as status_tarefas,
                
                -- Adicionar ROW_NUMBER para identificar duplicatas
                ROW_NUMBER() OVER (
                    PARTITION BY {colunas['B']} 
                    ORDER BY 
                        CASE WHEN {colunas['J']} IS NOT NULL AND {colunas['J']} != '' THEN 1 ELSE 2 END,
                        {colunas['J']} DESC NULLS LAST
                ) as rn
                
            FROM reservas.jira_issues
        ),
        dados_com_de_para AS (
            SELECT
                db.*,
                d.subtarefa as para_subtarefa,
                d.indice
            FROM dados_base db
            LEFT JOIN {schema_de_para}.de_para_situacoes_operacoes_jira d
                ON db.resumo = d.resumo
            WHERE db.rn = 1
        )
        SELECT
            tipo_item,
            chave,
            resumo,
            responsavel,
            prioridade,
            status,
            resolucao,
            atualizado,
            data_limite,
            projeto_name,
            data_inicio_corrigida,
            data_fim_corrigida,
            data_original_inicio,
            data_original_fim,
            start_date,
            dias_para_conclusao,
            para_subtarefa as chamada_Para,
            indice,
            status_tarefas
        FROM dados_com_de_para
        """
        
        conn.execute(sql_view)
        print("   View Jira_status_tarefas atualizada com sucesso!")
        
        # 4. Verificar resultado
        print(f"\n4. Verificando resultado...")
        result = conn.execute("SELECT COUNT(*) FROM Jira_status_tarefas").fetchone()
        print(f"   Total de registros: {result[0]:,}")
        
        # 5. Verificar estrutura da view
        print(f"\n5. Verificando estrutura da view:")
        print("-" * 50)
        result = conn.execute("DESCRIBE Jira_status_tarefas").fetchall()
        print("   Colunas na view:")
        for row in result:
            print(f"   - {row[0]}: {row[1]}")
        
        # 6. Verificar preenchimento das novas colunas
        print(f"\n6. Verificando preenchimento das novas colunas:")
        print("-" * 50)
        result = conn.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(chamada_Para) as com_chamada_para,
                COUNT(indice) as com_indice
            FROM Jira_status_tarefas
        """).fetchone()
        
        total = result[0]
        print(f"   Total de registros: {total:,}")
        print(f"   - chamada_Para (para_subtarefa): {result[1]:,} ({result[1]/total*100:.1f}%)")
        print(f"   - indice: {result[2]:,} ({result[2]/total*100:.1f}%)")
        
        # 7. Verificar alguns exemplos
        print(f"\n7. Exemplos de dados com chamada_Para:")
        print("-" * 50)
        result = conn.execute("""
            SELECT 
                chave,
                resumo,
                chamada_Para,
                indice,
                status_tarefas
            FROM Jira_status_tarefas
            WHERE chamada_Para IS NOT NULL
            ORDER BY chave
            LIMIT 5
        """).fetchall()
        
        print("   Exemplos de registros com correspondencia:")
        for row in result:
            resumo_curto = row[1][:40] + "..." if row[1] and len(row[1]) > 40 else (row[1] or "")
            print(f"   - {row[0]}: {resumo_curto}")
            print(f"     chamada_Para: {row[2]} | Indice: {row[3]} | Status: {row[4]}")
        
        # 8. Verificar valores únicos de chamada_Para
        print(f"\n8. Verificando valores unicos de chamada_Para:")
        print("-" * 50)
        result = conn.execute("""
            SELECT 
                chamada_Para,
                COUNT(*) as total
            FROM Jira_status_tarefas
            WHERE chamada_Para IS NOT NULL
            GROUP BY chamada_Para
            ORDER BY total DESC
            LIMIT 10
        """).fetchall()
        
        print("   Top 10 valores de chamada_Para:")
        for row in result:
            print(f"   - '{row[0]}': {row[1]:,} registros")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao atualizar view: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Funcao principal"""
    print("ADICIONANDO COLUNA CHAMADA_PARA À VIEW JIRA_STATUS_TAREFAS")
    print("="*60)
    print("Relacionamento: resumo (view) = resumo (de_para)")
    print("Colunas: subtarefa -> chamada_Para, indice")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        # Primeiro investigar a tabela de_para
        info_tabela = investigar_tabela_de_para(conn)
        
        if not info_tabela:
            print("\nERRO: Nao foi possivel investigar a tabela de_para!")
            return False
        
        # Depois atualizar a view
        if not atualizar_view_com_chamada_para(conn, info_tabela):
            return False
        
        print("\n" + "="*60)
        print("VIEW ATUALIZADA COM SUCESSO!")
        print("="*60)
        print("A coluna chamada_Para foi adicionada à view!")
        print("A coluna indice foi adicionada à view!")
        
        return True
        
    except Exception as e:
        print(f"ERRO na execucao: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if conn:
            conn.close()
            print("\nConexao com MotherDuck encerrada.")

if __name__ == "__main__":
    main()









