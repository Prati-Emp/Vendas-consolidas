#!/usr/bin/env python3
"""
Script para baixar dados da tabela sienge_vendas_realizadas do MotherDuck
e exportar para CSV para validação das informações.
"""

import os
import sys
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import duckdb

def configurar_ambiente():
    """Configura as variáveis de ambiente necessárias"""
    # Carregar variáveis do arquivo .env se existir
    load_dotenv()
    
    # Verificar se as variáveis necessárias estão configuradas
    required_vars = ['MOTHERDUCK_TOKEN']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"❌ Variáveis de ambiente faltando: {', '.join(missing_vars)}")
        print("💡 Configure as variáveis no arquivo .env ou no sistema")
        return False
    
    print("✅ Variáveis de ambiente configuradas")
    return True

def conectar_motherduck():
    """Conecta ao banco de dados MotherDuck"""
    try:
        # Configurar token do MotherDuck
        token = os.environ.get('MOTHERDUCK_TOKEN')
        
        # Conectar ao MotherDuck usando a sintaxe correta
        conn = duckdb.connect(f"motherduck:?motherduck_token={token}")
        
        print("✅ Conectado ao MotherDuck com sucesso")
        return conn
        
    except Exception as e:
        print(f"❌ Erro ao conectar ao MotherDuck: {e}")
        return None

def verificar_tabela_existe(conn):
    """Verifica se a tabela sienge_vendas_realizadas existe"""
    try:
        # Verificar se a tabela existe
        result = conn.execute("""
            SELECT COUNT(*) as total_tabelas
            FROM information_schema.tables 
            WHERE table_schema = 'main' 
            AND table_name = 'sienge_vendas_realizadas'
        """).fetchone()
        
        if result[0] > 0:
            print("✅ Tabela sienge_vendas_realizadas encontrada")
            return True
        else:
            print("❌ Tabela sienge_vendas_realizadas não encontrada")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao verificar tabela: {e}")
        return False

def obter_estatisticas_tabela(conn):
    """Obtém estatísticas básicas da tabela"""
    try:
        # Contar total de registros
        total = conn.execute("SELECT COUNT(*) FROM main.sienge_vendas_realizadas").fetchone()[0]
        
        # Data mais antiga e mais recente
        datas = conn.execute("""
            SELECT 
                MIN(creation_date) as data_mais_antiga,
                MAX(creation_date) as data_mais_recente
            FROM main.sienge_vendas_realizadas
        """).fetchone()
        
        print(f"📊 Estatísticas da tabela:")
        print(f"   • Total de registros: {total:,}")
        print(f"   • Data mais antiga: {datas[0]}")
        print(f"   • Data mais recente: {datas[1]}")
        
        return total
        
    except Exception as e:
        print(f"❌ Erro ao obter estatísticas: {e}")
        return 0

def baixar_dados_completos(conn):
    """Baixa todos os dados da tabela sienge_vendas_realizadas"""
    try:
        print("📥 Baixando dados da tabela sienge_vendas_realizadas...")
        
        # Query para obter todos os dados
        query = """
        SELECT *
        FROM main.sienge_vendas_realizadas
        ORDER BY creation_date DESC
        """
        
        # Executar query e converter para DataFrame
        df = conn.execute(query).df()
        
        print(f"✅ Dados baixados com sucesso: {len(df):,} registros")
        return df
        
    except Exception as e:
        print(f"❌ Erro ao baixar dados: {e}")
        return None

def exportar_para_csv(df, nome_arquivo=None):
    """Exporta DataFrame para arquivo CSV"""
    try:
        if nome_arquivo is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_arquivo = f"sienge_vendas_realizadas_{timestamp}.csv"
        
        # Exportar para CSV
        df.to_csv(nome_arquivo, index=False, encoding='utf-8')
        
        print(f"✅ Dados exportados para: {nome_arquivo}")
        print(f"📁 Localização: {os.path.abspath(nome_arquivo)}")
        
        return nome_arquivo
        
    except Exception as e:
        print(f"❌ Erro ao exportar CSV: {e}")
        return None

def mostrar_preview_dados(df):
    """Mostra um preview dos dados baixados"""
    try:
        print("\n📋 Preview dos dados:")
        print("=" * 80)
        
        # Mostrar informações básicas
        print(f"📊 Dimensões: {df.shape[0]:,} linhas x {df.shape[1]} colunas")
        print(f"📅 Colunas disponíveis: {', '.join(df.columns.tolist())}")
        
        # Mostrar primeiras linhas
        print("\n🔍 Primeiras 5 linhas:")
        print(df.head().to_string())
        
        # Mostrar tipos de dados
        print("\n📝 Tipos de dados:")
        print(df.dtypes.to_string())
        
    except Exception as e:
        print(f"❌ Erro ao mostrar preview: {e}")

def main():
    """Função principal"""
    print("🚀 BAIXANDO DADOS DA TABELA SIENGE_VENDAS_REALIZADAS")
    print("=" * 60)
    print(f"⏰ Timestamp: {datetime.now()}")
    
    # 1. Configurar ambiente
    if not configurar_ambiente():
        sys.exit(1)
    
    # 2. Conectar ao MotherDuck
    conn = conectar_motherduck()
    if conn is None:
        sys.exit(1)
    
    try:
        # 3. Verificar se tabela existe
        if not verificar_tabela_existe(conn):
            print("💡 Verifique se a tabela foi criada corretamente")
            sys.exit(1)
        
        # 4. Obter estatísticas
        total_registros = obter_estatisticas_tabela(conn)
        if total_registros == 0:
            print("⚠️ Tabela está vazia")
            sys.exit(1)
        
        # 5. Baixar dados
        df = baixar_dados_completos(conn)
        if df is None:
            sys.exit(1)
        
        # 6. Mostrar preview
        mostrar_preview_dados(df)
        
        # 7. Exportar para CSV
        arquivo_csv = exportar_para_csv(df)
        if arquivo_csv:
            print(f"\n🎉 SUCESSO! Dados exportados para: {arquivo_csv}")
            print(f"📁 Caminho completo: {os.path.abspath(arquivo_csv)}")
        else:
            print("\n❌ Falha ao exportar dados")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ ERRO INESPERADO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
        
    finally:
        # Fechar conexão
        if conn:
            conn.close()
            print("🔒 Conexão com MotherDuck fechada")

if __name__ == "__main__":
    main()
