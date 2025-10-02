#!/usr/bin/env python3
"""
Análises Possíveis com os Dados de CV Repasses
Baseado na estrutura da tabela cv_repasses corrigida
"""

import os
import duckdb
import pandas as pd
from dotenv import load_dotenv

def conectar_motherduck():
    """Conecta ao banco MotherDuck"""
    load_dotenv('motherduck_config.env')
    
    token = os.environ.get('MOTHERDUCK_TOKEN', '').strip()
    if not token:
        raise ValueError("MOTHERDUCK_TOKEN nao encontrado")
    
    # Configurar DuckDB
    duckdb.sql("INSTALL motherduck")
    duckdb.sql("LOAD motherduck")
    duckdb.sql(f"SET motherduck_token='{token}'")
    
    # Conectar
    conn = duckdb.connect('md:reservas')
    return conn

def explorar_estrutura_dados():
    """Explora a estrutura dos dados para identificar possibilidades de análise"""
    print("EXPLORANDO ESTRUTURA DOS DADOS - CV_REPASSES")
    print("="*60)
    
    conn = conectar_motherduck()
    
    try:
        # Obter estrutura da tabela
        print("1. ESTRUTURA DA TABELA:")
        print("-" * 40)
        columns = conn.execute("DESCRIBE main.cv_repasses").fetchall()
        for col in columns:
            print(f"  - {col[0]} ({col[1]})")
        
        # Contar registros
        total = conn.execute("SELECT COUNT(*) FROM main.cv_repasses").fetchone()[0]
        print(f"\nTotal de registros: {total:,}")
        
        # Explorar colunas categóricas
        print("\n2. COLUNAS CATEGÓRICAS DISPONÍVEIS:")
        print("-" * 40)
        
        colunas_categoricas = [
            'Para', 'empreendimento', 'regiao', 'correspondente', 
            'situacao', 'contrato_quitado', 'contrato_liquidado',
            'recebendo_financiamento', 'itbi_pago', 'laudemio_pago'
        ]
        
        for col in colunas_categoricas:
            try:
                valores_unicos = conn.execute(f"""
                    SELECT {col}, COUNT(*) as count
                    FROM main.cv_repasses 
                    WHERE {col} IS NOT NULL
                    GROUP BY {col}
                    ORDER BY count DESC
                    LIMIT 5
                """).fetchall()
                
                if valores_unicos:
                    print(f"\n{col.upper()}:")
                    for valor, count in valores_unicos:
                        print(f"  - {valor}: {count} registros")
            except:
                print(f"\n{col.upper()}: Erro ao consultar")
        
        # Explorar colunas numéricas
        print("\n3. COLUNAS NUMÉRICAS DISPONÍVEIS:")
        print("-" * 40)
        
        colunas_numericas = [
            'valor_contrato', 'valor_previsto', 'valor_divida', 
            'valor_subsidio', 'valor_fgts', 'valor_financiado'
        ]
        
        for col in colunas_numericas:
            try:
                stats = conn.execute(f"""
                    SELECT 
                        COUNT(*) as total,
                        ROUND(AVG({col}), 2) as media,
                        ROUND(MIN({col}), 2) as minimo,
                        ROUND(MAX({col}), 2) as maximo,
                        ROUND(SUM({col}), 2) as total_soma
                    FROM main.cv_repasses 
                    WHERE {col} IS NOT NULL
                """).fetchone()
                
                if stats[0] > 0:
                    print(f"\n{col.upper()}:")
                    print(f"  - Total: {stats[0]:,} registros")
                    print(f"  - Média: R$ {stats[1]:,.2f}")
                    print(f"  - Mínimo: R$ {stats[2]:,.2f}")
                    print(f"  - Máximo: R$ {stats[3]:,.2f}")
                    print(f"  - Soma total: R$ {stats[4]:,.2f}")
            except:
                print(f"\n{col.upper()}: Erro ao consultar")
        
        # Explorar colunas de data
        print("\n4. COLUNAS DE DATA DISPONÍVEIS:")
        print("-" * 40)
        
        colunas_data = [
            'data_cad', 'data_venda', 'data_contrato_contabilizado',
            'data_assinatura_de_contrato', 'data_cadastro'
        ]
        
        for col in colunas_data:
            try:
                range_datas = conn.execute(f"""
                    SELECT 
                        MIN({col}) as data_minima,
                        MAX({col}) as data_maxima,
                        COUNT(*) as registros_com_data
                    FROM main.cv_repasses 
                    WHERE {col} IS NOT NULL
                """).fetchone()
                
                if range_datas[2] > 0:
                    print(f"\n{col.upper()}:")
                    print(f"  - Período: {range_datas[0]} a {range_datas[1]}")
                    print(f"  - Registros: {range_datas[2]:,}")
            except:
                print(f"\n{col.upper()}: Erro ao consultar")
        
        return True
        
    except Exception as e:
        print(f"Erro: {e}")
        return False
    finally:
        conn.close()

