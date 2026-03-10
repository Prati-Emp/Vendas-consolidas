#!/usr/bin/env python3
"""
Snapshot Mensal de Inadimplência
Roda todo dia 10 do mês. Captura o estado atual (sem data de corte),
replicando a lógica das medidas padrão do Power BI:
  - cr_valor_devido = parcelas abertas clientes (exclui CP, MC, FI, FG)
  - cr_valor_devido_caixa = parcelas abertas caixa (apenas CP, MC, FI, FG)
  - cr_valor_devido_clientes_e_caixa = cr_valor_devido + cr_valor_devido_caixa
  - Valor_Inadimplente = parcelas clientes vencidas (Data_Vencimento <= hoje)
  - % Inadimplência = Valor_Inadimplente / cr_valor_devido
A foto é datada com o dia em que rodou (data_snapshot) e mes_referencia = fechamento do mês anterior.
"""

import asyncio

# Clientes: exclui CP, MC, FI, FG
FILTRO_TIPO_CONDICAO = "(Tipo_Condicao IS NULL OR TRIM(Tipo_Condicao) NOT IN ('CP','MC','FI','FG'))"
# Caixa: apenas CP, MC, FI, FG
FILTRO_TIPO_CONDICAO_CAIXA = "TRIM(Tipo_Condicao) IN ('CP','MC','FI','FG')"
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
                cr_valor_devido_caixa DOUBLE,
                cr_valor_devido_clientes_e_caixa DOUBLE,
                valor_inadimplente DOUBLE,
                pct_inadimplencia  DOUBLE,
                UNIQUE (mes_referencia, cod_centro_custo)
            )
        """)
        # Adicionar colunas se tabela existia com schema antigo
        for col in ["cr_valor_devido_caixa", "cr_valor_devido_clientes_e_caixa"]:
            try:
                conn.execute(f"ALTER TABLE snapshot_inadimplencia_mensal_ ADD COLUMN {col} DOUBLE")
                print(f"   Coluna {col} adicionada")
            except Exception:
                pass
        print("OK: Tabela verificada/criada")

        hoje = date.today()
        hoje_str = hoje.strftime("%Y-%m-%d")
        mes_anterior = hoje.replace(day=1) - relativedelta(months=1)
        mes_ref = mes_anterior.strftime("%Y-%m")

        # Data de corte para inadimplência alinhada à medida Valor_Inadimplente_Novo no Power BI:
        # consideramos inadimplente tudo que venceu ANTES do primeiro dia do mês seguinte ao mes_referencia.
        # Ex.: mes_ref = 2026-02 -> data_corte_inadimplente = 2026-03-01.
        primeiro_dia_mes_seguinte = (mes_anterior + relativedelta(months=1)).replace(day=1)
        data_corte_inadimplente_str = primeiro_dia_mes_seguinte.strftime("%Y-%m-%d")

        # Substitui apenas o mes_referencia atual; demais meses (historico) nao sao alterados.
        # Assim pode rodar de novo no mesmo dia 10 para corrigir/atualizar sem perder historico.
        deleted = conn.execute(
            "DELETE FROM snapshot_inadimplencia_mensal_ WHERE mes_referencia = ?",
            [mes_ref]
        )
        print(f"\n   Substituindo apenas mes_referencia = {mes_ref} (historico dos demais meses preservado).")

        print(f"\n3. Calculando fechamento de {mes_ref} (data snapshot: {hoje_str})...")

        # Regra de inadimplência:
        # - Parcelas abertas: Tipo_Baixa IS NULL
        # - Data_Vencimento < primeiro dia do mês seguinte ao mes_referencia (data_corte_inadimplente_str)
        # - Mesmo filtro de Tipo_Condicao utilizado nas medidas de CR/Inadimplência do Power BI
        cond_inad = (
            "Tipo_Baixa IS NULL AND "
            f"TRY_CAST(Data_Vencimento AS DATE) < '{data_corte_inadimplente_str}'::DATE"
        )

        # TOTAL
        conn.execute(f"""
            INSERT INTO snapshot_inadimplencia_mensal_
            (data_snapshot, mes_referencia, cod_centro_custo, centro_custo, cr_valor_devido, cr_valor_devido_caixa, cr_valor_devido_clientes_e_caixa, valor_inadimplente, pct_inadimplencia)
            WITH base AS (
                SELECT
                    SUM(CASE WHEN Tipo_Baixa IS NULL AND ({FILTRO_TIPO_CONDICAO}) THEN Valor_Corrigido ELSE 0 END) AS cr_clientes,
                    SUM(CASE WHEN Tipo_Baixa IS NULL AND ({FILTRO_TIPO_CONDICAO_CAIXA}) THEN Valor_Corrigido ELSE 0 END) AS cr_caixa,
                    SUM(CASE WHEN {cond_inad} AND ({FILTRO_TIPO_CONDICAO}) THEN Valor_Corrigido ELSE 0 END) AS inad_clientes
                FROM contas_recebidas_receber
            )
            SELECT
                '{hoje_str}'::DATE  AS data_snapshot,
                '{mes_ref}'         AS mes_referencia,
                NULL::INTEGER       AS cod_centro_custo,
                'Geral Prati'       AS centro_custo,
                cr_clientes         AS cr_valor_devido,
                cr_caixa            AS cr_valor_devido_caixa,
                cr_clientes + cr_caixa AS cr_valor_devido_clientes_e_caixa,
                inad_clientes       AS valor_inadimplente,
                CASE WHEN cr_clientes = 0 THEN 0 ELSE inad_clientes / cr_clientes END AS pct_inadimplencia
            FROM base
        """)

        # Por Centro de Custo
        conn.execute(f"""
            INSERT INTO snapshot_inadimplencia_mensal_
            (data_snapshot, mes_referencia, cod_centro_custo, centro_custo, cr_valor_devido, cr_valor_devido_caixa, cr_valor_devido_clientes_e_caixa, valor_inadimplente, pct_inadimplencia)
            SELECT
                '{hoje_str}'::DATE  AS data_snapshot,
                '{mes_ref}'         AS mes_referencia,
                Cod_Centro_Custo    AS cod_centro_custo,
                Centro_Custo        AS centro_custo,
                SUM(CASE WHEN Tipo_Baixa IS NULL AND ({FILTRO_TIPO_CONDICAO}) THEN Valor_Corrigido ELSE 0 END)
                    AS cr_valor_devido,
                SUM(CASE WHEN Tipo_Baixa IS NULL AND ({FILTRO_TIPO_CONDICAO_CAIXA}) THEN Valor_Corrigido ELSE 0 END)
                    AS cr_valor_devido_caixa,
                SUM(CASE WHEN Tipo_Baixa IS NULL AND ({FILTRO_TIPO_CONDICAO}) THEN Valor_Corrigido ELSE 0 END)
                  + SUM(CASE WHEN Tipo_Baixa IS NULL AND ({FILTRO_TIPO_CONDICAO_CAIXA}) THEN Valor_Corrigido ELSE 0 END)
                    AS cr_valor_devido_clientes_e_caixa,
                SUM(CASE WHEN {cond_inad} AND ({FILTRO_TIPO_CONDICAO}) THEN Valor_Corrigido ELSE 0 END)
                    AS valor_inadimplente,
                CASE
                    WHEN SUM(CASE WHEN Tipo_Baixa IS NULL AND ({FILTRO_TIPO_CONDICAO}) THEN Valor_Corrigido ELSE 0 END) = 0 THEN 0
                    ELSE SUM(CASE WHEN {cond_inad} AND ({FILTRO_TIPO_CONDICAO}) THEN Valor_Corrigido ELSE 0 END)
                       / SUM(CASE WHEN Tipo_Baixa IS NULL AND ({FILTRO_TIPO_CONDICAO}) THEN Valor_Corrigido ELSE 0 END)
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
