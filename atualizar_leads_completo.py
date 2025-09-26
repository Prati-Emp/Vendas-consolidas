#!/usr/bin/env python3
"""
Atualização Completa da Tabela de Leads
Script para coletar TODOS os dados de leads e atualizar a tabela
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
    print("🎯 ATUALIZAÇÃO COMPLETA DA TABELA DE LEADS")
    print("=" * 50)
    print(f"⏰ Timestamp: {datetime.now()}")
    
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
        from scripts.cv_leads_api import obter_dados_cv_leads
        
        print("\n🚀 COLETANDO TODOS OS DADOS DE LEADS...")
        print("⚠️ Este processo pode demorar alguns minutos...")
        
        # Coletar TODOS os dados
        df_leads = await obter_dados_cv_leads()
        
        print(f"\n📊 DADOS COLETADOS:")
        print(f"   - Total de registros: {len(df_leads):,}")
        
        if df_leads.empty:
            print("❌ Nenhum registro encontrado")
            return False
        
        print(f"   - Colunas: {len(df_leads.columns)}")
        print(f"   - Primeiros registros:")
        print(df_leads.head(3))
        
        # Upload para MotherDuck
        print(f"\n📤 FAZENDO UPLOAD COMPLETO PARA MOTHERDUCK...")
        
        # Configurar DuckDB
        print("1. Configurando DuckDB...")
        duckdb.sql("INSTALL motherduck")
        duckdb.sql("LOAD motherduck")
        
        os.environ['motherduck_token'] = motherduck
        
        # Conectar
        print("2. Conectando ao MotherDuck...")
        conn = duckdb.connect('md:reservas')
        print("✅ Conexão estabelecida")
        
        # Upload CV Leads (substituição completa)
        print(f"3. CV Leads - {len(df_leads):,} registros")
        print("   Fazendo upload completo CV Leads...")
        conn.register("df_cv_leads", df_leads)
        conn.execute("CREATE OR REPLACE TABLE main.cv_leads AS SELECT * FROM df_cv_leads")
        count_leads = conn.sql("SELECT COUNT(*) FROM main.cv_leads").fetchone()[0]
        print(f"   ✅ CV Leads: {count_leads:,} registros")
        
        # Verificar tabelas
        print("\n4. Verificando tabelas no banco 'reservas':")
        tables = conn.sql("SHOW TABLES").fetchall()
        for table in tables:
            table_name = table[0]
            try:
                count = conn.sql(f"SELECT COUNT(*) FROM main.{table_name}").fetchone()[0]
                print(f"   📊 {table_name}: {count:,} registros")
            except:
                print(f"   📊 {table_name}: (erro ao contar)")
        
        conn.close()
        print(f"\n✅ ATUALIZAÇÃO COMPLETA CONCLUÍDA!")
        print(f"🎉 Tabela 'main.cv_leads' atualizada com {count_leads:,} registros")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("⚠️ ATENÇÃO: Este script irá coletar TODOS os dados de leads")
    print("Pressione Ctrl+C para cancelar se necessário")
    print()
    
    try:
        sucesso = asyncio.run(asyncio.wait_for(main(), timeout=1800.0))  # 30 minutos timeout
        
        if sucesso:
            print(f"\n🎉 ATUALIZAÇÃO COMPLETA CONCLUÍDA COM SUCESSO!")
            print(f"📊 A tabela 'main.cv_leads' foi atualizada com todos os dados")
        else:
            print(f"\n❌ Falha na atualização completa")
            
    except asyncio.TimeoutError:
        print(f"\n⏰ TIMEOUT - Operação demorou mais de 30 minutos")
    except KeyboardInterrupt:
        print(f"\n⚠️ Operação cancelada pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")



