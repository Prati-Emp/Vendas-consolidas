#!/usr/bin/env python3
"""
Script para criar a view Jira_projeto_dho_consolidado
com base na tabela Jira_projeto_dho
"""

import os
import duckdb
from dotenv import load_dotenv
import json

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

def extrair_texto_json(json_str):
    """
    Extrai o texto de um JSON do tipo:
    {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "texto aqui"}]}]}
    """
    if not json_str or json_str == '' or json_str == 'NULL':
        return ''
    
    try:
        data = json.loads(json_str)
        if isinstance(data, dict) and 'content' in data:
            # Função recursiva para extrair texto
            def extract_text(obj):
                if isinstance(obj, dict):
                    if obj.get('type') == 'text' and 'text' in obj:
                        return obj['text']
                    elif 'content' in obj:
                        return ' '.join(extract_text(item) for item in obj['content'] if extract_text(item))
                elif isinstance(obj, list):
                    return ' '.join(extract_text(item) for item in obj if extract_text(item))
                return ''
            
            texto = extract_text(data)
            return texto.strip()
    except:
        pass
    
    return json_str if json_str else ''

def criar_funcao_extrair_texto(conn):
    """Cria uma função SQL para extrair texto do JSON"""
    try:
        # DuckDB não suporta funções Python diretamente, então vamos usar uma abordagem diferente
        # Vamos fazer a extração usando SQL com regex e string functions
        pass
    except:
        pass

def consolidar_cargo(colunas_cargo):
    """
    Cria uma expressão SQL para consolidar todas as colunas de cargo em uma única coluna
    Trata tanto NULL quanto strings vazias
    """
    # Lista de todas as colunas de cargo (nomes exatos da tabela)
    colunas = [
        "Cargos - DHO e RH",
        "Cargo - Comercial",
        "Cargos - Financeiro",
        "Cargo - Qualidade",
        "Cargos - Juridico",
        "Cargo - Urbanismo",
        "Cargo - Marketing",
        "Cargo - Planejamento de obra",
        "Cargo - Planejamento e Governança",
        "Cargo - Presidência",
        "Cargo - Projetos",
        "Cargo - Suprimentos",
        "Cargo - Obra",
        "MC Cargo - Obra",
        "MC Cargo - Suprimentos",
        "MC Cargo - Projetos",
        "MC Cargo - Presidência",
        "MC Cargo - Planejamento e Governança",
        "MC Cargo - Planejamento de obra",
        "MC Cargo - Marketing",
        "MC Cargo - Urbanismo",
        "MC Cargos - Juridico",
        "MC Cargo - Qualidade",
        "MC Cargos - Financeiro",
        "MC Cargo - Comercial",
        "MC Cargos - DHO e RH"
    ]
    
    # Criar CASE WHEN para pegar o primeiro valor não nulo e não vazio
    # Usar NULLIF para converter strings vazias em NULL
    partes = []
    for col in colunas:
        partes.append(f'NULLIF(TRIM("{col}"), \'\')')
    
    return f"COALESCE({', '.join(partes)})"


def consolidar_supervisao(desc_colunas):
    """
    Consolida em uma única coluna os valores das colunas relacionadas a Supervisão.
    Usa detecção dinâmica porque os nomes podem variar/vir com encoding quebrado.
    """
    colunas_supervisao = []
    for row in desc_colunas:
        col_name = row[0]
        if col_name and "supervis" in str(col_name).lower():
            colunas_supervisao.append(col_name)

    if not colunas_supervisao:
        return "NULL"

    partes = [f'NULLIF(TRIM("{col}"), \'\')' for col in colunas_supervisao]
    return f"COALESCE({', '.join(partes)})"


