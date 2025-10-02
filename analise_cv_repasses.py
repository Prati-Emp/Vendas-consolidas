#!/usr/bin/env python3
"""
Análise da tabela cv_repasses do banco reservas
Analisa situações atuais baseadas na coluna 'para' e valores da coluna 'valor_contrato'
"""

import os
import sys
import pandas as pd
from dotenv import load_dotenv
import duckdb

# Carregar variáveis de ambiente
load_dotenv('motherduck_config.env')

def conectar_motherduck():
    """Conecta ao banco MotherDuck"""
    try:
        token = os.getenv('MOTHERDUCK_TOKEN')
        if not token:
            print("ERRO: Token do MotherDuck não encontrado!")
            return None
        
        print("Conectando ao MotherDuck...")
        conn = duckdb.connect(f'md:?motherduck_token={token}')
        print("Conexão estabelecida com sucesso!")
        return conn
        
    except Exception as e:
        print(f"ERRO na conexão: {e}")
        return None

def explorar_estrutura_tabela(conn):
    """Explora a estrutura da tabela cv_repasses"""
    print("\n" + "="*60)
    print("ESTRUTURA DA TABELA CV_REPASSES")
    print("="*60)
    
    try:
        # Verificar se a tabela existe
        result = conn.execute("""
            SELECT COUNT(*) as total_registros 
            FROM reservas.cv_repasses
        """).fetchone()
        
        print(f"Total de registros na tabela: {result[0]:,}")
        
        # Obter estrutura da tabela
        print("\nColunas da tabela:")
        columns = conn.execute("DESCRIBE reservas.cv_repasses").fetchall()
        for col in columns:
            print(f"  - {col[0]} ({col[1]})")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao explorar estrutura: {e}")
        return False

def analisar_coluna_para(conn):
    """Analisa os status da coluna 'para'"""
    print("\n" + "="*60)
    print("ANÁLISE DA COLUNA 'PARA' - SITUAÇÕES ATUAIS")
    print("="*60)
    
    try:
        # Contar registros por status da coluna 'para'
        query = """
            SELECT 
                para,
                COUNT(*) as quantidade,
                ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentual
            FROM reservas.cv_repasses 
            WHERE para IS NOT NULL
            GROUP BY para
            ORDER BY quantidade DESC
        """
        
        result = conn.execute(query).fetchall()
        
        print("Distribuição por status da coluna 'para':")
        print("-" * 50)
        for row in result:
            print(f"{row[0]:<30} | {row[1]:>8,} registros | {row[2]:>6}%")
        
        return result
        
    except Exception as e:
        print(f"ERRO ao analisar coluna 'para': {e}")
        return None

def analisar_valores_contrato(conn):
    """Analisa os valores da coluna 'valor_contrato'"""
    print("\n" + "="*60)
    print("ANÁLISE DOS VALORES DE CONTRATO")
    print("="*60)
    
    try:
        # Estatísticas gerais dos valores
        query = """
            SELECT 
                COUNT(*) as total_registros,
                COUNT(valor_contrato) as registros_com_valor,
                ROUND(AVG(valor_contrato), 2) as valor_medio,
                ROUND(MIN(valor_contrato), 2) as valor_minimo,
                ROUND(MAX(valor_contrato), 2) as valor_maximo,
                ROUND(SUM(valor_contrato), 2) as valor_total
            FROM reservas.cv_repasses
            WHERE valor_contrato IS NOT NULL
        """
        
        result = conn.execute(query).fetchone()
        
        print("Estatísticas dos valores de contrato:")
        print("-" * 50)
        print(f"Total de registros: {result[0]:,}")
        print(f"Registros com valor: {result[1]:,}")
        print(f"Valor médio: R$ {result[2]:,.2f}")
        print(f"Valor mínimo: R$ {result[3]:,.2f}")
        print(f"Valor máximo: R$ {result[4]:,.2f}")
        print(f"Valor total: R$ {result[5]:,.2f}")
        
        # Análise por faixas de valor
        print("\nDistribuição por faixas de valor:")
        print("-" * 50)
        
        faixas_query = """
            SELECT 
                CASE 
                    WHEN valor_contrato < 100000 THEN 'Até R$ 100k'
                    WHEN valor_contrato < 500000 THEN 'R$ 100k - R$ 500k'
                    WHEN valor_contrato < 1000000 THEN 'R$ 500k - R$ 1M'
                    WHEN valor_contrato < 2000000 THEN 'R$ 1M - R$ 2M'
                    ELSE 'Acima de R$ 2M'
                END as faixa_valor,
                COUNT(*) as quantidade,
                ROUND(SUM(valor_contrato), 2) as valor_total_faixa,
                ROUND(AVG(valor_contrato), 2) as valor_medio_faixa
            FROM reservas.cv_repasses
            WHERE valor_contrato IS NOT NULL
            GROUP BY 
                CASE 
                    WHEN valor_contrato < 100000 THEN 'Até R$ 100k'
                    WHEN valor_contrato < 500000 THEN 'R$ 100k - R$ 500k'
                    WHEN valor_contrato < 1000000 THEN 'R$ 500k - R$ 1M'
                    WHEN valor_contrato < 2000000 THEN 'R$ 1M - R$ 2M'
                    ELSE 'Acima de R$ 2M'
                END
            ORDER BY MIN(valor_contrato)
        """
        
        faixas_result = conn.execute(faixas_query).fetchall()
        for row in faixas_result:
            print(f"{row[0]:<20} | {row[1]:>6} registros | Total: R$ {row[2]:>12,.2f} | Média: R$ {row[3]:>10,.2f}")
        
        return result
        
    except Exception as e:
        print(f"ERRO ao analisar valores: {e}")
        return None

