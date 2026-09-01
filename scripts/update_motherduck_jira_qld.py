#!/usr/bin/env python3
"""
Atualização do Jira QLD (NC - Não Conformidade) no MotherDuck
- Tabela reservas.Jira_projeto_qld
- View administracao.Jira_projeto_qld_consolidado
"""

import os
import sys
from datetime import datetime

from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from scripts.concurrency_control import check_concurrency, release_concurrency

SQL_VIEW_CONSOLIDADO = """
CREATE OR REPLACE VIEW Jira_projeto_qld_consolidado AS
SELECT
    Chave,
    Resumo,
    "Tipo de item" AS Tipo_de_item,
    Status,
    "Categoria do status" AS Categoria_do_status,
    Prioridade,
    "Responsável" AS Responsavel,
    Relator,
    Criador,
    Projeto,
    Pai,
    Etiquetas,
    Subtarefas,
    "Nível de Segurança" AS Nivel_de_Seguranca,
    "Descrição" AS Descricao,
    "Resolução" AS Resolucao,
    TRY_CAST("Resolvido" AS TIMESTAMP) AS Resolvido,
    TRY_CAST("Data limite" AS DATE) AS Data_limite,
    TRY_CAST("Data de início" AS DATE) AS Data_de_inicio,
    TRY_CAST("Data de Finalização" AS DATE) AS Data_de_Finalizacao,
    TRY_CAST("Criado em" AS TIMESTAMP) AS Criado_em,
    TRY_CAST("Atualizado em" AS TIMESTAMP) AS Atualizado_em,
    TRY_CAST("[CHART] Date of First Response" AS TIMESTAMP) AS Date_of_First_Response,
    "[CHART] Time in Status" AS Time_in_Status,
    "Área" AS Area,
    "Área Envolvida" AS Area_Envolvida,
    "Nível de Impacto" AS Nivel_de_Impacto,
    "Pessoa movimenta Pausa" AS Pessoa_movimenta_Pausa,
    "NC - Origem da NC" AS NC_Origem_da_NC,
    "NC - Origem" AS NC_Origem,
    "NC - Atividade" AS NC_Atividade,
    "NC - Disposição" AS NC_Disposicao,
    "NC - Processo" AS NC_Processo,
    "NC - Ações de Correção" AS NC_Acoes_de_Correcao,
    "NC - Necessidade de eliminar a Causa Raiz" AS NC_Necessidade_eliminar_Causa_Raiz,
    "NC - Análise Critica" AS NC_Analise_Critica,
    "NC - Causa Raiz" AS NC_Causa_Raiz,
    "NC - Eliminação da Causa Raiz" AS NC_Eliminacao_da_Causa_Raiz,
    "NC - Não Conformidade Similares" AS NC_Nao_Conformidade_Similares,
    "NC - Concessões Obtidas" AS NC_Concessoes_Obtidas,
    "NC - Eficácia das ações" AS NC_Eficacia_das_acoes,
    fonte,
    processado_em
FROM reservas.Jira_projeto_qld
"""


