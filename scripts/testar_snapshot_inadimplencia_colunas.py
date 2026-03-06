#!/usr/bin/env python3
"""Testa as novas colunas cr_valor_devido_caixa e cr_valor_devido_clientes_e_caixa - sem concurrency."""
import os
from datetime import date
from dotenv import load_dotenv
from dateutil.relativedelta import relativedelta

load_dotenv()
FILTRO = "(Tipo_Condicao IS NULL OR TRIM(Tipo_Condicao) NOT IN ('CP','MC','FI','FG'))"
FILTRO_CAIXA = "TRIM(Tipo_Condicao) IN ('CP','MC','FI','FG')"

def main():
    import duckdb
    duckdb.sql("INSTALL motherduck")
    duckdb.sql("LOAD motherduck")
    token = os.environ.get("MOTHERDUCK_TOKEN", "").strip()
    if not token:
        print("ERRO: MOTHERDUCK_TOKEN nao encontrado")
        return
    duckdb.sql(f"SET motherduck_token='{token}'")
    conn = duckdb.connect("md:administracao")

    hoje_str = date.today().strftime("%Y-%m-%d")
    mes_ref = (date.today().replace(day=1) - relativedelta(months=1)).strftime("%Y-%m")
    cond_inad = f"Tipo_Baixa IS NULL AND TRY_CAST(Data_Vencimento AS DATE) <= '{hoje_str}'::DATE"

    r = conn.execute(f"""
        SELECT
            SUM(CASE WHEN Tipo_Baixa IS NULL AND ({FILTRO}) THEN Valor_Corrigido ELSE 0 END) AS cr_clientes,
            SUM(CASE WHEN Tipo_Baixa IS NULL AND ({FILTRO_CAIXA}) THEN Valor_Corrigido ELSE 0 END) AS cr_caixa,
            SUM(CASE WHEN {cond_inad} AND ({FILTRO}) THEN Valor_Corrigido ELSE 0 END) AS inad_clientes
        FROM contas_recebidas_receber
    """).fetchone()

    cr_clientes, cr_caixa, inad = r[0] or 0, r[1] or 0, r[2] or 0
    total = cr_clientes + cr_caixa
    pct = (inad / cr_clientes * 100) if cr_clientes else 0

    print("=" * 60)
    print("TESTE - Novas colunas inadimplencia")
    print("=" * 60)
    print(f"Data: {hoje_str} | Mes: {mes_ref}")
    print()
    print("GERAL PRATI:")
    print(f"  cr_valor_devido (clientes):     R$ {cr_clientes:,.2f}")
    print(f"  cr_valor_devido_caixa:          R$ {cr_caixa:,.2f}")
    print(f"  cr_valor_devido_clientes_e_caixa: R$ {total:,.2f}")
    print(f"  valor_inadimplente:             R$ {inad:,.2f}")
    print(f"  % inadimplencia:                {pct:.2f}%")
    conn.close()

if __name__ == "__main__":
    main()
