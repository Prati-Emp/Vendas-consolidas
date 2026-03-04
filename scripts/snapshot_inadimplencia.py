#!/usr/bin/env python3
"""
Snapshot Mensal de Inadimplência
Roda todo dia 10 do mês. Captura o estado atual (sem data de corte),
replicando a lógica das medidas padrão do Power BI:
  - CR_Valor_Devido  = parcelas abertas (Tipo_Baixa IS NULL)
  - Valor_Inadimplente = parcelas abertas com Data_Vencimento <= hoje
  - % Inadimplência = Valor_Inadimplente / CR_Valor_Devido
A foto é datada com o dia em que rodou (data_snapshot) e mes_referencia = fechamento do mês anterior.
"""

import asyncio
import os
import sys
from datetime import date, datetime
from dotenv import load_dotenv
from dateutil.relativedelta import relativedelta

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from scripts.concurrency_control import check_concurrency, release_concurrency


async def sistema_snapshot_inadimplencia():
    print("SISTEMA DE SNAPSHOT MENSAL - INADIMPLENCIA")
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

        print("\n2. Verificando/criando tabela snapshot_inadimplencia_mensal_...")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS snapshot_inadimplencia_mensal_ (
                data_snapshot      DATE    NOT NULL,
                mes_referencia     VARCHAR NOT NULL,
                cod_centro_custo   INTEGER,
                centro_custo       VARCHAR,
                cr_valor_devido    DOUBLE,
                valor_inadimplente DOUBLE,
                pct_inadimplencia  DOUBLE,
                UNIQUE (mes_referencia, cod_centro_custo)
            )
        """)
        print("OK: Tabela verificada/criada")

        hoje = date.today()
        hoje_str = hoje.strftime("%Y-%m-%d")
        mes_anterior = hoje.replace(day=1) - relativedelta(months=1)
        mes_ref = mes_anterior.strftime("%Y-%m")

        # Remove dados existentes do mes_referencia (substitui no dia 10; historico de meses anteriores preservado)
        conn.execute(
            "DELETE FROM snapshot_inadimplencia_mensal_ WHERE mes_referencia = ?",
            [mes_ref]
        )

        print(f"\n3. Calculando fechamento de {mes_ref} (data snapshot: {hoje_str})...")

        cond_inad = "Tipo_Baixa IS NULL AND TRY_CAST(Data_Vencimento AS DATE) <= '{0}'::DATE".format(hoje_str)

        # TOTAL
        conn.execute(f"""
            INSERT INTO snapshot_inadimplencia_mensal_
            (data_snapshot, mes_referencia, cod_centro_custo, centro_custo, cr_valor_devido, valor_inadimplente, pct_inadimplencia)
            SELECT
                '{hoje_str}'::DATE  AS data_snapshot,
                '{mes_ref}'         AS mes_referencia,
                NULL::INTEGER       AS cod_centro_custo,
                'Geral Prati'       AS centro_custo,
                SUM(CASE WHEN Tipo_Baixa IS NULL THEN Valor_Corrigido ELSE 0 END)
                    AS cr_valor_devido,
                SUM(CASE WHEN {cond_inad} THEN Valor_Corrigido ELSE 0 END)
                    AS valor_inadimplente,
                CASE
                    WHEN SUM(CASE WHEN Tipo_Baixa IS NULL THEN Valor_Corrigido ELSE 0 END) = 0 THEN 0
                    ELSE SUM(CASE WHEN {cond_inad} THEN Valor_Corrigido ELSE 0 END)
                       / SUM(CASE WHEN Tipo_Baixa IS NULL THEN Valor_Corrigido ELSE 0 END)
                END AS pct_inadimplencia
            FROM contas_recebidas_receber
        """)

        # Por Centro de Custo
        conn.execute(f"""
            INSERT INTO snapshot_inadimplencia_mensal_
            (data_snapshot, mes_referencia, cod_centro_custo, centro_custo, cr_valor_devido, valor_inadimplente, pct_inadimplencia)
            SELECT
                '{hoje_str}'::DATE  AS data_snapshot,
                '{mes_ref}'         AS mes_referencia,
                Cod_Centro_Custo    AS cod_centro_custo,
                Centro_Custo        AS centro_custo,
                SUM(CASE WHEN Tipo_Baixa IS NULL THEN Valor_Corrigido ELSE 0 END)
                    AS cr_valor_devido,
                SUM(CASE WHEN {cond_inad} THEN Valor_Corrigido ELSE 0 END)
                    AS valor_inadimplente,
                CASE
                    WHEN SUM(CASE WHEN Tipo_Baixa IS NULL THEN Valor_Corrigido ELSE 0 END) = 0 THEN 0
                    ELSE SUM(CASE WHEN {cond_inad} THEN Valor_Corrigido ELSE 0 END)
                       / SUM(CASE WHEN Tipo_Baixa IS NULL THEN Valor_Corrigido ELSE 0 END)
                END AS pct_inadimplencia
            FROM contas_recebidas_receber
            WHERE Cod_Centro_Custo IS NOT NULL AND Centro_Custo IS NOT NULL
            GROUP BY Cod_Centro_Custo, Centro_Custo
        """)

        stats = conn.execute(
            "SELECT COUNT(*), SUM(cr_valor_devido), SUM(valor_inadimplente) FROM snapshot_inadimplencia_mensal_ WHERE mes_referencia = ?",
            [mes_ref]
        ).fetchone()
        pct = (stats[1] / stats[2] * 100) if stats[2] and stats[2] > 0 else 0
        print(f"  OK: {stats[0]} linhas inseridas")

        total_row = conn.execute(
            "SELECT cr_valor_devido, valor_inadimplente, pct_inadimplencia FROM snapshot_inadimplencia_mensal_ WHERE mes_referencia = ? AND cod_centro_custo IS NULL",
            [mes_ref]
        ).fetchone()
        if total_row:
            cr = total_row[0] if total_row[0] is not None else 0
            inad = total_row[1] if total_row[1] is not None else 0
            pct = (total_row[2] * 100) if total_row[2] is not None else 0
            print(f"  TOTAL: CR Devido = R$ {cr:,.2f} | Inadimplente = R$ {inad:,.2f} | % = {pct:.2f}%")

        conn.close()
        duration = datetime.now() - start_time
        print(f"\nSNAPSHOT INADIMPLENCIA CONCLUIDO em {duration}")
        print(f"   Tabela: snapshot_inadimplencia_mensal_ | Banco: administracao (MotherDuck)")
        return True

    except Exception as e:
        print(f"\nERRO no snapshot de inadimplencia: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("INICIANDO SNAPSHOT MENSAL DE INADIMPLENCIA")
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
            asyncio.wait_for(sistema_snapshot_inadimplencia(), timeout=1800.0)
        )
        if sucesso:
            print("\nOK: SNAPSHOT DE INADIMPLENCIA CONCLUIDO COM SUCESSO!")
            release_concurrency()
            sys.exit(0)
        else:
            print("\nERRO: FALHA NO SNAPSHOT DE INADIMPLENCIA")
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