def expr_data_para_date_sql(col_sql: str) -> str:
    """
    Converte coluna bruta da planilha/Jira para DATE na view.

    Texto ``YYYY-MM-DD`` (10 caracteres com hífens): a origem mistura **ISO Y-M-D**
    (2025-12-30) e **ano-dia-mês** (2025-30-12 = 30/12/2025). Sem isso, MAKE_DATE
    único gera erro "Date out of range" (ex.: mês 30).

    Usa-se ``COALESCE(TRY(Y-M-D), TRY(Y-D-M))``: o primeiro que for válido vence.

    Outros formatos: STRPTIME + TRY_CAST final.
    col_sql: identificador entre aspas, ex: \"Data de aprovação\"
    """
    t = f"TRIM(CAST({col_sql} AS VARCHAR))"
    hyphen = (
        f"(len({t}) = 10 AND substr({t}, 5, 1) = '-' AND substr({t}, 8, 1) = '-')"
    )
    y_m_d = (
        f"MAKE_DATE(CAST(SUBSTR({t}, 1, 4) AS INTEGER), "
        f"CAST(SUBSTR({t}, 6, 2) AS INTEGER), CAST(SUBSTR({t}, 9, 2) AS INTEGER))"
    )
    y_d_m = (
        f"MAKE_DATE(CAST(SUBSTR({t}, 1, 4) AS INTEGER), "
        f"CAST(SUBSTR({t}, 9, 2) AS INTEGER), CAST(SUBSTR({t}, 6, 2) AS INTEGER))"
    )
    return (
        "CASE "
        f"WHEN {t} IS NULL OR {t} = '' THEN CAST(NULL AS DATE) "
        f"WHEN {hyphen} THEN COALESCE(TRY({y_m_d}), TRY({y_d_m})) "
        "ELSE COALESCE("
        f"TRY_CAST(STRPTIME({t}, '%d/%m/%Y') AS DATE), "
        f"TRY_CAST(STRPTIME({t}, '%d-%m-%Y') AS DATE), "
        f"TRY_CAST(STRPTIME({t}, '%Y/%m/%d') AS DATE), "
        f"TRY_CAST(STRPTIME({t}, '%Y/%d/%m') AS DATE), "
        f"TRY_CAST({t} AS DATE)) "
        "END"
    )


