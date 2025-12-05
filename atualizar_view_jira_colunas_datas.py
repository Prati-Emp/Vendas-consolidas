#!/usr/bin/env python3
"""
Script para atualizar a view Jira_status_tarefas
Removendo colunas de status_transition e adicionando colunas de datas
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

def verificar_colunas_datas(conn):
    """Verifica as colunas de datas na tabela original"""
    print("\n" + "="*60)
    print("VERIFICANDO COLUNAS DE DATAS")
    print("="*60)
    
    try:
        # Verificar estrutura da tabela
        result = conn.execute("DESCRIBE reservas.jira_issues").fetchall()
        
        print("Procurando colunas de datas:")
        colunas_datas = {}
        
        for i, row in enumerate(result):
            nome_coluna = row[0]
            # Procurar por padrões de datas
            if 'Data Início corrigida' in nome_coluna or 'Data Inicio corrigida' in nome_coluna:
                colunas_datas['T'] = nome_coluna
                print(f"   T: {nome_coluna}")
            elif 'Data Fim corrigida' in nome_coluna:
                colunas_datas['U'] = nome_coluna
                print(f"   U: {nome_coluna}")
            elif 'Data original início' in nome_coluna or 'Data original inicio' in nome_coluna:
                colunas_datas['V'] = nome_coluna
                print(f"   V: {nome_coluna}")
            elif 'Data original fim' in nome_coluna:
                colunas_datas['W'] = nome_coluna
                print(f"   W: {nome_coluna}")
            elif 'Start date' in nome_coluna:
                colunas_datas['X'] = nome_coluna
                print(f"   X: {nome_coluna}")
            elif 'Dias para conclusão' in nome_coluna or 'Dias para conclusao' in nome_coluna:
                colunas_datas['Y'] = nome_coluna
                print(f"   Y: {nome_coluna}")
        
        # Verificar se todas as colunas foram encontradas
        if len(colunas_datas) < 6:
            print("\nColunas nao encontradas. Listando todas as colunas:")
            for i, row in enumerate(result):
                print(f"   {i+1}. {row[0]}")
        
        return colunas_datas
        
    except Exception as e:
        print(f"ERRO ao verificar colunas: {e}")
        import traceback
        traceback.print_exc()
        return None

def atualizar_view_colunas_datas(conn, colunas_datas):
    """Atualiza a view removendo status_transition e adicionando colunas de datas"""
    print("\n" + "="*60)
    print("ATUALIZANDO VIEW COM COLUNAS DE DATAS")
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
        print("\n3. Criando view atualizada...")
        
        # Mapeamento das colunas
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
            'Projeto': '"Z - Projeto.name"'
        }
        
        # Adicionar colunas de datas
        for letra, nome_coluna in colunas_datas.items():
            colunas[letra] = f'"{nome_coluna}"'
        
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
            status_tarefas
        FROM dados_base
        WHERE rn = 1
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
        
        # 6. Verificar se ainda há duplicatas
        print(f"\n6. Verificando se ainda ha duplicatas...")
        result = conn.execute("""
            SELECT 
                COUNT(*) as total_registros,
                COUNT(DISTINCT chave) as chaves_unicas
            FROM Jira_status_tarefas
        """).fetchone()
        
        print(f"   Total de registros: {result[0]:,}")
        print(f"   Chaves unicas: {result[1]:,}")
        
        if result[0] == result[1]:
            print("   SUCESSO: Nao ha mais duplicatas!")
        
        # 7. Verificar preenchimento das colunas de datas
        print(f"\n7. Verificando preenchimento das colunas de datas:")
        print("-" * 50)
        result = conn.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(data_inicio_corrigida) as com_data_inicio_corrigida,
                COUNT(data_fim_corrigida) as com_data_fim_corrigida,
                COUNT(data_original_inicio) as com_data_original_inicio,
                COUNT(data_original_fim) as com_data_original_fim,
                COUNT(start_date) as com_start_date,
                COUNT(dias_para_conclusao) as com_dias_para_conclusao
            FROM Jira_status_tarefas
        """).fetchone()
        
        total = result[0]
        print(f"   Total de registros: {total:,}")
        print(f"   - data_inicio_corrigida: {result[1]:,} ({result[1]/total*100:.1f}%)")
        print(f"   - data_fim_corrigida: {result[2]:,} ({result[2]/total*100:.1f}%)")
        print(f"   - data_original_inicio: {result[3]:,} ({result[3]/total*100:.1f}%)")
        print(f"   - data_original_fim: {result[4]:,} ({result[4]/total*100:.1f}%)")
        print(f"   - start_date: {result[5]:,} ({result[5]/total*100:.1f}%)")
        print(f"   - dias_para_conclusao: {result[6]:,} ({result[6]/total*100:.1f}%)")
        
        # 8. Verificar alguns exemplos
        print(f"\n8. Exemplos de dados com colunas de datas:")
        print("-" * 50)
        result = conn.execute("""
            SELECT 
                chave,
                resumo,
                data_inicio_corrigida,
                data_fim_corrigida,
                dias_para_conclusao,
                status_tarefas
            FROM Jira_status_tarefas
            WHERE data_inicio_corrigida IS NOT NULL
            ORDER BY chave
            LIMIT 5
        """).fetchall()
        
        print("   Exemplos de registros:")
        for row in result:
            resumo_curto = row[1][:30] + "..." if row[1] and len(row[1]) > 30 else (row[1] or "")
            print(f"   - {row[0]}: {resumo_curto}")
            print(f"     Início: {row[2]} | Fim: {row[3]} | Dias: {row[4]} | Status: {row[5]}")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao atualizar view: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Funcao principal"""
    print("ATUALIZANDO VIEW JIRA_STATUS_TAREFAS")
    print("="*60)
    print("Removendo colunas de status_transition")
    print("Adicionando colunas de datas")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        # Primeiro verificar as colunas de datas
        colunas_datas = verificar_colunas_datas(conn)
        
        if not colunas_datas or len(colunas_datas) < 6:
            print("\nERRO: Nao foi possivel encontrar todas as colunas de datas!")
            return False
        
        # Depois atualizar a view
        if not atualizar_view_colunas_datas(conn, colunas_datas):
            return False
        
        print("\n" + "="*60)
        print("VIEW ATUALIZADA COM SUCESSO!")
        print("="*60)
        print("Colunas de status_transition removidas")
        print("Colunas de datas adicionadas")
        
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









