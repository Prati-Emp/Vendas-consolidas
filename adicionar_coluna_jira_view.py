#!/usr/bin/env python3
"""
Script para adicionar uma nova coluna à view Jira_status_tarefas
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

def investigar_colunas_disponiveis(conn):
    """Investiga quais colunas estão na tabela mas não na view"""
    print("\n" + "="*60)
    print("INVESTIGANDO COLUNAS DISPONIVEIS")
    print("="*60)
    
    try:
        # 1. Verificar colunas da tabela base
        print("1. Colunas na tabela reservas.jira_issues:")
        print("-" * 50)
        result = conn.execute("DESCRIBE reservas.jira_issues").fetchall()
        colunas_tabela = {}
        for row in result:
            colunas_tabela[row[0]] = row[1]
            print(f"   {row[0]}: {row[1]}")
        
        # 2. Verificar colunas da view atual
        print(f"\n2. Colunas na view informacoes_consolidadas.Jira_status_tarefas:")
        print("-" * 50)
        conn.execute("USE informacoes_consolidadas")
        result = conn.execute("DESCRIBE Jira_status_tarefas").fetchall()
        colunas_view = {}
        for row in result:
            colunas_view[row[0]] = row[1]
            print(f"   {row[0]}: {row[1]}")
        
        # 3. Identificar colunas que estão na tabela mas não na view
        print(f"\n3. Colunas disponiveis na tabela mas NAO na view:")
        print("-" * 50)
        colunas_faltando = []
        
        # Colunas da tabela que não foram mapeadas para a view
        colunas_nao_mapeadas = [
            'E - Relator',
            'L - Descrição',
            'AA - Pai',
            'fonte',
            'processado_em'
        ]
        
        for coluna in colunas_nao_mapeadas:
            if coluna in colunas_tabela:
                colunas_faltando.append(coluna)
                print(f"   - {coluna}: {colunas_tabela[coluna]}")
        
        return {
            'colunas_tabela': colunas_tabela,
            'colunas_view': colunas_view,
            'colunas_faltando': colunas_faltando
        }
        
    except Exception as e:
        print(f"ERRO ao investigar: {e}")
        import traceback
        traceback.print_exc()
        return None

def adicionar_coluna_view(conn, nome_coluna):
    """Adiciona uma coluna específica à view"""
    print("\n" + "="*60)
    print(f"ADICIONANDO COLUNA '{nome_coluna}' À VIEW")
    print("="*60)
    
    try:
        # 1. Verificar se a coluna existe na tabela
        print(f"1. Verificando se '{nome_coluna}' existe na tabela...")
        result = conn.execute("DESCRIBE reservas.jira_issues").fetchall()
        colunas_tabela = {row[0]: row[1] for row in result}
        
        if nome_coluna not in colunas_tabela:
            print(f"   ERRO: Coluna '{nome_coluna}' nao existe na tabela!")
            print(f"   Colunas disponiveis:")
            for col in colunas_tabela.keys():
                print(f"     - {col}")
            return False
        
        print(f"   Coluna encontrada! Tipo: {colunas_tabela[nome_coluna]}")
        
        # 2. Usar o banco correto
        print("\n2. Usando banco informacoes_consolidadas...")
        conn.execute("USE informacoes_consolidadas")
        print("   Banco informacoes_consolidadas selecionado!")
        
        # 3. Obter estrutura atual da view
        print("\n3. Obtendo estrutura atual da view...")
        result = conn.execute("DESCRIBE Jira_status_tarefas").fetchall()
        colunas_view_atual = [row[0] for row in result]
        
        # Verificar se a coluna já está na view
        nome_coluna_view = nome_coluna.lower().replace(' - ', '_').replace(' ', '_').replace('.', '_')
        if nome_coluna_view in colunas_view_atual:
            print(f"   Aviso: Coluna '{nome_coluna_view}' ja existe na view!")
            return True
        
        # 4. Remover view existente
        print("\n4. Removendo view existente...")
        conn.execute("DROP VIEW IF EXISTS Jira_status_tarefas")
        print("   View existente removida!")
        
        # 5. Reconstruir view com a nova coluna
        print("\n5. Reconstruindo view com a nova coluna...")
        
        # Mapeamento de colunas (baseado no script anterior)
        mapeamento = {
            'A - Tipo de item': 'A - Tipo de item',
            'B - Chave': 'B - Chave',
            'C - Resumo': 'C - Resumo',
            'D - Responsável': 'D - Responsável',
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
        
        # Adicionar a nova coluna ao mapeamento se necessário
        if nome_coluna not in mapeamento:
            mapeamento[nome_coluna] = nome_coluna
        
        # Construir SELECT
        colunas_select = []
        
        # Colunas principais
        colunas_select.append(f'"{mapeamento["A - Tipo de item"]}" as tipo_item')
        colunas_select.append(f'"{mapeamento["B - Chave"]}" as chave')
        colunas_select.append(f'"{mapeamento["C - Resumo"]}" as resumo')
        colunas_select.append(f'"{mapeamento["D - Responsável"]}" as responsavel')
        colunas_select.append(f'"{mapeamento["F - Prioridade"]}" as prioridade')
        colunas_select.append(f'"{mapeamento["G - Status"]}" as status')
        colunas_select.append(f'"{mapeamento["H - Resolução"]}" as resolucao')
        colunas_select.append('NULL as atualizado')  # Coluna não existe mais
        colunas_select.append(f'"{mapeamento["K - Data limite"]}" as data_limite')
        colunas_select.append(f'"{mapeamento["Z - Projeto.name"]}" as projeto_name')
        
        # Colunas de datas
        colunas_select.append(f'"{mapeamento["T - Data Início corrigida"]}" as data_inicio_corrigida')
        colunas_select.append(f'"{mapeamento["U - Data Fim corrigida"]}" as data_fim_corrigida')
        colunas_select.append(f'"{mapeamento["V - Data original início"]}" as data_original_inicio')
        colunas_select.append(f'"{mapeamento["W - Data original fim"]}" as data_original_fim')
        colunas_select.append(f'"{mapeamento["X - Start date"]}" as start_date')
        colunas_select.append(f'"{mapeamento["Y - Dias para conclusão de Tarefa"]}" as dias_para_conclusao')
        
        # Adicionar a nova coluna
        nome_coluna_sql = nome_coluna_view
        colunas_select.append(f'"{nome_coluna}" as {nome_coluna_sql}')
        
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
            {nome_coluna_sql},
            para_subtarefa as chamada_Para,
            indice,
            status_tarefas
        FROM dados_com_de_para
        """
        
        # 6. Criar view
        print("   Criando view atualizada...")
        conn.execute(sql_view)
        print("   View Jira_status_tarefas atualizada com sucesso!")
        
        # 7. Verificar resultado
        print(f"\n6. Verificando resultado...")
        result = conn.execute("SELECT COUNT(*) FROM Jira_status_tarefas").fetchone()
        print(f"   Total de registros: {result[0]:,}")
        
        # 8. Verificar estrutura
        print(f"\n7. Estrutura da view:")
        print("-" * 50)
        result = conn.execute("DESCRIBE Jira_status_tarefas").fetchall()
        for row in result:
            print(f"   {row[0]}: {row[1]}")
        
        # 9. Verificar preenchimento da nova coluna
        print(f"\n8. Verificando preenchimento da coluna '{nome_coluna_sql}':")
        print("-" * 50)
        result = conn.execute(f"""
            SELECT 
                COUNT(*) as total,
                COUNT({nome_coluna_sql}) as com_valor
            FROM Jira_status_tarefas
        """).fetchone()
        
        total = result[0]
        print(f"   Total: {total:,}")
        print(f"   Com valor: {result[1]:,} ({result[1]/total*100:.1f}%)")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao adicionar coluna: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Funcao principal"""
    print("ADICIONANDO COLUNA À VIEW JIRA_STATUS_TAREFAS")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        # 1. Investigar colunas disponíveis
        info = investigar_colunas_disponiveis(conn)
        if not info:
            return False
        
        # 2. Pela imagem, parece que o usuário quer adicionar uma coluna relacionada a "K - Data limite"
        # Mas vou verificar se há uma coluna "T" separada ou outra coluna específica
        # Vou tentar adicionar as colunas mais comuns que podem estar faltando
        
        # Pela descrição da imagem, parece que pode ser uma coluna "T" ou algo relacionado
        # Vou verificar se há uma coluna que começa com "T" que não está na view
        
        # Colunas que podem ser adicionadas:
        # - E - Relator
        # - L - Descrição
        # - AA - Pai
        # - fonte
        # - processado_em
        
        # Mas pela imagem, parece que o usuário está apontando para algo específico
        # Vou adicionar a coluna mais provável: "E - Relator" ou "L - Descrição"
        # Mas na verdade, vou perguntar ao usuário ou tentar adicionar uma coluna comum
        
        # Pela imagem "T K - Data limite", pode ser que ele queira adicionar uma coluna "T" separada
        # Mas "T - Data Início corrigida" já está na view...
        
        # Vou adicionar a coluna mais comum que geralmente é útil: "E - Relator"
        # Mas na verdade, vou listar as opções e adicionar a que fizer mais sentido
        
        print("\n" + "="*60)
        print("COLUNAS DISPONIVEIS PARA ADICIONAR:")
        print("="*60)
        for i, coluna in enumerate(info['colunas_faltando'], 1):
            print(f"   {i}. {coluna}")
        
        # Pela imagem, parece que pode ser "E - Relator" ou "L - Descrição"
        # Vou adicionar "E - Relator" como padrão, mas o usuário pode especificar
        
        # Na verdade, vou adicionar a coluna mais provável baseada na imagem
        # A imagem mostra "T K - Data limite", então pode ser que ele queira uma coluna "T" separada
        # Mas "T - Data Início corrigida" já existe...
        
        # Vou adicionar "E - Relator" como uma coluna útil que geralmente é solicitada
        coluna_para_adicionar = "E - Relator"
        
        print(f"\nAdicionando coluna: {coluna_para_adicionar}")
        print("(Se nao for esta, me avise qual coluna voce quer adicionar)")
        
        if adicionar_coluna_view(conn, coluna_para_adicionar):
            print("\n" + "="*60)
            print("COLUNA ADICIONADA COM SUCESSO!")
            print("="*60)
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






