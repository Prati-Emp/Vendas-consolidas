#!/usr/bin/env python3
"""
Atualização Diária do CV Comissões no MotherDuck
Executa a API de Comissões e atualiza a tabela reservas.cv_comissoes
Executa diariamente às 03:45 BRT
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

async def sistema_comissoes():
    """Sistema de atualização diária de comissões do CV CRM"""
    print("SISTEMA DE ATUALIZACAO DIARIA - CV COMISSOES")
    print("=" * 60)
    print(f"Timestamp: {datetime.now()}")
    print(f"API: CV CRM Comissões")
    
    start_time = datetime.now()
    
    try:
        # Importar módulos necessários
        from scripts.cv_comissoes_api import obter_dados_cv_comissoes
        import duckdb
        import pandas as pd
        
        # 1. Coletar dados
        print("\n1. Coletando dados de comissões do CV CRM...")
        
        df_comissoes = obter_dados_cv_comissoes()
        
        if df_comissoes.empty:
            print("AVISO: Nenhum dado coletado de comissões")
            return False
        
        print(f"OK: Comissões: {len(df_comissoes)} registros")
        
        # 2. Upload para MotherDuck (banco reservas)
        print("\n2. Fazendo upload para MotherDuck (banco reservas)...")
        
        # Configurar DuckDB
        duckdb.sql("INSTALL motherduck")
        duckdb.sql("LOAD motherduck")
        
        token = os.environ.get('MOTHERDUCK_TOKEN', '').strip()
        if not token:
            print("ERRO: MOTHERDUCK_TOKEN nao encontrado")
            return False
        
        # Configurar token corretamente
        duckdb.sql(f"SET motherduck_token='{token}'")
        conn = duckdb.connect('md:reservas')
        
        # Upload (substituição completa)
        print("   - Fazendo upload completo CV Comissões (substituindo tabela)...")
        conn.register("df_comissoes", df_comissoes)
        
        # Substituir tabela completamente (CREATE OR REPLACE)
        # Tabela solicitada: cv_comissoes
        conn.execute("CREATE OR REPLACE TABLE cv_comissoes AS SELECT * FROM df_comissoes")
        
        count = conn.sql("SELECT COUNT(*) FROM cv_comissoes").fetchone()[0]
        print(f"OK: CV Comissões upload: {count:,} registros totais na tabela")
        
        # Verificar tabela criada
        print("\n3. Verificando tabela criada...")
        try:
            # Verificar estrutura da tabela
            colunas = conn.sql("DESCRIBE cv_comissoes").fetchall()
            print(f"Colunas da tabela ({len(colunas)}):")
            for coluna in colunas[:15]:
                print(f"   - {coluna[0]} ({coluna[1]})")
            
            # Estatísticas básicas
            if 'Data_Snapshot' in df_comissoes.columns:
                stats = conn.sql("""
                    SELECT 
                        COUNT(*) as total_registros,
                        COUNT(DISTINCT idcomissao_cv) as comissoes_unicas,
                        COUNT(DISTINCT idreserva_cv) as reservas_unicas,
                        COUNT(DISTINCT beneficiario_nome) as beneficiarios_unicos,
                        MIN(data_pagamento) as pagamento_mais_antigo,
                        MAX(data_pagamento) as pagamento_mais_recente,
                        SUM(valor_parcela) as valor_total_parcelas,
                        SUM(valor_comissao_total) as valor_total_comissoes
                    FROM cv_comissoes
                """).fetchone()
                
                print(f"\nEstatisticas da tabela:")
                print(f"   - Total de registros: {stats[0]:,}")
                print(f"   - Comissões únicas: {stats[1]:,}")
                print(f"   - Reservas únicas: {stats[2]:,}")
                print(f"   - Beneficiários únicos: {stats[3]:,}")
                print(f"   - Pagamento mais antigo: {stats[4]}")
                print(f"   - Pagamento mais recente: {stats[5]}")
                if stats[6] is not None:
                    print(f"   - Valor total parcelas: R$ {stats[6]:,.2f}")
                if stats[7] is not None:
                    print(f"   - Valor total comissões: R$ {stats[7]:,.2f}")
            
        except Exception as e:
            print(f"AVISO: Erro ao verificar tabela: {e}")
        
        conn.close()
        
        # 4. Estatísticas finais
        end_time = datetime.now()
        duration = end_time - start_time
        
        print(f"\nATUALIZACAO COMISSOES CONCLUIDA!")
        print(f"Duracao: {duration}")
        print(f"Resumo:")
        print(f"   - Registros: {len(df_comissoes):,}")
        print(f"   - Tabela: cv_comissoes")
        print(f"   - Banco: reservas (MotherDuck)")
        
        return True
        
    except Exception as e:
        print(f"\nERRO na atualizacao de comissoes: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Função principal para execução via GitHub Actions"""
    print("INICIANDO ATUALIZACAO DIARIA DE COMISSOES DO MOTHERDUCK")
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
    required_vars = ['MOTHERDUCK_TOKEN', 'CVCRM_EMAIL', 'CVCRM_TOKEN']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"ERRO: Variaveis de ambiente faltando: {', '.join(missing_vars)}")
        release_concurrency()
        sys.exit(1)
    
    print("OK: Variaveis de ambiente configuradas")
    
    try:
        # Executar com timeout de 30 minutos
        sucesso = asyncio.run(asyncio.wait_for(sistema_comissoes(), timeout=1800.0))
        
        if sucesso:
            print("\nOK: ATUALIZACAO DE COMISSOES CONCLUIDA COM SUCESSO!")
            release_concurrency()
            sys.exit(0)
        else:
            print("\nERRO: FALHA NA ATUALIZACAO DE COMISSOES")
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
