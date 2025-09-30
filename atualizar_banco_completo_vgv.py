#!/usr/bin/env python3
"""
Script para atualização manual completa do banco de dados
Inclui a nova API VGV Empreendimentos
"""

import os
import duckdb
import pandas as pd
import asyncio
import sys
from datetime import datetime
from dotenv import load_dotenv
from scripts.cv_vendas_api import CVVendasAPIClient, processar_dados_cv_vendas
from scripts.cv_repasses_api import obter_dados_cv_repasses
from scripts.cv_leads_api import obter_dados_cv_leads
from scripts.cv_repasses_workflow_api import obter_dados_cv_repasses_workflow
from scripts.cv_vgv_empreendimentos_api import obter_dados_vgv_empreendimentos
from scripts.sienge_apis import SiengeAPIClient, obter_dados_sienge_vendas_canceladas, obter_dados_sienge_vendas_realizadas

async def upload_banco_completo_vgv(df_cv_vendas, df_cv_repasses, df_cv_leads, df_cv_repasses_workflow, df_vgv_empreendimentos, df_sienge_realizadas, df_sienge_canceladas):
    """Faz upload completo para o MotherDuck incluindo VGV Empreendimentos"""
    print("\n📤 FAZENDO UPLOAD COMPLETO PARA MOTHERDUCK")
    print("=" * 60)
    
    try:
        # Configurar DuckDB
        print("1. Configurando DuckDB...")
        duckdb.sql("INSTALL motherduck")
        duckdb.sql("LOAD motherduck")
        
        token = os.environ.get('MOTHERDUCK_TOKEN', '').strip()
        if not token:
            print("❌ MOTHERDUCK_TOKEN não encontrado")
            return False
        
        # Configurar token corretamente
        duckdb.sql(f"SET motherduck_token='{token}'")
        
        # Conectar
        print("2. Conectando ao MotherDuck...")
        conn = duckdb.connect('md:reservas')
        print("✅ Conexão estabelecida")
        
        # Upload CV Vendas
        print(f"3. CV Vendas - linhas no DataFrame: {len(df_cv_vendas):,}")
        if not df_cv_vendas.empty:
            print("   Fazendo upload CV Vendas...")
            conn.register("df_cv_vendas", df_cv_vendas)
            conn.execute("CREATE OR REPLACE TABLE main.cv_vendas AS SELECT * FROM df_cv_vendas")
            count_cv = conn.sql("SELECT COUNT(*) FROM main.cv_vendas").fetchone()[0]
            print(f"   ✅ CV Vendas: {count_cv:,} registros")

        # Upload CV Repasses
        print(f"3b. CV Repasses - linhas no DataFrame: {len(df_cv_repasses):,}")
        if df_cv_repasses is not None and not df_cv_repasses.empty:
            print("   Fazendo upload CV Repasses...")
            conn.register("df_cv_repasses", df_cv_repasses)
            conn.execute("CREATE OR REPLACE TABLE main.cv_repasses AS SELECT * FROM df_cv_repasses")
            count_rep = conn.sql("SELECT COUNT(*) FROM main.cv_repasses").fetchone()[0]
            print(f"   ✅ CV Repasses: {count_rep:,} registros")
        
        # Upload CV Leads
        print(f"3c. CV Leads - linhas no DataFrame: {len(df_cv_leads):,}")
        if df_cv_leads is not None and not df_cv_leads.empty:
            print("   Fazendo upload CV Leads...")
            conn.register("df_cv_leads", df_cv_leads)
            conn.execute("CREATE OR REPLACE TABLE main.cv_leads AS SELECT * FROM df_cv_leads")
            count_leads = conn.sql("SELECT COUNT(*) FROM main.cv_leads").fetchone()[0]
            print(f"   ✅ CV Leads: {count_leads:,} registros")
        
        # Upload CV Repasses Workflow
        print(f"3d. CV Repasses Workflow - linhas no DataFrame: {len(df_cv_repasses_workflow):,}")
        if df_cv_repasses_workflow is not None and not df_cv_repasses_workflow.empty:
            print("   Fazendo upload CV Repasses Workflow...")
            conn.register("df_cv_repasses_workflow", df_cv_repasses_workflow)
            conn.execute("CREATE OR REPLACE TABLE main.Repases_Workflow AS SELECT * FROM df_cv_repasses_workflow")
            count_workflow = conn.sql("SELECT COUNT(*) FROM main.Repases_Workflow").fetchone()[0]
            print(f"   ✅ CV Repasses Workflow: {count_workflow:,} registros")
        
        # Upload VGV Empreendimentos
        print(f"3e. VGV Empreendimentos - linhas no DataFrame: {len(df_vgv_empreendimentos):,}")
        if df_vgv_empreendimentos is not None and not df_vgv_empreendimentos.empty:
            print("   Fazendo upload VGV Empreendimentos...")
            conn.register("df_vgv_empreendimentos", df_vgv_empreendimentos)
            conn.execute("CREATE OR REPLACE TABLE main.cv_vgv_empreendimentos AS SELECT * FROM df_vgv_empreendimentos")
            count_vgv = conn.sql("SELECT COUNT(*) FROM main.cv_vgv_empreendimentos").fetchone()[0]
            print(f"   ✅ VGV Empreendimentos: {count_vgv:,} registros")
        
        # Upload Sienge Vendas Realizadas
        print(f"4. Sienge Realizadas - linhas no DataFrame: {len(df_sienge_realizadas):,}")
        if not df_sienge_realizadas.empty:
            print("   Fazendo upload Sienge Vendas Realizadas...")
            conn.register("df_sienge_realizadas", df_sienge_realizadas)
            conn.execute("CREATE OR REPLACE TABLE main.sienge_vendas_realizadas AS SELECT * FROM df_sienge_realizadas")
            count_realizadas = conn.sql("SELECT COUNT(*) FROM main.sienge_vendas_realizadas").fetchone()[0]
            print(f"   ✅ Sienge Realizadas: {count_realizadas:,} registros")
        
        # Upload Sienge Vendas Canceladas
        print(f"5. Sienge Canceladas - linhas no DataFrame: {len(df_sienge_canceladas):,}")
        if not df_sienge_canceladas.empty:
            print("   Fazendo upload Sienge Vendas Canceladas...")
            conn.register("df_sienge_canceladas", df_sienge_canceladas)
            conn.execute("CREATE OR REPLACE TABLE main.sienge_vendas_canceladas AS SELECT * FROM df_sienge_canceladas")
            count_canceladas = conn.sql("SELECT COUNT(*) FROM main.sienge_vendas_canceladas").fetchone()[0]
            print(f"   ✅ Sienge Canceladas: {count_canceladas:,} registros")
        
        # Listar tabelas
        print("\n6. Tabelas no banco 'reservas':")
        tables = conn.sql("SHOW TABLES").fetchall()
        for table in tables:
            table_name = table[0]
            try:
                count = conn.sql(f"SELECT COUNT(*) FROM main.{table_name}").fetchone()[0]
                print(f"   📊 {table_name}: {count:,} registros")
            except:
                print(f"   📊 {table_name}: (erro ao contar)")
        
        conn.close()
        print("✅ Upload completo concluído com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro no upload: {str(e)}")
        return False

