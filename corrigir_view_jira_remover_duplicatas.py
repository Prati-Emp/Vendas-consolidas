#!/usr/bin/env python3
"""
Script para corrigir a view Jira_status_tarefas removendo duplicatas por chave
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

def verificar_duplicatas(conn):
    """Verifica quantas duplicatas existem por chave"""
    print("\n" + "="*60)
    print("VERIFICANDO DUPLICATAS POR CHAVE")
    print("="*60)
    
    try:
        # Verificar chaves duplicadas
        result = conn.execute("""
            SELECT 
                chave,
                COUNT(*) as total
            FROM informacoes_consolidadas.Jira_status_tarefas
            GROUP BY chave
            HAVING COUNT(*) > 1
            ORDER BY total DESC
            LIMIT 10
        """).fetchall()
        
        print(f"Top 10 chaves com mais duplicatas:")
        for row in result:
            print(f"   - {row[0]}: {row[1]} registros")
        
        # Contar total de duplicatas
        result = conn.execute("""
            SELECT 
                COUNT(*) as total_registros,
                COUNT(DISTINCT chave) as chaves_unicas,
                COUNT(*) - COUNT(DISTINCT chave) as registros_duplicados
            FROM informacoes_consolidadas.Jira_status_tarefas
        """).fetchone()
        
        print(f"\nEstatisticas:")
        print(f"   - Total de registros: {result[0]:,}")
        print(f"   - Chaves unicas: {result[1]:,}")
        print(f"   - Registros duplicados: {result[2]:,}")
        
        return result
        
    except Exception as e:
        print(f"ERRO ao verificar duplicatas: {e}")
        import traceback
        traceback.print_exc()
        return None

def corrigir_view_remover_duplicatas(conn):
    """Corrige a view removendo duplicatas por chave"""
    print("\n" + "="*60)
    print("CORRIGINDO VIEW PARA REMOVER DUPLICATAS")
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
        
        # 3. Criar view sem duplicatas usando ROW_NUMBER
        print("\n3. Criando view sem duplicatas...")
        
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
            'Z': '"R - Status Transition.date"'
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
            status_tarefas
        FROM dados_base
        WHERE rn = 1
        """
        
        conn.execute(sql_view)
        print("   View Jira_status_tarefas criada sem duplicatas!")
        
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
        
        # 6. Verificar distribuição de status_tarefas
        print(f"\n6. Verificando distribuicao de status_tarefas:")
        print("-" * 50)
        result = conn.execute("""
            SELECT 
                status_tarefas,
                COUNT(*) as total
            FROM Jira_status_tarefas
            GROUP BY status_tarefas
            ORDER BY total DESC
        """).fetchall()
        
        total = sum(row[1] for row in result)
        print("   Distribuicao:")
        for row in result:
            print(f"   - {row[0]}: {row[1]:,} registros ({row[1]/total*100:.1f}%)")
        
        # 7. Verificar alguns exemplos
        print(f"\n7. Exemplos de dados consolidados:")
        print("-" * 50)
        result = conn.execute("""
            SELECT 
                chave,
                resumo,
                status,
                status_tarefas
            FROM Jira_status_tarefas
            ORDER BY chave
            LIMIT 5
        """).fetchall()
        
        print("   Exemplos de registros:")
        for row in result:
            resumo_curto = row[1][:50] + "..." if row[1] and len(row[1]) > 50 else (row[1] or "")
            print(f"   - {row[0]}: {resumo_curto} | Status: {row[2]} | Status Tarefa: {row[3]}")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao corrigir view: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Funcao principal"""
    print("CORRIGINDO VIEW JIRA_STATUS_TAREFAS - REMOVENDO DUPLICATAS")
    print("="*60)
    print("Removendo duplicatas baseadas na coluna B (chave)")
    print("Mantendo apenas chaves unicas")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        # Primeiro verificar duplicatas
        verificar_duplicatas(conn)
        
        # Depois corrigir a view
        if not corrigir_view_remover_duplicatas(conn):
            return False
        
        print("\n" + "="*60)
        print("VIEW CORRIGIDA COM SUCESSO!")
        print("="*60)
        print("A view agora contem apenas chaves unicas!")
        
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










