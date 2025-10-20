#!/usr/bin/env python3
"""
Script para verificar tabelas CV no MotherDuck e identificar quais precisam de ajuste
"""

import os
import duckdb
import pandas as pd
from dotenv import load_dotenv

def conectar_motherduck():
    """Conecta ao MotherDuck"""
    load_dotenv()
    
    token = os.environ.get('MOTHERDUCK_TOKEN', '').strip()
    if not token:
        raise ValueError("MOTHERDUCK_TOKEN não encontrado")
    
    # Configurar DuckDB
    duckdb.sql("INSTALL motherduck")
    duckdb.sql("LOAD motherduck")
    duckdb.sql(f"SET motherduck_token='{token}'")
    
    # Conectar
    conn = duckdb.connect('md:reservas')
    return conn

def listar_tabelas_cv():
    """Lista todas as tabelas que começam com 'cv'"""
    print("VERIFICANDO TABELAS CV NO MOTHERDUCK")
    print("=" * 60)
    
    conn = conectar_motherduck()
    
    try:
        # Listar todas as tabelas
        print("1. Listando todas as tabelas...")
        tables = conn.sql("SHOW TABLES").fetchall()
        
        # Filtrar tabelas que começam com 'cv'
        tabelas_cv = [table[0] for table in tables if table[0].startswith('cv')]
        
        print(f"Total de tabelas: {len(tables)}")
        print(f"Tabelas CV encontradas: {len(tabelas_cv)}")
        print()
        
        if not tabelas_cv:
            print("Nenhuma tabela CV encontrada")
            return []
        
        print("TABELAS CV ENCONTRADAS:")
        for i, tabela in enumerate(tabelas_cv, 1):
            print(f"   {i}. {tabela}")
        
        return tabelas_cv
        
    except Exception as e:
        print(f"Erro ao listar tabelas: {e}")
        return []
    finally:
        conn.close()

def analisar_tabela_cv(tabela_nome):
    """Analisa uma tabela CV específica"""
    print(f"\n🔍 ANALISANDO TABELA: {tabela_nome}")
    print("-" * 50)
    
    conn = conectar_motherduck()
    
    try:
        # Verificar se a tabela existe
        try:
            count = conn.sql(f"SELECT COUNT(*) FROM main.{tabela_nome}").fetchone()[0]
            print(f"📊 Total de registros: {count:,}")
        except Exception as e:
            print(f"❌ Erro ao contar registros: {e}")
            return None
        
        # Obter schema da tabela
        print("\n📋 SCHEMA DA TABELA:")
        schema = conn.sql(f"DESCRIBE main.{tabela_nome}").fetchall()
        for col in schema:
            print(f"   {col[0]}: {col[1]}")
        
        # Identificar colunas de valor
        colunas_valor = []
        for col in schema:
            col_name = col[0].lower()
            if any(keyword in col_name for keyword in ['valor', 'value', 'price', 'amount', 'total']):
                colunas_valor.append(col[0])
        
        if colunas_valor:
            print(f"\n💰 COLUNAS DE VALOR IDENTIFICADAS: {colunas_valor}")
            
            # Analisar cada coluna de valor
            for col in colunas_valor:
                print(f"\n   📊 Analisando coluna: {col}")
                
                # Amostra de valores
                amostra = conn.sql(f"""
                    SELECT {col}, COUNT(*) as qtd
                    FROM main.{tabela_nome} 
                    WHERE {col} IS NOT NULL 
                    GROUP BY {col} 
                    ORDER BY qtd DESC 
                    LIMIT 5
                """).fetchall()
                
                print(f"      Exemplos de valores:")
                for valor, qtd in amostra:
                    print(f"        '{valor}' (aparece {qtd} vezes)")
                
                # Estatísticas
                stats = conn.sql(f"""
                    SELECT 
                        MIN(CAST({col} AS VARCHAR)) as min_valor,
                        MAX(CAST({col} AS VARCHAR)) as max_valor,
                        COUNT(*) as total_registros
                    FROM main.{tabela_nome} 
                    WHERE {col} IS NOT NULL
                """).fetchone()
                
                print(f"      Estatísticas:")
                print(f"        Min: {stats[0]}")
                print(f"        Max: {stats[1]}")
                print(f"        Total: {stats[2]} registros")
                
                # Verificar se precisa de normalização
                precisa_ajuste = verificar_se_precisa_ajuste(conn, tabela_nome, col)
                if precisa_ajuste:
                    print(f"      ⚠️  PRECISA DE AJUSTE: Valores mal formatados detectados")
                else:
                    print(f"      ✅ OK: Valores parecem estar corretos")
        else:
            print(f"\n💰 Nenhuma coluna de valor identificada")
        
        return {
            'tabela': tabela_nome,
            'registros': count,
            'colunas_valor': colunas_valor,
            'schema': [col[0] for col in schema]
        }
        
    except Exception as e:
        print(f"❌ Erro ao analisar tabela {tabela_nome}: {e}")
        return None
    finally:
        conn.close()

