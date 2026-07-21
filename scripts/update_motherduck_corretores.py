#!/usr/bin/env python3
"""
Atualizacao Diaria do CV Corretores no MotherDuck
Executa a API de Corretores e atualiza a tabela reservas.cv_corretores
"""

import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from scripts.concurrency_control import check_concurrency, release_concurrency


async def sistema_corretores():
    """Sistema de atualizacao diaria de corretores do CV CRM"""
    print("SISTEMA DE ATUALIZACAO DIARIA - CV CORRETORES")
    print("=" * 60)
    print(f"Timestamp: {datetime.now()}")
    print("API: CV CRM Cadastros Corretores")

    start_time = datetime.now()

    try:
        from scripts.cv_corretores_api import obter_dados_cv_corretores
        import duckdb

        print("\n1. Coletando dados de corretores do CV CRM...")
        df = obter_dados_cv_corretores()

        if df.empty:
            print("AVISO: Nenhum dado coletado de corretores")
            return False

        print(f"OK: Corretores: {len(df)} registros")

        print("\n2. Fazendo upload para MotherDuck (banco reservas)...")

        duckdb.sql("INSTALL motherduck")
        duckdb.sql("LOAD motherduck")

        token = os.environ.get("MOTHERDUCK_TOKEN", "").strip()
        if not token:
            print("ERRO: MOTHERDUCK_TOKEN nao encontrado")
            return False

        duckdb.sql(f"SET motherduck_token='{token}'")
        conn = duckdb.connect("md:reservas")

        print("   - Fazendo upload completo cv_corretores...")
        conn.register("df_corretores", df)
        conn.execute(
            "CREATE OR REPLACE TABLE cv_corretores AS SELECT * FROM df_corretores"
        )

        count = conn.sql("SELECT COUNT(*) FROM cv_corretores").fetchone()[0]
        print(f"OK: cv_corretores upload: {count:,} registros")

        print("\n3. Verificando tabela criada...")
        try:
            colunas = conn.sql("DESCRIBE cv_corretores").fetchall()
            print(f"Colunas da tabela ({len(colunas)}):")
            for coluna in colunas:
                print(f"   - {coluna[0]} ({coluna[1]})")

            stats = conn.sql("""
                SELECT
                    COUNT(*) as total,
                    COUNT(DISTINCT idcorretor) as corretores,
                    COUNT(DISTINCT idimobiliaria) as imobiliarias,
                    SUM(CASE WHEN ativo_login = 'S' THEN 1 ELSE 0 END) as ativos
                FROM cv_corretores
            """).fetchone()
            print("\nEstatisticas:")
            print(f"   - Total de registros: {stats[0]:,}")
            print(f"   - Corretores distintos: {stats[1]:,}")
            print(f"   - Imobiliarias distintas: {stats[2]:,}")
            print(f"   - Ativos (ativo_login=S): {stats[3]:,}")
        except Exception as e:
            print(f"AVISO: Erro ao verificar tabela: {e}")

        conn.close()

        duration = datetime.now() - start_time
        print("\nATUALIZACAO CV CORRETORES CONCLUIDA!")
        print(f"Duracao: {duration}")
        print(f"   - Registros: {len(df):,}")
        print("   - Tabela: cv_corretores")
        print("   - Banco: reservas (MotherDuck)")
        return True

    except Exception as e:
        print(f"\nERRO na atualizacao de corretores: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def main():
    print("INICIANDO ATUALIZACAO DIARIA CV CORRETORES DO MOTHERDUCK")
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
        sucesso = asyncio.run(asyncio.wait_for(sistema_corretores(), timeout=1800.0))
        if sucesso:
            print("\nOK: ATUALIZACAO CV CORRETORES CONCLUIDA COM SUCESSO!")
            release_concurrency()
            sys.exit(0)
        else:
            print("\nERRO: FALHA NA ATUALIZACAO CV CORRETORES")
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
