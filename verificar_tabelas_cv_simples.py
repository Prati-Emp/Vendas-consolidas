#!/usr/bin/env python3
"""
Script simples para verificar tabelas CV no MotherDuck
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
        raise ValueError("MOTHERDUCK_TOKEN nao encontrado")
    
    # Configurar DuckDB
    duckdb.sql("INSTALL motherduck")
    duckdb.sql("LOAD motherduck")
    duckdb.sql(f"SET motherduck_token='{token}'")
    
    # Conectar
    conn = duckdb.connect('md:reservas')
    return conn

def main():
    """Funcao principal"""
    print("VERIFICACAO DE TABELAS CV - MOTHERDUCK")
    print("=" * 50)
    
    try:
        conn = conectar_motherduck()
        
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
            return
        
        print("TABELAS CV ENCONTRADAS:")
        for i, tabela in enumerate(tabelas_cv, 1):
            print(f"   {i}. {tabela}")
        
        print("\n" + "=" * 50)
        print("ANALISANDO CADA TABELA:")
        print("=" * 50)
        
        # Analisar cada tabela CV
        for tabela in tabelas_cv:
            print(f"\nTABELA: {tabela}")
            print("-" * 30)
            
            try:
                # Contar registros
                count = conn.sql(f"SELECT COUNT(*) FROM main.{tabela}").fetchone()[0]
                print(f"Registros: {count:,}")
                
                # Obter schema
                schema = conn.sql(f"DESCRIBE main.{tabela}").fetchall()
                print("Colunas:")
                for col in schema:
                    print(f"  {col[0]}: {col[1]}")
                
                # Identificar colunas de valor
                colunas_valor = []
                for col in schema:
                    col_name = col[0].lower()
                    if any(keyword in col_name for keyword in ['valor', 'value', 'price', 'amount', 'total']):
                        colunas_valor.append(col[0])
                
                if colunas_valor:
                    print(f"Colunas de valor: {colunas_valor}")
                    
                    # Analisar cada coluna de valor
                    for col in colunas_valor:
                        print(f"\n  Analisando coluna: {col}")
                        
                        # Amostra de valores
                        try:
                            amostra = conn.sql(f"""
                                SELECT {col}, COUNT(*) as qtd
                                FROM main.{tabela} 
                                WHERE {col} IS NOT NULL 
                                GROUP BY {col} 
                                ORDER BY qtd DESC 
                                LIMIT 3
                            """).fetchall()
                            
                            print(f"    Exemplos:")
                            for valor, qtd in amostra:
                                print(f"      '{valor}' (aparece {qtd} vezes)")
                            
                            # Verificar se tem valores suspeitos
                            valores_suspeitos = conn.sql(f"""
                                SELECT {col}, COUNT(*) as qtd
                                FROM main.{tabela} 
                                WHERE {col} IS NOT NULL 
                                AND (
                                    CAST({col} AS VARCHAR) LIKE 'R$%' OR
                                    CAST({col} AS VARCHAR) LIKE '%.%' OR
                                    CAST({col} AS VARCHAR) LIKE '%,%'
                                )
                                GROUP BY {col} 
                                ORDER BY qtd DESC 
                                LIMIT 2
                            """).fetchall()
                            
                            if valores_suspeitos:
                                print(f"    VALORES SUSPEITOS (podem precisar de ajuste):")
                                for valor, qtd in valores_suspeitos:
                                    print(f"      '{valor}' (aparece {qtd} vezes)")
                            else:
                                print(f"    Valores parecem OK")
                                
                        except Exception as e:
                            print(f"    Erro ao analisar coluna: {e}")
                else:
                    print("Nenhuma coluna de valor identificada")
                
            except Exception as e:
                print(f"Erro ao analisar tabela {tabela}: {e}")
        
        conn.close()
        print("\n" + "=" * 50)
        print("VERIFICACAO CONCLUIDA")
        print("=" * 50)
        
    except Exception as e:
        print(f"Erro durante a verificacao: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
