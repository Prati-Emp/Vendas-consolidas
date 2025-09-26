#!/usr/bin/env python3
"""
Execução apenas da API de Leads
Script para criar a tabela cv_leads e alimentar com dados
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

def main():
    """Função principal para executar apenas a API de Leads"""
    print("🎯 EXECUTANDO APENAS API DE LEADS")
    print("=" * 50)
    print(f"⏰ Timestamp: {datetime.now()}")
    
    # Carregar variáveis de ambiente
    load_dotenv()
    
    # Verificar variáveis críticas
    required_vars = ['CVCRM_EMAIL', 'CVCRM_TOKEN', 'MOTHERDUCK_TOKEN']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"❌ Variáveis de ambiente faltando: {', '.join(missing_vars)}")
        return False
    
    print("✅ Variáveis de ambiente configuradas")
    
    try:
        # Importar a API de Leads
        from scripts.cv_leads_api import obter_dados_cv_leads
        
        print("\n🚀 Coletando dados CV Leads...")
        
        # Executar coleta de dados
        df_leads = asyncio.run(asyncio.wait_for(obter_dados_cv_leads(), timeout=600.0))
        
        print(f"\n📊 DADOS COLETADOS:")
        print(f"   - Registros: {len(df_leads):,}")
        
        if df_leads.empty:
            print("⚠️ Nenhum registro encontrado")
            return False
        
        print(f"   - Colunas: {list(df_leads.columns)}")
        print(f"   - Primeiros registros:")
        print(df_leads.head())
        
        # Upload para MotherDuck
        print(f"\n📤 FAZENDO UPLOAD PARA MOTHERDUCK...")
        
        # Configurar DuckDB
        print("1. Configurando DuckDB...")
        duckdb.sql("INSTALL motherduck")
        duckdb.sql("LOAD motherduck")
        
        token = os.environ.get('MOTHERDUCK_TOKEN', '').strip()
        os.environ['motherduck_token'] = token
        
        # Conectar
        print("2. Conectando ao MotherDuck...")
        conn = duckdb.connect('md:reservas')
        print("✅ Conexão estabelecida")
        
        # Upload CV Leads
        print(f"3. CV Leads - {len(df_leads):,} registros")
        print("   Fazendo upload CV Leads...")
        conn.register("df_cv_leads", df_leads)
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
        print("\n✅ Upload concluído com sucesso!")
        print(f"🎉 Tabela 'main.cv_leads' criada com {count_leads:,} registros")
        
        return True
        
    except asyncio.TimeoutError:
        print(f"\n⏰ TIMEOUT - Coleta demorou mais de 10 minutos")
        return False
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    sucesso = main()
    if sucesso:
        print(f"\n🎉 API de Leads executada com sucesso!")
        print(f"📊 Tabela 'main.cv_leads' criada no MotherDuck")
        sys.exit(0)
    else:
        print(f"\n❌ Falha na execução da API de Leads")
        sys.exit(1)



