#!/usr/bin/env python3
"""
Upload funcional de dados de vendas com timeout e finalização garantida
"""

import os
import duckdb
import pandas as pd
import asyncio
import sys
from datetime import datetime
from dotenv import load_dotenv
from scripts.cv_vendas_api import CVVendasAPIClient, processar_dados_cv_vendas

async def coletar_dados_com_timeout(max_paginas=None):
    """Coleta dados com timeout e controles de segurança - busca dinâmica até última página"""
    if max_paginas:
        print(f"📡 Coletando dados (máximo {max_paginas} páginas)...")
    else:
        print(f"📡 Coletando dados (busca dinâmica até última página)...")
    
    client = CVVendasAPIClient()
    pagina = 1
    todos_dados = []
    paginas_vazias = 0
    max_paginas_vazias = 5  # Aumentado para 5 páginas vazias consecutivas
    max_paginas_seguranca = 2000  # Aumentado para 2000 páginas
    total_paginas_processadas = 0
    
    while True:
        # Verificar limite máximo se especificado
        if max_paginas and pagina > max_paginas:
            print(f"\n✅ Limite de {max_paginas} páginas atingido")
            break
            
        # Verificar limite de segurança para evitar loops infinitos
        if pagina > max_paginas_seguranca:
            print(f"\n⚠️ Limite de segurança atingido ({max_paginas_seguranca} páginas)")
            break
        try:
            print(f"📄 Página {pagina}...", end=" ", flush=True)
            
            # Timeout de 20 segundos por página (aumentado)
            result = await asyncio.wait_for(
                client.get_pagina(pagina), 
                timeout=20.0
            )
            
            if not result['success']:
                print(f"❌ Erro: {result.get('error', 'Erro desconhecido')}")
                # Se for erro 404 ou similar, pode ser fim dos dados
                if '404' in str(result.get('error', '')) or 'not found' in str(result.get('error', '')).lower():
                    print(f"✅ Fim dos dados detectado (erro 404)")
                    break
                break
            
            dados = result['data'].get('dados', [])
            total_paginas_processadas += 1
            
            if not dados:
                paginas_vazias += 1
                print(f"Vazia ({paginas_vazias}/{max_paginas_vazias})")
                
                if paginas_vazias >= max_paginas_vazias:
                    print(f"\n✅ Fim da paginação: {paginas_vazias} páginas vazias consecutivas")
                    break
            else:
                paginas_vazias = 0
                todos_dados.extend(dados)
                print(f"✅ {len(dados)} registros (Total: {len(todos_dados)})")
            
            pagina += 1
            await asyncio.sleep(0.2)  # Rate limiting otimizado para ser mais rápido
            
        except asyncio.TimeoutError:
            print(f"⏰ Timeout na página {pagina}")
            break
        except Exception as e:
            print(f"❌ Erro na página {pagina}: {str(e)}")
            break
    
    print(f"\n📊 Total coletado: {len(todos_dados)} registros em {total_paginas_processadas} páginas processadas")
    return processar_dados_cv_vendas(todos_dados)

async def upload_vendas_funcional():
    """Upload funcional de dados de vendas"""
    print("🚀 UPLOAD FUNCIONAL DE DADOS DE VENDAS")
    print("=" * 50)
    
    start_time = datetime.now()
    conn = None
    
    try:
        # 1. Carregar .env
        print("1. Carregando configurações...")
        load_dotenv()
        token = os.environ.get('MOTHERDUCK_TOKEN', '').strip()
        
        if not token:
            print("❌ MOTHERDUCK_TOKEN não encontrado")
            return False
        
        print(f"✅ Token encontrado: {token[:10]}...")
        
        # 2. Configurar DuckDB
        print("\n2. Configurando DuckDB...")
        duckdb.sql("INSTALL motherduck")
        duckdb.sql("LOAD motherduck")
        os.environ['motherduck_token'] = token
        print("✅ MotherDuck configurado")
        
        # 3. Conectar
        print("\n3. Conectando ao MotherDuck...")
        conn = duckdb.connect('md:reservas')
        print("✅ Conexão estabelecida")
        
        # 4. Coletar dados
        print("\n4. Coletando dados do CV Vendas...")
        df_vendas = await coletar_dados_com_timeout()  # Busca dinâmica até última página
        
        if df_vendas.empty:
            print("⚠️ Nenhum dado coletado")
            return False
        
        print(f"✅ Dados coletados: {len(df_vendas)} registros")
        print(f"📊 Colunas: {list(df_vendas.columns)}")
        
        # 5. Upload para MotherDuck
        print("\n5. Fazendo upload para MotherDuck...")
        
        # Remover tabela existente
        conn.sql("DROP TABLE IF EXISTS main.cv_vendas")
        print("✅ Tabela antiga removida")
        
        # Criar nova tabela
        conn.execute("CREATE TABLE main.cv_vendas AS SELECT * FROM df_vendas")
        print("✅ Nova tabela criada")
        
        # Verificar
        count = conn.sql("SELECT COUNT(*) FROM main.cv_vendas").fetchone()[0]
        print(f"✅ Tabela 'cv_vendas' criada com {count:,} registros")
        
        # 6. Estatísticas
        print("\n6. Estatísticas dos dados:")
        if 'valor_venda' in df_vendas.columns:
            total_vendas = df_vendas['valor_venda'].sum()
            media_vendas = df_vendas['valor_venda'].mean()
            print(f"  💰 Valor total: R$ {total_vendas:,.2f}")
            print(f"  📈 Valor médio: R$ {media_vendas:,.2f}")
        
        # 7. Listar tabelas
        print("\n7. Tabelas no banco 'reservas':")
        tables = conn.sql("SHOW TABLES").fetchall()
        for table in tables:
            table_name = table[0]
            try:
                count = conn.sql(f"SELECT COUNT(*) FROM main.{table_name}").fetchone()[0]
                print(f"  📊 {table_name}: {count:,} registros")
            except:
                print(f"  📊 {table_name}: (erro ao contar)")
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        print(f"\n🎉 Upload concluído com sucesso!")
        print(f"⏱️ Duração total: {duration}")
        print(f"📊 Total de registros: {len(df_vendas):,}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Erro durante o processo: {str(e)}")
        return False
        
    finally:
        # SEMPRE fechar a conexão
        if conn:
            try:
                conn.close()
                print("🔒 Conexão com MotherDuck fechada")
            except:
                pass

def main():
    """Função principal"""
    print("⚠️ ATENÇÃO: Este script irá coletar dados das APIs e fazer upload para o MotherDuck")
    print("Pressione Ctrl+C para cancelar se necessário")
    print()
    
    try:
        # Timeout total de 10 minutos
        sucesso = asyncio.run(
            asyncio.wait_for(upload_vendas_funcional(), timeout=600.0)
        )
        
        if sucesso:
            print("\n✅ Dados de vendas carregados com sucesso no MotherDuck!")
            print("🌐 Você pode agora validar visualmente no dashboard")
        else:
            print("\n❌ Falha no upload dos dados")
            
    except asyncio.TimeoutError:
        print("\n⏰ Timeout - operação demorou mais de 10 minutos")
    except KeyboardInterrupt:
        print("\n⚠️ Upload cancelado pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
    finally:
        print("\n🏁 Script finalizado")
        sys.exit(0)

if __name__ == "__main__":
    main()

