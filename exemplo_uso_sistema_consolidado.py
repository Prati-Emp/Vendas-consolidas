#!/usr/bin/env python3
"""
Exemplo de Uso do Sistema de Banco de Dados Consolidado
Vendas Consolidadas - MotherDuck

Este script demonstra como utilizar o sistema consolidado
para análises de vendas e relatórios.
"""

import os
import duckdb
from dotenv import load_dotenv
import pandas as pd

def conectar_motherduck():
    """Conecta ao banco MotherDuck usando o token de autenticação."""
    load_dotenv('motherduck_config.env')
    token = os.getenv('MOTHERDUCK_TOKEN')
    
    if not token:
        raise ValueError("Token MotherDuck não encontrado. Verifique o arquivo motherduck_config.env")
    
    return duckdb.connect(f'md:?motherduck_token={token}')

def verificar_estrutura_banco(conn):
    """Verifica a estrutura do banco de dados consolidado."""
    print("=== VERIFICANDO ESTRUTURA DO BANCO ===")
    
    # Verificar bancos disponíveis
    bancos = conn.execute("SHOW DATABASES").fetchall()
    print(f"Bancos disponíveis: {[banco[0] for banco in bancos]}")
    
    # Verificar views no banco consolidado
    views = conn.execute("SHOW TABLES FROM informacoes_consolidadas").fetchall()
    print(f"Views no banco consolidado: {[view[0] for view in views]}")
    
    # Verificar estrutura da view principal
    estrutura = conn.execute("DESCRIBE informacoes_consolidadas.sienge_vendas_consolidadas").fetchall()
    print(f"Campos da view consolidada: {len(estrutura)} campos")
    
    return True

def analise_geral_vendas(conn, ano=2025):
    """Realiza análise geral de vendas para um ano específico."""
    print(f"\n=== ANÁLISE GERAL VENDAS {ano} ===")
    
    query = """
    SELECT 
        COUNT(*) as total_registros,
        SUM(value) as valor_total,
        AVG(value) as valor_medio,
        MIN(contractDate) as primeira_venda,
        MAX(contractDate) as ultima_venda
    FROM informacoes_consolidadas.sienge_vendas_consolidadas
    WHERE EXTRACT(YEAR FROM contractDate) = ?
    """
    
    resultado = conn.execute(query, [ano]).fetchone()
    
    print(f"Total de Registros: {resultado[0]:,}")
    print(f"Valor Total: R$ {resultado[1]:,.2f}")
    print(f"Valor Médio: R$ {resultado[2]:,.2f}")
    print(f"Primeira Venda: {resultado[3]}")
    print(f"Última Venda: {resultado[4]}")
    
    return resultado

def vendas_por_empreendimento(conn, ano=2025, limite=10):
    """Lista vendas por empreendimento."""
    print(f"\n=== TOP {limite} EMPREENDIMENTOS {ano} ===")
    
    query = """
    SELECT 
        enterpriseId,
        nome_empreendimento,
        COUNT(*) as total_vendas,
        SUM(value) as valor_total,
        AVG(value) as valor_medio
    FROM informacoes_consolidadas.sienge_vendas_consolidadas
    WHERE EXTRACT(YEAR FROM contractDate) = ?
    GROUP BY enterpriseId, nome_empreendimento
    ORDER BY valor_total DESC
    LIMIT ?
    """
    
    resultados = conn.execute(query, [ano, limite]).fetchall()
    
    print("Ranking | ID | Empreendimento | Vendas | Valor Total | Valor Médio")
    print("-" * 80)
    
    for i, row in enumerate(resultados, 1):
        print(f"{i:2d}º     | {int(row[0]):2d} | {row[1]:<25} | {row[2]:6,} | R$ {row[3]:12,.2f} | R$ {row[4]:10,.2f}")

def vendas_por_origem(conn, ano=2025):
    """Analisa vendas por origem (Sienge vs Reservas)."""
    print(f"\n=== VENDAS POR ORIGEM {ano} ===")
    
    query = """
    SELECT 
        origem,
        COUNT(*) as total_vendas,
        SUM(value) as valor_total,
        AVG(value) as valor_medio
    FROM informacoes_consolidadas.sienge_vendas_consolidadas
    WHERE EXTRACT(YEAR FROM contractDate) = ?
    GROUP BY origem
    ORDER BY valor_total DESC
    """
    
    resultados = conn.execute(query, [ano]).fetchall()
    
    for row in resultados:
        print(f"{row[0]}: {row[1]:,} vendas - R$ {row[2]:,.2f} (média: R$ {row[3]:,.2f})")

def top_corretores(conn, ano=2025, limite=10):
    """Lista top corretores por performance."""
    print(f"\n=== TOP {limite} CORRETORES {ano} ===")
    
    query = """
    SELECT 
        corretor,
        COUNT(*) as total_vendas,
        SUM(value) as valor_total,
        AVG(value) as valor_medio
    FROM informacoes_consolidadas.sienge_vendas_consolidadas
    WHERE EXTRACT(YEAR FROM contractDate) = ?
      AND corretor != 'N/A'
    GROUP BY corretor
    ORDER BY valor_total DESC
    LIMIT ?
    """
    
    resultados = conn.execute(query, [ano, limite]).fetchall()
    
    for i, row in enumerate(resultados, 1):
        print(f"{i:2d}º {row[0]:<30} - {row[1]:2} vendas - R$ {row[2]:10,.2f} (média: R$ {row[3]:8,.2f})")

