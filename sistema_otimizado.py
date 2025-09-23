#!/usr/bin/env python3
"""
Sistema Otimizado de Coleta de Dados
Versão com rate limiting otimizado e coleta mais eficiente
"""

import os
import duckdb
import pandas as pd
import asyncio
import sys
from datetime import datetime
from dotenv import load_dotenv
from scripts.cv_vendas_api import CVVendasAPIClient, processar_dados_cv_vendas
from scripts.sienge_apis import SiengeAPIClient, obter_dados_sienge_vendas_canceladas, obter_dados_sienge_vendas_realizadas

async def coletar_dados_cv_vendas_otimizado():
    """Coleta dados do CV Vendas com rate limiting otimizado"""
    print("🔍 COLETANDO DADOS CV VENDAS - VERSÃO OTIMIZADA")
    print("=" * 50)
    
    try:
        client = CVVendasAPIClient()
        
        pagina = 1
        todos_dados = []
        paginas_vazias = 0
        max_paginas_vazias = 3
        max_paginas_seguranca = 50  # Reduzido para evitar rate limit
        
        print("📄 Iniciando coleta otimizada...")
        
        while True:
            # Verificar limite de segurança
            if pagina > max_paginas_seguranca:
                print(f"   ⚠️ Limite de segurança atingido ({max_paginas_seguranca} páginas)")
                break
            
            result = await client.get_pagina(pagina)
            
            if result['success']:
                dados = result['data'].get('dados', [])
                
                if not dados:
                    paginas_vazias += 1
                    print(f"   Página {pagina}: Vazia ({paginas_vazias}/{max_paginas_vazias})")
                    
                    if paginas_vazias >= max_paginas_vazias:
                        print(f"   ✅ Fim dos dados: {paginas_vazias} páginas vazias consecutivas")
                        break
                else:
                    paginas_vazias = 0
                    todos_dados.extend(dados)
                    print(f"   Página {pagina}: {len(dados)} registros (Total: {len(todos_dados)})")
                
                pagina += 1
                # Rate limiting mais conservador
                await asyncio.sleep(0.5)  # Aumentado de 0.2 para 0.5
                
            else:
                print(f"   ❌ Erro na página {pagina}: {result.get('error')}")
                break
        
        print(f"\n📊 CV VENDAS - RESULTADO FINAL:")
        print(f"   - Total de registros: {len(todos_dados)}")
        print(f"   - Páginas processadas: {pagina - 1}")
        
        if len(todos_dados) >= 600:
            print(f"   ✅ Meta atingida: {len(todos_dados)} >= 600 registros")
        else:
            print(f"   ⚠️ Meta não atingida: {len(todos_dados)} < 600 registros")
        
        return todos_dados
        
    except Exception as e:
        print(f"❌ Erro na coleta CV Vendas: {str(e)}")
        return []

async def coletar_dados_sienge_otimizado():
    """Coleta dados do Sienge com controle de limite diário"""
    print("\n🔍 COLETANDO DADOS SIENGE - VERSÃO OTIMIZADA")
    print("=" * 50)
    
    try:
        # Buscar lista de empreendimentos
        from scripts.sienge_apis import obter_lista_empreendimentos_motherduck
        empreendimentos = obter_lista_empreendimentos_motherduck()
        
        print(f"📊 Empreendimentos encontrados: {len(empreendimentos)}")
        
        # Usar todos os empreendimentos disponíveis
        empreendimentos_teste = empreendimentos  # Todos os empreendimentos
        print(f"📊 Usando todos os {len(empreendimentos_teste)} empreendimentos disponíveis")
        
        for i, emp in enumerate(empreendimentos_teste, 1):
            print(f"   {i}. {emp['nome']} (ID: {emp['id']})")
        
        # Coletar dados de vendas realizadas
        print(f"\n📈 Coletando vendas realizadas...")
        df_realizadas = await obter_dados_sienge_vendas_realizadas()
        
        # Aguardar delay entre vendas realizadas e canceladas (5 minutos)
        print(f"\n⏳ Aguardando 5 minutos antes de buscar vendas canceladas...")
        import asyncio
        await asyncio.sleep(300)  # 5 minutos = 300 segundos
        
        # Coletar dados de vendas canceladas
        print(f"\n📉 Coletando vendas canceladas...")
        df_canceladas = await obter_dados_sienge_vendas_canceladas()
        
        print(f"\n📊 SIENGE - RESULTADO FINAL:")
        print(f"   - Vendas realizadas: {len(df_realizadas)} registros")
        print(f"   - Vendas canceladas: {len(df_canceladas)} registros")
        print(f"   - Total: {len(df_realizadas) + len(df_canceladas)} registros")
        
        return {
            'vendas_realizadas': df_realizadas,
            'vendas_canceladas': df_canceladas,
            'empreendimentos': len(empreendimentos_teste)
        }
        
    except Exception as e:
        print(f"❌ Erro na coleta Sienge: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'vendas_realizadas': pd.DataFrame(),
            'vendas_canceladas': pd.DataFrame(),
            'empreendimentos': 0
        }

