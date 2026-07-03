#!/usr/bin/env python3
"""
Atualização Diária do CV Times x Imobiliárias no MotherDuck
Executa a API de Gestão de Times e atualiza a tabela reservas.cv_times_imobiliarias
"""

import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from scripts.concurrency_control import check_concurrency, release_concurrency


async def sistema_times_imobiliarias():
    """Sistema de atualização diária de times x imobiliárias do CV CRM"""
    print("SISTEMA DE ATUALIZACAO DIARIA - CV TIMES IMOBILIARIAS")
    print("=" * 60)
    print(f"Timestamp: {datetime.now()}")
    print("API: CV CRM Gestão de Times x Imobiliárias")

    start_time = datetime.now()

    try:
        from scripts.cv_times_imobiliarias_api import obter_dados_cv_times_imobiliarias
        import duckdb

        print("\n1. Coletando dados de times x imobiliárias do CV CRM...")
        df = obter_dados_cv_times_imobiliarias()

        if df.empty:
            print("AVISO: Nenhum dado coletado de times/imobiliárias")
            return False

        print(f"OK: Times x Imobiliárias: {len(df)} registros")

        print("\n2. Fazendo upload para MotherDuck (banco reservas)...")

        duckdb.sql("INSTALL motherduck")
        duckdb.sql("LOAD motherduck")

        token = os.environ.get("MOTHERDUCK_TOKEN", "").strip()
        if not token:
            print("ERRO: MOTHERDUCK_TOKEN nao encontrado")
            return False

        duckdb.sql(f"SET motherduck_token='{token}'")
        conn = duckdb.connect("md:reservas")

        print("   - Fazendo upload completo cv_times_imobiliarias...")
        conn.register("df_times_imob", df)
        conn.execute(
            "CREATE OR REPLACE TABLE cv_times_imobiliarias AS SELECT * FROM df_times_imob"
        )

        count = conn.sql("SELECT COUNT(*) FROM cv_times_imobiliarias").fetchone()[0]
        print(f"OK: cv_times_imobiliarias upload: {count:,} registros")

        print("\n3. Verificando tabela criada...")
        try:
            colunas = conn.sql("DESCRIBE cv_times_imobiliarias").fetchall()
            print(f"Colunas da tabela ({len(colunas)}):")
            for coluna in colunas:
                print(f"   - {coluna[0]} ({coluna[1]})")

            stats = conn.sql("""
                SELECT
                    COUNT(*) as total,
                    COUNT(DISTINCT idtime) as times,
                    COUNT(DISTINCT idimobiliaria) as imobiliarias
                FROM cv_times_imobiliarias
            """).fetchone()
            print("\nEstatisticas:")
            print(f"   - Total de registros: {stats[0]:,}")
            print(f"   - Times distintos: {stats[1]:,}")
            print(f"   - Imobiliárias distintas: {stats[2]:,}")
        except Exception as e:
            print(f"AVISO: Erro ao verificar tabela: {e}")

        conn.close()

        duration = datetime.now() - start_time
        print(f"\nATUALIZACAO CV TIMES IMOBILIARIAS CONCLUIDA!")
        print(f"Duracao: {duration}")
        print(f"   - Registros: {len(df):,}")
        print("   - Tabela: cv_times_imobiliarias")
        print("   - Banco: reservas (MotherDuck)")
        return True

    except Exception as e:
        print(f"\nERRO na atualizacao de times/imobiliarias: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def main():
    print("INICIANDO ATUALIZACAO DIARIA CV TIMES IMOBILIARIAS DO MOTHERDUCK")
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
    required_vars = ["MOTHERDUCK_TOKEN", "CVCRM_EMAIL", "CVCRM_TOKEN"]
    missing_vars = [v for v in required_vars if not os.environ.get(v)]
    if missing_vars:
        print(f"ERRO: Variaveis faltando: {', '.join(missing_vars)}")
        release_concurrency()
        sys.exit(1)

    print("OK: Variaveis de ambiente configuradas")

    try:
        sucesso = asyncio.run(
            asyncio.wait_for(sistema_times_imobiliarias(), timeout=1800.0)
        )
        if sucesso:
            print("\nOK: ATUALIZACAO CV TIMES IMOBILIARIAS CONCLUIDA COM SUCESSO!")
            release_concurrency()
            sys.exit(0)
        else:
            print("\nERRO: FALHA NA ATUALIZACAO CV TIMES IMOBILIARIAS")
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
