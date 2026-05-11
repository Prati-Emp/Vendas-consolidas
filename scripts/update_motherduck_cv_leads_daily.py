#!/usr/bin/env python3
"""
Atualizacao dedicada de CV Leads no MotherDuck (scripts/cv_leads_api.py).
"""

import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from scripts.concurrency_control import check_concurrency, release_concurrency


async def atualizar_cv_leads():
    """Coleta leads e atualiza main.cv_leads."""
    print("ATUALIZACAO DEDICADA - CV LEADS")
    print("=" * 60)
    print(f"Timestamp: {datetime.now()}")

    start_time = datetime.now()

    try:
        from scripts.cv_leads_api import obter_dados_cv_leads
        import duckdb
        import pandas as pd

        print("\n1. Coletando dados CV Leads...")
        try:
            df = await obter_dados_cv_leads()
            print(f"OK: CV Leads: {len(df)} registros")
        except Exception as e:
            df = pd.DataFrame()
            print(f"AVISO: Falha ao coletar CV Leads: {e}")

        print("\n2. Fazendo upload para MotherDuck...")
        duckdb.sql("INSTALL motherduck")
        duckdb.sql("LOAD motherduck")

        token = os.environ.get("MOTHERDUCK_TOKEN", "").strip()
        if not token:
            print("ERRO: MOTHERDUCK_TOKEN nao encontrado")
            return False

        duckdb.sql(f"SET motherduck_token='{token}'")
        conn = duckdb.connect("md:reservas")

        if df is not None and not df.empty:
            conn.register("df_cv_leads", df)
            conn.execute("CREATE OR REPLACE TABLE main.cv_leads AS SELECT * FROM df_cv_leads")
            count = conn.sql("SELECT COUNT(*) FROM main.cv_leads").fetchone()[0]
            print(f"OK: CV Leads upload: {count:,} registros")
        else:
            print("AVISO: Sem dados de CV Leads para upload")

        conn.close()

        print("\nATUALIZACAO CV LEADS CONCLUIDA!")
        print(f"Duracao: {datetime.now() - start_time}")
        return True

    except Exception as e:
        print(f"\nERRO na atualizacao de CV Leads: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def main():
    print("INICIANDO ATUALIZACAO DEDICADA - CV LEADS")
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

    required_vars = ["MOTHERDUCK_TOKEN", "CVCRM_EMAIL", "CVCRM_TOKEN"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    if missing_vars:
        print(f"ERRO: Variaveis de ambiente faltando: {', '.join(missing_vars)}")
        release_concurrency()
        sys.exit(1)

    print("OK: Variaveis de ambiente configuradas")

    try:
        sucesso = asyncio.run(asyncio.wait_for(atualizar_cv_leads(), timeout=1200.0))

        if sucesso:
            print("\nOK: ATUALIZACAO CV LEADS CONCLUIDA COM SUCESSO!")
            release_concurrency()
            sys.exit(0)

        print("\nERRO: FALHA NA ATUALIZACAO CV LEADS")
        release_concurrency()
        sys.exit(1)

    except asyncio.TimeoutError:
        print("\nTIMEOUT - Operacao demorou mais de 20 minutos")
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
