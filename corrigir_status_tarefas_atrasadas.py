#!/usr/bin/env python3
"""
Script para corrigir a lógica da coluna status_tarefas
para considerar corretamente tarefas atrasadas baseado em k_data_limite
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

def investigar_problema(conn):
    """Investiga o problema atual com status_tarefas"""
    print("\n" + "="*60)
    print("INVESTIGANDO PROBLEMA COM STATUS_TAREFAS")
    print("="*60)
    
    try:
        conn.execute("USE informacoes_consolidadas")
        
        # 1. Verificar tarefas que deveriam estar atrasadas mas não estão
        print("1. Verificando tarefas que deveriam estar atrasadas:")
        print("-" * 50)
        result = conn.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN status_tarefas = 'Atrasada' THEN 1 END) as atrasadas,
                COUNT(CASE WHEN status_tarefas = 'Em Andamento' THEN 1 END) as em_andamento,
                COUNT(CASE WHEN status_tarefas = 'A iniciar' THEN 1 END) as a_iniciar,
                COUNT(CASE WHEN status_tarefas = 'Finalizada' THEN 1 END) as finalizadas
            FROM Jira_status_tarefas
        """).fetchone()
        
        print(f"   Total de tarefas: {result[0]:,}")
        print(f"   - Atrasadas: {result[1]:,}")
        print(f"   - Em Andamento: {result[2]:,}")
        print(f"   - A iniciar: {result[3]:,}")
        print(f"   - Finalizadas: {result[4]:,}")
        
        # 2. Verificar tarefas com data limite passada mas status incorreto
        print(f"\n2. Verificando tarefas com data limite passada mas status incorreto:")
        print("-" * 50)
        result = conn.execute("""
            SELECT 
                COUNT(*) as total_problema
            FROM Jira_status_tarefas
            WHERE status NOT IN ('Backlog', 'Concluído')
              AND k_data_limite IS NOT NULL
              AND k_data_limite != ''
              AND TRY_CAST(
                  SUBSTR(k_data_limite, 7, 4) || '-' || 
                  SUBSTR(k_data_limite, 4, 2) || '-' || 
                  SUBSTR(k_data_limite, 1, 2) 
                  AS DATE
              ) < CURRENT_DATE
              AND status_tarefas != 'Atrasada'
        """).fetchone()
        
        print(f"   Tarefas que deveriam estar atrasadas: {result[0]:,}")
        
        # 3. Mostrar exemplos
        print(f"\n3. Exemplos de tarefas com problema:")
        print("-" * 50)
        result = conn.execute("""
            SELECT 
                chave,
                resumo,
                status,
                k_data_limite,
                status_tarefas,
                TRY_CAST(
                    SUBSTR(k_data_limite, 7, 4) || '-' || 
                    SUBSTR(k_data_limite, 4, 2) || '-' || 
                    SUBSTR(k_data_limite, 1, 2) 
                    AS DATE
                ) as data_limite_convertida,
                CURRENT_DATE as hoje
            FROM Jira_status_tarefas
            WHERE status NOT IN ('Backlog', 'Concluído')
              AND k_data_limite IS NOT NULL
              AND k_data_limite != ''
              AND TRY_CAST(
                  SUBSTR(k_data_limite, 7, 4) || '-' || 
                  SUBSTR(k_data_limite, 4, 2) || '-' || 
                  SUBSTR(k_data_limite, 1, 2) 
                  AS DATE
              ) < CURRENT_DATE
              AND status_tarefas != 'Atrasada'
            ORDER BY k_data_limite
            LIMIT 10
        """).fetchall()
        
        print("   Exemplos:")
        for row in result:
            resumo_curto = row[1][:40] + "..." if row[1] and len(row[1]) > 40 else (row[1] or "")
            print(f"   - {row[0]}: {resumo_curto}")
            print(f"     Status: {row[2]} | Data limite: {row[3]} | Status atual: {row[4]}")
            print(f"     Data convertida: {row[5]} | Hoje: {row[6]}")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao investigar: {e}")
        import traceback
        traceback.print_exc()
        return False

