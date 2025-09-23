#!/usr/bin/env python3
"""
Script final para baixar dados da tabela sienge_vendas_realizadas
Tenta diferentes abordagens para encontrar a tabela correta.
"""

import os
import sys
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import duckdb

def configurar_ambiente():
    """Configura as variáveis de ambiente necessárias"""
    load_dotenv()
    
    required_vars = ['MOTHERDUCK_TOKEN']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"❌ Variáveis de ambiente faltando: {', '.join(missing_vars)}")
        return False
    
    print("✅ Variáveis de ambiente configuradas")
    return True

def conectar_motherduck():
    """Conecta ao banco de dados MotherDuck"""
    try:
        token = os.environ.get('MOTHERDUCK_TOKEN')
        conn = duckdb.connect(f"motherduck:?motherduck_token={token}")
        print("✅ Conectado ao MotherDuck com sucesso")
        return conn
    except Exception as e:
        print(f"❌ Erro ao conectar ao MotherDuck: {e}")
        return None

def encontrar_tabela_correta(conn):
    """Encontra a tabela sienge_vendas_realizadas usando diferentes abordagens"""
    print("🔍 Procurando tabela sienge_vendas_realizadas...")
    
    # Lista de possíveis localizações
    possibilidades = [
        "main.sienge_vendas_realizadas",
        "reservas.sienge_vendas_realizadas", 
        "sienge_vendas_realizadas"
    ]
    
    for tabela in possibilidades:
        try:
            print(f"   Testando: {tabela}")
            result = conn.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()
            print(f"   ✅ Encontrada! Total de registros: {result[0]:,}")
            return tabela
        except Exception as e:
            print(f"   ❌ Não encontrada: {e}")
            continue
    
    return None

def obter_estatisticas(conn, tabela):
    """Obtém estatísticas da tabela"""
    try:
        # Contar registros
        total = conn.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
        
        # Datas
        try:
            datas = conn.execute(f"""
                SELECT 
                    MIN(creationDate) as data_mais_antiga,
                    MAX(creationDate) as data_mais_recente
                FROM {tabela}
            """).fetchone()
            
            print(f"📊 Estatísticas da tabela:")
            print(f"   • Total de registros: {total:,}")
            print(f"   • Data mais antiga: {datas[0]}")
            print(f"   • Data mais recente: {datas[1]}")
        except:
            print(f"📊 Total de registros: {total:,}")
        
        return total
        
    except Exception as e:
        print(f"❌ Erro ao obter estatísticas: {e}")
        return 0

def baixar_dados(conn, tabela):
    """Baixa todos os dados da tabela"""
    try:
        print(f"📥 Baixando dados de {tabela}...")
        
        # Query para obter todos os dados
        query = f"SELECT * FROM {tabela} ORDER BY creationDate DESC"
        
        # Executar query e converter para DataFrame
        df = conn.execute(query).df()
        
        print(f"✅ Dados baixados com sucesso: {len(df):,} registros")
        return df
        
    except Exception as e:
        print(f"❌ Erro ao baixar dados: {e}")
        return None

def exportar_csv(df, nome_arquivo=None):
    """Exporta DataFrame para CSV"""
    try:
        if nome_arquivo is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_arquivo = f"sienge_vendas_realizadas_{timestamp}.csv"
        
        df.to_csv(nome_arquivo, index=False, encoding='utf-8')
        
        print(f"✅ Dados exportados para: {nome_arquivo}")
        print(f"📁 Localização: {os.path.abspath(nome_arquivo)}")
        
        return nome_arquivo
        
    except Exception as e:
        print(f"❌ Erro ao exportar CSV: {e}")
        return None

def mostrar_preview(df):
    """Mostra preview dos dados"""
    try:
        print("\n📋 Preview dos dados:")
        print("=" * 80)
        
        print(f"📊 Dimensões: {df.shape[0]:,} linhas x {df.shape[1]} colunas")
        print(f"📅 Colunas disponíveis: {', '.join(df.columns.tolist())}")
        
        print("\n🔍 Primeiras 3 linhas:")
        print(df.head(3).to_string())
        
    except Exception as e:
        print(f"❌ Erro ao mostrar preview: {e}")

def main():
    """Função principal"""
    print("🚀 BAIXANDO DADOS DA TABELA SIENGE_VENDAS_REALIZADAS - VERSÃO FINAL")
    print("=" * 80)
    print(f"⏰ Timestamp: {datetime.now()}")
    
    # 1. Configurar ambiente
    if not configurar_ambiente():
        sys.exit(1)
    
    # 2. Conectar ao MotherDuck
    conn = conectar_motherduck()
    if conn is None:
        sys.exit(1)
    
    try:
        # 3. Encontrar tabela correta
        tabela = encontrar_tabela_correta(conn)
        if not tabela:
            print("❌ Tabela sienge_vendas_realizadas não encontrada em nenhuma localização")
            sys.exit(1)
        
        # 4. Obter estatísticas
        total_registros = obter_estatisticas(conn, tabela)
        if total_registros == 0:
            print("⚠️ Tabela está vazia")
            sys.exit(1)
        
        # 5. Baixar dados
        df = baixar_dados(conn, tabela)
        if df is None:
            sys.exit(1)
        
        # 6. Mostrar preview
        mostrar_preview(df)
        
        # 7. Exportar para CSV
        arquivo_csv = exportar_csv(df)
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
        if conn:
            conn.close()
            print("🔒 Conexão com MotherDuck fechada")

if __name__ == "__main__":
    main()
