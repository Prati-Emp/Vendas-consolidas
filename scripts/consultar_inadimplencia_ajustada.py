#!/usr/bin/env python3
"""Consulta inadimplência com filtro Tipo_Condicao (exclui CP, MC, FI, FG) - apenas leitura."""
import os
from datetime import date
from dotenv import load_dotenv
from dateutil.relativedelta import relativedelta

load_dotenv()
FILTRO = "(Tipo_Condicao IS NULL OR TRIM(Tipo_Condicao) NOT IN ('CP','MC','FI','FG'))"

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

    # Total Geral Prati
    r = conn.execute(f"""
        SELECT
            SUM(CASE WHEN Tipo_Baixa IS NULL THEN Valor_Corrigido ELSE 0 END) AS cr_valor_devido,
            SUM(CASE WHEN {cond_inad} THEN Valor_Corrigido ELSE 0 END) AS valor_inadimplente,
            CASE WHEN SUM(CASE WHEN Tipo_Baixa IS NULL THEN Valor_Corrigido ELSE 0 END) = 0 THEN 0
                 ELSE SUM(CASE WHEN {cond_inad} THEN Valor_Corrigido ELSE 0 END)
                    / SUM(CASE WHEN Tipo_Baixa IS NULL THEN Valor_Corrigido ELSE 0 END)
            END AS pct_inadimplencia
        FROM contas_recebidas_receber
        WHERE {FILTRO}
    """).fetchone()

    print("=" * 60)
    print("INADIMPLÊNCIA COM FILTRO Tipo_Condicao (exclui CP, MC, FI, FG)")
    print("=" * 60)
    print(f"Data referência: {hoje_str} | Mês: {mes_ref}")
    print()
    cr, inad, pct = r[0] or 0, r[1] or 0, (r[2] or 0) * 100
    print("GERAL PRATI:")
    print(f"  CR Valor Devido:    R$ {cr:,.2f}")
    print(f"  Valor Inadimplente: R$ {inad:,.2f}")
    print(f"  % Inadimplência:    {pct:.2f}%")
    print()

    # Por centro de custo
    rows = conn.execute(f"""
        SELECT centro_custo, cr_valor_devido, valor_inadimplente, pct_inadimplencia
        FROM (
            SELECT
                Centro_Custo AS centro_custo,
                SUM(CASE WHEN Tipo_Baixa IS NULL THEN Valor_Corrigido ELSE 0 END) AS cr_valor_devido,
                SUM(CASE WHEN {cond_inad} THEN Valor_Corrigido ELSE 0 END) AS valor_inadimplente,
                CASE WHEN SUM(CASE WHEN Tipo_Baixa IS NULL THEN Valor_Corrigido ELSE 0 END) = 0 THEN 0
                     ELSE SUM(CASE WHEN {cond_inad} THEN Valor_Corrigido ELSE 0 END)
                        / SUM(CASE WHEN Tipo_Baixa IS NULL THEN Valor_Corrigido ELSE 0 END)
                END AS pct_inadimplencia
            FROM contas_recebidas_receber
            WHERE Cod_Centro_Custo IS NOT NULL AND Centro_Custo IS NOT NULL AND {FILTRO}
            GROUP BY Cod_Centro_Custo, Centro_Custo
        ) t
        ORDER BY valor_inadimplente DESC
        LIMIT 15
    """).fetchall()

    print("POR CENTRO DE CUSTO (top 15 por valor inadimplente):")
    print("-" * 60)
    for row in rows:
        nome, cr, inad, pct = row[0], row[1] or 0, row[2] or 0, (row[3] or 0) * 100
        print(f"  {nome[:35]:<35} | CR: R$ {cr:>12,.0f} | Inad: R$ {inad:>10,.0f} | {pct:>5.2f}%")
    conn.close()

if __name__ == "__main__":
    main()
