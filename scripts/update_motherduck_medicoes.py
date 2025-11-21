#!/usr/bin/env python3
"""
Atualização Mensal do Sienge Medições no MotherDuck
Executa a API de Building Cost Estimation Items e atualiza a tabela operacoes.sienge_medicoes
Executa uma vez por mês, no dia 7, buscando dados do mês anterior
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

async def sistema_medicoes():
    """Sistema de atualização mensal de medições do Sienge"""
    print("SISTEMA DE ATUALIZACAO MENSUAL - SIENGE MEDICOES")
    print("=" * 60)
    print(f"Timestamp: {datetime.now()}")
    print(f"API: Sienge Building Cost Estimation Items")
    
    start_time = datetime.now()
    
    try:
        # Importar módulos necessários
        from scripts.cv_sienge_medicoes_api import obter_dados_sienge_medicoes
        import duckdb
        import pandas as pd
        
        # 1. Coletar dados de medições
        print("\n1. Coletando dados de medições do Sienge...")
        
        # Configuração para primeira execução
        # IMPORTANTE: Altere modo_inicial para False após a primeira execução manual
        # True = busca todos os meses históricos (primeira execução)
        # False = busca apenas o mês anterior (execuções mensais automáticas)
        modo_inicial = os.environ.get('SIENGE_MEDICOES_MODO_INICIAL', 'false').lower() == 'true'
        
        if modo_inicial:
            print("🔄 Modo inicial ativado: buscando múltiplos meses históricos")
            # Configuração para buscar desde janeiro de 2025 até o mês anterior
            ano = 2025
            mes_inicio = 1
            mes_fim = None  # None = até o mês anterior
        else:
            print("🔄 Modo normal: buscando apenas o mês anterior")
            ano = None
            mes_inicio = None
            mes_fim = None
        
        df_medicoes = obter_dados_sienge_medicoes(
            modo_inicial=modo_inicial,
            ano=ano if modo_inicial else 2025,
            mes_inicio=mes_inicio if modo_inicial else 1,
            mes_fim=mes_fim
        )
        
        if df_medicoes.empty:
            print("AVISO: Nenhum dado coletado de medições")
            return False
        
        print(f"OK: Medições: {len(df_medicoes)} registros")
        
        # 2. Upload para MotherDuck (banco operacoes)
        print("\n2. Fazendo upload para MotherDuck (banco operacoes)...")
        
        # Configurar DuckDB
        duckdb.sql("INSTALL motherduck")
        duckdb.sql("LOAD motherduck")
        
        token = os.environ.get('MOTHERDUCK_TOKEN', '').strip()
        if not token:
            print("ERRO: MOTHERDUCK_TOKEN nao encontrado")
            return False
        
        # Configurar token corretamente
        duckdb.sql(f"SET motherduck_token='{token}'")
        conn = duckdb.connect('md:operacoes')
        
        # Upload Medições (incremental)
        print("   - Fazendo upload incremental Sienge Medições...")
        conn.register("df_medicoes", df_medicoes)
        
        # Verificar se a tabela existe
        tabela_existe = False
        try:
            conn.sql("SELECT 1 FROM sienge_medicoes LIMIT 1").fetchone()
            tabela_existe = True
            print("   - Tabela já existe, fazendo atualização incremental...")
        except:
            print("   - Tabela não existe, criando nova tabela...")
        
        if tabela_existe:
            # Obter Data_Snapshot dos novos dados para deletar duplicatas
            if 'Data_Snapshot' in df_medicoes.columns:
                # Obter datas únicas dos novos dados e converter para string
                datas_novas = df_medicoes['Data_Snapshot'].unique()
                datas_formatadas = []
                for d in datas_novas:
                    if isinstance(d, pd.Timestamp):
                        datas_formatadas.append(d.strftime('%Y-%m-%d'))
                    elif isinstance(d, str):
                        datas_formatadas.append(d[:10])  # Pega apenas a parte da data
                    else:
                        # Tentar converter
                        try:
                            dt = pd.to_datetime(d)
                            datas_formatadas.append(dt.strftime('%Y-%m-%d'))
                        except:
                            continue
                
                if datas_formatadas:
                    datas_str = "', '".join(datas_formatadas)
                    
                    # Contar registros antes da deleção
                    count_antes = conn.sql("SELECT COUNT(*) FROM sienge_medicoes").fetchone()[0]
                    
                    print(f"   - Removendo registros existentes para as datas: {', '.join(datas_formatadas)}")
                    # Deletar registros com as mesmas datas (para evitar duplicatas)
                    conn.execute(f"""
                        DELETE FROM sienge_medicoes 
                        WHERE DATE(Data_Snapshot) IN ('{datas_str}')
                    """)
                    
                    # Contar registros depois da deleção
                    count_depois = conn.sql("SELECT COUNT(*) FROM sienge_medicoes").fetchone()[0]
                    registros_deletados = count_antes - count_depois
                    print(f"   - Registros removidos: {registros_deletados}")
            
            # Inserir novos registros
            print("   - Inserindo novos registros...")
            conn.execute("INSERT INTO sienge_medicoes SELECT * FROM df_medicoes")
        else:
            # Criar tabela pela primeira vez
            conn.execute("CREATE TABLE sienge_medicoes AS SELECT * FROM df_medicoes")
        
        count_medicoes = conn.sql("SELECT COUNT(*) FROM sienge_medicoes").fetchone()[0]
        print(f"OK: Sienge Medições upload: {count_medicoes:,} registros totais na tabela")
        
        # Verificar tabela criada
        print("\n3. Verificando tabela criada...")
        try:
            # Verificar estrutura da tabela
            colunas = conn.sql("DESCRIBE sienge_medicoes").fetchall()
            print(f"Colunas da tabela ({len(colunas)}):")
            for coluna in colunas[:10]:  # Mostrar apenas as primeiras 10
                print(f"   - {coluna[0]} ({coluna[1]})")
            if len(colunas) > 10:
                print(f"   ... e mais {len(colunas) - 10} colunas")
            
            # Estatísticas básicas
            if 'Data_Snapshot' in df_medicoes.columns:
                stats = conn.sql("""
                    SELECT 
                        COUNT(*) as total_registros,
                        COUNT(DISTINCT ID_Empreendimento) as empreendimentos_unicos,
                        MIN(Data_Snapshot) as data_mais_antiga,
                        MAX(Data_Snapshot) as data_mais_recente,
                        SUM(Preco_total) as preco_total
                    FROM sienge_medicoes
                """).fetchone()
                
                print(f"\nEstatisticas da tabela:")
                print(f"   - Total de registros: {stats[0]:,}")
                print(f"   - Empreendimentos unicos: {stats[1]:,}")
                print(f"   - Data mais antiga: {stats[2]}")
                print(f"   - Data mais recente: {stats[3]}")
                if stats[4] is not None:
                    print(f"   - Preço total: R$ {stats[4]:,.2f}")
            
        except Exception as e:
            print(f"AVISO: Erro ao verificar tabela: {e}")
        
        conn.close()
        
        # 4. Estatísticas finais
        end_time = datetime.now()
        duration = end_time - start_time
        
        print(f"\nATUALIZACAO MEDICOES CONCLUIDA!")
        print(f"Duracao: {duration}")
        print(f"Resumo:")
        print(f"   - Sienge Medições: {len(df_medicoes):,} registros")
        print(f"   - Tabela: sienge_medicoes")
        print(f"   - Banco: operacoes (MotherDuck)")
        
        return True
        
    except Exception as e:
        print(f"\nERRO na atualizacao de medicoes: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Função principal para execução via GitHub Actions"""
    print("INICIANDO ATUALIZACAO MENSUAL DE MEDICOES DO MOTHERDUCK")
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
    required_vars = ['MOTHERDUCK_TOKEN', 'SIENGE_TOKEN']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"ERRO: Variaveis de ambiente faltando: {', '.join(missing_vars)}")
        release_concurrency()  # Liberar lock em caso de erro
        sys.exit(1)
    
    print("OK: Variaveis de ambiente configuradas")
    
    try:
        # Executar com timeout de 30 minutos (pode ser mais demorado)
        sucesso = asyncio.run(asyncio.wait_for(sistema_medicoes(), timeout=1800.0))
        
        if sucesso:
            print("\nOK: ATUALIZACAO DE MEDICOES CONCLUIDA COM SUCESSO!")
            print("Dados atualizados no MotherDuck")
            print("Dashboard pode ser consultado para validacao")
            release_concurrency()  # Liberar lock em caso de sucesso
            sys.exit(0)
        else:
            print("\nERRO: FALHA NA ATUALIZACAO DE MEDICOES")
            print("Verifique os logs acima para detalhes")
            release_concurrency()  # Liberar lock em caso de falha
            sys.exit(1)
            
    except asyncio.TimeoutError:
        print("\nTIMEOUT - Operacao demorou mais de 30 minutos")
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