def corrigir_status_tarefas(conn):
    """Corrige a lógica da coluna status_tarefas"""
    print("\n" + "="*60)
    print("CORRIGINDO LOGICA DE STATUS_TAREFAS")
    print("="*60)
    
    try:
        # 1. Usar o banco correto
        print("1. Usando banco informacoes_consolidadas...")
        conn.execute("USE informacoes_consolidadas")
        print("   Banco informacoes_consolidadas selecionado!")
        
        # 2. Remover view existente
        print("\n2. Removendo view existente...")
        conn.execute("DROP VIEW IF EXISTS Jira_status_tarefas")
        print("   View existente removida!")
        
        # 3. Reconstruir view com lógica corrigida
        print("\n3. Reconstruindo view com lógica corrigida...")
        
        # Mapeamento de colunas
        mapeamento = {
            'A - Tipo de item': 'A - Tipo de item',
            'B - Chave': 'B - Chave',
            'C - Resumo': 'C - Resumo',
            'D - Responsável': 'D - Responsável',
            'E - Relator': 'E - Relator',
            'F - Prioridade': 'F - Prioridade',
            'G - Status': 'G - Status',
            'H - Resolução': 'H - Resolução',
            'K - Data limite': 'K - Data limite',
            'Z - Projeto.name': 'Z - Projeto.name',
            'T - Data Início corrigida': 'T - Data Início corrigida',
            'U - Data Fim corrigida': 'U - Data Fim corrigida',
            'V - Data original início': 'J - Data original início',
            'W - Data original fim': 'I - Data original fim',
            'X - Start date': 'X - Start date',
            'Y - Dias para conclusão de Tarefa': 'Y - Dias para conclusão de Tarefa',
        }
        
        # Construir SELECT
        colunas_select = []
        
        # Colunas principais
        colunas_select.append(f'"{mapeamento["A - Tipo de item"]}" as tipo_item')
        colunas_select.append(f'"{mapeamento["B - Chave"]}" as chave')
        colunas_select.append(f'"{mapeamento["C - Resumo"]}" as resumo')
        colunas_select.append(f'"{mapeamento["D - Responsável"]}" as responsavel')
        colunas_select.append(f'"{mapeamento["E - Relator"]}" as e_relator')
        colunas_select.append(f'"{mapeamento["F - Prioridade"]}" as prioridade')
        colunas_select.append(f'"{mapeamento["G - Status"]}" as status')
        colunas_select.append(f'"{mapeamento["H - Resolução"]}" as resolucao')
        colunas_select.append('NULL as atualizado')
        colunas_select.append(f'"{mapeamento["K - Data limite"]}" as data_limite')
        colunas_select.append(f'"{mapeamento["K - Data limite"]}" as k_data_limite')
        colunas_select.append(f'"{mapeamento["Z - Projeto.name"]}" as projeto_name')
        
        # Colunas de datas
        colunas_select.append(f'"{mapeamento["T - Data Início corrigida"]}" as data_inicio_corrigida')
        colunas_select.append(f'"{mapeamento["U - Data Fim corrigida"]}" as data_fim_corrigida')
        colunas_select.append(f'"{mapeamento["V - Data original início"]}" as data_original_inicio')
        colunas_select.append(f'"{mapeamento["W - Data original fim"]}" as data_original_fim')
        colunas_select.append(f'"{mapeamento["X - Start date"]}" as start_date')
        colunas_select.append(f'"{mapeamento["Y - Dias para conclusão de Tarefa"]}" as dias_para_conclusao')
        
        # Construir CASE para status_tarefas com lógica corrigida
        coluna_status = mapeamento['G - Status']
        coluna_data_limite = mapeamento['K - Data limite']
        
        # Converter data limite do formato DD/MM/YYYY para DATE
        # A data vem no formato DD/MM/YYYY (ex: 05/11/2025)
        expr_data_limite_convertida = f"""
            CASE
                WHEN "{coluna_data_limite}" IS NULL OR "{coluna_data_limite}" = '' THEN NULL
                WHEN LENGTH(TRIM("{coluna_data_limite}")) = 10 THEN 
                    TRY_CAST(
                        SUBSTR(TRIM("{coluna_data_limite}"), 7, 4) || '-' || 
                        SUBSTR(TRIM("{coluna_data_limite}"), 4, 2) || '-' || 
                        SUBSTR(TRIM("{coluna_data_limite}"), 1, 2) 
                        AS DATE
                    )
                ELSE NULL
            END
        """
        
        # Nova lógica corrigida:
        # 1. A iniciar = Status = "Backlog"
        # 2. Finalizada = Status = "Concluído"
        # 3. Atrasada = Status <> "Backlog" E Status <> "Concluído" E data_limite < hoje
        # 4. Em Andamento = Status <> "Backlog" E Status <> "Concluído" E (data_limite >= hoje OU data_limite IS NULL)
        case_status_tarefas = f"""
            CASE
                -- A iniciar = Status = "Backlog"
                WHEN "{coluna_status}" = 'Backlog' THEN 'A iniciar'
                
                -- Finalizada = Status = "Concluído"
                WHEN "{coluna_status}" = 'Concluído' THEN 'Finalizada'
                
                -- Atrasada = Status <> "Backlog" E Status <> "Concluído" E data_limite < hoje
                WHEN "{coluna_status}" NOT IN ('Backlog', 'Concluído')
                     AND ({expr_data_limite_convertida}) IS NOT NULL
                     AND ({expr_data_limite_convertida}) < CURRENT_DATE
                THEN 'Atrasada'
                
                -- Em Andamento = Status <> "Backlog" E Status <> "Concluído" E (data_limite >= hoje OU data_limite IS NULL)
                WHEN "{coluna_status}" NOT IN ('Backlog', 'Concluído') THEN 'Em Andamento'
                
                -- Caso padrão
                ELSE 'Em Andamento'
            END
        """
        
        colunas_select.append(f'{case_status_tarefas} as status_tarefas')
        
        # Construir SQL completo
        coluna_chave = mapeamento['B - Chave']
        
        sql_view = f"""
        CREATE VIEW Jira_status_tarefas AS
        WITH dados_base AS (
            SELECT
                {', '.join(colunas_select)},
                ROW_NUMBER() OVER (
                    PARTITION BY "{coluna_chave}" 
                    ORDER BY processado_em DESC NULLS LAST
                ) as rn
            FROM reservas.jira_issues
        ),
        dados_com_de_para AS (
            SELECT
                db.*,
                d.subtarefa as para_subtarefa,
                d.indice
            FROM dados_base db
            LEFT JOIN informacoes_consolidadas.de_para_situacoes_operacoes_jira d
                ON db.resumo = d.resumo
            WHERE db.rn = 1
        )
        SELECT
            tipo_item,
            chave,
            resumo,
            responsavel,
            e_relator,
            prioridade,
            status,
            resolucao,
            atualizado,
            data_limite,
            k_data_limite,
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
        
        # 4. Criar view
        print("   Criando view atualizada...")
        conn.execute(sql_view)
        print("   View Jira_status_tarefas atualizada com sucesso!")
        
        # 5. Verificar resultado
        print(f"\n4. Verificando resultado...")
        result = conn.execute("SELECT COUNT(*) FROM Jira_status_tarefas").fetchone()
        print(f"   Total de registros: {result[0]:,}")
        
        # 6. Verificar distribuição de status
        print(f"\n5. Distribuicao de status_tarefas:")
        print("-" * 50)
        result = conn.execute("""
            SELECT 
                status_tarefas,
                COUNT(*) as total
            FROM Jira_status_tarefas
            GROUP BY status_tarefas
            ORDER BY total DESC
        """).fetchall()
        
        total_geral = sum(row[1] for row in result)
        for row in result:
            print(f"   {row[0]}: {row[1]:,} ({row[1]/total_geral*100:.1f}%)")
        
        # 7. Verificar se o problema foi corrigido
        print(f"\n6. Verificando se o problema foi corrigido:")
        print("-" * 50)
        result = conn.execute("""
            SELECT 
                COUNT(*) as total_problema
            FROM Jira_status_tarefas
            WHERE status NOT IN ('Backlog', 'Concluído')
              AND k_data_limite IS NOT NULL
              AND k_data_limite != ''
              AND TRY_CAST(
                  SUBSTR(TRIM(k_data_limite), 7, 4) || '-' || 
                  SUBSTR(TRIM(k_data_limite), 4, 2) || '-' || 
                  SUBSTR(TRIM(k_data_limite), 1, 2) 
                  AS DATE
              ) < CURRENT_DATE
              AND status_tarefas != 'Atrasada'
        """).fetchone()
        
        if result[0] == 0:
            print("   SUCESSO: Nenhuma tarefa com data passada esta incorretamente marcada!")
        else:
            print(f"   ATENCAO: Ainda ha {result[0]:,} tarefas com problema")
        
        # 8. Mostrar exemplos de tarefas atrasadas
        print(f"\n7. Exemplos de tarefas atrasadas:")
        print("-" * 50)
        result = conn.execute("""
            SELECT 
                chave,
                resumo,
                status,
                k_data_limite,
                status_tarefas,
                TRY_CAST(
                    SUBSTR(TRIM(k_data_limite), 7, 4) || '-' || 
                    SUBSTR(TRIM(k_data_limite), 4, 2) || '-' || 
                    SUBSTR(TRIM(k_data_limite), 1, 2) 
                    AS DATE
                ) as data_limite_convertida,
                CURRENT_DATE as hoje
            FROM Jira_status_tarefas
            WHERE status_tarefas = 'Atrasada'
            ORDER BY k_data_limite
            LIMIT 10
        """).fetchall()
        
        print("   Exemplos:")
        for row in result:
            resumo_curto = row[1][:40] + "..." if row[1] and len(row[1]) > 40 else (row[1] or "")
            print(f"   - {row[0]}: {resumo_curto}")
            print(f"     Status: {row[2]} | Data limite: {row[3]} | Status tarefa: {row[4]}")
            if row[5]:
                print(f"     Data convertida: {row[5]} | Hoje: {row[6]}")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao corrigir status_tarefas: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Funcao principal"""
    print("CORRIGINDO LOGICA DE STATUS_TAREFAS")
    print("="*60)
    print("Ajustando para considerar corretamente tarefas atrasadas")
    print("baseado em k_data_limite")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        # 1. Investigar problema
        if not investigar_problema(conn):
            return False
        
        # 2. Corrigir lógica
        if not corrigir_status_tarefas(conn):
            return False
        
        print("\n" + "="*60)
        print("LOGICA DE STATUS_TAREFAS CORRIGIDA COM SUCESSO!")
        print("="*60)
        print("Agora as tarefas sao classificadas corretamente:")
        print("  - A iniciar: Status = Backlog")
        print("  - Finalizada: Status = Concluido")
        print("  - Atrasada: Status <> Backlog/Concluido E data_limite < hoje")
        print("  - Em Andamento: Status <> Backlog/Concluido E data_limite >= hoje")
        
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






