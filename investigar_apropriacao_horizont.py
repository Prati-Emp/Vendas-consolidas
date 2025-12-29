#!/usr/bin/env python3
"""
Script para investigar a estrutura da tabela apropriacao_horizont
e preparar a criação da view tratada
"""

import os
import duckdb
from dotenv import load_dotenv

def conectar_motherduck():
    """Conecta ao MotherDuck"""
    try:
        load_dotenv('.env')
        token = os.getenv('MOTHERDUCK_TOKEN')
        if not token:
            print("ERRO: Token do MotherDuck nao encontrado!")
            return None
        
        print("Conectando ao MotherDuck...")
        conn = duckdb.connect(f'md:?motherduck_token={token}')
        print("Conexao estabelecida com sucesso!")
        return conn
        
    except Exception as e:
        print(f"ERRO na conexao: {e}")
        return None

def investigar_tabela(conn):
    """Investiga a estrutura da tabela apropriacao_horizont"""
    print("\n" + "="*60)
    print("INVESTIGANDO TABELA apropriacao_horizont")
    print("="*60)
    
    try:
        # 1. Verificar se a tabela existe
        print("1. Verificando existencia da tabela...")
        result = conn.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'planilhas' 
            AND table_name = 'apropriacao_horizont'
        """).fetchone()
        
        if result[0] == 0:
            print("   ERRO: Tabela nao encontrada!")
            return False
        
        print("   Tabela encontrada!")
        
        # 2. Contar registros
        print("\n2. Contando registros...")
        result = conn.execute("SELECT COUNT(*) FROM planilhas.apropriacao_horizont").fetchone()
        print(f"   Total de registros: {result[0]:,}")
        
        # 3. Descrever estrutura
        print("\n3. Estrutura da tabela:")
        print("-" * 50)
        result = conn.execute("DESCRIBE planilhas.apropriacao_horizont").fetchall()
        
        colunas = []
        for row in result:
            colunas.append(row[0])
            print(f"   {row[0]}: {row[1]}")
        
        print(f"\n   Total de colunas: {len(colunas)}")
        
        # 4. Verificar primeiras linhas para entender a estrutura
        print("\n4. Primeiras 5 linhas da tabela:")
        print("-" * 50)
        result = conn.execute(f"""
            SELECT * 
            FROM planilhas.apropriacao_horizont 
            LIMIT 5
        """).fetchall()
        
        if result:
            # Mostrar cabeçalhos
            print("   Colunas:", ", ".join(colunas[:10]) + ("..." if len(colunas) > 10 else ""))
            print("\n   Primeiras linhas:")
            for i, row in enumerate(result, 1):
                valores = [str(val)[:30] if val is not None else "NULL" for val in row[:10]]
                print(f"   Linha {i}: {', '.join(valores)}" + ("..." if len(row) > 10 else ""))
        
        # 5. Verificar se a primeira linha parece ser cabeçalho
        print("\n5. Analisando primeira linha (possivel cabecalho):")
        print("-" * 50)
        result = conn.execute(f"""
            SELECT * 
            FROM planilhas.apropriacao_horizont 
            LIMIT 1
        """).fetchone()
        
        if result:
            print("   Valores da primeira linha:")
            for i, (col, val) in enumerate(zip(colunas[:15], result[:15])):
                val_str = str(val)[:50] if val is not None else "NULL"
                print(f"   {col}: {val_str}")
        
        # 6. Verificar colunas com valores nulos
        print("\n6. Verificando colunas com valores nulos:")
        print("-" * 50)
        
        # Contar NULLs por coluna
        colunas_nulas = []
        for col in colunas:
            try:
                result = conn.execute(f"""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(*) - COUNT({col}) as nulos
                    FROM planilhas.apropriacao_horizont
                """).fetchone()
                
                total = result[0]
                nulos = result[1]
                pct_nulo = (nulos / total * 100) if total > 0 else 0
                
                if nulos == total:  # Coluna completamente nula
                    colunas_nulas.append(col)
                    print(f"   {col}: {nulos}/{total} NULL ({pct_nulo:.1f}%) - COMPLETAMENTE NULA")
                elif pct_nulo > 50:
                    print(f"   {col}: {nulos}/{total} NULL ({pct_nulo:.1f}%) - MAIORIA NULA")
            except Exception as e:
                print(f"   {col}: ERRO ao verificar - {e}")
        
        print(f"\n   Total de colunas completamente nulas: {len(colunas_nulas)}")
        
        # 7. Verificar se há uma linha de cabeçalho (valores que parecem nomes de colunas)
        print("\n7. Verificando se primeira linha e cabecalho:")
        print("-" * 50)
        result = conn.execute(f"""
            SELECT * 
            FROM planilhas.apropriacao_horizont 
            LIMIT 1
        """).fetchone()
        
        # Verificar se os valores da primeira linha parecem nomes de colunas
        # (não são números, não são datas, são strings que parecem nomes)
        if result:
            parece_cabecalho = True
            for i, val in enumerate(result[:20]):  # Verificar primeiras 20 colunas
                if val is not None:
                    val_str = str(val).strip()
                    # Se for um número ou data, provavelmente não é cabeçalho
                    try:
                        float(val_str.replace(',', '.'))
                        parece_cabecalho = False
                        break
                    except:
                        pass
            
            if parece_cabecalho:
                print("   Primeira linha parece ser cabecalho (valores textuais)")
            else:
                print("   Primeira linha parece ser dados (valores numericos/datas)")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao investigar: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Funcao principal"""
    print("INVESTIGANDO TABELA apropriacao_horizont")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        if not investigar_tabela(conn):
            return False
        
        print("\n" + "="*60)
        print("INVESTIGACAO CONCLUIDA!")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"ERRO na execucao: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if conn:
            conn.close()
            print("\nConexao com MotherDuck encerrada.")

if __name__ == "__main__":
    main()




























