#!/usr/bin/env python3
"""
Atualizacao dedicada de VGV Empreendimentos no MotherDuck.
"""

import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Garante import do projeto quando rodar via Actions
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from scripts.concurrency_control import check_concurrency, release_concurrency


async def atualizar_vgv():
    """Coleta VGV e atualiza tabela no MotherDuck."""
    print("ATUALIZACAO DEDICADA - VGV EMPREENDIMENTOS")
    print("=" * 60)
    print(f"Timestamp: {datetime.now()}")

    start_time = datetime.now()

    try:
        from scripts.cv_vgv_empreendimentos_api import obter_dados_vgv_empreendimentos
        import duckdb
        import pandas as pd

        print("\n1. Coletando dados VGV Empreendimentos...")
        try:
            df_vgv_empreendimentos = await obter_dados_vgv_empreendimentos(1, 20)
            print(f"OK: VGV Empreendimentos: {len(df_vgv_empreendimentos)} registros")
        except Exception as e:
            df_vgv_empreendimentos = pd.DataFrame()
            print(f"AVISO: Falha ao coletar VGV Empreendimentos: {e}")

        print("\n2. Fazendo upload para MotherDuck...")
        duckdb.sql("INSTALL motherduck")
        duckdb.sql("LOAD motherduck")

        token = os.environ.get("MOTHERDUCK_TOKEN", "").strip()
        if not token:
            print("ERRO: MOTHERDUCK_TOKEN nao encontrado")
            return False

        duckdb.sql(f"SET motherduck_token='{token}'")
        conn = duckdb.connect("md:reservas")

        if df_vgv_empreendimentos is not None and not df_vgv_empreendimentos.empty:
            conn.register("df_vgv_empreendimentos", df_vgv_empreendimentos)
            conn.execute(
                "CREATE OR REPLACE TABLE main.cv_vgv_empreendimentos AS SELECT * FROM df_vgv_empreendimentos"
            )
            count_vgv = conn.sql("SELECT COUNT(*) FROM main.cv_vgv_empreendimentos").fetchone()[0]
            print(f"OK: VGV Empreendimentos upload: {count_vgv:,} registros")
        else:
            print("AVISO: Sem dados de VGV para upload")

        conn.close()

        end_time = datetime.now()
        duration = end_time - start_time
        print("\nATUALIZACAO VGV CONCLUIDA!")
        print(f"Duracao: {duration}")

        return True

    except Exception as e:
        print(f"\nERRO na atualizacao de VGV: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Execucao principal para GitHub Actions."""
    print("INICIANDO ATUALIZACAO DEDICADA DE VGV")
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

    required_vars = ["MOTHERDUCK_TOKEN"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    if missing_vars:
        print(f"ERRO: Variaveis de ambiente faltando: {', '.join(missing_vars)}")
        release_concurrency()
        sys.exit(1)

    print("OK: Variaveis de ambiente configuradas")

    try:
        sucesso = asyncio.run(asyncio.wait_for(atualizar_vgv(), timeout=1200.0))

        if sucesso:
            print("\nOK: ATUALIZACAO VGV CONCLUIDA COM SUCESSO!")
            release_concurrency()
            sys.exit(0)

        print("\nERRO: FALHA NA ATUALIZACAO VGV")
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
