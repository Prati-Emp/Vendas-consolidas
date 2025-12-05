#!/usr/bin/env python3
"""
Script para adicionar a coluna Projeto.name à view Jira_status_tarefas
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

def verificar_coluna_projeto(conn):
    """Verifica a coluna Projeto.name na tabela original"""
    print("\n" + "="*60)
    print("VERIFICANDO COLUNA PROJETO.NAME")
    print("="*60)
    
    try:
        # Verificar estrutura da tabela
        result = conn.execute("DESCRIBE reservas.jira_issues").fetchall()
        
        print("Procurando coluna 'Projeto.name' na tabela:")
        for i, row in enumerate(result):
            if 'Projeto' in row[0] or 'projeto' in row[0].lower():
                print(f"   {i+1}. {row[0]}: {row[1]}")
        
        # Verificar valores únicos da coluna Projeto.name
        coluna_projeto = None
        for row in result:
            if 'Projeto.name' in row[0] or 'Projeto' in row[0] and 'name' in row[0]:
                coluna_projeto = row[0]
                break
        
        if not coluna_projeto:
            # Tentar encontrar por padrão
            for row in result:
                if 'Z -' in row[0] and 'Projeto' in row[0]:
                    coluna_projeto = row[0]
                    break
        
        if coluna_projeto:
            print(f"\nColuna encontrada: {coluna_projeto}")
            
            # Verificar valores únicos
            result = conn.execute(f"""
                SELECT 
                    "{coluna_projeto}" as projeto,
                    COUNT(*) as total
                FROM reservas.jira_issues
                WHERE "{coluna_projeto}" IS NOT NULL
                GROUP BY "{coluna_projeto}"
                ORDER BY total DESC
                LIMIT 10
            """).fetchall()
            
            print(f"\nTop 10 valores unicos em '{coluna_projeto}':")
            for row in result:
                print(f"   - '{row[0]}': {row[1]:,} registros")
            
            return coluna_projeto
        else:
            print("ERRO: Coluna Projeto.name nao encontrada!")
            print("\nTodas as colunas disponiveis:")
            for i, row in enumerate(result):
                print(f"   {i+1}. {row[0]}")
            return None
        
    except Exception as e:
        print(f"ERRO ao verificar coluna: {e}")
        import traceback
        traceback.print_exc()
        return None

def atualizar_view_com_projeto(conn, coluna_projeto):
    """Atualiza a view adicionando a coluna Projeto.name"""
    print("\n" + "="*60)
    print("ATUALIZANDO VIEW COM COLUNA PROJETO.NAME")
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
        
        # 3. Criar view atualizada com a coluna Projeto.name
        print("\n3. Criando view atualizada com coluna Projeto.name...")
        
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
            'T': '"AA - Pai"',
            'U': '"M - Status Transition"',
            'V': '"N - Status Transition.to"',
            'W': '"O - Status Transition.from"',
            'X': '"P - Status Transition.authorDisplayName"',
            'Y': '"Q - Status Transition.authorEmail"',
            'Z': '"R - Status Transition.date"',
            'Projeto': f'"{coluna_projeto}"'
        }
        
        sql_view = f"""
        CREATE VIEW Jira_status_tarefas AS
        WITH dados_base AS (
            SELECT
                -- COLUNAS SOLICITADAS
                {colunas['A']} as tipo_item,
                {colunas['B']} as chave,
                {colunas['C']} as resumo,
                {colunas['D']} as responsavel,
                {colunas['F']} as prioridade,
                {colunas['G']} as status,
                {colunas['H']} as resolucao,
                {colunas['J']} as atualizado,
                {colunas['K']} as data_limite,
                {colunas['T']} as pai,
                {colunas['U']} as status_transition,
                {colunas['V']} as status_transition_to,
                {colunas['W']} as status_transition_from,
                {colunas['X']} as status_transition_author_display_name,
                {colunas['Y']} as status_transition_author_email,
                {colunas['Z']} as status_transition_date,
                {colunas['Projeto']} as projeto_name,
                
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
            pai,
            status_transition,
            status_transition_to,
            status_transition_from,
            status_transition_author_display_name,
            status_transition_author_email,
            status_transition_date,
            projeto_name,
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
        
        # 5. Verificar se ainda há duplicatas
        print(f"\n5. Verificando se ainda ha duplicatas...")
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
        else:
            print(f"   ATENCAO: Ainda ha {result[0] - result[1]} registros duplicados!")
        
        # 6. Verificar valores da coluna projeto_name
        print(f"\n6. Verificando valores da coluna projeto_name:")
        print("-" * 50)
        result = conn.execute("""
            SELECT 
                projeto_name,
                COUNT(*) as total
            FROM Jira_status_tarefas
            WHERE projeto_name IS NOT NULL
            GROUP BY projeto_name
            ORDER BY total DESC
            LIMIT 10
        """).fetchall()
        
        total_com_projeto = sum(row[1] for row in result)
        total_geral = conn.execute("SELECT COUNT(*) FROM Jira_status_tarefas").fetchone()[0]
        
        print("   Top 10 projetos:")
        for row in result:
            print(f"   - '{row[0]}': {row[1]:,} registros")
        
        print(f"\n   Total com projeto preenchido: {total_com_projeto:,} ({total_com_projeto/total_geral*100:.1f}%)")
        print(f"   Total sem projeto: {total_geral - total_com_projeto:,} ({(total_geral - total_com_projeto)/total_geral*100:.1f}%)")
        
        # 7. Verificar alguns exemplos
        print(f"\n7. Exemplos de dados com projeto_name:")
        print("-" * 50)
        result = conn.execute("""
            SELECT 
                chave,
                resumo,
                projeto_name,
                status_tarefas
            FROM Jira_status_tarefas
            WHERE projeto_name IS NOT NULL
            ORDER BY chave
            LIMIT 5
        """).fetchall()
        
        print("   Exemplos de registros:")
        for row in result:
            resumo_curto = row[1][:40] + "..." if row[1] and len(row[1]) > 40 else (row[1] or "")
            print(f"   - {row[0]}: {resumo_curto} | Projeto: {row[2]} | Status: {row[3]}")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao atualizar view: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Funcao principal"""
    print("ADICIONANDO COLUNA PROJETO.NAME À VIEW JIRA_STATUS_TAREFAS")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        # Primeiro verificar a coluna
        coluna_projeto = verificar_coluna_projeto(conn)
        
        if not coluna_projeto:
            print("\nERRO: Nao foi possivel encontrar a coluna Projeto.name!")
            return False
        
        # Depois atualizar a view
        if not atualizar_view_com_projeto(conn, coluna_projeto):
            return False
        
        print("\n" + "="*60)
        print("VIEW ATUALIZADA COM SUCESSO!")
        print("="*60)
        print("A coluna projeto_name foi adicionada à view!")
        
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









