#!/usr/bin/env python3
"""
Compara inadimplência ANTES e PÓS ajuste do filtro Tipo_Condicao.

ANTES: todas as parcelas (sem filtro)
PÓS:   exclui Tipo_Condicao IN ('CP','MC','FI','FG')
"""
import os
from datetime import date
from dotenv import load_dotenv
from dateutil.relativedelta import relativedelta

load_dotenv()
FILTRO_POS = "(Tipo_Condicao IS NULL OR TRIM(Tipo_Condicao) NOT IN ('CP','MC','FI','FG'))"


def run_query(conn, cond_inad, where_extra=""):
    """Retorna (cr_valor_devido, valor_inadimplente, pct) para Geral Prati."""
    where_clause = f"WHERE {where_extra}" if where_extra else ""
    r = conn.execute(f"""
        SELECT
            SUM(CASE WHEN Tipo_Baixa IS NULL THEN Valor_Corrigido ELSE 0 END) AS cr_valor_devido,
            SUM(CASE WHEN {cond_inad} THEN Valor_Corrigido ELSE 0 END) AS valor_inadimplente,
            CASE WHEN SUM(CASE WHEN Tipo_Baixa IS NULL THEN Valor_Corrigido ELSE 0 END) = 0 THEN 0
                 ELSE SUM(CASE WHEN {cond_inad} THEN Valor_Corrigido ELSE 0 END)
                    / SUM(CASE WHEN Tipo_Baixa IS NULL THEN Valor_Corrigido ELSE 0 END)
            END AS pct_inadimplencia
        FROM contas_recebidas_receber
        {where_clause}
    """).fetchone()
    return (r[0] or 0, r[1] or 0, (r[2] or 0) * 100)


def run_query_por_centro(conn, cond_inad, where_extra=""):
    """Retorna lista (centro_custo, cr, inad, pct) ordenada por inadimplente."""
    and_clause = f"AND {where_extra}" if where_extra else ""
    rows = conn.execute(f"""
        SELECT
            Centro_Custo,
            SUM(CASE WHEN Tipo_Baixa IS NULL THEN Valor_Corrigido ELSE 0 END) AS cr_valor_devido,
            SUM(CASE WHEN {cond_inad} THEN Valor_Corrigido ELSE 0 END) AS valor_inadimplente,
            CASE WHEN SUM(CASE WHEN Tipo_Baixa IS NULL THEN Valor_Corrigido ELSE 0 END) = 0 THEN 0
                 ELSE SUM(CASE WHEN {cond_inad} THEN Valor_Corrigido ELSE 0 END)
                    / SUM(CASE WHEN Tipo_Baixa IS NULL THEN Valor_Corrigido ELSE 0 END)
            END AS pct_inadimplencia
        FROM contas_recebidas_receber
        WHERE Cod_Centro_Custo IS NOT NULL AND Centro_Custo IS NOT NULL {and_clause}
        GROUP BY Cod_Centro_Custo, Centro_Custo
        ORDER BY valor_inadimplente DESC
        LIMIT 15
    """).fetchall()
    return [(r[0], r[1] or 0, r[2] or 0, (r[3] or 0) * 100) for r in rows]


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

    # ANTES (sem filtro)
    cr_ant, inad_ant, pct_ant = run_query(conn, cond_inad, "")
    rows_ant = run_query_por_centro(conn, cond_inad, "")

    # PÓS (com filtro)
    cr_pos, inad_pos, pct_pos = run_query(conn, cond_inad, FILTRO_POS)
    rows_pos = run_query_por_centro(conn, cond_inad, FILTRO_POS)

    conn.close()

    # Saída
    print("=" * 90)
    print("COMPARAÇÃO INADIMPLÊNCIA - ANTES vs PÓS AJUSTE (filtro Tipo_Condicao)")
    print("=" * 90)
    print(f"Data referência: {hoje_str} | Mês: {mes_ref}")
    print()
    print("Cenário ANTES: todas as parcelas (sem filtro Tipo_Condicao)")
    print("Cenário PÓS:   exclui Tipo_Condicao IN ('CP','MC','FI','FG')")
    print()
    print("-" * 90)
    print("GERAL PRATI")
    print("-" * 90)
    print(f"{'Indicador':<25} {'ANTES':>20} {'PÓS':>20} {'Diferença':>20}")
    print("-" * 90)
    print(f"{'CR Valor Devido':<25} {cr_ant:>18,.0f}  {cr_pos:>18,.0f}  {cr_pos-cr_ant:>+18,.0f}")
    print(f"{'Valor Inadimplente':<25} {inad_ant:>18,.0f}  {inad_pos:>18,.0f}  {inad_pos-inad_ant:>+18,.0f}")
    print(f"{'% Inadimplência':<25} {pct_ant:>17.2f}%  {pct_pos:>17.2f}%  {pct_pos-pct_ant:>+17.2f}%")
    print()
    print("-" * 90)
    print("POR CENTRO DE CUSTO (top 15 - ordenado por PÓS)")
    print("-" * 90)
    print(f"{'Centro de Custo':<30} {'ANTES %':>10} {'POS %':>10} {'Diff (p.p.)':>10}")
    print("-" * 90)

    # Unir por centro_custo para comparar (ordenado por PÓS)
    dict_ant = {r[0]: r for r in rows_ant}
    centros = [r[0] for r in rows_pos]
    for cc in centros[:15]:
        r_ant = dict_ant.get(cc, (cc, 0, 0, 0))
        r_pos = next((r for r in rows_pos if r[0] == cc), (cc, 0, 0, 0))
        pct_a, pct_p = r_ant[3], r_pos[3]
        delta = pct_p - pct_a
        print(f"{cc[:30]:<30} {pct_a:>9.2f}% {pct_p:>9.2f}% {delta:>+9.2f}")

    print()
    print("=" * 90)


if __name__ == "__main__":
    main()
