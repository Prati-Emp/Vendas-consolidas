#!/usr/bin/env python3
"""
Script para investigar e corrigir a view Jira_status_tarefas
que quebrou devido a mudanças na tabela base
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

def investigar_tabela_base(conn):
    """Investiga a estrutura atual da tabela jira_issues"""
    print("\n" + "="*60)
    print("INVESTIGANDO TABELA BASE: reservas.jira_issues")
    print("="*60)
    
    try:
        # 1. Verificar se a tabela existe
        print("1. Verificando existencia da tabela...")
        try:
            result = conn.execute("DESCRIBE reservas.jira_issues").fetchall()
            print("   Tabela encontrada!")
        except Exception as e:
            print(f"   ERRO: {e}")
            return None
        
        # 2. Listar todas as colunas
        print("\n2. Estrutura da tabela reservas.jira_issues:")
        print("-" * 50)
        colunas_existentes = {}
        for row in result:
            nome_coluna = row[0]
            tipo_coluna = row[1]
            colunas_existentes[nome_coluna] = tipo_coluna
            print(f"   {nome_coluna}: {tipo_coluna}")
        
        # 3. Verificar quantidade de registros
        print(f"\n3. Quantidade de registros:")
        print("-" * 50)
        result = conn.execute("SELECT COUNT(*) FROM reservas.jira_issues").fetchone()
        print(f"   Total: {result[0]:,} registros")
        
        # 4. Verificar algumas colunas específicas que usamos na view
        print(f"\n4. Verificando colunas especificas usadas na view:")
        print("-" * 50)
        colunas_esperadas = [
            'A - Tipo de item',
            'B - Chave',
            'C - Resumo',
            'D - Responsável',
            'F - Prioridade',
            'G - Status',
            'H - Resolução',
            'J - Atualizado(a)',
            'K - Data limite',
            'Z - Projeto.name',
            'T - Data Início corrigida',
            'U - Data Fim corrigida',
            'V - Data original início',
            'W - Data original fim',
            'X - Start date',
            'Y - Dias para conclusão de Tarefa'
        ]
        
        colunas_encontradas = {}
        colunas_faltando = []
        
        for coluna in colunas_esperadas:
            if coluna in colunas_existentes:
                colunas_encontradas[coluna] = colunas_existentes[coluna]
                print(f"   [OK] {coluna}: EXISTE ({colunas_existentes[coluna]})")
            else:
                colunas_faltando.append(coluna)
                print(f"   [FALTA] {coluna}: NAO EXISTE")
        
        # 5. Listar todas as colunas disponíveis para ajudar a identificar correspondências
        print(f"\n5. Todas as colunas disponiveis na tabela:")
        print("-" * 50)
        todas_colunas = list(colunas_existentes.keys())
        for i, col in enumerate(todas_colunas, 1):
            print(f"   {i:2d}. {col}")
        
        return {
            'colunas_existentes': colunas_existentes,
            'colunas_encontradas': colunas_encontradas,
            'colunas_faltando': colunas_faltando,
            'todas_colunas': todas_colunas
        }
        
    except Exception as e:
        print(f"ERRO ao investigar tabela: {e}")
        import traceback
        traceback.print_exc()
        return None

def verificar_view_atual(conn):
    """Tenta verificar a view atual para ver qual erro está ocorrendo"""
    print("\n" + "="*60)
    print("VERIFICANDO VIEW ATUAL: informacoes_consolidadas.Jira_status_tarefas")
    print("="*60)
    
    try:
        # Tentar usar o banco correto
        conn.execute("USE informacoes_consolidadas")
        
        # Tentar descrever a view
        print("1. Tentando descrever a view...")
        try:
            result = conn.execute("DESCRIBE Jira_status_tarefas").fetchall()
            print("   View existe e pode ser descrita!")
            print("\n   Estrutura atual da view:")
            print("-" * 50)
            for row in result:
                print(f"   {row[0]}: {row[1]}")
            return True
        except Exception as e:
            print(f"   ERRO ao descrever view: {e}")
            
        # Tentar consultar a view
        print("\n2. Tentando consultar a view...")
        try:
            result = conn.execute("SELECT COUNT(*) FROM Jira_status_tarefas").fetchone()
            print(f"   View funciona! Total de registros: {result[0]:,}")
            return True
        except Exception as e:
            print(f"   ERRO ao consultar view: {e}")
            return False
            
    except Exception as e:
        print(f"ERRO ao verificar view: {e}")
        import traceback
        traceback.print_exc()
        return False

def corrigir_view(conn, info_tabela):
    """Corrige a view usando apenas as colunas que existem"""
    print("\n" + "="*60)
    print("CORRIGINDO VIEW JIRA_STATUS_TAREFAS")
    print("="*60)
    
    try:
        # Usar o banco correto
        print("1. Usando banco informacoes_consolidadas...")
        conn.execute("USE informacoes_consolidadas")
        print("   Banco informacoes_consolidadas selecionado!")
        
        # Remover view existente
        print("\n2. Removendo view existente...")
        try:
            conn.execute("DROP VIEW IF EXISTS Jira_status_tarefas")
            print("   View existente removida!")
        except Exception as e:
            print(f"   Aviso ao remover view: {e}")
        
        # Mapear colunas existentes
        colunas_existentes = info_tabela['colunas_existentes']
        todas_colunas = info_tabela['todas_colunas']
        
        # Criar mapeamento de colunas
        mapeamento = {}
        
        # Mapeamento direto baseado na estrutura real da tabela
        # Primeiro tentar correspondência exata
        mapeamento_direto = {
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
            'X - Start date': 'X - Start date',
            'Y - Dias para conclusão de Tarefa': 'Y - Dias para conclusão de Tarefa',
            # Mapeamentos especiais baseados na estrutura real
            'V - Data original início': 'J - Data original início',  # Coluna J na tabela
            'W - Data original fim': 'I - Data original fim',  # Coluna I na tabela
        }
        
        # Tentar encontrar correspondências para as colunas esperadas
        colunas_esperadas_map = {
            'A - Tipo de item': ['A - Tipo de item', 'A', 'Tipo de item', 'Tipo'],
            'B - Chave': ['B - Chave', 'B', 'Chave', 'Key'],
            'C - Resumo': ['C - Resumo', 'C', 'Resumo', 'Summary'],
            'D - Responsável': ['D - Responsável', 'D', 'Responsável', 'Responsavel', 'Assignee'],
            'F - Prioridade': ['F - Prioridade', 'F', 'Prioridade', 'Priority'],
            'G - Status': ['G - Status', 'G', 'Status'],
            'H - Resolução': ['H - Resolução', 'H', 'Resolução', 'Resolucao', 'Resolution'],
            'J - Atualizado(a)': ['J - Atualizado(a)', 'J', 'Atualizado(a)', 'Atualizado', 'Updated'],
            'K - Data limite': ['K - Data limite', 'K', 'Data limite', 'Due Date', 'Due'],
            'Z - Projeto.name': ['Z - Projeto.name', 'Z', 'Projeto.name', 'Projeto', 'Project'],
            'T - Data Início corrigida': ['T - Data Início corrigida', 'T', 'Data Início corrigida', 'Data Inicio corrigida'],
            'U - Data Fim corrigida': ['U - Data Fim corrigida', 'U', 'Data Fim corrigida'],
            'V - Data original início': ['V - Data original início', 'V', 'Data original início', 'Data original inicio', 'J - Data original início'],
            'W - Data original fim': ['W - Data original fim', 'W', 'Data original fim', 'I - Data original fim'],
            'X - Start date': ['X - Start date', 'X', 'Start date', 'Start'],
            'Y - Dias para conclusão de Tarefa': ['Y - Dias para conclusão de Tarefa', 'Y', 'Dias para conclusão de Tarefa', 'Dias para conclusao']
        }
        
        print("\n3. Mapeando colunas...")
        print("-" * 50)
        
        for coluna_esperada, variantes in colunas_esperadas_map.items():
            encontrada = None
            
            # Primeiro verificar mapeamento direto
            if coluna_esperada in mapeamento_direto:
                coluna_mapeada = mapeamento_direto[coluna_esperada]
                if coluna_mapeada in todas_colunas:
                    encontrada = coluna_mapeada
                    mapeamento[coluna_esperada] = encontrada
                    print(f"   [OK] {coluna_esperada} -> {encontrada} (mapeamento direto)")
                    continue
            
            # Se não encontrou no mapeamento direto, tentar busca
            for variante in variantes:
                # Buscar correspondência exata
                for col_existente in todas_colunas:
                    if col_existente == variante:
                        encontrada = col_existente
                        break
                if encontrada:
                    break
            
            if encontrada:
                mapeamento[coluna_esperada] = encontrada
                print(f"   [OK] {coluna_esperada} -> {encontrada}")
            else:
                print(f"   [FALTA] {coluna_esperada} -> NAO ENCONTRADA")
        
        # Verificar se temos as colunas mínimas necessárias
        # J - Atualizado(a) não existe mais, então vamos usar NULL
        colunas_minimas = ['B - Chave', 'G - Status']
        tem_minimas = all(col in mapeamento for col in colunas_minimas)
        
        if not tem_minimas:
            print("\n   ERRO: Nao foram encontradas as colunas minimas necessarias!")
            print("   Colunas minimas necessarias:")
            for col in colunas_minimas:
                if col not in mapeamento:
                    print(f"     - {col} (FALTANDO)")
            return False
        
        # Construir SQL da view
        print("\n4. Construindo SQL da view...")
        print("-" * 50)
        
        # Colunas principais
        colunas_select = []
        
        # Adicionar colunas mapeadas
        if 'A - Tipo de item' in mapeamento:
            colunas_select.append(f'"{mapeamento["A - Tipo de item"]}" as tipo_item')
        else:
            colunas_select.append('NULL as tipo_item')
        
        if 'B - Chave' in mapeamento:
            colunas_select.append(f'"{mapeamento["B - Chave"]}" as chave')
        else:
            colunas_select.append('NULL as chave')
        
        if 'C - Resumo' in mapeamento:
            colunas_select.append(f'"{mapeamento["C - Resumo"]}" as resumo')
        else:
            colunas_select.append('NULL as resumo')
        
        if 'D - Responsável' in mapeamento:
            colunas_select.append(f'"{mapeamento["D - Responsável"]}" as responsavel')
        else:
            colunas_select.append('NULL as responsavel')
        
        if 'F - Prioridade' in mapeamento:
            colunas_select.append(f'"{mapeamento["F - Prioridade"]}" as prioridade')
        else:
            colunas_select.append('NULL as prioridade')
        
        if 'G - Status' in mapeamento:
            colunas_select.append(f'"{mapeamento["G - Status"]}" as status')
        else:
            colunas_select.append('NULL as status')
        
        if 'H - Resolução' in mapeamento:
            colunas_select.append(f'"{mapeamento["H - Resolução"]}" as resolucao')
        else:
            colunas_select.append('NULL as resolucao')
        
        if 'J - Atualizado(a)' in mapeamento:
            colunas_select.append(f'"{mapeamento["J - Atualizado(a)"]}" as atualizado')
        else:
            colunas_select.append('NULL as atualizado')
        
        if 'K - Data limite' in mapeamento:
            colunas_select.append(f'"{mapeamento["K - Data limite"]}" as data_limite')
        else:
            colunas_select.append('NULL as data_limite')
        
        if 'Z - Projeto.name' in mapeamento:
            colunas_select.append(f'"{mapeamento["Z - Projeto.name"]}" as projeto_name')
        else:
            colunas_select.append('NULL as projeto_name')
        
        # Colunas de datas
        if 'T - Data Início corrigida' in mapeamento:
            colunas_select.append(f'"{mapeamento["T - Data Início corrigida"]}" as data_inicio_corrigida')
        else:
            colunas_select.append('NULL as data_inicio_corrigida')
        
        if 'U - Data Fim corrigida' in mapeamento:
            colunas_select.append(f'"{mapeamento["U - Data Fim corrigida"]}" as data_fim_corrigida')
        else:
            colunas_select.append('NULL as data_fim_corrigida')
        
        if 'V - Data original início' in mapeamento:
            colunas_select.append(f'"{mapeamento["V - Data original início"]}" as data_original_inicio')
        else:
            colunas_select.append('NULL as data_original_inicio')
        
        if 'W - Data original fim' in mapeamento:
            colunas_select.append(f'"{mapeamento["W - Data original fim"]}" as data_original_fim')
        else:
            colunas_select.append('NULL as data_original_fim')
        
        if 'X - Start date' in mapeamento:
            colunas_select.append(f'"{mapeamento["X - Start date"]}" as start_date')
        else:
            colunas_select.append('NULL as start_date')
        
        if 'Y - Dias para conclusão de Tarefa' in mapeamento:
            colunas_select.append(f'"{mapeamento["Y - Dias para conclusão de Tarefa"]}" as dias_para_conclusao')
        else:
            colunas_select.append('NULL as dias_para_conclusao')
        
        # Construir CASE para status_tarefas
        coluna_status = mapeamento.get('G - Status', 'NULL')
        coluna_data_limite = mapeamento.get('K - Data limite', 'NULL')
        
        # Construir expressão para data_limite
        if coluna_data_limite != 'NULL':
            # Tentar diferentes formatos de data
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
        else:
            expr_data_limite = 'NULL'
        
        # Construir CASE para status_tarefas
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
        
        # Adicionar ROW_NUMBER para remover duplicatas
        coluna_chave = mapeamento.get('B - Chave', 'NULL')
        
        # Verificar se existe coluna processado_em para ordenação
        tem_processado_em = 'processado_em' in todas_colunas
        
        # Construir ORDER BY para ROW_NUMBER
        if tem_processado_em:
            order_by = 'processado_em DESC NULLS LAST'
        else:
            # Se não tem processado_em, usar apenas a chave (manter primeiro registro)
            order_by = '1'
        
        # Construir SQL completo
        sql_view = f"""
        CREATE VIEW Jira_status_tarefas AS
        WITH dados_base AS (
            SELECT
                {', '.join(colunas_select)},
                ROW_NUMBER() OVER (
                    PARTITION BY "{coluna_chave}" 
                    ORDER BY {order_by}
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
            para_subtarefa as chamada_Para,
            indice,
            status_tarefas
        FROM dados_com_de_para
        """
        
        print("   SQL construido com sucesso!")
        
        # 5. Criar view
        print("\n5. Criando view atualizada...")
        try:
            conn.execute(sql_view)
            print("   View Jira_status_tarefas criada com sucesso!")
        except Exception as e:
            print(f"   ERRO ao criar view: {e}")
            print("\n   SQL que causou erro:")
            print("-" * 50)
            print(sql_view)
            return False
        
        # 6. Verificar resultado
        print(f"\n6. Verificando resultado...")
        try:
            result = conn.execute("SELECT COUNT(*) FROM Jira_status_tarefas").fetchone()
            print(f"   Total de registros: {result[0]:,}")
            
            # Verificar estrutura
            print(f"\n7. Estrutura da view:")
            print("-" * 50)
            result = conn.execute("DESCRIBE Jira_status_tarefas").fetchall()
            for row in result:
                print(f"   {row[0]}: {row[1]}")
            
            # Verificar algumas colunas importantes
            print(f"\n8. Verificando preenchimento das colunas:")
            print("-" * 50)
            result = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(chave) as com_chave,
                    COUNT(status) as com_status,
                    COUNT(chamada_Para) as com_chamada_para,
                    COUNT(indice) as com_indice
                FROM Jira_status_tarefas
            """).fetchone()
            
            total = result[0]
            print(f"   Total: {total:,}")
            print(f"   - chave: {result[1]:,} ({result[1]/total*100:.1f}%)")
            print(f"   - status: {result[2]:,} ({result[2]/total*100:.1f}%)")
            print(f"   - chamada_Para: {result[3]:,} ({result[3]/total*100:.1f}%)")
            print(f"   - indice: {result[4]:,} ({result[4]/total*100:.1f}%)")
            
            return True
            
        except Exception as e:
            print(f"   ERRO ao verificar view: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    except Exception as e:
        print(f"ERRO ao corrigir view: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Funcao principal"""
    print("CORRIGINDO VIEW JIRA_STATUS_TAREFAS")
    print("="*60)
    print("Investigando tabela base e corrigindo view quebrada")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        # 1. Investigar tabela base
        info_tabela = investigar_tabela_base(conn)
        if not info_tabela:
            print("\nERRO: Nao foi possivel investigar a tabela base!")
            return False
        
        # 2. Verificar view atual (se possível)
        verificar_view_atual(conn)
        
        # 3. Corrigir view
        if not corrigir_view(conn, info_tabela):
            return False
        
        print("\n" + "="*60)
        print("VIEW CORRIGIDA COM SUCESSO!")
        print("="*60)
        
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
