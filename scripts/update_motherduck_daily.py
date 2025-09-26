#!/usr/bin/env python3
"""
Atualização diária do MotherDuck (APIs não-Sienge)
Executa CV Vendas, CV Repasses, CV Leads e CV Repasses Workflow
"""

import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Garante import do projeto quando rodar via Actions
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

async def sistema_diario():
    """Sistema de atualização diária (sem APIs Sienge)"""
    print("🌅 SISTEMA DE ATUALIZAÇÃO DIÁRIA (NÃO-SIENGE)")
    print("=" * 60)
    print(f"⏰ Timestamp: {datetime.now()}")
    print(f"🎯 APIs: CV Vendas, CV Repasses, CV Leads, CV Repasses Workflow")
    
    start_time = datetime.now()
    
    try:
        # Importar módulos necessários
        from scripts.cv_vendas_api import CVVendasAPIClient, processar_dados_cv_vendas
        from scripts.cv_repasses_api import obter_dados_cv_repasses
        from scripts.cv_leads_api import obter_dados_cv_leads
        from scripts.cv_repasses_workflow_api import obter_dados_cv_repasses_workflow
        import duckdb
        import pandas as pd
        
        # 1. Coletar dados CV Vendas
        print("\n1. Coletando dados CV Vendas...")
        client = CVVendasAPIClient()
        todos_dados = []
        pagina = 1
        
        while True:
            result = await client.get_pagina(pagina)
            if result['success']:
                dados = result['data'].get('dados', [])
                if dados:
                    todos_dados.extend(dados)
                    pagina += 1
                    await asyncio.sleep(0.2)
                else:
                    break
            else:
                break
        
        df_cv_vendas = processar_dados_cv_vendas(todos_dados)
        print(f"✅ CV Vendas: {len(df_cv_vendas)} registros")
        
        # 2. Coletar CV Repasses
        print("\n2. Coletando dados CV Repasses...")
        try:
            df_cv_repasses = await obter_dados_cv_repasses()
            print(f"✅ CV Repasses: {len(df_cv_repasses)} registros")
        except Exception as e:
            df_cv_repasses = pd.DataFrame()
            print(f"⚠️ Falha ao coletar CV Repasses: {e}")
        
        # 3. Coletar CV Leads
        print("\n3. Coletando dados CV Leads...")
        try:
            df_cv_leads = await obter_dados_cv_leads()
            print(f"✅ CV Leads: {len(df_cv_leads)} registros")
        except Exception as e:
            df_cv_leads = pd.DataFrame()
            print(f"⚠️ Falha ao coletar CV Leads: {e}")
        
        # 4. Coletar CV Repasses Workflow
        print("\n4. Coletando dados CV Repasses Workflow...")
        try:
            df_cv_repasses_workflow = await obter_dados_cv_repasses_workflow()
            print(f"✅ CV Repasses Workflow: {len(df_cv_repasses_workflow)} registros")
        except Exception as e:
            df_cv_repasses_workflow = pd.DataFrame()
            print(f"⚠️ Falha ao coletar CV Repasses Workflow: {e}")
        
        # 5. Upload para MotherDuck
        print("\n5. Fazendo upload para MotherDuck...")
        
        # Configurar DuckDB
        duckdb.sql("INSTALL motherduck")
        duckdb.sql("LOAD motherduck")
        
        token = os.environ.get('MOTHERDUCK_TOKEN', '').strip()
        if not token:
            print("❌ MOTHERDUCK_TOKEN não encontrado")
            return False
        
        os.environ['motherduck_token'] = token
        conn = duckdb.connect('md:reservas')
        
        # Upload CV Vendas
        if not df_cv_vendas.empty:
            conn.register("df_cv_vendas", df_cv_vendas)
            conn.execute("CREATE OR REPLACE TABLE main.cv_vendas AS SELECT * FROM df_cv_vendas")
            count_cv = conn.sql("SELECT COUNT(*) FROM main.cv_vendas").fetchone()[0]
            print(f"✅ CV Vendas upload: {count_cv:,} registros")
        
        # Upload CV Repasses
        if df_cv_repasses is not None and not df_cv_repasses.empty:
            conn.register("df_cv_repasses", df_cv_repasses)
            conn.execute("CREATE OR REPLACE TABLE main.cv_repasses AS SELECT * FROM df_cv_repasses")
            count_rep = conn.sql("SELECT COUNT(*) FROM main.cv_repasses").fetchone()[0]
            print(f"✅ CV Repasses upload: {count_rep:,} registros")
        
        # Upload CV Leads
        if df_cv_leads is not None and not df_cv_leads.empty:
            conn.register("df_cv_leads", df_cv_leads)
            conn.execute("CREATE OR REPLACE TABLE main.cv_leads AS SELECT * FROM df_cv_leads")
            count_leads = conn.sql("SELECT COUNT(*) FROM main.cv_leads").fetchone()[0]
            print(f"✅ CV Leads upload: {count_leads:,} registros")
        
        # Upload CV Repasses Workflow
        if df_cv_repasses_workflow is not None and not df_cv_repasses_workflow.empty:
            conn.register("df_cv_repasses_workflow", df_cv_repasses_workflow)
            conn.execute("CREATE OR REPLACE TABLE main.Repases_Workflow AS SELECT * FROM df_cv_repasses_workflow")
            count_workflow = conn.sql("SELECT COUNT(*) FROM main.Repases_Workflow").fetchone()[0]
            print(f"✅ CV Repasses Workflow upload: {count_workflow:,} registros")
        
        conn.close()
        
        # 6. Estatísticas finais
        end_time = datetime.now()
        duration = end_time - start_time
        
        print(f"\n🎉 ATUALIZAÇÃO DIÁRIA CONCLUÍDA!")
        print(f"⏱️ Duração: {duration}")
        print(f"📊 Resumo:")
        print(f"   - CV Vendas: {len(df_cv_vendas):,} registros")
        print(f"   - CV Repasses: {len(df_cv_repasses):,} registros")
        print(f"   - CV Leads: {len(df_cv_leads):,} registros")
        print(f"   - CV Repasses Workflow: {len(df_cv_repasses_workflow):,} registros")
        print("   - Sienge: ⏸️ Pausado (execução 2x/semana)")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Erro na atualização diária: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Função principal para execução via GitHub Actions"""
    print("🌅 INICIANDO ATUALIZAÇÃO DIÁRIA DO MOTHERDUCK")
    print("=" * 60)
    print(f"⏰ Timestamp: {datetime.now()}")
    print(f"🐍 Python: {sys.version}")
    print(f"📁 Working directory: {os.getcwd()}")
    
    # Carregar variáveis de ambiente
    load_dotenv()
    
    # Verificar variáveis críticas
    required_vars = ['MOTHERDUCK_TOKEN', 'CVCRM_EMAIL', 'CVCRM_TOKEN']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"❌ Variáveis de ambiente faltando: {', '.join(missing_vars)}")
        sys.exit(1)
    
    print("✅ Variáveis de ambiente configuradas")
    
    try:
        # Executar com timeout de 15 minutos
        sucesso = asyncio.run(asyncio.wait_for(sistema_diario(), timeout=900.0))
        
        if sucesso:
            print("\n✅ ATUALIZAÇÃO DIÁRIA CONCLUÍDA COM SUCESSO!")
            print("🌐 Dados atualizados no MotherDuck")
            print("📊 Dashboard pode ser consultado para validação")
            sys.exit(0)
        else:
            print("\n❌ FALHA NA ATUALIZAÇÃO DIÁRIA")
            print("🔍 Verifique os logs acima para detalhes")
            sys.exit(1)
            
    except asyncio.TimeoutError:
        print("\n⏰ TIMEOUT - Operação demorou mais de 15 minutos")
        print("🔍 Considere otimizar o pipeline ou aumentar o timeout")
        sys.exit(1)
        
    except ImportError as e:
        print(f"\n❌ ERRO DE IMPORTAÇÃO: {e}")
        print("🔍 Verifique se todos os módulos estão disponíveis")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ ERRO INESPERADO: {e}")
        print("🔍 Verifique a configuração e conectividade")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

