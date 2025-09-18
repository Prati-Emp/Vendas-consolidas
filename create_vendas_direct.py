#!/usr/bin/env python3
"""
Criar tabela de vendas diretamente
"""

import os
import duckdb
import pandas as pd
import asyncio
from dotenv import load_dotenv
from scripts.cv_vendas_api import obter_dados_cv_vendas

async def create_vendas_direct():
    """Cria tabela de vendas diretamente"""
    print("=== Criando Tabela de Vendas Diretamente ===")
    
    # Carregar .env
    print("Carregando variáveis de ambiente...")
    load_dotenv()
    token = os.environ.get('MOTHERDUCK_TOKEN', '').strip()
    
    if not token:
        print("❌ MOTHERDUCK_TOKEN não encontrado")
        return False
    
    print(f"✅ Token encontrado: {token[:10]}...")
    
    try:
        # Configurar DuckDB
        print("Configurando DuckDB...")
        duckdb.sql("INSTALL motherduck")
        duckdb.sql("LOAD motherduck")
        
        # Configurar token
        print("Configurando token...")
        os.environ['motherduck_token'] = token
        
        # Conectar
        print("Conectando ao MotherDuck...")
        conn = duckdb.connect('md:reservas')
        print("✅ Conexão estabelecida!")
        
        # Coletar dados do CV Vendas (apenas algumas páginas para teste)
        print("Coletando dados do CV Vendas...")
        df_vendas = await obter_dados_cv_vendas()
        print(f"Dados coletados: {len(df_vendas)} registros")
        
        if df_vendas.empty:
            print("❌ Nenhum dado coletado")
            return False
        
        # Criar tabela diretamente no schema main
        print("Criando tabela cv_vendas...")
        conn.execute("DROP TABLE IF EXISTS reservas.main.cv_vendas")
        conn.execute("CREATE TABLE reservas.main.cv_vendas AS SELECT * FROM df_vendas")
        
        # Verificar se foi criada
        print("Verificando tabela criada...")
        count = conn.sql("SELECT COUNT(*) FROM reservas.main.cv_vendas").fetchone()[0]
        print(f"✅ Tabela cv_vendas criada com {count} registros")
        
        # Listar tabelas
        print("\nTabelas existentes:")
        tables = conn.sql("SHOW TABLES").fetchall()
        for table in tables:
            print(f"  - {table[0]}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(create_vendas_direct())

