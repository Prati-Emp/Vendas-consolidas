#!/usr/bin/env python3
"""
Script simples para adicionar apenas a tabela Sienge Vendas Realizadas
"""

import os
import duckdb
import pandas as pd
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from scripts.sienge_apis import obter_dados_sienge_vendas_realizadas

async def adicionar_sienge_realizadas():
    """Adiciona apenas a tabela de vendas realizadas do Sienge"""
    print("🚀 ADICIONANDO SIENGE VENDAS REALIZADAS")
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
        
        # 4. Coletar dados do Sienge
        print("\n4. Coletando dados do Sienge - Vendas Realizadas...")
        df_sienge = await obter_dados_sienge_vendas_realizadas()
        
        if df_sienge.empty:
            print("⚠️ Nenhum dado coletado do Sienge")
            return False
        
        print(f"✅ Dados coletados: {len(df_sienge)} registros")
        print(f"📊 Colunas: {len(df_sienge.columns)}")
        
        # 5. Criar tabela no MotherDuck
        print("\n5. Criando tabela sienge_vendas_realizadas...")
        
        # Remover tabela existente se houver
        conn.sql("DROP TABLE IF EXISTS main.sienge_vendas_realizadas")
        print("✅ Tabela antiga removida (se existia)")
        
        # Criar nova tabela
        conn.execute("CREATE TABLE main.sienge_vendas_realizadas AS SELECT * FROM df_sienge")
        print("✅ Nova tabela criada")
        
        # Verificar
        count = conn.sql("SELECT COUNT(*) FROM main.sienge_vendas_realizadas").fetchone()[0]
        print(f"✅ Tabela 'sienge_vendas_realizadas' criada com {count:,} registros")
        
        # 6. Mostrar algumas colunas
        print("\n6. Estrutura da tabela:")
        columns = conn.sql("DESCRIBE main.sienge_vendas_realizadas").fetchall()
        print(f"📋 Total de colunas: {len(columns)}")
        for i, col in enumerate(columns[:10]):  # Mostrar apenas as primeiras 10
            print(f"   {i+1}. {col[0]} ({col[1]})")
        if len(columns) > 10:
            print(f"   ... e mais {len(columns)-10} colunas")
        
        # 7. Listar todas as tabelas de vendas
        print("\n7. Tabelas de vendas no banco:")
        tabelas_vendas = ['cv_vendas', 'sienge_vendas_realizadas', 'sienge_vendas_canceladas']
        
        for tabela in tabelas_vendas:
            try:
                count = conn.sql(f"SELECT COUNT(*) FROM main.{tabela}").fetchone()[0]
                print(f"  📊 {tabela}: {count:,} registros")
            except:
                print(f"  📊 {tabela}: não existe")
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        print(f"\n🎉 Sienge Vendas Realizadas adicionada com sucesso!")
        print(f"⏱️ Duração: {duration}")
        print(f"📊 Registros: {len(df_sienge):,}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Erro durante o processo: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        if conn:
            try:
                conn.close()
                print("🔒 Conexão com MotherDuck fechada")
            except:
                pass

if __name__ == "__main__":
    print("⚠️ ATENÇÃO: Este script irá adicionar apenas a tabela Sienge Vendas Realizadas")
    print("Pressione Ctrl+C para cancelar se necessário")
    print()
    
    try:
        sucesso = asyncio.run(adicionar_sienge_realizadas())
        
        if sucesso:
            print("\n✅ Tabela sienge_vendas_realizadas criada com sucesso!")
        else:
            print("\n❌ Falha ao criar a tabela")
            
    except KeyboardInterrupt:
        print("\n⚠️ Operação cancelada pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
    finally:
        print("\n🏁 Script finalizado")