async def upload_dados_motherduck_otimizado(df_cv_vendas, df_sienge_realizadas, df_sienge_canceladas):
    """Faz upload dos dados para o MotherDuck"""
    print("\n📤 FAZENDO UPLOAD PARA MOTHERDUCK")
    print("=" * 50)
    
    try:
        # Configurar DuckDB
        print("1. Configurando DuckDB...")
        duckdb.sql("INSTALL motherduck")
        duckdb.sql("LOAD motherduck")
        
        token = os.environ.get('MOTHERDUCK_TOKEN', '').strip()
        if not token:
            print("❌ MOTHERDUCK_TOKEN não encontrado")
            return False
        
        os.environ['motherduck_token'] = token
        
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
        print("✅ Upload concluído com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro no upload: {str(e)}")
        return False

async def sistema_otimizado():
    """Sistema otimizado de coleta e upload de dados"""
    print("🚀 SISTEMA OTIMIZADO DE COLETA DE DADOS")
    print("=" * 60)
    
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
        dados_cv = await coletar_dados_cv_vendas_otimizado()
        
        # 3. Coletar dados Sienge
        print("\n3. Coletando dados Sienge...")
        dados_sienge = await coletar_dados_sienge_otimizado()
        
        # 4. Processar dados CV Vendas
        print("\n4. Processando dados CV Vendas...")
        if dados_cv:
            df_cv_vendas = processar_dados_cv_vendas(dados_cv)
            print(f"✅ CV Vendas processado: {len(df_cv_vendas)} registros")
        else:
            df_cv_vendas = pd.DataFrame()
            print("⚠️ Nenhum dado CV Vendas para processar")
        
        # 5. Upload para MotherDuck
        print("\n5. Fazendo upload para MotherDuck...")
        sucesso_upload = await upload_dados_motherduck_otimizado(
            df_cv_vendas,
            dados_sienge['vendas_realizadas'],
            dados_sienge['vendas_canceladas']
        )
        
        # 6. Estatísticas finais
        end_time = datetime.now()
        duration = end_time - start_time
        
        print(f"\n🎉 SISTEMA OTIMIZADO FINALIZADO!")
        print(f"⏱️ Duração total: {duration}")
        print(f"📊 Resumo:")
        print(f"   - CV Vendas: {len(df_cv_vendas):,} registros")
        print(f"   - Sienge Realizadas: {len(dados_sienge['vendas_realizadas']):,} registros")
        print(f"   - Sienge Canceladas: {len(dados_sienge['vendas_canceladas']):,} registros")
        print(f"   - Empreendimentos Sienge: {dados_sienge['empreendimentos']}")
        print(f"   - Upload: {'✅ Sucesso' if sucesso_upload else '❌ Falha'}")
        
        return sucesso_upload
        
    except Exception as e:
        print(f"\n❌ Erro no sistema otimizado: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Função principal"""
    print("⚠️ ATENÇÃO: Este script irá coletar dados de todas as APIs e fazer upload para o MotherDuck")
    print("Versão otimizada com rate limiting melhorado")
    print("Pressione Ctrl+C para cancelar se necessário")
    print()
    
    try:
        # Timeout total de 10 minutos
        sucesso = asyncio.run(
            asyncio.wait_for(sistema_otimizado(), timeout=600.0)
        )
        
        if sucesso:
            print("\n✅ Sistema otimizado executado com sucesso!")
            print("🌐 Você pode agora validar visualmente no dashboard")
        else:
            print("\n❌ Falha na execução do sistema otimizado")
            
    except asyncio.TimeoutError:
        print("\n⏰ Timeout - operação demorou mais de 10 minutos")
    except KeyboardInterrupt:
        print("\n⚠️ Sistema cancelado pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
    finally:
        print("\n🏁 Sistema finalizado")
        sys.exit(0)

if __name__ == "__main__":
    main()

