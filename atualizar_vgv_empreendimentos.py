#!/usr/bin/env python3
"""
Script para atualização diária dos dados VGV Empreendimentos
Integra com o sistema existente e faz upload para MotherDuck
"""

import os
import duckdb
import pandas as pd
import asyncio
import sys
from datetime import datetime
from dotenv import load_dotenv
from scripts.cv_vgv_empreendimentos_api import obter_dados_vgv_empreendimentos

async def upload_vgv_empreendimentos_motherduck(df_vgv_empreendimentos):
    """Faz upload dos dados VGV Empreendimentos para o MotherDuck"""
    print("\n📤 FAZENDO UPLOAD VGV EMPREENDIMENTOS PARA MOTHERDUCK")
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
        
        # Upload VGV Empreendimentos
        print(f"3. VGV Empreendimentos - linhas no DataFrame: {len(df_vgv_empreendimentos):,}")
        if not df_vgv_empreendimentos.empty:
            print("   Fazendo upload VGV Empreendimentos...")
            conn.register("df_vgv_empreendimentos", df_vgv_empreendimentos)
            conn.execute("CREATE OR REPLACE TABLE main.cv_vgv_empreendimentos AS SELECT * FROM df_vgv_empreendimentos")
            count_vgv = conn.sql("SELECT COUNT(*) FROM main.cv_vgv_empreendimentos").fetchone()[0]
            print(f"   ✅ VGV Empreendimentos: {count_vgv:,} registros")
        else:
            print("   ⚠️ Nenhum dado VGV Empreendimentos para upload")
        
        # Verificar tabela criada
        print("\n4. Verificando tabela criada:")
        try:
            count_final = conn.sql("SELECT COUNT(*) FROM main.cv_vgv_empreendimentos").fetchone()[0]
            print(f"   📊 Total de registros na tabela: {count_final:,}")
            
            # Mostrar algumas colunas para verificação
            colunas = conn.sql("DESCRIBE main.cv_vgv_empreendimentos").fetchall()
            print(f"   📋 Colunas da tabela: {len(colunas)}")
            for col in colunas[:5]:  # Mostrar apenas as primeiras 5 colunas
                print(f"      - {col[0]}: {col[1]}")
            if len(colunas) > 5:
                print(f"      ... e mais {len(colunas) - 5} colunas")
                
        except Exception as e:
            print(f"   ❌ Erro ao verificar tabela: {e}")
        
        conn.close()
        print("✅ Upload VGV Empreendimentos concluído com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro no upload VGV Empreendimentos: {str(e)}")
        return False

async def atualizar_vgv_empreendimentos_completo():
    """Atualização completa dos dados VGV Empreendimentos"""
    print("ATUALIZACAO VGV EMPREENDIMENTOS")
    print("=" * 50)
    
    start_time = datetime.now()
    
    try:
        # 1. Carregar configurações
        print("1. Carregando configurações...")
        load_dotenv()
        
        # Verificar variáveis de ambiente
        env_vars = ['CVCRM_EMAIL', 'CVCRM_TOKEN', 'MOTHERDUCK_TOKEN']
        for var in env_vars:
            if not os.environ.get(var):
                print(f"❌ {var} não encontrado")
                return False
        
        print("SUCESSO: Configuracoes carregadas")
        
        # 2. Coletar dados VGV Empreendimentos
        print("\n2. Coletando dados VGV Empreendimentos...")
        df_vgv_empreendimentos = await obter_dados_vgv_empreendimentos(1, 20)  # IDs 1-20
        print(f"✅ VGV Empreendimentos coletados: {len(df_vgv_empreendimentos)} registros")
        
        if df_vgv_empreendimentos.empty:
            print("⚠️ Nenhum dado coletado - encerrando")
            return False
        
        # 3. Upload para MotherDuck
        print("\n3. Fazendo upload para MotherDuck...")
        sucesso_upload = await upload_vgv_empreendimentos_motherduck(df_vgv_empreendimentos)
        
        # 4. Estatísticas finais
        end_time = datetime.now()
        duration = end_time - start_time
        
        print(f"\n🎉 ATUALIZAÇÃO VGV EMPREENDIMENTOS FINALIZADA!")
        print(f"⏱️ Duração total: {duration}")
        print(f"📊 Resumo:")
        print(f"   - VGV Empreendimentos: {len(df_vgv_empreendimentos):,} registros")
        print(f"   - Upload: {'✅ Sucesso' if sucesso_upload else '❌ Falha'}")
        
        return sucesso_upload
        
    except Exception as e:
        print(f"\n❌ Erro na atualização VGV Empreendimentos: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Função principal"""
    print("ATENCAO: Este script ira atualizar os dados VGV Empreendimentos no MotherDuck")
    print("Pressione Ctrl+C para cancelar se necessario")
    print()
    
    try:
        # Timeout total de 10 minutos
        sucesso = asyncio.run(
            asyncio.wait_for(atualizar_vgv_empreendimentos_completo(), timeout=600.0)
        )
        
        if sucesso:
            print("\nSUCESSO: Atualizacao VGV Empreendimentos executada com sucesso!")
            print("Voce pode agora validar visualmente no dashboard")
        else:
            print("\nERRO: Falha na execucao da atualizacao VGV Empreendimentos")
            
    except asyncio.TimeoutError:
        print("\nTIMEOUT - operacao demorou mais de 10 minutos")
    except KeyboardInterrupt:
        print("\nCANCELADO: Atualizacao cancelada pelo usuario")
    except Exception as e:
        print(f"\nERRO INESPERADO: {e}")
    finally:
        print("\nAtualizacao finalizada")
        sys.exit(0)

if __name__ == "__main__":
    main()
