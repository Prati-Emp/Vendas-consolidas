#!/usr/bin/env python3
"""
Atualizacao Diaria do CV Assistencias Workflow Tempo no MotherDuck
Executa a API e atualiza a tabela reservas.cv_assistencias_workflow_tempo
"""

import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from scripts.concurrency_control import check_concurrency, release_concurrency


async def sistema_assistencias_workflow_tempo():
    """Sistema de atualizacao diaria de assistencias workflow tempo do CV CRM"""
    print("SISTEMA DE ATUALIZACAO DIARIA - CV ASSISTENCIAS WORKFLOW TEMPO")
    print("=" * 60)
    print(f"Timestamp: {datetime.now()}")
    print("API: CV CRM Assistencias Workflow Tempo")

    start_time = datetime.now()

    try:
        from scripts.cv_assistencias_workflow_tempo_api import (
            obter_dados_cv_assistencias_workflow_tempo,
        )
        import duckdb

        print("\n1. Coletando dados de assistencias workflow tempo do CV CRM...")
        df = obter_dados_cv_assistencias_workflow_tempo()

        if df.empty:
            print("AVISO: Nenhum dado coletado de assistencias workflow tempo")
            return False

        print(f"OK: Assistencias Workflow Tempo: {len(df)} registros")

        print("\n2. Fazendo upload para MotherDuck (banco reservas)...")

        duckdb.sql("INSTALL motherduck")
        duckdb.sql("LOAD motherduck")

        token = os.environ.get("MOTHERDUCK_TOKEN", "").strip()
        if not token:
            print("ERRO: MOTHERDUCK_TOKEN nao encontrado")
            return False

        duckdb.sql(f"SET motherduck_token='{token}'")
        conn = duckdb.connect("md:reservas")

        print("   - Fazendo upload completo cv_assistencias_workflow_tempo...")
        conn.register("df_assist_wf", df)
        conn.execute(
            "CREATE OR REPLACE TABLE cv_assistencias_workflow_tempo AS SELECT * FROM df_assist_wf"
        )

        count = conn.sql(
            "SELECT COUNT(*) FROM cv_assistencias_workflow_tempo"
        ).fetchone()[0]
        print(f"OK: cv_assistencias_workflow_tempo upload: {count:,} registros")

        print("\n3. Verificando tabela criada...")
        try:
            colunas = conn.sql("DESCRIBE cv_assistencias_workflow_tempo").fetchall()
            print(f"Colunas da tabela ({len(colunas)}):")
            for coluna in colunas:
                print(f"   - {coluna[0]} ({coluna[1]})")

            stats = conn.sql("""
                SELECT
                    COUNT(*) as total,
                    COUNT(DISTINCT idassistencia) as assistencias,
                    SUM(CASE WHEN finalizada THEN 1 ELSE 0 END) as finalizadas,
                    SUM(CASE WHEN cancelada THEN 1 ELSE 0 END) as canceladas
                FROM cv_assistencias_workflow_tempo
            """).fetchone()
            print("\nEstatisticas:")
            print(f"   - Total de registros: {stats[0]:,}")
            print(f"   - Assistencias distintas: {stats[1]:,}")
            print(f"   - Linhas com finalizada: {stats[2]:,}")
            print(f"   - Linhas com cancelada: {stats[3]:,}")
        except Exception as e:
            print(f"AVISO: Erro ao verificar tabela: {e}")

        conn.close()

        duration = datetime.now() - start_time
        print("\nATUALIZACAO CV ASSISTENCIAS WORKFLOW TEMPO CONCLUIDA!")
        print(f"Duracao: {duration}")
        print(f"   - Registros: {len(df):,}")
        print("   - Tabela: cv_assistencias_workflow_tempo")
        print("   - Banco: reservas (MotherDuck)")
        return True

    except Exception as e:
        print(f"\nERRO na atualizacao de assistencias workflow tempo: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def main():
    print("INICIANDO ATUALIZACAO DIARIA CV ASSISTENCIAS WORKFLOW TEMPO DO MOTHERDUCK")
    print("=" * 60)
    print(f"Timestamp: {datetime.now()}")
    print(f"Python: {sys.version}")
    print(f"Working directory: {os.getcwd()}")

    print("\nVerificando controle de concorrencia...")
    if not check_concurrency():
        print("ERRO: Outro workflow esta executando. Abortando.")
        sys.exit(1)
    print("OK: Controle de concorrencia OK")

    load_dotenv()
    required_vars = ["MOTHERDUCK_TOKEN", "CVCRM_EMAIL", "CVCRM_TOKEN"]
    missing_vars = [v for v in required_vars if not os.environ.get(v)]
    if missing_vars:
        print(f"ERRO: Variaveis faltando: {', '.join(missing_vars)}")
        release_concurrency()
        sys.exit(1)

    print("OK: Variaveis de ambiente configuradas")

    try:
        sucesso = asyncio.run(
            asyncio.wait_for(sistema_assistencias_workflow_tempo(), timeout=1800.0)
        )
        if sucesso:
            print(
                "\nOK: ATUALIZACAO CV ASSISTENCIAS WORKFLOW TEMPO CONCLUIDA COM SUCESSO!"
            )
            release_concurrency()
            sys.exit(0)
        else:
            print("\nERRO: FALHA NA ATUALIZACAO CV ASSISTENCIAS WORKFLOW TEMPO")
            release_concurrency()
            sys.exit(1)
    except asyncio.TimeoutError:
        print("\nTIMEOUT - Operacao demorou mais de 30 minutos")
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
