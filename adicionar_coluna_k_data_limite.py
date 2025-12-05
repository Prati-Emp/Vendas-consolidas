#!/usr/bin/env python3
"""
Script para adicionar a coluna "K - Data limite" à view Jira_status_tarefas
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

def verificar_coluna_atual(conn):
    """Verifica se a coluna K - Data limite já está na view"""
    print("\n" + "="*60)
    print("VERIFICANDO COLUNA K - DATA LIMITE")
    print("="*60)
    
    try:
        conn.execute("USE informacoes_consolidadas")
        
        # Verificar estrutura da view
        print("1. Estrutura atual da view:")
        print("-" * 50)
        result = conn.execute("DESCRIBE Jira_status_tarefas").fetchall()
        colunas_view = {}
        for row in result:
            colunas_view[row[0]] = row[1]
            print(f"   {row[0]}: {row[1]}")
        
        # Verificar se já existe data_limite ou k_data_limite
        tem_data_limite = 'data_limite' in colunas_view
        tem_k_data_limite = 'k_data_limite' in colunas_view or 'K - Data limite' in colunas_view
        
        print(f"\n2. Verificando coluna K - Data limite:")
        print("-" * 50)
        print(f"   Coluna 'data_limite' existe: {tem_data_limite}")
        print(f"   Coluna 'k_data_limite' existe: {tem_k_data_limite}")
        
        if tem_data_limite:
            print(f"   A coluna 'data_limite' ja existe e vem de 'K - Data limite'")
            print(f"   Vamos adicionar tambem com o nome 'k_data_limite' para facilitar")
        
        return {
            'colunas_view': colunas_view,
            'tem_data_limite': tem_data_limite,
            'tem_k_data_limite': tem_k_data_limite
        }
        
    except Exception as e:
        print(f"ERRO ao verificar: {e}")
        import traceback
        traceback.print_exc()
        return None

def adicionar_coluna_k_data_limite(conn, info):
    """Adiciona a coluna K - Data limite à view"""
    print("\n" + "="*60)
    print("ADICIONANDO COLUNA K - DATA LIMITE À VIEW")
    print("="*60)
    
    try:
        # 1. Verificar se a coluna existe na tabela
        print("1. Verificando se 'K - Data limite' existe na tabela...")
        result = conn.execute("DESCRIBE reservas.jira_issues").fetchall()
        colunas_tabela = {row[0]: row[1] for row in result}
        
        if 'K - Data limite' not in colunas_tabela:
            print("   ERRO: Coluna 'K - Data limite' nao existe na tabela!")
            return False
        
        print(f"   Coluna encontrada! Tipo: {colunas_tabela['K - Data limite']}")
        
        # 2. Usar o banco correto
        print("\n2. Usando banco informacoes_consolidadas...")
        conn.execute("USE informacoes_consolidadas")
        print("   Banco informacoes_consolidadas selecionado!")
        
        # 3. Remover view existente
        print("\n3. Removendo view existente...")
        conn.execute("DROP VIEW IF EXISTS Jira_status_tarefas")
        print("   View existente removida!")
        
        # 4. Reconstruir view com a coluna K - Data limite
        print("\n4. Reconstruindo view com a coluna K - Data limite...")
        
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
        colunas_select.append('NULL as atualizado')  # Coluna não existe mais
        colunas_select.append(f'"{mapeamento["K - Data limite"]}" as data_limite')
        colunas_select.append(f'"{mapeamento["K - Data limite"]}" as k_data_limite')  # Adicionar também com nome original
        colunas_select.append(f'"{mapeamento["Z - Projeto.name"]}" as projeto_name')
        
        # Colunas de datas
        colunas_select.append(f'"{mapeamento["T - Data Início corrigida"]}" as data_inicio_corrigida')
        colunas_select.append(f'"{mapeamento["U - Data Fim corrigida"]}" as data_fim_corrigida')
        colunas_select.append(f'"{mapeamento["V - Data original início"]}" as data_original_inicio')
        colunas_select.append(f'"{mapeamento["W - Data original fim"]}" as data_original_fim')
        colunas_select.append(f'"{mapeamento["X - Start date"]}" as start_date')
        colunas_select.append(f'"{mapeamento["Y - Dias para conclusão de Tarefa"]}" as dias_para_conclusao')
        
        # Construir CASE para status_tarefas
        coluna_status = mapeamento['G - Status']
        coluna_data_limite = mapeamento['K - Data limite']
        
        expr_data_limite = f"""
            CASE
                WHEN "{coluna_data_limite}" IS NULL OR "{coluna_data_limite}" = '' THEN NULL
                WHEN LENGTH("{coluna_data_limite}") = 10 THEN 
                    TRY_CAST("{coluna_data_limite}" AS DATE)
                WHEN LENGTH("{coluna_data_limite}") >= 10 THEN
                    TRY_CAST(
                        SUBSTR("{coluna_data_limite}", 7, 4) || '-' || 
                        SUBSTR("{coluna_data_limite}", 4, 2) || '-' || 
                        SUBSTR("{coluna_data_limite}", 1, 2) 
                        AS DATE
                    )
                ELSE NULL
            END
        """
        
        case_status_tarefas = f"""
            CASE
                WHEN "{coluna_status}" = 'Backlog' THEN 'A iniciar'
                WHEN "{coluna_status}" = 'Concluído' THEN 'Finalizada'
                WHEN "{coluna_status}" NOT IN ('Backlog', 'Concluído')
                     AND ({expr_data_limite}) < CURRENT_DATE
                     AND ({expr_data_limite}) IS NOT NULL
                THEN 'Atrasada'
                WHEN "{coluna_status}" NOT IN ('Backlog', 'Concluído') THEN 'Em Andamento'
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
        
        # 5. Criar view
        print("   Criando view atualizada...")
        conn.execute(sql_view)
        print("   View Jira_status_tarefas atualizada com sucesso!")
        
        # 6. Verificar resultado
        print(f"\n5. Verificando resultado...")
        result = conn.execute("SELECT COUNT(*) FROM Jira_status_tarefas").fetchone()
        print(f"   Total de registros: {result[0]:,}")
        
        # 7. Verificar estrutura
        print(f"\n6. Estrutura da view:")
        print("-" * 50)
        result = conn.execute("DESCRIBE Jira_status_tarefas").fetchall()
        for row in result:
            print(f"   {row[0]}: {row[1]}")
        
        # 8. Verificar preenchimento da coluna k_data_limite
        print(f"\n7. Verificando preenchimento da coluna 'k_data_limite':")
        print("-" * 50)
        result = conn.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(k_data_limite) as com_valor,
                COUNT(DISTINCT k_data_limite) as valores_unicos
            FROM Jira_status_tarefas
        """).fetchone()
        
        total = result[0]
        print(f"   Total: {total:,}")
        print(f"   Com valor: {result[1]:,} ({result[1]/total*100:.1f}%)")
        print(f"   Valores unicos: {result[2]:,}")
        
        # 9. Mostrar alguns exemplos
        print(f"\n8. Exemplos de valores de k_data_limite:")
        print("-" * 50)
        result = conn.execute("""
            SELECT 
                chave,
                resumo,
                k_data_limite,
                status_tarefas
            FROM Jira_status_tarefas
            WHERE k_data_limite IS NOT NULL
            ORDER BY chave
            LIMIT 5
        """).fetchall()
        
        for row in result:
            resumo_curto = row[1][:40] + "..." if row[1] and len(row[1]) > 40 else (row[1] or "")
            print(f"   {row[0]}: {resumo_curto}")
            print(f"     k_data_limite: {row[2]} | Status: {row[3]}")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao adicionar coluna: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Funcao principal"""
    print("ADICIONANDO COLUNA K - DATA LIMITE À VIEW")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        # 1. Verificar coluna atual
        info = verificar_coluna_atual(conn)
        if not info:
            return False
        
        # 2. Adicionar coluna K - Data limite
        if adicionar_coluna_k_data_limite(conn, info):
            print("\n" + "="*60)
            print("COLUNA K - DATA LIMITE ADICIONADA COM SUCESSO!")
            print("="*60)
            print("A coluna 'k_data_limite' foi adicionada à view!")
            print("A coluna 'data_limite' tambem permanece na view.")
            return True
        else:
            return False
        
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