def analisar_por_status_e_valor(conn):
    """Analisa cruzando status 'para' com valores"""
    print("\n" + "="*60)
    print("ANÁLISE CRUZADA: STATUS 'PARA' x VALORES")
    print("="*60)
    
    try:
        query = """
            SELECT 
                para,
                COUNT(*) as quantidade,
                ROUND(AVG(valor_contrato), 2) as valor_medio,
                ROUND(SUM(valor_contrato), 2) as valor_total,
                ROUND(SUM(valor_contrato) * 100.0 / SUM(SUM(valor_contrato)) OVER(), 2) as percentual_valor
            FROM reservas.cv_repasses
            WHERE para IS NOT NULL AND valor_contrato IS NOT NULL
            GROUP BY para
            ORDER BY valor_total DESC
        """
        
        result = conn.execute(query).fetchall()
        
        print("Análise por status da coluna 'para':")
        print("-" * 80)
        print(f"{'Status':<30} | {'Qtd':>6} | {'Valor Médio':>12} | {'Valor Total':>15} | {'% Valor':>8}")
        print("-" * 80)
        
        for row in result:
            print(f"{row[0]:<30} | {row[1]:>6,} | R$ {row[2]:>9,.2f} | R$ {row[3]:>12,.2f} | {row[4]:>6}%")
        
        return result
        
    except Exception as e:
        print(f"ERRO na análise cruzada: {e}")
        return None

def gerar_relatorio_completo(conn):
    """Gera relatório completo da análise"""
    print("\n" + "="*60)
    print("RELATÓRIO COMPLETO - CV_REPASSES")
    print("="*60)
    
    try:
        # Top 10 registros por valor
        print("\nTop 10 registros por valor de contrato:")
        print("-" * 80)
        
        top_query = """
            SELECT 
                para,
                valor_contrato,
                ROW_NUMBER() OVER (ORDER BY valor_contrato DESC) as ranking
            FROM reservas.cv_repasses
            WHERE valor_contrato IS NOT NULL
            ORDER BY valor_contrato DESC
            LIMIT 10
        """
        
        top_result = conn.execute(top_query).fetchall()
        print(f"{'Rank':<4} | {'Status':<30} | {'Valor':<15}")
        print("-" * 80)
        for row in top_result:
            print(f"{row[2]:<4} | {row[0]:<30} | R$ {row[1]:>12,.2f}")
        
        # Resumo executivo
        print("\n" + "="*60)
        print("RESUMO EXECUTIVO")
        print("="*60)
        
        resumo_query = """
            SELECT 
                COUNT(*) as total_registros,
                COUNT(DISTINCT para) as status_unicos,
                ROUND(SUM(valor_contrato), 2) as valor_total_geral,
                ROUND(AVG(valor_contrato), 2) as valor_medio_geral
            FROM reservas.cv_repasses
            WHERE valor_contrato IS NOT NULL
        """
        
        resumo = conn.execute(resumo_query).fetchone()
        
        print(f"Total de registros analisados: {resumo[0]:,}")
        print(f"Status únicos na coluna 'para': {resumo[1]}")
        print(f"Valor total dos contratos: R$ {resumo[2]:,.2f}")
        print(f"Valor médio dos contratos: R$ {resumo[3]:,.2f}")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao gerar relatório: {e}")
        return False

def main():
    """Função principal"""
    print("ANÁLISE DA TABELA CV_REPASSES - BANCO RESERVAS")
    print("="*60)
    
    # Conectar ao banco
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        # Explorar estrutura
        if not explorar_estrutura_tabela(conn):
            return False
        
        # Analisar coluna 'para'
        analisar_coluna_para(conn)
        
        # Analisar valores
        analisar_valores_contrato(conn)
        
        # Análise cruzada
        analisar_por_status_e_valor(conn)
        
        # Relatório completo
        gerar_relatorio_completo(conn)
        
        print("\n" + "="*60)
        print("ANÁLISE CONCLUÍDA COM SUCESSO!")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"ERRO na análise: {e}")
        return False
    
    finally:
        if conn:
            conn.close()
            print("\nConexão com MotherDuck encerrada.")

if __name__ == "__main__":
    main()