def identificar_analises_possiveis():
    """Identifica as análises possíveis baseadas na estrutura dos dados"""
    print("\n" + "="*60)
    print("ANÁLISES POSSÍVEIS COM OS DADOS DE CV_REPASSES")
    print("="*60)
    
    print("\n📊 1. ANÁLISES POR STATUS (Coluna 'Para'):")
    print("   - Distribuição por status atual")
    print("   - Evolução temporal dos status")
    print("   - Tempo médio em cada status")
    print("   - Análise de gargalos no processo")
    print("   - Identificação de contratos 'presos'")
    
    print("\n🏢 2. ANÁLISES POR EMPREENDIMENTO:")
    print("   - Performance por empreendimento")
    print("   - Ranking de empreendimentos por valor")
    print("   - Análise de velocidade de vendas")
    print("   - Comparação entre projetos")
    print("   - Análise por região")
    
    print("\n💰 3. ANÁLISES FINANCEIRAS:")
    print("   - Análise de valores de contrato")
    print("   - Distribuição por faixas de valor")
    print("   - Análise de subsídios e financiamentos")
    print("   - Comparação valor previsto vs realizado")
    print("   - Análise de inadimplência")
    
    print("\n👥 4. ANÁLISES DE CLIENTES:")
    print("   - Perfil demográfico dos clientes")
    print("   - Análise por cidade/região")
    print("   - Segmentação de clientes")
    print("   - Análise de comportamento de compra")
    
    print("\n📅 5. ANÁLISES TEMPORAIS:")
    print("   - Vendas por período (mensal, trimestral)")
    print("   - Sazonalidade dos negócios")
    print("   - Análise de crescimento")
    print("   - Tendências temporais")
    print("   - Análise de picos e vales")
    
    print("\n🔄 6. ANÁLISES DE PROCESSO:")
    print("   - Tempo médio de processamento")
    print("   - Análise de etapas do processo")
    print("   - Identificação de gargalos")
    print("   - Eficiência por correspondente")
    print("   - Análise de documentação")
    
    print("\n📈 7. ANÁLISES DE PERFORMANCE:")
    print("   - KPIs de processamento")
    print("   - Taxa de conversão por status")
    print("   - Análise de retrabalho")
    print("   - Benchmarking interno")
    print("   - Análise de qualidade")
    
    print("\n🎯 8. ANÁLISES ESPECÍFICAS:")
    print("   - Análise de contratos quitados vs liquidados")
    print("   - Análise de financiamento")
    print("   - Análise de ITBI e laudêmio")
    print("   - Análise de correspondentes")
    print("   - Análise de documentação pendente")

def exemplos_queries_uteis():
    """Mostra exemplos de queries úteis para análises"""
    print("\n" + "="*60)
    print("EXEMPLOS DE QUERIES ÚTEIS")
    print("="*60)
    
    queries = {
        "Status por Empreendimento": """
        SELECT 
            empreendimento,
            Para,
            COUNT(*) as quantidade,
            ROUND(SUM(valor_contrato), 2) as valor_total
        FROM main.cv_repasses
        GROUP BY empreendimento, Para
        ORDER BY empreendimento, valor_total DESC
        """,
        
        "Top 10 Maiores Valores": """
        SELECT 
            empreendimento,
            cliente,
            valor_contrato,
            Para,
            data_venda
        FROM main.cv_repasses
        ORDER BY valor_contrato DESC
        LIMIT 10
        """,
        
        "Análise Temporal": """
        SELECT 
            EXTRACT(YEAR FROM data_venda) as ano,
            EXTRACT(MONTH FROM data_venda) as mes,
            COUNT(*) as total_contratos,
            ROUND(SUM(valor_contrato), 2) as valor_total
        FROM main.cv_repasses
        WHERE data_venda IS NOT NULL
        GROUP BY EXTRACT(YEAR FROM data_venda), EXTRACT(MONTH FROM data_venda)
        ORDER BY ano DESC, mes DESC
        """,
        
        "Performance por Região": """
        SELECT 
            regiao,
            COUNT(*) as total_contratos,
            ROUND(AVG(valor_contrato), 2) as valor_medio,
            ROUND(SUM(valor_contrato), 2) as valor_total
        FROM main.cv_repasses
        WHERE regiao IS NOT NULL
        GROUP BY regiao
        ORDER BY valor_total DESC
        """,
        
        "Análise de Financiamento": """
        SELECT 
            recebendo_financiamento,
            COUNT(*) as quantidade,
            ROUND(AVG(valor_contrato), 2) as valor_medio,
            ROUND(SUM(valor_contrato), 2) as valor_total
        FROM main.cv_repasses
        GROUP BY recebendo_financiamento
        ORDER BY quantidade DESC
        """
    }
    
    for titulo, query in queries.items():
        print(f"\n{titulo}:")
        print("-" * 40)
        print(query)

def main():
    """Função principal"""
    print("ANÁLISES POSSÍVEIS - CV_REPASSES")
    print("="*60)
    
    try:
        # Explorar estrutura dos dados
        if explorar_estrutura_dados():
            # Identificar análises possíveis
            identificar_analises_possiveis()
            
            # Mostrar exemplos de queries
            exemplos_queries_uteis()
            
            print("\n" + "="*60)
            print("CONCLUSÃO")
            print("="*60)
            print("Com os dados de CV Repasses, você pode fazer análises muito ricas!")
            print("Os dados incluem informações sobre:")
            print("- Status de contratos e repasses")
            print("- Valores financeiros detalhados")
            print("- Informações de clientes e empreendimentos")
            print("- Dados temporais para análise de tendências")
            print("- Informações de processo e documentação")
            print("\nRecomendo começar com análises de status e performance por empreendimento!")
        
    except Exception as e:
        print(f"Erro durante a análise: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

