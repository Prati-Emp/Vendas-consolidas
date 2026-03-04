#!/usr/bin/env python3
"""
Snapshot Mensal de Pró-Soluto
Calcula e persiste no MotherDuck (banco administracao) o estado histórico
de pró-soluto no último dia de cada mês.

Numerador  = parcelas abertas no último dia do mês,
             Tipo_Condicao IN ('12','PM','AT','PB','PA','PI','PQ','PS'),
             vinculadas a cv_vendas com tipovenda = 'Venda Financiamento'.
Denominador = contratos cv_vendas tipovenda = 'Venda Financiamento'
              com data_venda <= último dia do mês.

Roda no 1º dia de cada mês via GitHub Actions.
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


async def sistema_snapshot_prosoluto(meses_arg=None):
    """Sistema de snapshot mensal de pró-soluto"""
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

        print("\n2. Verificando/criando tabela snapshot_prosoluto_mensal...")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS snapshot_prosoluto_mensal (
                data_snapshot                DATE    NOT NULL,
                mes_referencia               VARCHAR NOT NULL,
                data_corte                   DATE    NOT NULL,
                idempreendimento             BIGINT,
                empreendimento               VARCHAR,
                codigointerno_empreendimento VARCHAR,
                valor_prosoluto              DOUBLE,
                valor_venda_financiamento    DOUBLE,
                pct_prosoluto                DOUBLE,
                UNIQUE (mes_referencia, idempreendimento)
            )
        """)
        print("OK: Tabela verificada/criada")

        if meses_arg:
            meses_para_processar = meses_arg
        else:
            primeiro_dia_mes_atual = date.today().replace(day=1)
            mes_anterior = primeiro_dia_mes_atual - relativedelta(months=1)
            meses_para_processar = [mes_anterior.strftime("%Y-%m")]

        print(f"\n3. Processando meses: {', '.join(meses_para_processar)}")

        total_inserido = 0
        for mes_ref in meses_para_processar:
            ano, mes = int(mes_ref.split("-")[0]), int(mes_ref.split("-")[1])
            primeiro_dia_proximo = date(ano, mes, 1) + relativedelta(months=1)
            data_corte = primeiro_dia_proximo - relativedelta(days=1)
            data_corte_str = data_corte.strftime("%Y-%m-%d")
            hoje = date.today().strftime("%Y-%m-%d")

            count_existente = conn.execute(
                "SELECT COUNT(*) FROM snapshot_prosoluto_mensal WHERE mes_referencia = ? AND idempreendimento IS NULL",
                [mes_ref]
            ).fetchone()[0]

            if count_existente > 0:
                print(f"  SKIP: {mes_ref} ja processado")
                continue

            print(f"\n  Calculando {mes_ref} (corte: {data_corte_str})...")

            cond_aberta_cr = f"""(
                cr.Tipo_Baixa IS NULL
                OR (cr.Data_Baixa IS NOT NULL
                    AND TRY_CAST(cr.Data_Baixa AS DATE) IS NOT NULL
                    AND TRY_CAST(cr.Data_Baixa AS DATE) > '{data_corte_str}'::DATE)
            )"""

            # TOTAL
            conn.execute(f"""
                INSERT OR IGNORE INTO snapshot_prosoluto_mensal
                WITH parcelas AS (
                    SELECT cr.Valor_Devido
                    FROM contas_recebidas_receber cr
                    WHERE TRY_CAST(cr.Data_Emissao AS DATE) <= '{data_corte_str}'::DATE
                      AND cr.Tipo_Condicao IN ({TIPOS_PROSOLUTO})
                      AND {cond_aberta_cr}
                      AND EXISTS (
                          SELECT 1 FROM cv_vendas v
                          WHERE v.tipovenda = 'Venda Financiamento'
                            AND v.contrato_interno = cr.N_Documento
                      )
                ),
                denom AS (
                    SELECT SUM(valor_contrato) AS total
                    FROM cv_vendas
                    WHERE tipovenda = 'Venda Financiamento'
                      AND TRY_CAST(data_venda AS DATE) <= '{data_corte_str}'::DATE
                )
                SELECT
                    '{hoje}'::DATE           AS data_snapshot,
                    '{mes_ref}'              AS mes_referencia,
                    '{data_corte_str}'::DATE AS data_corte,
                    NULL::BIGINT             AS idempreendimento,
                    'TOTAL'                  AS empreendimento,
                    NULL                     AS codigointerno_empreendimento,
                    (SELECT SUM(Valor_Devido) FROM parcelas) AS valor_prosoluto,
                    (SELECT total FROM denom)                AS valor_venda_financiamento,
                    CASE
                        WHEN (SELECT total FROM denom) IS NULL OR (SELECT total FROM denom) = 0 THEN 0
                        ELSE (SELECT SUM(Valor_Devido) FROM parcelas) / (SELECT total FROM denom)
                    END AS pct_prosoluto
            """)

            # Por Empreendimento
            conn.execute(f"""
                INSERT OR IGNORE INTO snapshot_prosoluto_mensal
                WITH parcelas_emp AS (
                    SELECT v.idempreendimento, v.empreendimento, v.codigointerno_empreendimento,
                           SUM(cr.Valor_Devido) AS valor_prosoluto
                    FROM contas_recebidas_receber cr
                    INNER JOIN cv_vendas v
                        ON v.tipovenda = 'Venda Financiamento'
                       AND v.contrato_interno = cr.N_Documento
                    WHERE TRY_CAST(cr.Data_Emissao AS DATE) <= '{data_corte_str}'::DATE
                      AND cr.Tipo_Condicao IN ({TIPOS_PROSOLUTO})
                      AND {cond_aberta_cr}
                    GROUP BY v.idempreendimento, v.empreendimento, v.codigointerno_empreendimento
                ),
                denom_emp AS (
                    SELECT idempreendimento, empreendimento, codigointerno_empreendimento,
                           SUM(valor_contrato) AS total
                    FROM cv_vendas
                    WHERE tipovenda = 'Venda Financiamento'
                      AND TRY_CAST(data_venda AS DATE) <= '{data_corte_str}'::DATE
                    GROUP BY idempreendimento, empreendimento, codigointerno_empreendimento
                )
                SELECT
                    '{hoje}'::DATE           AS data_snapshot,
                    '{mes_ref}'              AS mes_referencia,
                    '{data_corte_str}'::DATE AS data_corte,
                    d.idempreendimento,
                    d.empreendimento,
                    d.codigointerno_empreendimento,
                    COALESCE(p.valor_prosoluto, 0) AS valor_prosoluto,
                    d.total                        AS valor_venda_financiamento,
                    CASE WHEN d.total IS NULL OR d.total = 0 THEN 0
                         ELSE COALESCE(p.valor_prosoluto, 0) / d.total
                    END AS pct_prosoluto
                FROM denom_emp d
                LEFT JOIN parcelas_emp p ON d.idempreendimento = p.idempreendimento
            """)

            stats = conn.execute(
                "SELECT COUNT(*), SUM(valor_prosoluto), SUM(valor_venda_financiamento) FROM snapshot_prosoluto_mensal WHERE mes_referencia = ?",
                [mes_ref]
            ).fetchone()
            pct = (stats[1] / stats[2] * 100) if stats[2] and stats[2] > 0 else 0
            print(f"  OK: {stats[0]} linhas | Pro-Soluto: R$ {stats[1]:,.0f} | Venda Fin: R$ {stats[2]:,.0f} | %: {pct:.2f}%")
            total_inserido += stats[0]

        conn.close()
        duration = datetime.now() - start_time
        print(f"\nSNAPSHOT PRO-SOLUTO CONCLUIDO!")
        print(f"Duracao: {duration}")
        print(f"   - Total de linhas inseridas: {total_inserido}")
        print(f"   - Tabela: snapshot_prosoluto_mensal")
        print(f"   - Banco: administracao (MotherDuck)")
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

    meses_arg = sys.argv[1:] if len(sys.argv) > 1 else None

    try:
        sucesso = asyncio.run(
            asyncio.wait_for(sistema_snapshot_prosoluto(meses_arg), timeout=1800.0)
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
