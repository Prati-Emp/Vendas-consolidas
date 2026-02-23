#!/usr/bin/env python3
"""
Atualização Mensal do Sienge Stock Inventories no MotherDuck
Executa a API de Stock Inventories (estoque por empreendimento) e atualiza a tabela
operacoes.sienge_stock_inventories.
Executa uma vez por mês no dia 5: Data_Snapshot = último dia do mês anterior (atualização incremental).
"""

import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Garante import do projeto quando rodar via Actions
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from scripts.concurrency_control import check_concurrency, release_concurrency


async def sistema_stock_inventories():
    """Sistema de atualização mensal de stock inventories do Sienge"""
    print("SISTEMA DE ATUALIZACAO MENSUAL - SIENGE STOCK INVENTORIES")
    print("=" * 60)
    print(f"Timestamp: {datetime.now()}")
    print(f"API: Sienge Stock Inventories (estoque por empreendimento)")

    start_time = datetime.now()

    try:
        from scripts.cv_sienge_stock_inventories_api import obter_dados_sienge_stock_inventories
        import duckdb
        import pandas as pd

        # 1. Coletar dados de estoque
        print("\n1. Coletando dados de stock inventories do Sienge...")
        print("   - Data_Snapshot: último dia do mês anterior")
        df = obter_dados_sienge_stock_inventories()

        if df.empty:
            print("AVISO: Nenhum dado coletado de stock inventories")
            return False

        print(f"OK: Stock Inventories: {len(df)} registros")

        # 2. Upload para MotherDuck (banco operacoes)
        print("\n2. Fazendo upload para MotherDuck (banco operacoes)...")

        duckdb.sql("INSTALL motherduck")
        duckdb.sql("LOAD motherduck")

        token = os.environ.get("MOTHERDUCK_TOKEN", "").strip()
        if not token:
            print("ERRO: MOTHERDUCK_TOKEN nao encontrado")
            return False

        duckdb.sql(f"SET motherduck_token='{token}'")
        conn = duckdb.connect("md:operacoes")

        conn.register("df_stock", df)

        tabela_existe = False
        try:
            conn.sql("SELECT 1 FROM sienge_stock_inventories LIMIT 1").fetchone()
            tabela_existe = True
            print("   - Tabela já existe, fazendo atualização incremental...")
        except Exception:
            print("   - Tabela não existe, criando nova tabela...")

        if tabela_existe:
            if "Data_Snapshot" in df.columns:
                datas_novas = df["Data_Snapshot"].unique()
                datas_formatadas = []
                for d in datas_novas:
                    if hasattr(d, "strftime"):
                        datas_formatadas.append(d.strftime("%Y-%m-%d"))
                    elif isinstance(d, str):
                        datas_formatadas.append(d[:10])
                    else:
                        try:
                            dt = pd.to_datetime(d)
                            datas_formatadas.append(dt.strftime("%Y-%m-%d"))
                        except Exception:
                            continue

                if datas_formatadas:
                    datas_str = "', '".join(datas_formatadas)
                    count_antes = conn.sql(
                        "SELECT COUNT(*) FROM sienge_stock_inventories"
                    ).fetchone()[0]
                    print(
                        f"   - Removendo registros existentes para as datas: {', '.join(datas_formatadas)}"
                    )
                    conn.execute(f"""
                        DELETE FROM sienge_stock_inventories
                        WHERE DATE(Data_Snapshot) IN ('{datas_str}')
                    """)
                    count_depois = conn.sql(
                        "SELECT COUNT(*) FROM sienge_stock_inventories"
                    ).fetchone()[0]
                    print(f"   - Registros removidos: {count_antes - count_depois}")

            print("   - Inserindo novos registros...")
            conn.execute("INSERT INTO sienge_stock_inventories SELECT * FROM df_stock")
        else:
            conn.execute(
                "CREATE TABLE sienge_stock_inventories AS SELECT * FROM df_stock"
            )

        count_final = conn.sql(
            "SELECT COUNT(*) FROM sienge_stock_inventories"
        ).fetchone()[0]
        print(f"OK: Sienge Stock Inventories: {count_final:,} registros totais na tabela")

        # 3. Verificação
        print("\n3. Verificando tabela...")
        try:
            colunas = conn.sql("DESCRIBE sienge_stock_inventories").fetchall()
            print(f"Colunas da tabela ({len(colunas)}):")
            for coluna in colunas[:12]:
                print(f"   - {coluna[0]} ({coluna[1]})")
            if len(colunas) > 12:
                print(f"   ... e mais {len(colunas) - 12} colunas")

            if "Data_Snapshot" in df.columns:
                stats = conn.sql("""
                    SELECT
                        COUNT(*) as total,
                        COUNT(DISTINCT ID_Empreendimento) as empreendimentos,
                        MIN(Data_Snapshot) as data_mais_antiga,
                        MAX(Data_Snapshot) as data_mais_recente
                    FROM sienge_stock_inventories
                """).fetchone()
                print(f"\nEstatisticas:")
                print(f"   - Total de registros: {stats[0]:,}")
                print(f"   - Empreendimentos: {stats[1]:,}")
                print(f"   - Data mais antiga: {stats[2]}")
                print(f"   - Data mais recente: {stats[3]}")
        except Exception as e:
            print(f"AVISO: Erro ao verificar tabela: {e}")

        conn.close()

        duration = datetime.now() - start_time
        print(f"\nATUALIZACAO STOCK INVENTORIES CONCLUIDA!")
        print(f"Duracao: {duration}")
        print(f"   - Registros enviados: {len(df):,}")
        print(f"   - Tabela: sienge_stock_inventories")
        print(f"   - Banco: operacoes (MotherDuck)")
        return True

    except Exception as e:
        print(f"\nERRO na atualizacao de stock inventories: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("INICIANDO ATUALIZACAO MENSUAL DE STOCK INVENTORIES DO MOTHERDUCK")
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
    required_vars = ["MOTHERDUCK_TOKEN", "SIENGE_TOKEN"]
    missing_vars = [v for v in required_vars if not os.environ.get(v)]
    if missing_vars:
        print(f"ERRO: Variaveis faltando: {', '.join(missing_vars)}")
        release_concurrency()
        sys.exit(1)
    print("OK: Variaveis de ambiente configuradas")

    try:
        sucesso = asyncio.run(
            asyncio.wait_for(sistema_stock_inventories(), timeout=1800.0)
        )
        if sucesso:
            print("\nOK: ATUALIZACAO DE STOCK INVENTORIES CONCLUIDA COM SUCESSO!")
            release_concurrency()
            sys.exit(0)
        else:
            print("\nERRO: FALHA NA ATUALIZACAO DE STOCK INVENTORIES")
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
