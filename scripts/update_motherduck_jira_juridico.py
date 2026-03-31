#!/usr/bin/env python3
"""
Atualização do Jira Jurídico no MotherDuck
Executa a API do Jira para o projeto JRD e atualiza a tabela Jira_projeto_juridico
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Garante import do projeto quando rodar via Actions
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Importar controle de concorrência
from scripts.concurrency_control import check_concurrency, release_concurrency


def sistema_jira_juridico():
    """Sistema de atualização do Jira Jurídico"""
    print("SISTEMA DE ATUALIZACAO JIRA JURIDICO")
    print("=" * 60)
    print(f"Timestamp: {datetime.now()}")
    print("API: Jira Issues - Projeto Jurídico (JRD)")

    start_time = datetime.now()

    try:
        # Importar módulos necessários
        from scripts.cv_jira_juridico_api import obter_dados_jira_juridico
        import duckdb
        import pandas as pd

        # 1. Coletar dados do Jira Jurídico
        print("\n1. Coletando dados do projeto JRD do Jira...")
        df_jira_juridico = obter_dados_jira_juridico()

        if df_jira_juridico.empty:
            print("AVISO: Nenhum dado coletado do Jira Jurídico")
            return False

        print(f"OK: Jira Jurídico: {len(df_jira_juridico)} registros")

        # 2. Upload para MotherDuck
        print("\n2. Fazendo upload para MotherDuck...")

        duckdb.sql("INSTALL motherduck")
        duckdb.sql("LOAD motherduck")

        token = os.environ.get("MOTHERDUCK_TOKEN", "").strip()
        if not token:
            print("ERRO: MOTHERDUCK_TOKEN nao encontrado")
            return False

        duckdb.sql(f"SET motherduck_token='{token}'")
        conn = duckdb.connect("md:reservas")

        # Upload Jira Jurídico (substituição completa)
        print("   - Fazendo upload Jira Jurídico...")
        conn.register("df_jira_juridico", df_jira_juridico)
        conn.execute(
            "CREATE OR REPLACE TABLE Jira_projeto_juridico AS SELECT * FROM df_jira_juridico"
        )
        count_jira_juridico = conn.sql(
            "SELECT COUNT(*) FROM Jira_projeto_juridico"
        ).fetchone()[0]
        print(f"OK: Jira Jurídico upload: {count_jira_juridico:,} registros")

        # Verificar tabela criada
        print("\n3. Verificando tabela criada...")
        try:
            colunas = conn.sql("DESCRIBE Jira_projeto_juridico").fetchall()
            print(f"Colunas da tabela ({len(colunas)}):")
            for coluna in colunas[:15]:
                print(f"   - {coluna[0]} ({coluna[1]})")
            if len(colunas) > 15:
                print(f"   ... e mais {len(colunas) - 15} colunas")

            if "Chave" in df_jira_juridico.columns or "key" in df_jira_juridico.columns:
                col_key = "Chave" if "Chave" in df_jira_juridico.columns else "key"
                stats = conn.sql(
                    f"""
                    SELECT
                        COUNT(*) as total_registros,
                        COUNT(DISTINCT "{col_key}") as issues_unicas
                    FROM Jira_projeto_juridico
                    """
                ).fetchone()
                print("\nEstatisticas da tabela:")
                print(f"   - Total de registros: {stats[0]:,}")
                print(f"   - Issues unicas: {stats[1]:,}")
        except Exception as e:
            print(f"AVISO: Erro ao verificar tabela: {e}")

        conn.close()

        duration = datetime.now() - start_time
        print("\nATUALIZACAO JIRA JURIDICO CONCLUIDA!")
        print(f"Duracao: {duration}")
        print("Resumo:")
        print(f"   - Jira Jurídico Issues: {len(df_jira_juridico):,} registros")
        print("   - Tabela: Jira_projeto_juridico")
        print("   - Banco: reservas (MotherDuck)")

        return True

    except Exception as e:
        print(f"\nERRO na atualizacao Jira Jurídico: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Função principal para execução via GitHub Actions"""
    print("INICIANDO ATUALIZACAO JIRA JURIDICO DO MOTHERDUCK")
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
        sucesso = sistema_jira_juridico()
        if sucesso:
            print("\nOK: ATUALIZACAO JIRA JURIDICO CONCLUIDA COM SUCESSO!")
            release_concurrency()
            sys.exit(0)
        else:
            print("\nERRO: FALHA NA ATUALIZACAO JIRA JURIDICO")
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

