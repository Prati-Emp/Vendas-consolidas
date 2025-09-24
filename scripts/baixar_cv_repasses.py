#!/usr/bin/env python3
"""
Utilitário para baixar a tabela `main.cv_repasses` do MotherDuck.

Funcionalidades:
 1. Conectar ao banco MotherDuck usando `MOTHERDUCK_TOKEN`.
 2. Validar se a tabela existe e exibir contagem de registros.
 3. Exportar todos os dados para CSV (nome com timestamp) na pasta `exports/`.

Uso (PowerShell):
  python -u scripts\baixar_cv_repasses.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime

import duckdb
import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))


def configurar_ambiente() -> bool:
    load_dotenv(override=True)
    token = os.environ.get('MOTHERDUCK_TOKEN', '').strip().strip('"').strip("'")
    if not token:
        print("❌ MOTHERDUCK_TOKEN não encontrado")
        return False
    os.environ['motherduck_token'] = token
    return True


def conectar() -> duckdb.DuckDBPyConnection:
    try:
        duckdb.sql("INSTALL motherduck")
        duckdb.sql("LOAD motherduck")
        conn = duckdb.connect('md:reservas')
        print("✅ Conectado ao MotherDuck")
        return conn
    except Exception as e:
        raise RuntimeError(f"Erro ao conectar: {e}")


def verificar_tabela(conn: duckdb.DuckDBPyConnection) -> int:
    try:
        count = conn.sql("SELECT COUNT(*) FROM main.cv_repasses").fetchone()[0]
        print(f"📊 Registros em main.cv_repasses: {count:,}")
        return count
    except Exception:
        raise RuntimeError("Tabela main.cv_repasses não encontrada")


def exportar(conn: duckdb.DuckDBPyConnection) -> Path:
    df = conn.sql("SELECT * FROM main.cv_repasses").df()
    exports_dir = Path('exports')
    exports_dir.mkdir(exist_ok=True)
    nome_arquivo = exports_dir / f"cv_repasses_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(nome_arquivo, index=False, decimal=',')
    print(f"✅ Dados exportados para {nome_arquivo}")
    return nome_arquivo


def main():
    print("📥 BAIXAR CV REPASSES")
    print("=" * 40)

    if not configurar_ambiente():
        return

    conn = None
    try:
        conn = conectar()
        count = verificar_tabela(conn)
        if count == 0:
            print("⚠️ Tabela vazia, nenhum arquivo gerado")
            return
        exportar(conn)
    except Exception as e:
        print(f"❌ Erro: {e}")
    finally:
        if conn:
            conn.close()
            print("🔒 Conexão fechada")


if __name__ == '__main__':
    main()