def sistema_jira_qld():
    print("SISTEMA DE ATUALIZACAO JIRA QLD (NC - Nao Conformidade)")
    print("=" * 60)
    print(f"Timestamp: {datetime.now()}")
    print("API: Jira Issues - Projeto QLD")

    start_time = datetime.now()

    try:
        from scripts.cv_jira_qld_api import obter_dados_jira_qld
        import duckdb

        print("\n1. Coletando dados do projeto QLD do Jira...")
        df_jira_qld = obter_dados_jira_qld()
        if df_jira_qld.empty:
            print("AVISO: Nenhum dado coletado do Jira QLD")
            return False
        print(f"OK: Jira QLD: {len(df_jira_qld)} registros, {len(df_jira_qld.columns)} colunas")

        print("\n2. Fazendo upload para MotherDuck (reservas.Jira_projeto_qld)...")
        duckdb.sql("INSTALL motherduck")
        duckdb.sql("LOAD motherduck")
        token = os.environ.get("MOTHERDUCK_TOKEN", "").strip()
        if not token:
            print("ERRO: MOTHERDUCK_TOKEN nao encontrado")
            return False
        duckdb.sql(f"SET motherduck_token='{token}'")
        conn = duckdb.connect("md:reservas")
        conn.register("df_jira_qld", df_jira_qld)
        conn.execute(
            "CREATE OR REPLACE TABLE Jira_projeto_qld AS SELECT * FROM df_jira_qld"
        )
        count_jira_qld = conn.sql("SELECT COUNT(*) FROM Jira_projeto_qld").fetchone()[0]
        print(f"OK: Jira QLD upload: {count_jira_qld:,} registros")

        print("\n3. Verificando tabela criada...")
        try:
            colunas = conn.sql("DESCRIBE Jira_projeto_qld").fetchall()
            print(f"Colunas da tabela ({len(colunas)}):")
            for coluna in colunas:
                print(f"   - {coluna[0]} ({coluna[1]})")
            col_key = "Chave" if "Chave" in df_jira_qld.columns else "key"
            stats = conn.sql(
                f"""
                SELECT
                    COUNT(*) as total_registros,
                    COUNT(DISTINCT "{col_key}") as issues_unicas
                FROM Jira_projeto_qld
                """
            ).fetchone()
            print("\nEstatisticas da tabela:")
            print(f"   - Total de registros: {stats[0]:,}")
            print(f"   - Issues unicas: {stats[1]:,}")
        except Exception as e:
            print(f"AVISO: Erro ao verificar tabela: {e}")
        conn.close()

        print("\n4. Criando/atualizando view administracao.Jira_projeto_qld_consolidado...")
        conn_adm = duckdb.connect("md:administracao")
        conn_adm.execute(SQL_VIEW_CONSOLIDADO)
        n_view = conn_adm.sql(
            "SELECT COUNT(*) FROM Jira_projeto_qld_consolidado"
        ).fetchone()[0]
        print(f"OK: View consolidado: {n_view:,} registros")
        conn_adm.close()

        duration = datetime.now() - start_time
        print("\nATUALIZACAO JIRA QLD CONCLUIDA!")
        print(f"Duracao: {duration}")
        print("Resumo:")
        print(f"   - Jira QLD Issues: {len(df_jira_qld):,} registros")
        print("   - Tabela: reservas.Jira_projeto_qld")
        print("   - View: administracao.Jira_projeto_qld_consolidado")
        return True
    except Exception as e:
        print(f"\nERRO na atualizacao Jira QLD: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def main():
    print("INICIANDO ATUALIZACAO JIRA QLD DO MOTHERDUCK")
    print("=" * 60)
    print(f"Timestamp: {datetime.now()}")
    print(f"Python: {sys.version}")
    print(f"Working directory: {os.getcwd()}")

    print("\nVerificando controle de concorrencia...")
    if not check_concurrency():
        print("ERRO: Outro workflow esta executando. Abortando para evitar conflitos.")
        sys.exit(1)
    print("OK: Controle de concorrencia OK - Prosseguindo com execucao")

    load_dotenv()
    required_vars = ["MOTHERDUCK_TOKEN", "JIRA_URL", "JIRA_EMAIL", "JIRA_TOKEN"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    if missing_vars:
        print(f"ERRO: Variaveis de ambiente faltando: {', '.join(missing_vars)}")
        release_concurrency()
        sys.exit(1)
    print("OK: Variaveis de ambiente configuradas")

    try:
        sucesso = sistema_jira_qld()
        if sucesso:
            print("\nOK: ATUALIZACAO JIRA QLD CONCLUIDA COM SUCESSO!")
            release_concurrency()
            sys.exit(0)
        print("\nERRO: FALHA NA ATUALIZACAO JIRA QLD")
        release_concurrency()
        sys.exit(1)
    except ImportError as e:
        print(f"\nERRO DE IMPORTACAO: {e}")
        release_concurrency()
        sys.exit(1)
    except Exception as e:
        print(f"\nERRO INESPERADO: {e}")
        import traceback

        traceback.print_exc()
        release_concurrency()
        sys.exit(1)


if __name__ == "__main__":
    main()
