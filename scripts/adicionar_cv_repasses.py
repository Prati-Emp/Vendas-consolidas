#!/usr/bin/env python3
"""
Cria/atualiza a tabela main.cv_repasses no MotherDuck usando a API de Repasses.

Uso (PowerShell):
  python -u scripts\adicionar_cv_repasses.py
"""

import os
import sys
from pathlib import Path
import asyncio
from datetime import datetime

import duckdb
import pandas as pd
from dotenv import load_dotenv

# Garantir que o diretório raiz esteja no sys.path para permitir `import scripts.*`
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from scripts.cv_repasses_api import obter_dados_cv_repasses


async def main() -> bool:
    print("🚀 ADICIONANDO CV REPASSES")
    print("=" * 50)

    try:
        # 1) Carregar .env
        print("1. Carregando configurações (.env)...")
        load_dotenv(override=True)

        required = ['MOTHERDUCK_TOKEN', 'CVCRM_EMAIL', 'CVCRM_TOKEN']
        missing = [v for v in required if not os.environ.get(v)]
        if missing:
            print(f"❌ Variáveis ausentes: {', '.join(missing)}")
            return False

        # 2) Coletar dados de repasses
        print("\n2. Coletando dados de CV Repasses...")
        df = await obter_dados_cv_repasses()
        print(f"   📦 Registros coletados: {len(df):,}")
        if df.empty:
            print("⚠️ Nenhum dado de repasse retornado. Abortando upload.")
            return False

        # 3) Configurar MotherDuck
        print("\n3. Configurando MotherDuck...")
        duckdb.sql("INSTALL motherduck")
        duckdb.sql("LOAD motherduck")
        os.environ['motherduck_token'] = os.environ.get('MOTHERDUCK_TOKEN', '').strip()

        # 4) Conectar e escrever
        print("\n4. Gravando tabela main.cv_repasses...")
        con = duckdb.connect('md:reservas')
        con.register('df', df)
        con.execute("CREATE OR REPLACE TABLE main.cv_repasses AS SELECT * FROM df")
        count = con.sql("SELECT COUNT(*) FROM main.cv_repasses").fetchone()[0]
        con.close()

        print(f"✅ Tabela 'main.cv_repasses' criada/atualizada com {count:,} registros")
        return True

    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


if __name__ == '__main__':
    ok = asyncio.run(main())
    if ok:
        print("\n🎉 Finalizado com sucesso")
    else:
        print("\n⚠️ Finalizado com avisos/erros")