def criar_view(conn):
    """Cria a view consolidada"""
    print("\n" + "="*60)
    print("CRIANDO VIEW Jira_projeto_dho_consolidado")
    print("="*60)
    
    try:
        # Verificar se a view já existe
        print("\n1. Verificando se a view ja existe...")
        try:
            result = conn.execute("""
                SELECT COUNT(*) 
                FROM administracao.Jira_projeto_dho_consolidado
            """).fetchone()
            print("   View ja existe. Será substituída.")
        except:
            print("   View nao existe. Será criada.")
        
        # Criar a view com todos os tratamentos
        print("\n2. Criando view com tratamentos...")
        
        # Detectar coluna "Responsável" na origem (o nome vem com caractere quebrado)
        responsavel_col = None
        desc = conn.execute("DESCRIBE reservas.Jira_projeto_dho").fetchall()
        for row in desc:
            col_name = row[0]
            if col_name and "respons" in str(col_name).lower():
                responsavel_col = col_name
                break
        if not responsavel_col:
            raise ValueError("Nao foi encontrada coluna contendo 'Respons' em reservas.Jira_projeto_dho")
        responsavel_ref = f"\"{responsavel_col}\""

        # Detectar coluna "Data de finalização" na origem (nome pode vir com encoding quebrado)
        finalizacao_col = None
        for row in desc:
            col_name = row[0]
            if col_name and "finaliz" in str(col_name).lower():
                finalizacao_col = col_name
                break
        if not finalizacao_col:
            raise ValueError("Nao foi encontrada coluna contendo 'finaliz' em reservas.Jira_projeto_dho")
        finalizacao_ref = f"\"{finalizacao_col}\""

        # Expressão para extrair texto do JSON da Justificativa da Vaga
        justificativa_extract = """
        CASE 
            WHEN "Justificativa da Vaga" IS NULL OR "Justificativa da Vaga" = '' THEN NULL
            WHEN "Justificativa da Vaga" LIKE '%"text":%' THEN
                REGEXP_EXTRACT("Justificativa da Vaga", '"text":\\s*"([^"]+)"', 1)
            ELSE "Justificativa da Vaga"
        END
        """
        
        # Consolidar colunas de Cargo - todas as colunas de cargo por setor
        cargo_consolidado = consolidar_cargo([])
        # Consolidar colunas de Supervisão em uma única coluna
        supervisao_consolidada = consolidar_supervisao(desc)

        d_start = expr_data_para_date_sql('"Start date"')
        d_pretendida = expr_data_para_date_sql('"Data pretendida"')
        d_proposta = expr_data_para_date_sql('"Data Proposta"')
        d_aprov = expr_data_para_date_sql('"Data de aprovação"')
        d_fech = expr_data_para_date_sql('"Data de fechamento"')
        d_fin = expr_data_para_date_sql(finalizacao_ref)
        d_inicio = expr_data_para_date_sql('"Data de inicio"')
        
        # SQL da view - seguindo a ordem especificada pelo usuário
        sql_view = f"""
        CREATE OR REPLACE VIEW administracao.Jira_projeto_dho_consolidado AS
        SELECT
            "Chave" as Chave,
            {d_start} as "Start_date",
            "Aprovador" as Aprovador,
            -- Responsável: coluna da origem pode vir com encoding quebrado.
            {responsavel_ref} as Responsavel,
            {responsavel_ref} as "Responsável",
            {justificativa_extract} as "Justificativa_da_Vaga",
            "Área" as Área,
            "Aprovador presidência" as "Aprovador_presidência",
            "Empreendimento Destino" as "Empreendimento_Destino",
            "Motivo da Requisição" as "Motivo_da_Requisição",
            "Escolaridade" as Escolaridade,
            "Salário proposto" as "Salário_proposto",
            {d_pretendida} as "Data_pretendida",
            "Colaborador" as "Nome_do_colaborador",
            "Touch" as Touch,
            "Outros pagamentos" as "Outros_pagamentos",
            "Cargo" as "Cargo_Atual",
            "Cargo Novo" as "Cargo_Novo",
            "Setor Novo" as "Setor_Atual",
            "Setor Novo" as "Setor_Novo",
            "Salário proposto" as "Salário_Atual",
            "Salário Novo" as "Salário_Novo",
            {d_proposta} as "Data_Proposta",
            "Gestor imediato" as "Gestor_imediato",
            {d_aprov} as "Data_de_aprovação",
            {d_fech} as "Data_de_fechamento",
            {d_fin} as "Data_de_finalizacao",
            {d_inicio} as "Data_de_inicio",
            "Horário de trabalho" as "Horário_de_trabalho",
            "Status" as Status,
            "Resumo" as Resumo,
            "Tipo de item" as "Tipo_de_item",
            "Horário de trabalho Pretendido" as "Horário_de_trabalho_Pretendido",
            "Recontratação" as Recontratação,
            "Motivo do Cancelamento" as "Motivo_do_Cancelamento",
            {cargo_consolidado} as Cargo,
            {supervisao_consolidada} as "Supervisão",
            "Prioridade" as Prioridade,
            "Atualizado em" as "Atualizado_em"
        FROM reservas.Jira_projeto_dho
        """
        
        conn.execute(sql_view)
        print("   View criada com sucesso!")
        
        # Verificar resultado
        print("\n3. Verificando view criada...")
        result = conn.execute("""
            SELECT COUNT(*) 
            FROM administracao.Jira_projeto_dho_consolidado
        """).fetchone()
        print(f"   Total de registros: {result[0]:,}")
        
        # Mostrar estrutura
        print("\n4. Estrutura da view:")
        print("-" * 50)
        result = conn.execute("DESCRIBE administracao.Jira_projeto_dho_consolidado").fetchall()
        for i, row in enumerate(result, 1):
            print(f"   {i:2d}. {row[0]:<40} : {row[1]}")
        
        # Mostrar amostra
        print("\n5. Amostra de dados (primeira linha):")
        print("-" * 50)
        result = conn.execute("""
            SELECT 
                Chave,
                Start_date,
                Justificativa_da_Vaga,
                Cargo,
                Status
            FROM administracao.Jira_projeto_dho_consolidado
            LIMIT 1
        """).fetchone()
        
        if result:
            print(f"   Chave: {result[0]}")
            print(f"   Start_date: {result[1]}")
            print(f"   Justificativa_da_Vaga: {result[2][:80] if result[2] else 'NULL'}")
            print(f"   Cargo: {result[3]}")
            print(f"   Status: {result[4]}")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao criar view: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Funcao principal"""
    print("CRIANDO VIEW Jira_projeto_dho_consolidado")
    print("="*60)
    print("Base: reservas.Jira_projeto_dho")
    print("Destino: administracao.Jira_projeto_dho_consolidado")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        if not criar_view(conn):
            return False
        
        print("\n" + "="*60)
        print("VIEW CRIADA COM SUCESSO!")
        print("="*60)
        print("View: administracao.Jira_projeto_dho_consolidado")
        print("\nTratamentos aplicados:")
        print("  - Justificativa da Vaga: Extração de texto do JSON")
        print("  - Cargo: Consolidação de todas as colunas de cargo em uma única coluna")
        print("  - Colunas renomeadas para facilitar uso")
        
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
