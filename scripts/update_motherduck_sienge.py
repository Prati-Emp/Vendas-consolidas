#!/usr/bin/env python3
"""
Atualização Sienge do MotherDuck (2x/semana)
Executa apenas APIs Sienge: Vendas Realizadas e Canceladas
"""

import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Garante import do projeto quando rodar via Actions
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

async def sistema_sienge():
    """Sistema de atualização Sienge (2x/semana)"""
    print("🌙 SISTEMA DE ATUALIZAÇÃO SIENGE (2X/SEMANA)")
    print("=" * 60)
    print(f"⏰ Timestamp: {datetime.now()}")
    print(f"🎯 APIs: Sienge Vendas Realizadas e Canceladas")
    
    start_time = datetime.now()
    
    try:
        # Importar módulos necessários
        from scripts.sienge_apis import obter_dados_sienge_vendas_realizadas, obter_dados_sienge_vendas_canceladas
        import duckdb
        import pandas as pd
        
        # 1. Coletar dados Sienge Vendas Realizadas
        print("\n1. Coletando dados Sienge Vendas Realizadas...")
        try:
            df_sienge_realizadas = await obter_dados_sienge_vendas_realizadas()
            print(f"✅ Sienge Vendas Realizadas: {len(df_sienge_realizadas)} registros")
        except Exception as e:
            df_sienge_realizadas = pd.DataFrame()
            print(f"❌ Falha ao coletar Sienge Vendas Realizadas: {e}")
            return False
        
        # 2. Aguardar delay entre vendas realizadas e canceladas (5 minutos)
        print(f"\n⏳ Aguardando 5 minutos antes de buscar vendas canceladas...")
        await asyncio.sleep(300)  # 5 minutos = 300 segundos
        
        # 3. Coletar dados Sienge Vendas Canceladas
        print("\n2. Coletando dados Sienge Vendas Canceladas...")
        try:
            df_sienge_canceladas = await obter_dados_sienge_vendas_canceladas()
            print(f"✅ Sienge Vendas Canceladas: {len(df_sienge_canceladas)} registros")
        except Exception as e:
            df_sienge_canceladas = pd.DataFrame()
            print(f"❌ Falha ao coletar Sienge Vendas Canceladas: {e}")
            return False
        
        # 4. Upload para MotherDuck
        print("\n3. Fazendo upload para MotherDuck...")
        
        # Configurar DuckDB
        duckdb.sql("INSTALL motherduck")
        duckdb.sql("LOAD motherduck")
        
        token = os.environ.get('MOTHERDUCK_TOKEN', '').strip()
        if not token:
            print("❌ MOTHERDUCK_TOKEN não encontrado")
            return False
        
        os.environ['motherduck_token'] = token
        conn = duckdb.connect('md:reservas')
        
        # Upload Sienge Vendas Realizadas
        if not df_sienge_realizadas.empty:
            conn.register("df_sienge_realizadas", df_sienge_realizadas)
            conn.execute("CREATE OR REPLACE TABLE main.sienge_vendas_realizadas AS SELECT * FROM df_sienge_realizadas")
            count_realizadas = conn.sql("SELECT COUNT(*) FROM main.sienge_vendas_realizadas").fetchone()[0]
            print(f"✅ Sienge Vendas Realizadas upload: {count_realizadas:,} registros")
        
        # Upload Sienge Vendas Canceladas
        if not df_sienge_canceladas.empty:
            conn.register("df_sienge_canceladas", df_sienge_canceladas)
            conn.execute("CREATE OR REPLACE TABLE main.sienge_vendas_canceladas AS SELECT * FROM df_sienge_canceladas")
            count_canceladas = conn.sql("SELECT COUNT(*) FROM main.sienge_vendas_canceladas").fetchone()[0]
            print(f"✅ Sienge Vendas Canceladas upload: {count_canceladas:,} registros")
        
        # Listar tabelas Sienge
        print("\n4. Tabelas Sienge no banco 'reservas':")
        try:
            count_realizadas = conn.sql("SELECT COUNT(*) FROM main.sienge_vendas_realizadas").fetchone()[0]
            print(f"   📊 sienge_vendas_realizadas: {count_realizadas:,} registros")
        except:
            print(f"   📊 sienge_vendas_realizadas: (erro ao contar)")
        
        try:
            count_canceladas = conn.sql("SELECT COUNT(*) FROM main.sienge_vendas_canceladas").fetchone()[0]
            print(f"   📊 sienge_vendas_canceladas: {count_canceladas:,} registros")
        except:
            print(f"   📊 sienge_vendas_canceladas: (erro ao contar)")
        
        conn.close()
        
        # 5. Estatísticas finais
        end_time = datetime.now()
        duration = end_time - start_time
        
        print(f"\n🎉 ATUALIZAÇÃO SIENGE CONCLUÍDA!")
        print(f"⏱️ Duração: {duration}")
        print(f"📊 Resumo:")
        print(f"   - Sienge Vendas Realizadas: {len(df_sienge_realizadas):,} registros")
        print(f"   - Sienge Vendas Canceladas: {len(df_sienge_canceladas):,} registros")
        print("   - Outras APIs: ⏸️ Pausadas (execução diária)")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Erro na atualização Sienge: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Função principal para execução via GitHub Actions"""
    print("🌙 INICIANDO ATUALIZAÇÃO SIENGE DO MOTHERDUCK")
    print("=" * 60)
    print(f"⏰ Timestamp: {datetime.now()}")
    print(f"🐍 Python: {sys.version}")
    print(f"📁 Working directory: {os.getcwd()}")
    
    # Carregar variáveis de ambiente
    load_dotenv()
    
    # Verificar variáveis críticas
    required_vars = ['MOTHERDUCK_TOKEN', 'SIENGE_TOKEN']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"❌ Variáveis de ambiente faltando: {', '.join(missing_vars)}")
        sys.exit(1)
    
    print("✅ Variáveis de ambiente configuradas")
    
    try:
        # Executar com timeout de 15 minutos
        sucesso = asyncio.run(asyncio.wait_for(sistema_sienge(), timeout=900.0))
        
        if sucesso:
            print("\n✅ ATUALIZAÇÃO SIENGE CONCLUÍDA COM SUCESSO!")
            print("🌐 Dados Sienge atualizados no MotherDuck")
            print("📊 Dashboard pode ser consultado para validação")
            sys.exit(0)
        else:
            print("\n❌ FALHA NA ATUALIZAÇÃO SIENGE")
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
