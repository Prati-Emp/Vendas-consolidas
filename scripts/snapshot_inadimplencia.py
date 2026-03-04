#!/usr/bin/env python3
"""
Snapshot Mensal de Inadimplência
Calcula e persiste no MotherDuck (banco administracao) o estado histórico
de inadimplência no último dia de cada mês.

Lógica: uma parcela estava aberta no último dia do mês se:
  - Tipo_Baixa é NULL (ainda aberta hoje), OU
  - Data_Baixa > último dia do mês (foi paga depois daquela data)

Roda no 1º dia de cada mês via GitHub Actions, capturando o fechamento
do mês anterior. Também pode ser executado manualmente para backfill.
"""

import os
import sys
import duckdb
from datetime import date, datetime
from dateutil.relativedelta import relativedelta


def get_connection():
    """Conecta ao banco administracao no MotherDuck."""
    token = os.environ.get("MOTHERDUCK_TOKEN", "").strip()
    if not token:
        print("ERRO: MOTHERDUCK_TOKEN não encontrado")
        sys.exit(1)

    duckdb.sql("INSTALL motherduck")
    duckdb.sql("LOAD motherduck")
    duckdb.sql(f"SET motherduck_token='{token}'")
    conn = duckdb.connect("md:administracao")
    return conn


def criar_tabela_se_necessario(conn):
    """Cria a tabela de snapshot se ainda não existir."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS snapshot_inadimplencia_mensal (
            data_snapshot        DATE        NOT NULL,
            mes_referencia       VARCHAR     NOT NULL,  -- formato '2026-02'
            data_corte           DATE        NOT NULL,  -- último dia do mês
            cod_centro_custo     INTEGER,               -- NULL = linha TOTAL
            centro_custo         VARCHAR,               -- NULL = linha TOTAL
            cr_valor_devido      DOUBLE,
            valor_inadimplente   DOUBLE,
            pct_inadimplencia    DOUBLE,
            UNIQUE (mes_referencia, cod_centro_custo)
        )
    """)
    print("OK: Tabela snapshot_inadimplencia_mensal verificada/criada")


def mes_ja_processado(conn, mes_referencia: str) -> bool:
    """Verifica se o mês já foi processado (linha TOTAL existe)."""
    result = conn.execute("""
        SELECT COUNT(*) FROM snapshot_inadimplencia_mensal
        WHERE mes_referencia = ? AND cod_centro_custo IS NULL
    """, [mes_referencia]).fetchone()
    return result[0] > 0


