#!/usr/bin/env python3
"""
Análise das vendas de 2025 na tabela cv_vendas
Separação por imobiliária
"""

import os
import sys
import pandas as pd
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv('motherduck_config.env')

def conectar_motherduck():
    """Conecta ao MotherDuck"""
    try:
        import duckdb
        
        # Obter token do MotherDuck
        token = os.getenv('MOTHERDUCK_TOKEN')
        if not token:
            print("ERRO: Token do MotherDuck não encontrado!")
            return None
        
        # Configurar conexão com MotherDuck
        conn = duckdb.connect(f'md:?motherduck_token={token}')
        print("Conexão com MotherDuck estabelecida!")
        return conn
        
    except ImportError as e:
        print(f"ERRO de importação: {e}")
        print("Execute: pip install duckdb python-dotenv pandas")
        return None
    except Exception as e:
        print(f"ERRO na conexão: {e}")
        return None

def verificar_estrutura_tabela(conn):
    """Verifica a estrutura da tabela cv_vendas"""
    try:
        print("\nVerificando estrutura da tabela cv_vendas...")
        
        # Verificar se a tabela existe
        tables = conn.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'my_db' 
            AND table_name = 'cv_vendas'
        """).fetchall()
        
        if not tables:
            print("Tabela cv_vendas não encontrada!")
            return False
        
        print("Tabela cv_vendas encontrada!")
        
        # Verificar estrutura da tabela
        print("\nEstrutura da tabela:")
        columns = conn.execute("DESCRIBE my_db.cv_vendas").fetchall()
        for col in columns:
            print(f"  - {col[0]}: {col[1]}")
        
        return True
        
    except Exception as e:
        print(f"Erro ao verificar estrutura: {e}")
        return False

def analisar_vendas_2025(conn):
    """Analisa as vendas de 2025 por imobiliária"""
    try:
        print("\nAnalisando vendas de 2025...")
        
        # Consulta para vendas de 2025 por imobiliária
        query = """
        SELECT 
            imobiliaria,
            COUNT(*) as total_vendas,
            SUM(valor_contrato) as valor_total_contratos,
            AVG(valor_contrato) as valor_medio_contrato,
            MIN(data_venda) as primeira_venda,
            MAX(data_venda) as ultima_venda
        FROM my_db.cv_vendas 
        WHERE EXTRACT(YEAR FROM data_venda) = 2025
        GROUP BY imobiliaria
        ORDER BY valor_total_contratos DESC
        """
        
        result = conn.execute(query).fetchall()
        
        if not result:
            print("Nenhuma venda encontrada para 2025!")
            return None
        
        # Converter para DataFrame para melhor visualização
        df = pd.DataFrame(result, columns=[
            'Imobiliária', 'Total Vendas', 'Valor Total Contratos', 
            'Valor Médio Contrato', 'Primeira Venda', 'Última Venda'
        ])
        
        print("\nRESUMO DAS VENDAS DE 2025 POR IMOBILIARIA:")
        print("=" * 80)
        print(df.to_string(index=False, formatters={
            'Valor Total Contratos': 'R$ {:,.2f}'.format,
            'Valor Médio Contrato': 'R$ {:,.2f}'.format
        }))
        
        # Calcular totais gerais
        total_vendas = df['Total Vendas'].sum()
        valor_total_geral = df['Valor Total Contratos'].sum()
        
        print(f"\nTOTAIS GERAIS 2025:")
        print(f"  - Total de Vendas: {total_vendas:,}")
        print(f"  - Valor Total: R$ {valor_total_geral:,.2f}")
        
        return df
        
    except Exception as e:
        print(f"❌ Erro na análise: {e}")
        return None

def analisar_evolucao_mensal(conn):
    """Analisa a evolução mensal das vendas em 2025"""
    try:
        print("\n📅 Evolução mensal das vendas em 2025...")
        
        query = """
        SELECT 
            EXTRACT(MONTH FROM data_venda) as mes,
            imobiliaria,
            COUNT(*) as vendas_mes,
            SUM(valor_contrato) as valor_mes
        FROM my_db.cv_vendas 
        WHERE EXTRACT(YEAR FROM data_venda) = 2025
        GROUP BY EXTRACT(MONTH FROM data_venda), imobiliaria
        ORDER BY mes, valor_mes DESC
        """
        
        result = conn.execute(query).fetchall()
        
        if result:
            df_mensal = pd.DataFrame(result, columns=['Mês', 'Imobiliária', 'Vendas', 'Valor'])
            
            print("\n📊 EVOLUÇÃO MENSAL 2025:")
            print("=" * 60)
            for mes in sorted(df_mensal['Mês'].unique()):
                print(f"\nMês {int(mes)}:")
                mes_data = df_mensal[df_mensal['Mês'] == mes]
                for _, row in mes_data.iterrows():
                    print(f"  {row['Imobiliária']}: {row['Vendas']} vendas - R$ {row['Valor']:,.2f}")
        
    except Exception as e:
        print(f"❌ Erro na análise mensal: {e}")

def main():
    """Função principal"""
    print("🔍 ANÁLISE DAS VENDAS DE 2025 - CV VENDAS")
    print("=" * 50)
    
    # Conectar ao MotherDuck
    conn = conectar_motherduck()
    if not conn:
        return
    
    try:
        # Verificar estrutura da tabela
        if not verificar_estrutura_tabela(conn):
            return
        
        # Analisar vendas de 2025
        df_vendas = analisar_vendas_2025(conn)
        if df_vendas is not None:
            # Analisar evolução mensal
            analisar_evolucao_mensal(conn)
        
        print("\n✅ Análise concluída com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro geral: {e}")
    finally:
        conn.close()
        print("🔌 Conexão encerrada.")

if __name__ == "__main__":
    main()
