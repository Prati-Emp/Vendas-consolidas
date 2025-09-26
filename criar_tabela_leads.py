#!/usr/bin/env python3
"""
Criar tabela de Leads rapidamente
Coleta apenas algumas páginas para criar a tabela
"""

import asyncio
import os
import sys
import duckdb
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# Adicionar o diretório scripts ao path
sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))

async def main():
    print("🎯 CRIANDO TABELA DE LEADS")
    print("=" * 40)
    
    # Carregar variáveis de ambiente
    load_dotenv()
    
    # Verificar variáveis
    email = os.environ.get('CVCRM_EMAIL')
    token = os.environ.get('CVCRM_TOKEN')
    motherduck = os.environ.get('MOTHERDUCK_TOKEN')
    
    if not all([email, token, motherduck]):
        print("❌ Variáveis de ambiente faltando")
        return False
    
    print("✅ Variáveis de ambiente OK")
    
    try:
        from scripts.cv_leads_api import CVLeadsAPIClient, processar_dados_cv_leads
        
        print("\n🚀 Coletando dados (limitado a 3 páginas)...")
        
        # Criar cliente
        client = CVLeadsAPIClient()
        
        # Coletar apenas algumas páginas
        todos_dados = []
        for pagina in range(1, 4):  # Apenas 3 páginas
            print(f"   Página {pagina}...")
            result = await client.get_pagina(pagina, 500)
            
            if result['success']:
                dados = result['data'].get('dados', [])
                if dados:
                    todos_dados.extend(dados)
                    print(f"   ✅ {len(dados)} registros")
                else:
                    print(f"   ⚠️ Página vazia")
                    break
            else:
                print(f"   ❌ Erro na página {pagina}")
                break
            
            await asyncio.sleep(0.5)  # Rate limiting
        
        print(f"\n📊 DADOS COLETADOS: {len(todos_dados)} registros")
        
        if not todos_dados:
            print("❌ Nenhum dado coletado")
            return False
        
        # Processar dados
        print("🔄 Processando dados...")
        df = processar_dados_cv_leads(todos_dados)
        
        print(f"📊 DADOS PROCESSADOS: {len(df)} registros")
        print(f"   - Colunas: {list(df.columns)}")
        
        # Upload para MotherDuck
        print(f"\n📤 FAZENDO UPLOAD PARA MOTHERDUCK...")
        
        # Configurar DuckDB
        print("1. Configurando DuckDB...")
        duckdb.sql("INSTALL motherduck")
        duckdb.sql("LOAD motherduck")
        
        os.environ['motherduck_token'] = motherduck
        
        # Conectar
        print("2. Conectando ao MotherDuck...")
        conn = duckdb.connect('md:reservas')
        print("✅ Conexão estabelecida")
        
        # Upload CV Leads
        print(f"3. CV Leads - {len(df):,} registros")
        print("   Fazendo upload CV Leads...")
        conn.register("df_cv_leads", df)
        conn.execute("CREATE OR REPLACE TABLE main.cv_leads AS SELECT * FROM df_cv_leads")
        count_leads = conn.sql("SELECT COUNT(*) FROM main.cv_leads").fetchone()[0]
        print(f"   ✅ CV Leads: {count_leads:,} registros")
        
        # Listar tabelas
        print("\n4. Tabelas no banco 'reservas':")
        tables = conn.sql("SHOW TABLES").fetchall()
        for table in tables:
            table_name = table[0]
            try:
                count = conn.sql(f"SELECT COUNT(*) FROM main.{table_name}").fetchone()[0]
                print(f"   📊 {table_name}: {count:,} registros")
            except:
                print(f"   📊 {table_name}: (erro ao contar)")
        
        conn.close()
        print(f"\n✅ TABELA 'main.cv_leads' CRIADA COM SUCESSO!")
        print(f"🎉 {count_leads:,} registros de leads foram inseridos")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    sucesso = asyncio.run(main())
    if sucesso:
        print(f"\n🎉 Tabela de Leads criada com sucesso!")
        print(f"📊 A tabela 'main.cv_leads' está disponível no MotherDuck")
    else:
        print(f"\n❌ Falha ao criar tabela de Leads")



