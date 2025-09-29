#!/usr/bin/env python3
"""
Atualização da Tabela de Repasses Workflow
Script para coletar dados e atualizar a tabela Repases_Workflow
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
    print("🎯 ATUALIZAÇÃO DA TABELA DE REPASSES WORKFLOW")
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
        from scripts.cv_repasses_workflow_api import obter_dados_cv_repasses_workflow
        
        print("\n🚀 COLETANDO DADOS DE REPASSES WORKFLOW...")
        print("⚠️ Coletando todos os dados disponíveis...")
        
        # Coletar dados
        df_workflow = await obter_dados_cv_repasses_workflow()
        
        print(f"\n📊 DADOS COLETADOS:")
        print(f"   - Total de registros: {len(df_workflow):,}")
        
        if df_workflow.empty:
            print("❌ Nenhum registro encontrado")
            return False
        
        print(f"   - Colunas: {len(df_workflow.columns)}")
        print(f"   - Primeiros registros:")
        print(df_workflow.head(3))
        
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
        
        # Upload CV Repasses Workflow
        print(f"3. CV Repasses Workflow - {len(df_workflow):,} registros")
        print("   Fazendo upload CV Repasses Workflow...")
        conn.register("df_cv_repasses_workflow", df_workflow)
        conn.execute("CREATE OR REPLACE TABLE main.Repases_Workflow AS SELECT * FROM df_cv_repasses_workflow")
        count_workflow = conn.sql("SELECT COUNT(*) FROM main.Repases_Workflow").fetchone()[0]
        print(f"   ✅ CV Repasses Workflow: {count_workflow:,} registros")
        
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
        print(f"\n✅ ATUALIZAÇÃO CONCLUÍDA!")
        print(f"🎉 Tabela 'main.Repases_Workflow' atualizada com {count_workflow:,} registros")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("⚠️ ATENÇÃO: Este script irá atualizar a tabela Repases_Workflow")
    print("Pressione Ctrl+C para cancelar se necessário")
    print()
    
    try:
        sucesso = asyncio.run(asyncio.wait_for(main(), timeout=600.0))  # 10 minutos timeout
        
        if sucesso:
            print(f"\n🎉 ATUALIZAÇÃO CONCLUÍDA COM SUCESSO!")
            print(f"📊 A tabela 'main.Repases_Workflow' foi atualizada")
        else:
            print(f"\n❌ Falha na atualização")
            
    except asyncio.TimeoutError:
        print(f"\n⏰ TIMEOUT - Operação demorou mais de 10 minutos")
    except KeyboardInterrupt:
        print(f"\n⚠️ Operação cancelada pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")





