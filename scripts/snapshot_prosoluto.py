#!/usr/bin/env python3
"""
Snapshot Mensal de Pró-Soluto
Calcula e persiste no MotherDuck (banco administracao) o estado histórico
de pró-soluto no último dia de cada mês.

Lógica:
  Numerador  = parcelas abertas no último dia do mês
               com Tipo_Condicao IN ('12','PM','AT','PB','PA','PI','PQ','PS')
               cruzadas com cv_vendas onde tipovenda = 'Venda Financiamento'
  Denominador = contratos cv_vendas com tipovenda = 'Venda Financiamento'
                e data_venda <= último dia do mês

Roda no 1º dia de cada mês via GitHub Actions.
"""

import os
import sys
import duckdb
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

TIPOS_PROSOLUTO = ("'12'", "'PM'", "'AT'", "'PB'", "'PA'", "'PI'", "'PQ'", "'PS'")
TIPOS_PROSOLUTO_SQL = ", ".join(TIPOS_PROSOLUTO)


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
        CREATE TABLE IF NOT EXISTS snapshot_prosoluto_mensal (
            data_snapshot                  DATE    NOT NULL,
            mes_referencia                 VARCHAR NOT NULL,  -- '2026-02'
            data_corte                     DATE    NOT NULL,  -- último dia do mês
            idempreendimento               BIGINT,            -- NULL = linha TOTAL
            empreendimento                 VARCHAR,           -- NULL = linha TOTAL
            codigointerno_empreendimento   VARCHAR,           -- NULL = linha TOTAL
            valor_prosoluto                DOUBLE,
            valor_venda_financiamento      DOUBLE,
            pct_prosoluto                  DOUBLE,
            UNIQUE (mes_referencia, idempreendimento)
        )
    """)
    print("OK: Tabela snapshot_prosoluto_mensal verificada/criada")


def mes_ja_processado(conn, mes_referencia: str) -> bool:
    """Verifica se o mês já foi processado (linha TOTAL existe)."""
    result = conn.execute("""
        SELECT COUNT(*) FROM snapshot_prosoluto_mensal
        WHERE mes_referencia = ? AND idempreendimento IS NULL
    """, [mes_referencia]).fetchone()
    return result[0] > 0


def calcular_e_inserir_snapshot(conn, data_corte: date):
    """
    Calcula o snapshot de pró-soluto para uma data de corte específica
    e insere na tabela (total + por empreendimento).
    """
    mes_referencia = data_corte.strftime("%Y-%m")
    data_corte_str = data_corte.strftime("%Y-%m-%d")
    hoje = date.today().strftime("%Y-%m-%d")

    print(f"\n--- Calculando snapshot pró-soluto para {mes_referencia} (corte: {data_corte_str}) ---")

    # Condição de parcela aberta no dia de corte (reutilizada nos dois queries)
    cond_aberta = f"""
        (
            cr.Tipo_Baixa IS NULL
            OR (cr.Data_Baixa IS NOT NULL AND cr.Data_Baixa <> ''
                AND cr.Data_Baixa::DATE > '{data_corte_str}'::DATE)
        )
    """

    # Linha TOTAL
    total_sql = f"""
        INSERT OR IGNORE INTO snapshot_prosoluto_mensal
        WITH parcelas_prosoluto AS (
            SELECT cr.Valor_Devido
            FROM "contas_recebidas_receber- API" cr
            WHERE cr.Data_Emissao::DATE <= '{data_corte_str}'::DATE
              AND cr.Tipo_Condicao IN ({TIPOS_PROSOLUTO_SQL})
              AND {cond_aberta}
              -- Garante que o título está vinculado a uma Venda Financiamento
              AND EXISTS (
                  SELECT 1 FROM cv_vendas v
                  WHERE v.tipovenda = 'Venda Financiamento'
                    AND v.contrato_interno = cr.N_Documento
              )
        ),
        denom AS (
            SELECT SUM(v.valor_contrato) AS valor_venda_fin
            FROM cv_vendas v
            WHERE v.tipovenda = 'Venda Financiamento'
              AND v.data_venda::DATE <= '{data_corte_str}'::DATE
        )
        SELECT
            '{hoje}'::DATE          AS data_snapshot,
            '{mes_referencia}'      AS mes_referencia,
            '{data_corte_str}'::DATE AS data_corte,
            NULL::BIGINT            AS idempreendimento,
            'TOTAL'                 AS empreendimento,
            NULL                    AS codigointerno_empreendimento,
            (SELECT SUM(Valor_Devido) FROM parcelas_prosoluto) AS valor_prosoluto,
            (SELECT valor_venda_fin FROM denom)                AS valor_venda_financiamento,
            CASE
                WHEN (SELECT valor_venda_fin FROM denom) = 0 OR (SELECT valor_venda_fin FROM denom) IS NULL THEN 0
                ELSE (SELECT SUM(Valor_Devido) FROM parcelas_prosoluto)
                     / (SELECT valor_venda_fin FROM denom)
            END                     AS pct_prosoluto
    """
    conn.execute(total_sql)

    # Linhas por Empreendimento (via cv_vendas)
    detalhe_sql = f"""
        INSERT OR IGNORE INTO snapshot_prosoluto_mensal
        WITH parcelas_por_emp AS (
            SELECT
                v.idempreendimento,
                v.empreendimento,
                v.codigointerno_empreendimento,
                SUM(cr.Valor_Devido) AS valor_prosoluto
            FROM "contas_recebidas_receber- API" cr
            INNER JOIN cv_vendas v
                ON v.tipovenda = 'Venda Financiamento'
               AND v.contrato_interno = cr.N_Documento
            WHERE cr.Data_Emissao::DATE <= '{data_corte_str}'::DATE
              AND cr.Tipo_Condicao IN ({TIPOS_PROSOLUTO_SQL})
              AND {cond_aberta}
            GROUP BY v.idempreendimento, v.empreendimento, v.codigointerno_empreendimento
        ),
        denom_por_emp AS (
            SELECT
                idempreendimento,
                empreendimento,
                codigointerno_empreendimento,
                SUM(valor_contrato) AS valor_venda_fin
            FROM cv_vendas
            WHERE tipovenda = 'Venda Financiamento'
              AND data_venda::DATE <= '{data_corte_str}'::DATE
            GROUP BY idempreendimento, empreendimento, codigointerno_empreendimento
        )
        SELECT
            '{hoje}'::DATE           AS data_snapshot,
            '{mes_referencia}'       AS mes_referencia,
            '{data_corte_str}'::DATE AS data_corte,
            d.idempreendimento,
            d.empreendimento,
            d.codigointerno_empreendimento,
            COALESCE(p.valor_prosoluto, 0)  AS valor_prosoluto,
            d.valor_venda_fin               AS valor_venda_financiamento,
            CASE
                WHEN d.valor_venda_fin = 0 OR d.valor_venda_fin IS NULL THEN 0
                ELSE COALESCE(p.valor_prosoluto, 0) / d.valor_venda_fin
            END                             AS pct_prosoluto
        FROM denom_por_emp d
        LEFT JOIN parcelas_por_emp p
            ON d.idempreendimento = p.idempreendimento
    """
    conn.execute(detalhe_sql)

    # Verificar resultado
    count = conn.execute("""
        SELECT COUNT(*), SUM(valor_prosoluto), SUM(valor_venda_financiamento)
        FROM snapshot_prosoluto_mensal
        WHERE mes_referencia = ?
    """, [mes_referencia]).fetchone()

    pct = (count[1] / count[2] * 100) if count[2] and count[2] > 0 else 0
    print(f"  Inserido: {count[0]} linhas | Pró-Soluto: R$ {count[1]:,.0f} | "
          f"Venda Fin: R$ {count[2]:,.0f} | %: {pct:.2f}%")


def main():
    print("=" * 60)
    print("SNAPSHOT MENSAL DE PRÓ-SOLUTO")
    print(f"Timestamp: {datetime.now()}")
    print("=" * 60)

    conn = get_connection()
    criar_tabela_se_necessario(conn)

    meses_arg = sys.argv[1:] if len(sys.argv) > 1 else []

    if meses_arg:
        meses_para_processar = meses_arg
    else:
        primeiro_dia_mes_atual = date.today().replace(day=1)
        mes_anterior = primeiro_dia_mes_atual - relativedelta(months=1)
        meses_para_processar = [mes_anterior.strftime("%Y-%m")]

    for mes_ref in meses_para_processar:
        try:
            ano, mes = int(mes_ref.split("-")[0]), int(mes_ref.split("-")[1])
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
    print("\nOK: Snapshot de pró-soluto concluído com sucesso!")


if __name__ == "__main__":
    main()
