#!/usr/bin/env python3
"""
Script para criar a view Jira_status_tarefas
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

def criar_view_jira_status_tarefas(conn):
    """Cria a view Jira_status_tarefas"""
    print("\n" + "="*60)
    print("CRIANDO VIEW JIRA_STATUS_TAREFAS")
    print("="*60)
    
    try:
        # 1. Usar o banco informacoes_consolidadas
        print("1. Usando banco informacoes_consolidadas...")
        conn.execute("USE informacoes_consolidadas")
        print("   Banco informacoes_consolidadas selecionado!")
        
        # 2. Remover view existente se houver
        print("\n2. Removendo view existente se houver...")
        conn.execute("DROP VIEW IF EXISTS Jira_status_tarefas")
        print("   View existente removida!")
        
        # 3. Criar view consolidada
        print("\n3. Criando view Jira_status_tarefas...")
        
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
            END as status_tarefas
            
        FROM reservas.jira_issues
        """
        
        conn.execute(sql_view)
        print("   View Jira_status_tarefas criada com sucesso!")
        
        # 4. Verificar resultado
        print(f"\n4. Verificando resultado...")
        result = conn.execute("SELECT COUNT(*) FROM Jira_status_tarefas").fetchone()
        print(f"   Total de registros: {result[0]:,}")
        
        # 5. Verificar distribuição de status_tarefas
        print(f"\n5. Verificando distribuicao de status_tarefas:")
        print("-" * 50)
        result = conn.execute("""
            SELECT 
                status_tarefas,
                COUNT(*) as total
            FROM Jira_status_tarefas
            GROUP BY status_tarefas
            ORDER BY total DESC
        """).fetchall()
        
        print("   Distribuicao:")
        for row in result:
            print(f"   - {row[0]}: {row[1]:,} registros ({row[1]/result[0][1]*100:.1f}%)")
        
        # 6. Verificar alguns exemplos
        print(f"\n6. Exemplos de dados consolidados:")
        print("-" * 50)
        result = conn.execute("""
            SELECT 
                chave,
                resumo,
                status,
                data_limite,
                status_tarefas
            FROM Jira_status_tarefas
            WHERE status_tarefas = 'Atrasada'
            LIMIT 5
        """).fetchall()
        
        print("   Exemplos de tarefas Atrasadas:")
        for row in result:
            print(f"   - {row[0]}: {row[1][:50]}... | Status: {row[2]} | Data: {row[3]} | Status Tarefa: {row[4]}")
        
        # 7. Verificar status originais vs status_tarefas
        print(f"\n7. Verificando mapeamento Status -> status_tarefas:")
        print("-" * 50)
        result = conn.execute("""
            SELECT 
                status,
                status_tarefas,
                COUNT(*) as total
            FROM Jira_status_tarefas
            GROUP BY status, status_tarefas
            ORDER BY total DESC
            LIMIT 15
        """).fetchall()
        
        print("   Top 15 combinacoes:")
        for row in result:
            print(f"   - Status '{row[0]}' -> {row[1]}: {row[2]:,} registros")
        
        # 8. Verificar tarefas atrasadas por status original
        print(f"\n8. Verificando tarefas atrasadas por status original:")
        print("-" * 50)
        result = conn.execute("""
            SELECT 
                status,
                COUNT(*) as total_atrasadas
            FROM Jira_status_tarefas
            WHERE status_tarefas = 'Atrasada'
            GROUP BY status
            ORDER BY total_atrasadas DESC
            LIMIT 10
        """).fetchall()
        
        print("   Top 10 status originais com tarefas atrasadas:")
        for row in result:
            print(f"   - {row[0]}: {row[1]:,} tarefas atrasadas")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao criar view: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Funcao principal"""
    print("CRIANDO VIEW JIRA_STATUS_TAREFAS")
    print("="*60)
    print("Regras de status_tarefas:")
    print("  - A iniciar = Status = 'Backlog'")
    print("  - Finalizada = Status = 'Concluído'")
    print("  - Atrasada = Status <> 'Backlog' E <> 'Concluído' E Data limite < hoje")
    print("  - Em Andamento = Status <> 'Backlog' E <> 'Concluído' E <> 'Atrasada'")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        if not criar_view_jira_status_tarefas(conn):
            return False
        
        print("\n" + "="*60)
        print("VIEW JIRA_STATUS_TAREFAS CRIADA COM SUCESSO!")
        print("="*60)
        print("A view consolida jira_issues com a coluna status_tarefas calculada!")
        print("Colunas: A, B, C, D, F, G, H, J, K, T, U, V, W, X, Y, Z + status_tarefas")
        
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





