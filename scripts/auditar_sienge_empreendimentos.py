#!/usr/bin/env python3
"""
Auditoria dos empreendimentos Sienge: mede quantos registros retornam por ID
e grava um relatório no MotherDuck para análise (tabela: main.sienge_empreendimentos_auditoria).
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import asyncio
import pandas as pd
import duckdb
from dotenv import load_dotenv

# Garantir que o diretório raiz do projeto esteja no sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from scripts.sienge_apis import SiengeAPIClient, _extrair_registros  # type: ignore
from scripts.orchestrator import make_api_request


async def auditar_empreendimentos() -> pd.DataFrame:
    load_dotenv(override=True)

    cli = SiengeAPIClient()
    data_fim = datetime.now().strftime("%Y-%m-%d")

    resultados = []

    for idx, emp in enumerate(cli.empreendimentos, 1):
        empre_id = int(emp["id"])
        nome = emp.get("nome", str(empre_id))

        # Realizadas
        r1 = await make_api_request(
            "sienge_vendas_realizadas",
            "/sales",
            params={
                "enterpriseId": empre_id,
                "createdAfter": "2020-01-01",
                "createdBefore": data_fim,
                "situation": "SOLD",
            },
        )
        dados1 = _extrair_registros(r1)

        # Canceladas
        r2 = await make_api_request(
            "sienge_vendas_canceladas",
            "/sales",
            params={
                "enterpriseId": empre_id,
                "createdAfter": "2020-01-01",
                "createdBefore": data_fim,
                "situation": "CANCELED",
            },
        )
        dados2 = _extrair_registros(r2)

        resultados.append(
            {
                "enterpriseId": empre_id,
                "nome": nome,
                "qtd_realizadas": len(dados1) if isinstance(dados1, list) else 0,
                "qtd_canceladas": len(dados2) if isinstance(dados2, list) else 0,
                "success_realizadas": bool(r1.get("success")),
                "success_canceladas": bool(r2.get("success")),
                "response_ms_realizadas": int(1000 * float(r1.get("response_time", 0) or 0)),
                "response_ms_canceladas": int(1000 * float(r2.get("response_time", 0) or 0)),
                "audit_at": datetime.now(),
            }
        )

        # Pequeno delay para não sobrecarregar
        await asyncio.sleep(0.2)

    return pd.DataFrame(resultados)


def gravar_motherduck(df: pd.DataFrame) -> int:
    token = os.environ.get("MOTHERDUCK_TOKEN", "").strip().strip('"').strip("'")
    if not token:
        raise RuntimeError("MOTHERDUCK_TOKEN não encontrado")

    os.environ["motherduck_token"] = token
    con = duckdb.connect("md:reservas")
    con.register("df", df)
    con.execute(
        """
        CREATE OR REPLACE TABLE main.sienge_empreendimentos_auditoria AS
        SELECT * FROM df
        """
    )
    total = con.sql("SELECT COUNT(*) FROM main.sienge_empreendimentos_auditoria").fetchone()[0]
    con.close()
    return total


async def main():
    df = await auditar_empreendimentos()
    print("Linhas auditadas:", len(df))
    if not df.empty:
        print(df.sort_values(["qtd_realizadas", "qtd_canceladas"], ascending=False).head(10))
        total = gravar_motherduck(df)
        print(f"✅ Relatório gravado no MotherDuck: {total} linhas em main.sienge_empreendimentos_auditoria")
    else:
        print("⚠️ Auditoria vazia.")


if __name__ == "__main__":
    asyncio.run(main())


