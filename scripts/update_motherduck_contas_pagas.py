#!/usr/bin/env python3
"""
Atualização Diária do Sienge Contas Pagas no MotherDuck
Executa a API de Outcome (Contas Pagas e a Pagar) e atualiza a tabela administracao.sienge_contas_pagas_e_a_pagar
Executa diariamente na madrugada, buscando dados dos últimos 30 dias
"""

import asyncio
import os
import sys
from datetime import datetime, date, timedelta
from dotenv import load_dotenv

# Garante import do projeto quando rodar via Actions
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Importar controle de concorrência
from scripts.concurrency_control import check_concurrency, release_concurrency

async def sistema_contas_pagas():
    """Sistema de atualização diária de contas pagas do Sienge"""
    print("SISTEMA DE ATUALIZACAO DIARIA - SIENGE CONTAS PAGAS")
    print("=" * 60)
    print(f"Timestamp: {datetime.now()}")
    print(f"API: Sienge Outcome (Contas Pagas e a Pagar)")
    
    start_time = datetime.now()
    
    try:
        # Importar módulos necessários
        from scripts.cv_sienge_contas_pagas_api import obter_dados_sienge_contas_pagas
        import duckdb
        import pandas as pd
        
        # 1. Coletar dados de contas pagas
        print("\n1. Coletando dados de contas pagas do Sienge...")
        
        # Busca dados dos últimos 30 dias (padrão)
        # Para primeira execução, pode buscar desde 2025-01-01
        dias_retrocesso = int(os.environ.get('SIENGE_CONTAS_PAGAS_DIAS_RETRO', '30'))
        
        # Para primeira execução, pode usar modo inicial
        modo_inicial = os.environ.get('SIENGE_CONTAS_PAGAS_MODO_INICIAL', 'false').lower() == 'true'
        
        if modo_inicial:
            print("🔄 Modo inicial ativado: buscando desde 2025-01-01")
            data_inicio = "2025-01-01"
            data_fim = date.today().strftime("%Y-%m-%d")
            dias_retrocesso = None  # Não usar dias_retrocesso no modo inicial
        else:
            print(f"🔄 Modo normal: buscando últimos {dias_retrocesso} dias")
            data_inicio = None  # Será calculado dentro da função
            data_fim = None  # Será calculado dentro da função
        
        df_contas_pagas = obter_dados_sienge_contas_pagas(
            data_inicio=data_inicio,
            data_fim=data_fim,
            dias_retrocesso=dias_retrocesso
        )
        
        if df_contas_pagas.empty:
            print("AVISO: Nenhum dado coletado de contas pagas")
            return False
        
        print(f"OK: Contas Pagas: {len(df_contas_pagas)} registros")
        
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
        
        # Upload Contas Pagas (incremental)
        print("   - Fazendo upload incremental Sienge Contas Pagas...")
        conn.register("df_contas_pagas", df_contas_pagas)
        
        # Verificar se a tabela existe
        tabela_existe = False
        try:
            conn.sql("SELECT 1 FROM sienge_contas_pagas_e_a_pagar LIMIT 1").fetchone()
            tabela_existe = True
            print("   - Tabela já existe, fazendo atualização incremental...")
        except:
            print("   - Tabela não existe, criando nova tabela...")
        
        if tabela_existe:
            # Obter Data_Snapshot dos novos dados para deletar duplicatas
            if 'Data_Snapshot' in df_contas_pagas.columns:
                # Obter data única dos novos dados e converter para string
                data_snapshot = df_contas_pagas['Data_Snapshot'].iloc[0]
                
                if isinstance(data_snapshot, pd.Timestamp):
                    data_snapshot_str = data_snapshot.strftime('%Y-%m-%d')
                elif isinstance(data_snapshot, str):
                    data_snapshot_str = data_snapshot[:10]  # Pega apenas a parte da data
                else:
                    try:
                        dt = pd.to_datetime(data_snapshot)
                        data_snapshot_str = dt.strftime('%Y-%m-%d')
                    except:
                        data_snapshot_str = date.today().strftime('%Y-%m-%d')
                
                # Contar registros antes da deleção
                count_antes = conn.sql("SELECT COUNT(*) FROM sienge_contas_pagas_e_a_pagar").fetchone()[0]
                
                print(f"   - Removendo registros existentes para Data_Snapshot: {data_snapshot_str}")
                # Deletar registros com a mesma data (para evitar duplicatas)
                conn.execute(f"""
                    DELETE FROM sienge_contas_pagas_e_a_pagar 
                    WHERE DATE(Data_Snapshot) = '{data_snapshot_str}'
                """)
                
                # Contar registros depois da deleção
                count_depois = conn.sql("SELECT COUNT(*) FROM sienge_contas_pagas_e_a_pagar").fetchone()[0]
                registros_deletados = count_antes - count_depois
                print(f"   - Registros removidos: {registros_deletados}")
            
            # Inserir novos registros
            print("   - Inserindo novos registros...")
            conn.execute("INSERT INTO sienge_contas_pagas_e_a_pagar SELECT * FROM df_contas_pagas")
        else:
            # Criar tabela pela primeira vez
            conn.execute("CREATE TABLE sienge_contas_pagas_e_a_pagar AS SELECT * FROM df_contas_pagas")
        
        count_contas_pagas = conn.sql("SELECT COUNT(*) FROM sienge_contas_pagas_e_a_pagar").fetchone()[0]
        print(f"OK: Sienge Contas Pagas upload: {count_contas_pagas:,} registros totais na tabela")
        
        # Verificar tabela criada
        print("\n3. Verificando tabela criada...")
        try:
            # Verificar estrutura da tabela
            colunas = conn.sql("DESCRIBE sienge_contas_pagas_e_a_pagar").fetchall()
            print(f"Colunas da tabela ({len(colunas)}):")
            for coluna in colunas[:15]:  # Mostrar apenas as primeiras 15
                print(f"   - {coluna[0]} ({coluna[1]})")
            if len(colunas) > 15:
                print(f"   ... e mais {len(colunas) - 15} colunas")
            
            # Estatísticas básicas
            if 'Data_Snapshot' in df_contas_pagas.columns:
                stats = conn.sql("""
                    SELECT 
                        COUNT(*) as total_registros,
                        COUNT(DISTINCT Titulo) as titulos_unicos,
                        COUNT(DISTINCT Cod_empresa) as empresas_unicas,
                        MIN(Data_Snapshot) as data_mais_antiga,
                        MAX(Data_Snapshot) as data_mais_recente,
                        SUM(Valor_bruto) as valor_bruto_total,
                        SUM(Saldo_em_aberto) as saldo_aberto_total
                    FROM sienge_contas_pagas_e_a_pagar
                """).fetchone()
                
                print(f"\nEstatisticas da tabela:")
                print(f"   - Total de registros: {stats[0]:,}")
                print(f"   - Títulos únicos: {stats[1]:,}")
                print(f"   - Empresas únicas: {stats[2]:,}")
                print(f"   - Data mais antiga: {stats[3]}")
                print(f"   - Data mais recente: {stats[4]}")
                if stats[5] is not None:
                    print(f"   - Valor bruto total: R$ {stats[5]:,.2f}")
                if stats[6] is not None:
                    print(f"   - Saldo em aberto total: R$ {stats[6]:,.2f}")
            
        except Exception as e:
            print(f"AVISO: Erro ao verificar tabela: {e}")
        
        conn.close()
        
        # 4. Estatísticas finais
        end_time = datetime.now()
        duration = end_time - start_time
        
        print(f"\nATUALIZACAO CONTAS PAGAS CONCLUIDA!")
        print(f"Duracao: {duration}")
        print(f"Resumo:")
        print(f"   - Sienge Contas Pagas: {len(df_contas_pagas):,} registros")
        print(f"   - Tabela: sienge_contas_pagas_e_a_pagar")
        print(f"   - Banco: administracao (MotherDuck)")
        
        return True
        
    except Exception as e:
        print(f"\nERRO na atualizacao de contas pagas: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Função principal para execução via GitHub Actions"""
    print("INICIANDO ATUALIZACAO DIARIA DE CONTAS PAGAS DO MOTHERDUCK")
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
        # Executar com timeout de 30 minutos
        sucesso = asyncio.run(asyncio.wait_for(sistema_contas_pagas(), timeout=1800.0))
        
        if sucesso:
            print("\nOK: ATUALIZACAO DE CONTAS PAGAS CONCLUIDA COM SUCESSO!")
            print("Dados atualizados no MotherDuck")
            print("Dashboard pode ser consultado para validacao")
            release_concurrency()  # Liberar lock em caso de sucesso
            sys.exit(0)
        else:
            print("\nERRO: FALHA NA ATUALIZACAO DE CONTAS PAGAS")
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

