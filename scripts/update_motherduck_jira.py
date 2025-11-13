#!/usr/bin/env python3
"""
Atualização do Jira no MotherDuck
Executa a API do Jira e atualiza a tabela jira_issues
Script separado devido ao tempo de execução mais longo
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

async def sistema_jira():
    """Sistema de atualização do Jira"""
    print("SISTEMA DE ATUALIZACAO JIRA")
    print("=" * 60)
    print(f"Timestamp: {datetime.now()}")
    print(f"API: Jira Issues")
    
    start_time = datetime.now()
    
    try:
        # Importar módulos necessários
        from scripts.cv_jira_api import obter_dados_jira
        import duckdb
        import pandas as pd
        
        # 1. Coletar dados do Jira
        print("\n1. Coletando dados do Jira...")
        df_jira = await obter_dados_jira()
        
        if df_jira.empty:
            print("AVISO: Nenhum dado coletado do Jira")
            return False
        
        print(f"OK: Jira: {len(df_jira)} registros")
        
        # 2. Upload para MotherDuck
        print("\n2. Fazendo upload para MotherDuck...")
        
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
        
        # Upload Jira
        print("   - Fazendo upload Jira Issues...")
        conn.register("df_jira", df_jira)
        conn.execute("CREATE OR REPLACE TABLE main.jira_issues AS SELECT * FROM df_jira")
        count_jira = conn.sql("SELECT COUNT(*) FROM main.jira_issues").fetchone()[0]
        print(f"OK: Jira Issues upload: {count_jira:,} registros")
        
        # Verificar tabela criada
        print("\n3. Verificando tabela criada...")
        try:
            # Verificar estrutura da tabela
            colunas = conn.sql("DESCRIBE main.jira_issues").fetchall()
            print(f"Colunas da tabela ({len(colunas)}):")
            for coluna in colunas[:10]:  # Mostrar apenas as primeiras 10
                print(f"   - {coluna[0]} ({coluna[1]})")
            if len(colunas) > 10:
                print(f"   ... e mais {len(colunas) - 10} colunas")
            
            # Estatísticas básicas
            stats = conn.sql("""
                SELECT 
                    COUNT(*) as total_registros,
                    COUNT(DISTINCT "B - Chave") as issues_unicas,
                    COUNT(DISTINCT "Z - Projeto.name") as projetos_unicos,
                    MIN("I - Criado") as data_mais_antiga,
                    MAX("I - Criado") as data_mais_recente
                FROM main.jira_issues
            """).fetchone()
            
            print(f"\nEstatisticas da tabela:")
            print(f"   - Total de registros: {stats[0]:,}")
            print(f"   - Issues unicas: {stats[1]:,}")
            print(f"   - Projetos unicos: {stats[2]:,}")
            print(f"   - Data mais antiga: {stats[3]}")
            print(f"   - Data mais recente: {stats[4]}")
            
        except Exception as e:
            print(f"AVISO: Erro ao verificar tabela: {e}")
        
        conn.close()
        
        # 4. Estatísticas finais
        end_time = datetime.now()
        duration = end_time - start_time
        
        print(f"\nATUALIZACAO JIRA CONCLUIDA!")
        print(f"Duracao: {duration}")
        print(f"Resumo:")
        print(f"   - Jira Issues: {len(df_jira):,} registros")
        print(f"   - Tabela: main.jira_issues")
        print(f"   - Banco: reservas (MotherDuck)")
        
        return True
        
    except Exception as e:
        print(f"\nERRO na atualizacao Jira: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Função principal para execução via GitHub Actions"""
    print("INICIANDO ATUALIZACAO JIRA DO MOTHERDUCK")
    print("=" * 60)
    print(f"Timestamp: {datetime.now()}")
    print(f"Python: {sys.version}")
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
    required_vars = ['MOTHERDUCK_TOKEN', 'JIRA_URL', 'JIRA_EMAIL', 'JIRA_TOKEN']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"ERRO: Variaveis de ambiente faltando: {', '.join(missing_vars)}")
        release_concurrency()  # Liberar lock em caso de erro
        sys.exit(1)
    
    print("OK: Variaveis de ambiente configuradas")
    
    try:
        # Executar com timeout de 60 minutos (Jira é mais demorado)
        sucesso = asyncio.run(asyncio.wait_for(sistema_jira(), timeout=3600.0))
        
        if sucesso:
            print("\nOK: ATUALIZACAO JIRA CONCLUIDA COM SUCESSO!")
            print("Dados atualizados no MotherDuck")
            print("Dashboard pode ser consultado para validacao")
            release_concurrency()  # Liberar lock em caso de sucesso
            sys.exit(0)
        else:
            print("\nERRO: FALHA NA ATUALIZACAO JIRA")
            print("Verifique os logs acima para detalhes")
            release_concurrency()  # Liberar lock em caso de falha
            sys.exit(1)
            
    except asyncio.TimeoutError:
        print("\nTIMEOUT - Operacao demorou mais de 60 minutos")
        print("Considere otimizar o pipeline ou aumentar o timeout")
        release_concurrency()  # Liberar lock em caso de timeout
        sys.exit(1)
        
    except ImportError as e:
        print(f"\nERRO DE IMPORTACAO: {e}")
        print("Verifique se todos os modulos estao disponiveis")
        release_concurrency()  # Liberar lock em caso de erro de importação
        sys.exit(1)
        
    except Exception as e:
        print(f"\nERRO INESPERADO: {e}")
        print("Verifique a configuracao e conectividade")
        import traceback
        traceback.print_exc()
        release_concurrency()  # Liberar lock em caso de erro inesperado
        sys.exit(1)

if __name__ == "__main__":
    main()

