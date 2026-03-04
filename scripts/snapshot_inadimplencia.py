#!/usr/bin/env python3
"""
Snapshot Mensal de Inadimplência
Calcula e persiste no MotherDuck (banco administracao) o estado histórico
de inadimplência no último dia de cada mês.

Lógica: uma parcela estava aberta no último dia do mês se:
  - Tipo_Baixa é NULL (ainda aberta hoje), OU
  - Data_Baixa existe e é depois da data de corte (foi paga após aquela data)

Roda no 1º dia de cada mês via GitHub Actions, capturando o fechamento
do mês anterior. Suporta backfill passando meses como argumentos.
"""

import asyncio
import os
import sys
from datetime import date, datetime
from dotenv import load_dotenv
from dateutil.relativedelta import relativedelta

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from scripts.concurrency_control import check_concurrency, release_concurrency


async def sistema_snapshot_inadimplencia(meses_arg=None):
    """Sistema de snapshot mensal de inadimplência"""
    print("SISTEMA DE SNAPSHOT MENSAL - INADIMPLÊNCIA")
    print("=" * 60)
    print(f"Timestamp: {datetime.now()}")

    start_time = datetime.now()

    try:
        import duckdb

        # Conectar ao MotherDuck
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

        # Criar tabela se não existir
        print("\n2. Verificando/criando tabela snapshot_inadimplencia_mensal...")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS snapshot_inadimplencia_mensal (
                data_snapshot     DATE    NOT NULL,
                mes_referencia    VARCHAR NOT NULL,
                data_corte        DATE    NOT NULL,
                cod_centro_custo  INTEGER,
                centro_custo      VARCHAR,
                cr_valor_devido   DOUBLE,
                valor_inadimplente DOUBLE,
                pct_inadimplencia DOUBLE,
                UNIQUE (mes_referencia, cod_centro_custo)
            )
        """)
        print("OK: Tabela verificada/criada")

        # Determinar meses a processar
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

            # Verificar se já foi processado
            count_existente = conn.execute(
                "SELECT COUNT(*) FROM snapshot_inadimplencia_mensal WHERE mes_referencia = ? AND cod_centro_custo IS NULL",
                [mes_ref]
            ).fetchone()[0]

            if count_existente > 0:
                print(f"  SKIP: {mes_ref} ja processado")
                continue

            print(f"\n  Calculando {mes_ref} (corte: {data_corte_str})...")

            cond_aberta = f"""(
                Tipo_Baixa IS NULL
                OR (Data_Baixa IS NOT NULL
                    AND TRY_CAST(Data_Baixa AS DATE) IS NOT NULL
                    AND TRY_CAST(Data_Baixa AS DATE) > '{data_corte_str}'::DATE)
            )"""

            # TOTAL
            conn.execute(f"""
                INSERT OR IGNORE INTO snapshot_inadimplencia_mensal
                SELECT
                    '{hoje}'::DATE    AS data_snapshot,
                    '{mes_ref}'       AS mes_referencia,
                    '{data_corte_str}'::DATE AS data_corte,
                    NULL::INTEGER     AS cod_centro_custo,
                    'TOTAL'           AS centro_custo,
                    SUM(CASE WHEN TRY_CAST(Data_Emissao AS DATE) <= '{data_corte_str}'::DATE AND {cond_aberta} THEN Valor_Corrigido ELSE 0 END) AS cr_valor_devido,
                    SUM(CASE WHEN TRY_CAST(Data_Vencimento AS DATE) <= '{data_corte_str}'::DATE AND TRY_CAST(Data_Emissao AS DATE) <= '{data_corte_str}'::DATE AND {cond_aberta} THEN Valor_Corrigido ELSE 0 END) AS valor_inadimplente,
                    CASE
                        WHEN SUM(CASE WHEN TRY_CAST(Data_Emissao AS DATE) <= '{data_corte_str}'::DATE AND {cond_aberta} THEN Valor_Corrigido ELSE 0 END) = 0 THEN 0
                        ELSE SUM(CASE WHEN TRY_CAST(Data_Vencimento AS DATE) <= '{data_corte_str}'::DATE AND TRY_CAST(Data_Emissao AS DATE) <= '{data_corte_str}'::DATE AND {cond_aberta} THEN Valor_Corrigido ELSE 0 END)
                           / SUM(CASE WHEN TRY_CAST(Data_Emissao AS DATE) <= '{data_corte_str}'::DATE AND {cond_aberta} THEN Valor_Corrigido ELSE 0 END)
                    END AS pct_inadimplencia
                FROM contas_recebidas_receber
                WHERE 1=1
            """)

            # Por Centro de Custo
            conn.execute(f"""
                INSERT OR IGNORE INTO snapshot_inadimplencia_mensal
                SELECT
                    '{hoje}'::DATE    AS data_snapshot,
                    '{mes_ref}'       AS mes_referencia,
                    '{data_corte_str}'::DATE AS data_corte,
                    Cod_Centro_Custo  AS cod_centro_custo,
                    Centro_Custo      AS centro_custo,
                    SUM(CASE WHEN TRY_CAST(Data_Emissao AS DATE) <= '{data_corte_str}'::DATE AND {cond_aberta} THEN Valor_Corrigido ELSE 0 END) AS cr_valor_devido,
                    SUM(CASE WHEN TRY_CAST(Data_Vencimento AS DATE) <= '{data_corte_str}'::DATE AND TRY_CAST(Data_Emissao AS DATE) <= '{data_corte_str}'::DATE AND {cond_aberta} THEN Valor_Corrigido ELSE 0 END) AS valor_inadimplente,
                    CASE
                        WHEN SUM(CASE WHEN TRY_CAST(Data_Emissao AS DATE) <= '{data_corte_str}'::DATE AND {cond_aberta} THEN Valor_Corrigido ELSE 0 END) = 0 THEN 0
                        ELSE SUM(CASE WHEN TRY_CAST(Data_Vencimento AS DATE) <= '{data_corte_str}'::DATE AND TRY_CAST(Data_Emissao AS DATE) <= '{data_corte_str}'::DATE AND {cond_aberta} THEN Valor_Corrigido ELSE 0 END)
                           / SUM(CASE WHEN TRY_CAST(Data_Emissao AS DATE) <= '{data_corte_str}'::DATE AND {cond_aberta} THEN Valor_Corrigido ELSE 0 END)
                    END AS pct_inadimplencia
                FROM contas_recebidas_receber
                WHERE Cod_Centro_Custo IS NOT NULL AND Centro_Custo IS NOT NULL
                GROUP BY Cod_Centro_Custo, Centro_Custo
            """)

            stats = conn.execute(
                "SELECT COUNT(*), SUM(cr_valor_devido), SUM(valor_inadimplente) FROM snapshot_inadimplencia_mensal WHERE mes_referencia = ?",
                [mes_ref]
            ).fetchone()
            pct = (stats[2] / stats[1] * 100) if stats[1] and stats[1] > 0 else 0
            print(f"  OK: {stats[0]} linhas | CR Devido: R$ {stats[1]:,.0f} | Inadimplente: R$ {stats[2]:,.0f} | %: {pct:.2f}%")
            total_inserido += stats[0]

        conn.close()
        duration = datetime.now() - start_time
        print(f"\nSNAPSHOT INADIMPLENCIA CONCLUIDO!")
        print(f"Duracao: {duration}")
        print(f"   - Total de linhas inseridas: {total_inserido}")
        print(f"   - Tabela: snapshot_inadimplencia_mensal")
        print(f"   - Banco: administracao (MotherDuck)")
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

    # Meses via argumento (backfill): python snapshot_inadimplencia.py 2025-10 2025-11
    meses_arg = sys.argv[1:] if len(sys.argv) > 1 else None

    try:
        sucesso = asyncio.run(
            asyncio.wait_for(sistema_snapshot_inadimplencia(meses_arg), timeout=1800.0)
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