def calcular_e_inserir_snapshot(conn, data_corte: date):
    """
    Calcula o snapshot de inadimplência para uma data de corte específica
    e insere na tabela (total + por centro de custo).
    """
    mes_referencia = data_corte.strftime("%Y-%m")
    data_corte_str = data_corte.strftime("%Y-%m-%d")
    hoje = date.today().strftime("%Y-%m-%d")

    print(f"\n--- Calculando snapshot para {mes_referencia} (corte: {data_corte_str}) ---")

    # Linha TOTAL
    total_sql = f"""
        INSERT OR IGNORE INTO snapshot_inadimplencia_mensal
        SELECT
            '{hoje}'::DATE                                      AS data_snapshot,
            '{mes_referencia}'                                  AS mes_referencia,
            '{data_corte_str}'::DATE                            AS data_corte,
            NULL::INTEGER                                       AS cod_centro_custo,
            'TOTAL'                                             AS centro_custo,

            -- Denominador: parcelas abertas no último dia do mês
            SUM(CASE
                WHEN Data_Emissao::DATE <= '{data_corte_str}'::DATE
                 AND (
                     Tipo_Baixa IS NULL
                     OR (Data_Baixa IS NOT NULL AND Data_Baixa <> ''
                         AND Data_Baixa::DATE > '{data_corte_str}'::DATE)
                 )
                THEN Valor_Corrigido ELSE 0
            END)                                               AS cr_valor_devido,

            -- Numerador: abertas E vencidas até o último dia do mês
            SUM(CASE
                WHEN Data_Vencimento::DATE <= '{data_corte_str}'::DATE
                 AND Data_Emissao::DATE    <= '{data_corte_str}'::DATE
                 AND (
                     Tipo_Baixa IS NULL
                     OR (Data_Baixa IS NOT NULL AND Data_Baixa <> ''
                         AND Data_Baixa::DATE > '{data_corte_str}'::DATE)
                 )
                THEN Valor_Corrigido ELSE 0
            END)                                               AS valor_inadimplente,

            -- Percentual calculado direto
            CASE
                WHEN SUM(CASE
                    WHEN Data_Emissao::DATE <= '{data_corte_str}'::DATE
                     AND (Tipo_Baixa IS NULL
                          OR (Data_Baixa IS NOT NULL AND Data_Baixa <> ''
                              AND Data_Baixa::DATE > '{data_corte_str}'::DATE))
                    THEN Valor_Corrigido ELSE 0 END) = 0 THEN 0
                ELSE
                    SUM(CASE
                        WHEN Data_Vencimento::DATE <= '{data_corte_str}'::DATE
                         AND Data_Emissao::DATE    <= '{data_corte_str}'::DATE
                         AND (Tipo_Baixa IS NULL
                              OR (Data_Baixa IS NOT NULL AND Data_Baixa <> ''
                                  AND Data_Baixa::DATE > '{data_corte_str}'::DATE))
                        THEN Valor_Corrigido ELSE 0 END)
                    /
                    SUM(CASE
                        WHEN Data_Emissao::DATE <= '{data_corte_str}'::DATE
                         AND (Tipo_Baixa IS NULL
                              OR (Data_Baixa IS NOT NULL AND Data_Baixa <> ''
                                  AND Data_Baixa::DATE > '{data_corte_str}'::DATE))
                        THEN Valor_Corrigido ELSE 0 END)
            END                                                AS pct_inadimplencia

        FROM "contas_recebidas_receber- API"
        WHERE 1=1
    """

    conn.execute(total_sql)

    # Linhas por Centro de Custo
    detalhe_sql = f"""
        INSERT OR IGNORE INTO snapshot_inadimplencia_mensal
        SELECT
            '{hoje}'::DATE                                      AS data_snapshot,
            '{mes_referencia}'                                  AS mes_referencia,
            '{data_corte_str}'::DATE                            AS data_corte,
            Cod_Centro_Custo                                    AS cod_centro_custo,
            Centro_Custo                                        AS centro_custo,

            SUM(CASE
                WHEN Data_Emissao::DATE <= '{data_corte_str}'::DATE
                 AND (
                     Tipo_Baixa IS NULL
                     OR (Data_Baixa IS NOT NULL AND Data_Baixa <> ''
                         AND Data_Baixa::DATE > '{data_corte_str}'::DATE)
                 )
                THEN Valor_Corrigido ELSE 0
            END)                                               AS cr_valor_devido,

            SUM(CASE
                WHEN Data_Vencimento::DATE <= '{data_corte_str}'::DATE
                 AND Data_Emissao::DATE    <= '{data_corte_str}'::DATE
                 AND (
                     Tipo_Baixa IS NULL
                     OR (Data_Baixa IS NOT NULL AND Data_Baixa <> ''
                         AND Data_Baixa::DATE > '{data_corte_str}'::DATE)
                 )
                THEN Valor_Corrigido ELSE 0
            END)                                               AS valor_inadimplente,

            CASE
                WHEN SUM(CASE
                    WHEN Data_Emissao::DATE <= '{data_corte_str}'::DATE
                     AND (Tipo_Baixa IS NULL
                          OR (Data_Baixa IS NOT NULL AND Data_Baixa <> ''
                              AND Data_Baixa::DATE > '{data_corte_str}'::DATE))
                    THEN Valor_Corrigido ELSE 0 END) = 0 THEN 0
                ELSE
                    SUM(CASE
                        WHEN Data_Vencimento::DATE <= '{data_corte_str}'::DATE
                         AND Data_Emissao::DATE    <= '{data_corte_str}'::DATE
                         AND (Tipo_Baixa IS NULL
                              OR (Data_Baixa IS NOT NULL AND Data_Baixa <> ''
                                  AND Data_Baixa::DATE > '{data_corte_str}'::DATE))
                        THEN Valor_Corrigido ELSE 0 END)
                    /
                    SUM(CASE
                        WHEN Data_Emissao::DATE <= '{data_corte_str}'::DATE
                         AND (Tipo_Baixa IS NULL
                              OR (Data_Baixa IS NOT NULL AND Data_Baixa <> ''
                                  AND Data_Baixa::DATE > '{data_corte_str}'::DATE))
                        THEN Valor_Corrigido ELSE 0 END)
            END                                                AS pct_inadimplencia

        FROM "contas_recebidas_receber- API"
        WHERE Cod_Centro_Custo IS NOT NULL
          AND Centro_Custo IS NOT NULL
        GROUP BY Cod_Centro_Custo, Centro_Custo
    """

    conn.execute(detalhe_sql)

    # Verificar resultado
    count = conn.execute("""
        SELECT COUNT(*), SUM(cr_valor_devido), SUM(valor_inadimplente)
        FROM snapshot_inadimplencia_mensal
        WHERE mes_referencia = ?
    """, [mes_referencia]).fetchone()

    pct = (count[2] / count[1] * 100) if count[1] and count[1] > 0 else 0
    print(f"  Inserido: {count[0]} linhas | CR Devido: R$ {count[1]:,.0f} | "
          f"Inadimplente: R$ {count[2]:,.0f} | %: {pct:.2f}%")


def main():
    print("=" * 60)
    print("SNAPSHOT MENSAL DE INADIMPLÊNCIA")
    print(f"Timestamp: {datetime.now()}")
    print("=" * 60)

    conn = get_connection()
    criar_tabela_se_necessario(conn)

    # Por padrão: processa o mês anterior (fechamento do mês passado)
    # Para backfill, pode-se passar meses específicos como argumento
    meses_arg = sys.argv[1:] if len(sys.argv) > 1 else []

    if meses_arg:
        # Backfill: ex: python snapshot_inadimplencia.py 2025-10 2025-11 2025-12
        meses_para_processar = meses_arg
    else:
        # Padrão: mês anterior
        primeiro_dia_mes_atual = date.today().replace(day=1)
        mes_anterior = primeiro_dia_mes_atual - relativedelta(months=1)
        meses_para_processar = [mes_anterior.strftime("%Y-%m")]

    for mes_ref in meses_para_processar:
        try:
            ano, mes = int(mes_ref.split("-")[0]), int(mes_ref.split("-")[1])
            # Último dia do mês (EOMONTH)
            primeiro_dia_proximo_mes = date(ano, mes, 1) + relativedelta(months=1)
            data_corte = primeiro_dia_proximo_mes - relativedelta(days=1)

            if mes_ja_processado(conn, mes_ref):
                print(f"SKIP: {mes_ref} já processado (use DELETE manual para reprocessar)")
                continue

            calcular_e_inserir_snapshot(conn, data_corte)

        except Exception as e:
            print(f"ERRO ao processar {mes_ref}: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    conn.close()
    print("\nOK: Snapshot de inadimplência concluído com sucesso!")


if __name__ == "__main__":
    main()