async def atualizar_banco_completo_vgv():
    """Atualização completa do banco incluindo VGV Empreendimentos"""
    print("🚀 ATUALIZAÇÃO COMPLETA DO BANCO - COM VGV EMPREENDIMENTOS")
    print("=" * 70)
    
    start_time = datetime.now()
    
    try:
        # 1. Carregar configurações
        print("1. Carregando configurações...")
        load_dotenv()
        
        # Verificar variáveis de ambiente
        env_vars = ['CVCRM_EMAIL', 'CVCRM_TOKEN', 'SIENGE_TOKEN', 'MOTHERDUCK_TOKEN']
        for var in env_vars:
            if not os.environ.get(var):
                print(f"❌ {var} não encontrado")
                return False
        
        print("✅ Configurações carregadas")
        
        # 2. Coletar dados CV Vendas
        print("\n2. Coletando dados CV Vendas...")
        try:
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
            print(f"✅ CV Vendas processado: {len(df_cv_vendas)} registros")
        except Exception as e:
            df_cv_vendas = pd.DataFrame()
            print(f"⚠️ Falha ao coletar CV Vendas: {e}")

        # 3. Coletar CV Repasses
        print("\n3. Coletando dados CV Repasses...")
        try:
            df_cv_repasses = await obter_dados_cv_repasses()
            print(f"✅ CV Repasses processado: {len(df_cv_repasses)} registros")
        except Exception as e:
            df_cv_repasses = pd.DataFrame()
            print(f"⚠️ Falha ao coletar CV Repasses: {e}")

        # 4. Coletar CV Leads
        print("\n4. Coletando dados CV Leads...")
        try:
            df_cv_leads = await obter_dados_cv_leads()
            print(f"✅ CV Leads processado: {len(df_cv_leads)} registros")
        except Exception as e:
            df_cv_leads = pd.DataFrame()
            print(f"⚠️ Falha ao coletar CV Leads: {e}")

        # 5. Coletar CV Repasses Workflow
        print("\n5. Coletando dados CV Repasses Workflow...")
        try:
            df_cv_repasses_workflow = await obter_dados_cv_repasses_workflow()
            print(f"✅ CV Repasses Workflow processado: {len(df_cv_repasses_workflow)} registros")
        except Exception as e:
            df_cv_repasses_workflow = pd.DataFrame()
            print(f"⚠️ Falha ao coletar CV Repasses Workflow: {e}")

        # 6. Coletar VGV Empreendimentos
        print("\n6. Coletando dados VGV Empreendimentos...")
        try:
            df_vgv_empreendimentos = await obter_dados_vgv_empreendimentos(1, 20)  # IDs 1-20
            print(f"✅ VGV Empreendimentos processado: {len(df_vgv_empreendimentos)} registros")
        except Exception as e:
            df_vgv_empreendimentos = pd.DataFrame()
            print(f"⚠️ Falha ao coletar VGV Empreendimentos: {e}")

        # 7. Coletar dados Sienge
        print("\n7. Coletando dados Sienge...")
        try:
            df_sienge_realizadas = await obter_dados_sienge_vendas_realizadas()
            print(f"✅ Sienge Realizadas processado: {len(df_sienge_realizadas)} registros")
        except Exception as e:
            df_sienge_realizadas = pd.DataFrame()
            print(f"⚠️ Falha ao coletar Sienge Realizadas: {e}")

        try:
            df_sienge_canceladas = await obter_dados_sienge_vendas_canceladas()
            print(f"✅ Sienge Canceladas processado: {len(df_sienge_canceladas)} registros")
        except Exception as e:
            df_sienge_canceladas = pd.DataFrame()
            print(f"⚠️ Falha ao coletar Sienge Canceladas: {e}")

        # 8. Upload para MotherDuck
        print("\n8. Fazendo upload completo para MotherDuck...")
        sucesso_upload = await upload_banco_completo_vgv(
            df_cv_vendas,
            df_cv_repasses,
            df_cv_leads,
            df_cv_repasses_workflow,
            df_vgv_empreendimentos,
            df_sienge_realizadas,
            df_sienge_canceladas
        )
        
        # 9. Estatísticas finais
        end_time = datetime.now()
        duration = end_time - start_time
        
        print(f"\n🎉 ATUALIZAÇÃO COMPLETA FINALIZADA!")
        print(f"⏱️ Duração total: {duration}")
        print(f"📊 Resumo:")
        print(f"   - CV Vendas: {len(df_cv_vendas):,} registros")
        print(f"   - CV Repasses: {len(df_cv_repasses):,} registros")
        print(f"   - CV Leads: {len(df_cv_leads):,} registros")
        print(f"   - CV Repasses Workflow: {len(df_cv_repasses_workflow):,} registros")
        print(f"   - VGV Empreendimentos: {len(df_vgv_empreendimentos):,} registros")
        print(f"   - Sienge Realizadas: {len(df_sienge_realizadas):,} registros")
        print(f"   - Sienge Canceladas: {len(df_sienge_canceladas):,} registros")
        print(f"   - Upload: {'✅ Sucesso' if sucesso_upload else '❌ Falha'}")
        
        return sucesso_upload
        
    except Exception as e:
        print(f"\n❌ Erro na atualização completa: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Função principal"""
    print("⚠️ ATENÇÃO: Este script irá atualizar TODOS os dados do banco incluindo VGV Empreendimentos")
    print("Pressione Ctrl+C para cancelar se necessário")
    print()
    
    try:
        # Timeout total de 20 minutos
        sucesso = asyncio.run(
            asyncio.wait_for(atualizar_banco_completo_vgv(), timeout=1200.0)
        )
        
        if sucesso:
            print("\n✅ Atualização completa executada com sucesso!")
            print("🌐 Você pode agora validar visualmente no dashboard")
        else:
            print("\n❌ Falha na execução da atualização completa")
            
    except asyncio.TimeoutError:
        print("\n⏰ Timeout - operação demorou mais de 20 minutos")
    except KeyboardInterrupt:
        print("\n⚠️ Atualização cancelada pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
    finally:
        print("\n🏁 Atualização finalizada")
        sys.exit(0)

if __name__ == "__main__":
    main()
