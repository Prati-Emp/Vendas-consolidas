#!/usr/bin/env python3
"""
Atualização diária do MotherDuck (Sienge Contratos Suprimentos + Pedidos Compras)
Executa apenas as APIs de contratos de suprimentos e pedidos de compra do Sienge.
"""

import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Garantir import do projeto quando rodar via Actions
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Importar controle de concorrência
from scripts.concurrency_control import check_concurrency, release_concurrency


async def sistema_sienge_diario_geral():
    """Executa a coleta e carga diária das APIs de contratos e pedidos do Sienge."""

    print("🌐 SISTEMA SIENGE DIÁRIO (CONTRATOS + PEDIDOS)")
    print("=" * 70)
    print(f"⏰ Timestamp: {datetime.now()}")
    print("🎯 APIs: Contratos de Suprimentos, Pedidos de Compra")

    start_time = datetime.now()

    try:
        from scripts.cv_sienge_contratos_suprimentos_api import (
            obter_dados_sienge_contratos_suprimentos,
        )
        from scripts.cv_sienge_pedidos_compras_api import (
            obter_dados_sienge_pedidos_compras,
        )
        import duckdb
        import pandas as pd

        # 1. Coletar contratos de suprimentos
        print("\n1. Coletando Sienge Contratos Suprimentos...")
        try:
            df_contratos = await obter_dados_sienge_contratos_suprimentos("2020-01-01")
            print(f"✅ Contratos: {len(df_contratos)} registros")
        except Exception as e:
            df_contratos = pd.DataFrame()
            print(f"❌ Falha ao coletar contratos de suprimentos: {e}")

        # 2. Coletar pedidos de compra
        print("\n2. Coletando Sienge Pedidos Compras...")
        try:
            df_pedidos = await obter_dados_sienge_pedidos_compras("2020-01-01")
            print(f"✅ Pedidos de compra: {len(df_pedidos)} registros")
        except Exception as e:
            df_pedidos = pd.DataFrame()
            print(f"❌ Falha ao coletar pedidos de compra: {e}")

        # 3. Upload para MotherDuck
        print("\n3. Fazendo upload para MotherDuck...")

        duckdb.sql("INSTALL motherduck")
        duckdb.sql("LOAD motherduck")

        token = os.environ.get("MOTHERDUCK_TOKEN", "").strip()
        if not token:
            print("❌ MOTHERDUCK_TOKEN não encontrado")
            return False

        duckdb.sql(f"SET motherduck_token='{token}'")
        conn = duckdb.connect("md:reservas")

        if not df_contratos.empty:
            conn.register("df_contratos", df_contratos)
            conn.execute(
                "CREATE OR REPLACE TABLE main.sienge_contratos_suprimentos AS SELECT * FROM df_contratos"
            )
            count_contratos = conn.sql(
                "SELECT COUNT(*) FROM main.sienge_contratos_suprimentos"
            ).fetchone()[0]
            print(f"✅ Upload contratos: {count_contratos:,} registros")

        if not df_pedidos.empty:
            conn.register("df_pedidos", df_pedidos)
            conn.execute(
                "CREATE OR REPLACE TABLE main.sienge_pedidos_compras AS SELECT * FROM df_pedidos"
            )
            count_pedidos = conn.sql(
                "SELECT COUNT(*) FROM main.sienge_pedidos_compras"
            ).fetchone()[0]
            print(f"✅ Upload pedidos: {count_pedidos:,} registros")

        conn.close()

        end_time = datetime.now()
        duration = end_time - start_time

        print("\n🎉 SIENGE DIÁRIO CONCLUÍDO!")
        print(f"⏱️ Duração: {duration}")
        print("📊 Resumo:")
        print(f"   - Contratos Suprimentos: {len(df_contratos):,} registros")
        print(f"   - Pedidos Compras: {len(df_pedidos):,} registros")

        return True

    except Exception as e:
        print(f"\n❌ Erro na atualização Sienge diária: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Função principal para execução via GitHub Actions."""

    print("🌐 INICIANDO ATUALIZAÇÃO SIENGE DIÁRIA (CONTRATOS + PEDIDOS)")
    print("=" * 70)
    print(f"⏰ Timestamp: {datetime.now()}")
    print(f"🐍 Python: {sys.version}")
    print(f"📁 Working directory: {os.getcwd()}")

    print("\n🔒 Verificando controle de concorrência...")
    if not check_concurrency():
        print("❌ Outro workflow está executando. Abortando para evitar conflitos.")
        sys.exit(1)
    print("✅ Controle de concorrência OK - prosseguindo")

    load_dotenv()

    required_vars = ["MOTHERDUCK_TOKEN", "SIENGE_TOKEN"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]

    if missing_vars:
        print(f"❌ Variáveis de ambiente faltando: {', '.join(missing_vars)}")
        release_concurrency()
        sys.exit(1)

    print("✅ Variáveis de ambiente configuradas")

    try:
        sucesso = asyncio.run(asyncio.wait_for(sistema_sienge_diario_geral(), timeout=900.0))

        if sucesso:
            print("\n✅ Atualização Sienge diária concluída com sucesso!")
            release_concurrency()
            sys.exit(0)
        else:
            print("\n❌ Falha na atualização Sienge diária")
            release_concurrency()
            sys.exit(1)

    except asyncio.TimeoutError:
        print("\n⏰ TIMEOUT - Operação demorou mais de 15 minutos")
        release_concurrency()
        sys.exit(1)

    except ImportError as e:
        print(f"\n❌ ERRO DE IMPORTAÇÃO: {e}")
        release_concurrency()
        sys.exit(1)

    except Exception as e:
        print(f"\n❌ ERRO INESPERADO: {e}")
        import traceback

        traceback.print_exc()
        release_concurrency()
        sys.exit(1)


if __name__ == "__main__":
    main()