def top_imobiliarias(conn, ano=2025, limite=10):
    """Lista top imobiliárias por performance."""
    print(f"\n=== TOP {limite} IMOBILIÁRIAS {ano} ===")
    
    query = """
    SELECT 
        imobiliaria,
        COUNT(*) as total_vendas,
        SUM(value) as valor_total,
        AVG(value) as valor_medio
    FROM informacoes_consolidadas.sienge_vendas_consolidadas
    WHERE EXTRACT(YEAR FROM contractDate) = ?
      AND imobiliaria != 'N/A'
    GROUP BY imobiliaria
    ORDER BY valor_total DESC
    LIMIT ?
    """
    
    resultados = conn.execute(query, [ano, limite]).fetchall()
    
    for i, row in enumerate(resultados, 1):
        print(f"{i:2d}º {row[0]:<30} - {row[1]:2} vendas - R$ {row[2]:10,.2f} (média: R$ {row[3]:8,.2f})")

def analise_mensal(conn, ano=2025, mes=9):
    """Realiza análise mensal detalhada."""
    print(f"\n=== ANÁLISE MENSAL {mes:02d}/{ano} ===")
    
    # Resumo geral do mês
    query_geral = """
    SELECT 
        COUNT(*) as total_registros,
        SUM(value) as valor_total,
        AVG(value) as valor_medio
    FROM informacoes_consolidadas.sienge_vendas_consolidadas
    WHERE EXTRACT(YEAR FROM contractDate) = ?
      AND EXTRACT(MONTH FROM contractDate) = ?
    """
    
    resultado = conn.execute(query_geral, [ano, mes]).fetchone()
    
    print(f"Total de Registros: {resultado[0]:,}")
    print(f"Valor Total: R$ {resultado[1]:,.2f}")
    print(f"Valor Médio: R$ {resultado[2]:,.2f}")
    
    # Vendas por empreendimento no mês
    query_empreendimento = """
    SELECT 
        enterpriseId,
        nome_empreendimento,
        COUNT(*) as total_vendas,
        SUM(value) as valor_total
    FROM informacoes_consolidadas.sienge_vendas_consolidadas
    WHERE EXTRACT(YEAR FROM contractDate) = ?
      AND EXTRACT(MONTH FROM contractDate) = ?
    GROUP BY enterpriseId, nome_empreendimento
    ORDER BY valor_total DESC
    """
    
    resultados = conn.execute(query_empreendimento, [ano, mes]).fetchall()
    
    print(f"\nVendas por Empreendimento em {mes:02d}/{ano}:")
    for row in resultados:
        print(f"ID {row[0]}: {row[1]} - {row[2]} vendas - R$ {row[3]:,.2f}")

def exportar_dados_para_excel(conn, ano=2025, arquivo="vendas_consolidadas.xlsx"):
    """Exporta dados consolidados para Excel."""
    print(f"\n=== EXPORTANDO DADOS PARA {arquivo} ===")
    
    query = """
    SELECT 
        enterpriseId,
        nome_empreendimento,
        value,
        issueDate,
        contractDate,
        origem,
        corretor,
        imobiliaria,
        cliente,
        email,
        cidade,
        sexo,
        idade,
        estado_civil,
        renda
    FROM informacoes_consolidadas.sienge_vendas_consolidadas
    WHERE EXTRACT(YEAR FROM contractDate) = ?
    ORDER BY contractDate DESC
    """
    
    df = conn.execute(query, [ano]).df()
    
    # Salvar em Excel
    df.to_excel(arquivo, index=False)
    print(f"Dados exportados: {len(df)} registros salvos em {arquivo}")
    
    return df

def main():
    """Função principal que executa todas as análises."""
    try:
        # Conectar ao banco
        conn = conectar_motherduck()
        print("✅ Conectado ao MotherDuck com sucesso!")
        
        # Verificar estrutura
        verificar_estrutura_banco(conn)
        
        # Análises para 2025
        analise_geral_vendas(conn, 2025)
        vendas_por_empreendimento(conn, 2025, 10)
        vendas_por_origem(conn, 2025)
        top_corretores(conn, 2025, 10)
        top_imobiliarias(conn, 2025, 10)
        
        # Análise específica de setembro 2025
        analise_mensal(conn, 2025, 9)
        
        # Exportar dados (opcional)
        # exportar_dados_para_excel(conn, 2025, "vendas_2025.xlsx")
        
        print("\n✅ Análises concluídas com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro durante a execução: {e}")
    
    finally:
        if 'conn' in locals():
            conn.close()
            print("🔒 Conexão com o banco fechada.")

if __name__ == "__main__":
    main()
