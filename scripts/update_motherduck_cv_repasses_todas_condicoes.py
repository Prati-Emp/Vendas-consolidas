#!/usr/bin/env python3
"""
Atualizacao diaria da tabela main.cv_repasses_todas_condicoes no MotherDuck.

Copia o processamento de CV Repasses (valores, de-para, campos_adicionais),
mas NAO aplica o recorte operacional (Venda a Investidor, Distrato, Cancelado).
A tabela main.cv_repasses permanece filtrada no job diario.
"""

import asyncio
import os
import sys
from datetime import datetime

from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(__file__)))


TABELA = "main.cv_repasses_todas_condicoes"


async def atualizar_repasses_todas_condicoes() -> bool:
    print("SISTEMA DE ATUALIZACAO - REPASSES TODAS CONDICOES")
    print("=" * 60)
    print(f"Timestamp: {datetime.now()}")
    print(f"Tabela: {TABELA} (banco reservas)")
    print("Filtro operacional: ignorado (traz todas as situacoes)")

    start_time = datetime.now()

    try:
        import duckdb

        from scripts.cv_repasses_api import obter_dados_cv_repasses_todas_condicoes

        print("\n1. Coletando CV Repasses (todas as condicoes)...")
        df = await obter_dados_cv_repasses_todas_condicoes()
        if df.empty:
            print("ERRO: Nenhum dado retornado. Abortando upload.")
            return False
        print(f"OK: {len(df):,} registros")

        print("\n2. Gravando no MotherDuck...")
        duckdb.sql("INSTALL motherduck")
        duckdb.sql("LOAD motherduck")

        token = os.environ.get("MOTHERDUCK_TOKEN", "").strip()
        if not token:
            print("ERRO: MOTHERDUCK_TOKEN nao encontrado")
            return False

        os.environ["motherduck_token"] = token
        duckdb.sql(f"SET motherduck_token='{token}'")
        conn = duckdb.connect("md:reservas")
        conn.register("df_repasses_todas", df)
        conn.execute(
            f"CREATE OR REPLACE TABLE {TABELA} AS SELECT * FROM df_repasses_todas"
        )
        count = conn.sql(f"SELECT COUNT(*) FROM {TABELA}").fetchone()[0]

        try:
            dist = conn.sql(
                f"""
                SELECT Para, COUNT(*) AS qtd
                FROM {TABELA}
                GROUP BY Para
                ORDER BY qtd DESC
                """
            ).fetchall()
            print(f"OK: upload {count:,} registros")
            print("Distribuicao por Para:")
            for para, qtd in dist:
                print(f"   - {para}: {qtd:,}")
        except Exception as e:
            print(f"OK: upload {count:,} registros")
            print(f"AVISO: nao foi possivel resumir Para: {e}")

        conn.close()

        duration = datetime.now() - start_time
        print("\nATUALIZACAO CONCLUIDA")
        print(f"Duracao: {duration}")
        print(f"Tabela: {TABELA}")
        return True

    except Exception as e:
        print(f"\nERRO na atualizacao: {e}")
        import traceback

        traceback.print_exc()
        return False


def main() -> None:
    print("INICIANDO ATUALIZACAO REPASSES TODAS CONDICOES")
    print("=" * 60)
    print(f"Timestamp: {datetime.now()}")
    print(f"Python: {sys.version}")
    print(f"Working directory: {os.getcwd()}")

    load_dotenv(override=True)
    required_vars = ["MOTHERDUCK_TOKEN", "CVCRM_EMAIL", "CVCRM_TOKEN"]
    missing = [v for v in required_vars if not os.environ.get(v)]
    if missing:
        print(f"ERRO: Variaveis faltando: {', '.join(missing)}")
        sys.exit(1)
    print("OK: Variaveis de ambiente configuradas")

    try:
        sucesso = asyncio.run(
            asyncio.wait_for(atualizar_repasses_todas_condicoes(), timeout=1200.0)
        )
        if sucesso:
            print("\nOK: ATUALIZACAO CONCLUIDA COM SUCESSO")
            sys.exit(0)
        print("\nERRO: FALHA NA ATUALIZACAO")
        sys.exit(1)
    except asyncio.TimeoutError:
        print("\nTIMEOUT - Operacao demorou mais de 20 minutos")
        sys.exit(1)
    except Exception as e:
        print(f"\nERRO INESPERADO: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
