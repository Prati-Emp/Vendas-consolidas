#!/usr/bin/env python3
"""
Atualização do Jira DHO no MotherDuck
Executa a API do Jira para o projeto DHO e atualiza a tabela Jira_projeto_dho
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Garante import do projeto quando rodar via Actions
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Importar controle de concorrência
from scripts.concurrency_control import check_concurrency, release_concurrency

def sistema_jira_dho():
    """Sistema de atualização do Jira DHO"""
    print("SISTEMA DE ATUALIZACAO JIRA DHO")
    print("=" * 60)
    print(f"Timestamp: {datetime.now()}")
    print(f"API: Jira Issues - Projeto DHO")
    
    start_time = datetime.now()
    
    try:
        # Importar módulos necessários
        from scripts.cv_jira_dho_api import obter_dados_jira_dho
        import duckdb
        import pandas as pd
        
        # 1. Coletar dados do Jira DHO
        print("\n1. Coletando dados do projeto DHO do Jira...")
        df_jira_dho = obter_dados_jira_dho()
        
        if df_jira_dho.empty:
            print("AVISO: Nenhum dado coletado do Jira DHO")
            return False
        
        print(f"OK: Jira DHO: {len(df_jira_dho)} registros")
        
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
        
        # Upload Jira DHO (substituição completa)
        print("   - Fazendo upload Jira DHO...")
        conn.register("df_jira_dho", df_jira_dho)
        conn.execute("CREATE OR REPLACE TABLE Jira_projeto_dho AS SELECT * FROM df_jira_dho")
        count_jira_dho = conn.sql("SELECT COUNT(*) FROM Jira_projeto_dho").fetchone()[0]
        print(f"OK: Jira DHO upload: {count_jira_dho:,} registros")
        
        # Verificar tabela criada
        print("\n3. Verificando tabela criada...")
        try:
            # Verificar estrutura da tabela
            colunas = conn.sql("DESCRIBE Jira_projeto_dho").fetchall()
            print(f"Colunas da tabela ({len(colunas)}):")
            for coluna in colunas[:15]:  # Mostrar apenas as primeiras 15
                print(f"   - {coluna[0]} ({coluna[1]})")
            if len(colunas) > 15:
                print(f"   ... e mais {len(colunas) - 15} colunas")
            
            # Estatísticas básicas
            if 'Chave' in df_jira_dho.columns or 'key' in df_jira_dho.columns:
                col_key = 'Chave' if 'Chave' in df_jira_dho.columns else 'key'
                stats = conn.sql(f"""
                    SELECT 
                        COUNT(*) as total_registros,
                        COUNT(DISTINCT "{col_key}") as issues_unicas
                    FROM Jira_projeto_dho
                """).fetchone()
                
                print(f"\nEstatisticas da tabela:")
                print(f"   - Total de registros: {stats[0]:,}")
                print(f"   - Issues unicas: {stats[1]:,}")
            
        except Exception as e:
            print(f"AVISO: Erro ao verificar tabela: {e}")
        
        conn.close()
        
        # 4. Estatísticas finais
        end_time = datetime.now()
        duration = end_time - start_time
        
        print(f"\nATUALIZACAO JIRA DHO CONCLUIDA!")
        print(f"Duracao: {duration}")
        print(f"Resumo:")
        print(f"   - Jira DHO Issues: {len(df_jira_dho):,} registros")
        print(f"   - Tabela: Jira_projeto_dho")
        print(f"   - Banco: reservas (MotherDuck)")
        
        return True
        
    except Exception as e:
        print(f"\nERRO na atualizacao Jira DHO: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Função principal para execução via GitHub Actions"""
    print("INICIANDO ATUALIZACAO JIRA DHO DO MOTHERDUCK")
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
        # Executar sistema
        sucesso = sistema_jira_dho()
        
        if sucesso:
            print("\nOK: ATUALIZACAO JIRA DHO CONCLUIDA COM SUCESSO!")
            print("Dados atualizados no MotherDuck")
            print("Dashboard pode ser consultado para validacao")
            release_concurrency()  # Liberar lock em caso de sucesso
            sys.exit(0)
        else:
            print("\nERRO: FALHA NA ATUALIZACAO JIRA DHO")
            print("Verifique os logs acima para detalhes")
            release_concurrency()  # Liberar lock em caso de falha
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

