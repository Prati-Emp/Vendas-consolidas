#!/usr/bin/env python3
"""
Snapshot Mensal de Pró-Soluto
Roda todo dia 10 do mês. Captura o estado atual (sem data de corte),
replicando exatamente a lógica das medidas padrão do Power BI:
  - Valor_ProSoluto = parcelas abertas (Tipo_Baixa IS NULL) com
    Tipo_Condicao IN ('12','PM','AT','PB','PA','PI','PQ','PS'),
    vinculadas a cv_vendas via id2 = id1 (Cod_Centro_Custo & Unidade = codigointerno_empreendimento & unidade)
  - Valor_Venda_Financiamento = SUM(valor_contrato) de cv_vendas tipovenda = 'Venda Financiamento'
  - % ProSoluto = Valor_ProSoluto / Valor_Venda_Financiamento
A foto é datada com o dia em que rodou (data_snapshot) e o mês de referência.
"""

import asyncio
import os
import sys
from datetime import date, datetime
from dotenv import load_dotenv
from dateutil.relativedelta import relativedelta

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from scripts.concurrency_control import check_concurrency, release_concurrency

TIPOS_PROSOLUTO = "'12', 'PM', 'AT', 'PB', 'PA', 'PI', 'PQ', 'PS'"


async def sistema_snapshot_prosoluto():
    print("SISTEMA DE SNAPSHOT MENSAL - PRO-SOLUTO")
    print("=" * 60)
    print(f"Timestamp: {datetime.now()}")

    start_time = datetime.now()

    try:
        import duckdb

        print("\n1. Conectando ao MotherDuck (banco administracao)...")
        duckdb.sql("INSTALL motherduck")
        duckdb.sql("LOAD motherduck")

        token = os.environ.get("MOTHERDUCK_TOKEN", "").strip()
        if not token:
            print("ERRO: MOTHERDUCK_TOKEN nao encontrado")
            return False

        duckdb.sql(f"SET motherduck_token='{token}'")
        conn = duckdb.connect("md:administracao")
        print("OK: Conectado ao MotherDuck")

        print("\n2. Verificando/criando tabela snapshot_prosoluto_mensal_...")
        try:
            cols = [r[0] for r in conn.execute("DESCRIBE snapshot_prosoluto_mensal_").fetchall()]
            if "idempreendimento" in cols:
                conn.execute("DROP TABLE IF EXISTS snapshot_prosoluto_mensal_")
        except Exception:
            pass
        conn.execute("""
            CREATE TABLE IF NOT EXISTS snapshot_prosoluto_mensal_ (
                data_snapshot                DATE    NOT NULL,
                mes_referencia               VARCHAR NOT NULL,
                codigointerno_empreendimento VARCHAR,
                empreendimento               VARCHAR,
                valor_prosoluto              DOUBLE,
                valor_venda_financiamento    DOUBLE,
                pct_prosoluto                DOUBLE,
                UNIQUE (mes_referencia, codigointerno_empreendimento)
            )
        """)
        print("OK: Tabela verificada/criada")

        hoje = date.today()
        hoje_str = hoje.strftime("%Y-%m-%d")
        mes_anterior = hoje.replace(day=1) - relativedelta(months=1)
        mes_ref = mes_anterior.strftime("%Y-%m")

        # Remove dados existentes do mes_referencia (substitui no dia 10; historico de meses anteriores preservado)
        conn.execute(
            "DELETE FROM snapshot_prosoluto_mensal_ WHERE mes_referencia = ?",
            [mes_ref]
        )
        print(f"\n3. Calculando fechamento de {mes_ref} (data snapshot: {hoje_str})...")

        # TOTAL
        conn.execute(f"""
            INSERT INTO snapshot_prosoluto_mensal_
            WITH parcelas AS (
                SELECT cr.Valor_Devido
                FROM contas_recebidas_receber cr
                WHERE cr.Tipo_Baixa IS NULL
                  AND cr.Tipo_Condicao IN ({TIPOS_PROSOLUTO})
                  AND EXISTS (
                      SELECT 1 FROM reservas.cv_vendas v
                      WHERE v.tipovenda = 'Venda Financiamento'
                        AND (COALESCE(CAST(cr.Cod_Centro_Custo AS VARCHAR), '') || COALESCE(TRIM(CAST(cr.Unidade AS VARCHAR)), ''))
                          = (COALESCE(CAST(v.codigointerno_empreendimento AS VARCHAR), '') || COALESCE(TRIM(CAST(v.unidade AS VARCHAR)), ''))
                  )
            ),
            denom AS (
                SELECT SUM(valor_contrato) AS total
                FROM reservas.cv_vendas
                WHERE tipovenda = 'Venda Financiamento'
            )
            SELECT
                '{hoje_str}'::DATE AS data_snapshot,
                '{mes_ref}'        AS mes_referencia,
                NULL               AS codigointerno_empreendimento,
                'Geral Prati'      AS empreendimento,
                COALESCE((SELECT SUM(Valor_Devido) FROM parcelas), 0) AS valor_prosoluto,
                COALESCE((SELECT total FROM denom), 0)               AS valor_venda_financiamento,
                CASE
                    WHEN (SELECT total FROM denom) IS NULL OR (SELECT total FROM denom) = 0 THEN 0
                    ELSE COALESCE((SELECT SUM(Valor_Devido) FROM parcelas), 0) / (SELECT total FROM denom)
                END AS pct_prosoluto
        """)

        # Por Empreendimento (identificador: codigointerno_empreendimento = Cod_Centro_Custo)
        conn.execute(f"""
            INSERT INTO snapshot_prosoluto_mensal_
            WITH parcelas_emp AS (
                SELECT v.codigointerno_empreendimento, v.empreendimento,
                       SUM(cr.Valor_Devido) AS valor_prosoluto
                FROM contas_recebidas_receber cr
                INNER JOIN reservas.cv_vendas v
                    ON v.tipovenda = 'Venda Financiamento'
                   AND (COALESCE(CAST(cr.Cod_Centro_Custo AS VARCHAR), '') || COALESCE(TRIM(CAST(cr.Unidade AS VARCHAR)), ''))
                     = (COALESCE(CAST(v.codigointerno_empreendimento AS VARCHAR), '') || COALESCE(TRIM(CAST(v.unidade AS VARCHAR)), ''))
                WHERE cr.Tipo_Baixa IS NULL
                  AND cr.Tipo_Condicao IN ({TIPOS_PROSOLUTO})
                GROUP BY v.codigointerno_empreendimento, v.empreendimento
            ),
            denom_emp AS (
                SELECT codigointerno_empreendimento, empreendimento,
                       SUM(valor_contrato) AS total
                FROM reservas.cv_vendas
                WHERE tipovenda = 'Venda Financiamento'
                  AND codigointerno_empreendimento IS NOT NULL
                GROUP BY codigointerno_empreendimento, empreendimento
            )
            SELECT
                '{hoje_str}'::DATE AS data_snapshot,
                '{mes_ref}'        AS mes_referencia,
                d.codigointerno_empreendimento,
                d.empreendimento,
                COALESCE(p.valor_prosoluto, 0) AS valor_prosoluto,
                COALESCE(d.total, 0)           AS valor_venda_financiamento,
                CASE WHEN d.total IS NULL OR d.total = 0 THEN 0
                     ELSE COALESCE(p.valor_prosoluto, 0) / d.total
                END AS pct_prosoluto
            FROM denom_emp d
            LEFT JOIN parcelas_emp p ON d.codigointerno_empreendimento = p.codigointerno_empreendimento
        """)

        stats = conn.execute(
            "SELECT COUNT(*), SUM(valor_prosoluto), SUM(valor_venda_financiamento) FROM snapshot_prosoluto_mensal_ WHERE mes_referencia = ?",
            [mes_ref]
        ).fetchone()
        print(f"  OK: {stats[0]} linhas inseridas")

        total_row = conn.execute(
            "SELECT valor_prosoluto, valor_venda_financiamento, pct_prosoluto FROM snapshot_prosoluto_mensal_ WHERE mes_referencia = ? AND codigointerno_empreendimento IS NULL",
            [mes_ref]
        ).fetchone()
        if total_row:
            vp = total_row[0] if total_row[0] is not None else 0
            vf = total_row[1] if total_row[1] is not None else 0
            pct = (total_row[2] * 100) if total_row[2] is not None else 0
            print(f"  TOTAL: Pro-Soluto = R$ {vp:,.2f} | Venda Fin = R$ {vf:,.2f} | % = {pct:.2f}%")

        conn.close()
        duration = datetime.now() - start_time
        print(f"\nSNAPSHOT PRO-SOLUTO CONCLUIDO em {duration}")
        print(f"   Tabela: snapshot_prosoluto_mensal_ | Banco: administracao (MotherDuck)")
        return True

    except Exception as e:
        print(f"\nERRO no snapshot de pro-soluto: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("INICIANDO SNAPSHOT MENSAL DE PRO-SOLUTO")
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

    required_vars = ["MOTHERDUCK_TOKEN"]
    missing_vars = [v for v in required_vars if not os.environ.get(v)]
    if missing_vars:
        print(f"ERRO: Variaveis faltando: {', '.join(missing_vars)}")
        release_concurrency()
        sys.exit(1)
    print("OK: Variaveis de ambiente configuradas")

    try:
        sucesso = asyncio.run(
            asyncio.wait_for(sistema_snapshot_prosoluto(), timeout=1800.0)
        )
        if sucesso:
            print("\nOK: SNAPSHOT DE PRO-SOLUTO CONCLUIDO COM SUCESSO!")
            release_concurrency()
            sys.exit(0)
        else:
            print("\nERRO: FALHA NO SNAPSHOT DE PRO-SOLUTO")
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
