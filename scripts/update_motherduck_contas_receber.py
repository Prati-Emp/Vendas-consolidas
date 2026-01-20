#!/usr/bin/env python3
"""
Atualização Diária do Sienge Contas a Receber no MotherDuck
Executa a API de Income (Contas a Receber) e atualiza a tabela administracao.contas_recebidas_receber
Executa diariamente na madrugada
"""

import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Garante import do projeto quando rodar via Actions
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Importar controle de concorrência
from scripts.concurrency_control import check_concurrency, release_concurrency

async def sistema_contas_receber():
    """Sistema de atualização diária de contas a receber do Sienge"""
    print("SISTEMA DE ATUALIZACAO DIARIA - SIENGE CONTAS A RECEBER")
    print("=" * 60)
    print(f"Timestamp: {datetime.now()}")
    print(f"API: Sienge Income (Contas a Receber)")
    
    start_time = datetime.now()
    
    try:
        # Importar módulos necessários
        from scripts.cv_sienge_contas_receber_api import obter_dados_sienge_contas_receber
        import duckdb
        import pandas as pd
        
        # 1. Coletar dados
        print("\n1. Coletando dados de contas a receber do Sienge...")
        
        df_contas = obter_dados_sienge_contas_receber()
        
        if df_contas.empty:
            print("AVISO: Nenhum dado coletado de contas a receber")
            return False
        
        print(f"OK: Contas a Receber: {len(df_contas)} registros")
        
        # 2. Upload para MotherDuck (banco administracao)
        print("\n2. Fazendo upload para MotherDuck (banco administracao)...")
        
        # Configurar DuckDB
        duckdb.sql("INSTALL motherduck")
        duckdb.sql("LOAD motherduck")
        
        token = os.environ.get('MOTHERDUCK_TOKEN', '').strip()
        if not token:
            print("ERRO: MOTHERDUCK_TOKEN nao encontrado")
            return False
        
        # Configurar token corretamente
        duckdb.sql(f"SET motherduck_token='{token}'")
        conn = duckdb.connect('md:administracao')
        
        # Upload (substituição completa)
        print("   - Fazendo upload completo Sienge Contas a Receber (substituindo tabela)...")
        conn.register("df_contas_receber", df_contas)
        
        # Substituir tabela completamente (CREATE OR REPLACE)
        # Tabela solicitada: contas_recebidas_receber
        conn.execute("CREATE OR REPLACE TABLE contas_recebidas_receber AS SELECT * FROM df_contas_receber")
        
        count = conn.sql("SELECT COUNT(*) FROM contas_recebidas_receber").fetchone()[0]
        print(f"OK: Sienge Contas a Receber upload: {count:,} registros totais na tabela")
        
        # Verificar tabela criada
        print("\n3. Verificando tabela criada...")
        try:
            # Verificar estrutura da tabela
            colunas = conn.sql("DESCRIBE contas_recebidas_receber").fetchall()
            print(f"Colunas da tabela ({len(colunas)}):")
            for coluna in colunas[:15]:
                print(f"   - {coluna[0]} ({coluna[1]})")
            
            # Estatísticas básicas
            if 'Data_Snapshot' in df_contas.columns:
                stats = conn.sql("""
                    SELECT 
                        COUNT(*) as total_registros,
                        COUNT(DISTINCT ID_Titulo) as titulos_unicos,
                        COUNT(DISTINCT ID_Empresa) as empresas_unicas,
                        MIN(Data_Vencimento) as vencimento_mais_antigo,
                        MAX(Data_Vencimento) as vencimento_mais_recente,
                        SUM(Valor_Original) as valor_original_total,
                        SUM(Valor_Saldo) as saldo_total
                    FROM contas_recebidas_receber
                """).fetchone()
                
                print(f"\nEstatisticas da tabela:")
                print(f"   - Total de registros: {stats[0]:,}")
                print(f"   - Títulos únicos: {stats[1]:,}")
                print(f"   - Empresas únicas: {stats[2]:,}")
                print(f"   - Vencimento mais antigo: {stats[3]}")
                print(f"   - Vencimento mais recente: {stats[4]}")
                if stats[5] is not None:
                    print(f"   - Valor original total: R$ {stats[5]:,.2f}")
                if stats[6] is not None:
                    print(f"   - Saldo total: R$ {stats[6]:,.2f}")
            
        except Exception as e:
            print(f"AVISO: Erro ao verificar tabela: {e}")
        
        conn.close()
        
        # 4. Estatísticas finais
        end_time = datetime.now()
        duration = end_time - start_time
        
        print(f"\nATUALIZACAO CONTAS A RECEBER CONCLUIDA!")
        print(f"Duracao: {duration}")
        print(f"Resumo:")
        print(f"   - Registros: {len(df_contas):,}")
        print(f"   - Tabela: contas_recebidas_receber")
        print(f"   - Banco: administracao (MotherDuck)")
        
        return True
        
    except Exception as e:
        print(f"\nERRO na atualizacao de contas a receber: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Função principal para execução via GitHub Actions"""
    print("INICIANDO ATUALIZACAO DIARIA DE CONTAS A RECEBER DO MOTHERDUCK")
    print("=" * 60)
    print(f"Timestamp: {datetime.now()}")
    print(f"Working directory: {os.getcwd()}")
    
    # Verificar concorrência antes de executar
    print("\nVerificando controle de concorrencia...")
    if not check_concurrency():
        print("ERRO: Outro workflow esta executando. Abortando para evitar conflitos.")
        sys.exit(1)
    print("OK: Controle de concorrencia OK - Prosseguindo com execucao")
    
    # Carregar variáveis de ambiente
    load_dotenv()
    
    # Verificar variáveis críticas
    required_vars = ['MOTHERDUCK_TOKEN', 'SIENGE_TOKEN']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"ERRO: Variaveis de ambiente faltando: {', '.join(missing_vars)}")
        release_concurrency()
        sys.exit(1)
    
    print("OK: Variaveis de ambiente configuradas")
    
    try:
        # Executar com timeout de 30 minutos
        sucesso = asyncio.run(asyncio.wait_for(sistema_contas_receber(), timeout=1800.0))
        
        if sucesso:
            print("\nOK: ATUALIZACAO DE CONTAS A RECEBER CONCLUIDA COM SUCESSO!")
            release_concurrency()
            sys.exit(0)
        else:
            print("\nERRO: FALHA NA ATUALIZACAO DE CONTAS A RECEBER")
            release_concurrency()
            sys.exit(1)
            
    except asyncio.TimeoutError:
        print("\nTIMEOUT - Operacao demorou mais de 30 minutos")
        release_concurrency()
        sys.exit(1)
        
    except Exception as e:
        print(f"\nERRO INESPERADO: {e}")
        import traceback
        traceback.print_exc()
        release_concurrency()
        sys.exit(1)

if __name__ == "__main__":
    main()