def verificar_se_precisa_ajuste(conn, tabela_nome, coluna):
    """Verifica se uma coluna precisa de ajuste de normalização"""
    try:
        # Buscar valores que podem estar mal formatados
        # (valores com pontos que não são decimais, valores com R$, etc.)
        valores_suspeitos = conn.sql(f"""
            SELECT {coluna}, COUNT(*) as qtd
            FROM main.{tabela_nome} 
            WHERE {coluna} IS NOT NULL 
            AND (
                CAST({coluna} AS VARCHAR) LIKE 'R$%' OR
                CAST({coluna} AS VARCHAR) LIKE '%.%' OR
                CAST({coluna} AS VARCHAR) LIKE '%,%'
            )
            GROUP BY {coluna} 
            ORDER BY qtd DESC 
            LIMIT 3
        """).fetchall()
        
        if valores_suspeitos:
            print(f"      🔍 Valores suspeitos encontrados:")
            for valor, qtd in valores_suspeitos:
                print(f"        '{valor}' (aparece {qtd} vezes)")
            return True
        
        return False
        
    except Exception as e:
        print(f"      ⚠️  Erro ao verificar ajuste: {e}")
        return False

def gerar_relatorio(tabelas_analisadas):
    """Gera relatório final"""
    print("\n" + "=" * 60)
    print("📊 RELATÓRIO FINAL")
    print("=" * 60)
    
    tabelas_com_problema = []
    tabelas_ok = []
    
    for analise in tabelas_analisadas:
        if analise is None:
            continue
            
        tem_colunas_valor = len(analise['colunas_valor']) > 0
        if tem_colunas_valor:
            # Verificar se precisa de ajuste (lógica simplificada)
            if any('valor' in col.lower() for col in analise['colunas_valor']):
                tabelas_com_problema.append(analise)
            else:
                tabelas_ok.append(analise)
        else:
            tabelas_ok.append(analise)
    
    print(f"📈 RESUMO:")
    print(f"   ✅ Tabelas OK: {len(tabelas_ok)}")
    print(f"   ⚠️  Tabelas que podem precisar de ajuste: {len(tabelas_com_problema)}")
    print()
    
    if tabelas_com_problema:
        print("🔧 TABELAS QUE PODEM PRECISAR DE AJUSTE:")
        for analise in tabelas_com_problema:
            print(f"   📊 {analise['tabela']}")
            print(f"      Registros: {analise['registros']:,}")
            print(f"      Colunas de valor: {analise['colunas_valor']}")
            print()
    
    if tabelas_ok:
        print("✅ TABELAS QUE PARECEM OK:")
        for analise in tabelas_ok:
            print(f"   📊 {analise['tabela']} ({analise['registros']:,} registros)")
    
    print("\n🎯 RECOMENDAÇÕES:")
    if tabelas_com_problema:
        print("1. Verificar manualmente as tabelas com colunas de valor")
        print("2. Aplicar a mesma correção de normalização se necessário")
        print("3. Testar com uma amostra pequena antes de aplicar em massa")
    else:
        print("1. Todas as tabelas parecem estar OK")
        print("2. Não são necessários ajustes adicionais")

def main():
    """Função principal"""
    print("🔍 VERIFICAÇÃO DE TABELAS CV - MOTHERDUCK")
    print("Este script verifica se outras tabelas CV precisam do mesmo ajuste")
    print()
    
    try:
        # 1. Listar tabelas CV
        tabelas_cv = listar_tabelas_cv()
        
        if not tabelas_cv:
            print("❌ Nenhuma tabela CV encontrada para analisar")
            return
        
        # 2. Analisar cada tabela
        tabelas_analisadas = []
        for tabela in tabelas_cv:
            analise = analisar_tabela_cv(tabela)
            tabelas_analisadas.append(analise)
        
        # 3. Gerar relatório
        gerar_relatorio(tabelas_analisadas)
        
    except Exception as e:
        print(f"❌ Erro durante a verificação: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
