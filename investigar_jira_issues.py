#!/usr/bin/env python3
"""
Script para investigar a estrutura da tabela jira_issues
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

def investigar_tabela_jira(conn):
    """Investiga a estrutura da tabela jira_issues"""
    print("\n" + "="*60)
    print("INVESTIGANDO ESTRUTURA DA TABELA JIRA_ISSUES")
    print("="*60)
    
    try:
        # 1. Verificar estrutura da tabela
        print("1. Estrutura da tabela reservas.jira_issues:")
        print("-" * 50)
        result = conn.execute("DESCRIBE reservas.jira_issues").fetchall()
        
        colunas = []
        for i, row in enumerate(result):
            colunas.append(row[0])
            print(f"   {i+1}. {row[0]}: {row[1]}")
        
        # 2. Mapear colunas por letra (A=1, B=2, C=3, etc.)
        print(f"\n2. Mapeamento de colunas por letra:")
        print("-" * 50)
        letras = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']
        
        colunas_solicitadas = ['A', 'B', 'C', 'D', 'F', 'G', 'H', 'J', 'K', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']
        mapeamento = {}
        
        for letra in colunas_solicitadas:
            indice = letras.index(letra)
            if indice < len(colunas):
                mapeamento[letra] = colunas[indice]
                print(f"   {letra} ({indice+1}): {colunas[indice]}")
        
        # 3. Verificar quantidade de registros
        print(f"\n3. Quantidade de registros:")
        print("-" * 50)
        result = conn.execute("SELECT COUNT(*) FROM reservas.jira_issues").fetchone()
        print(f"   Total: {result[0]:,} registros")
        
        # 4. Verificar valores únicos da coluna G (Status)
        print(f"\n4. Valores únicos da coluna G (Status):")
        print("-" * 50)
        if 'G' in mapeamento:
            coluna_g = mapeamento['G']
            # Usar aspas para colunas com espaços e hífens
            coluna_g_quoted = f'"{coluna_g}"'
            result = conn.execute(f"""
                SELECT 
                    {coluna_g_quoted} as status,
                    COUNT(*) as total
                FROM reservas.jira_issues
                WHERE {coluna_g_quoted} IS NOT NULL
                GROUP BY {coluna_g_quoted}
                ORDER BY total DESC
            """).fetchall()
            
            print(f"   Valores únicos em '{coluna_g}':")
            for row in result:
                print(f"   - '{row[0]}': {row[1]:,} registros")
        
        # 5. Verificar coluna K (Data limite)
        print(f"\n5. Informações da coluna K (Data limite):")
        print("-" * 50)
        if 'K' in mapeamento:
            coluna_k = mapeamento['K']
            coluna_k_quoted = f'"{coluna_k}"'
            result = conn.execute(f"""
                SELECT 
                    COUNT(*) as total,
                    COUNT({coluna_k_quoted}) as com_data,
                    MIN({coluna_k_quoted}) as data_minima,
                    MAX({coluna_k_quoted}) as data_maxima
                FROM reservas.jira_issues
            """).fetchone()
            
            print(f"   Coluna '{coluna_k}':")
            print(f"   - Total de registros: {result[0]:,}")
            print(f"   - Com data preenchida: {result[1]:,} ({result[1]/result[0]*100:.1f}%)")
            print(f"   - Data mínima: {result[2]}")
            print(f"   - Data máxima: {result[3]}")
        
        # 6. Verificar alguns exemplos de dados
        print(f"\n6. Exemplos de dados:")
        print("-" * 50)
        if 'G' in mapeamento and 'K' in mapeamento:
            coluna_g = mapeamento['G']
            coluna_k = mapeamento['K']
            coluna_g_quoted = f'"{coluna_g}"'
            coluna_k_quoted = f'"{coluna_k}"'
            result = conn.execute(f"""
                SELECT 
                    {coluna_g_quoted} as status,
                    {coluna_k_quoted} as data_limite,
                    COUNT(*) as total
                FROM reservas.jira_issues
                WHERE {coluna_g_quoted} IS NOT NULL
                GROUP BY {coluna_g_quoted}, {coluna_k_quoted}
                ORDER BY total DESC
                LIMIT 10
            """).fetchall()
            
            print("   Top 10 combinações de Status e Data limite:")
            for row in result:
                print(f"   - Status: '{row[0]}' | Data: {row[1]} | Total: {row[2]:,}")
        
        # 7. Verificar status específicos mencionados
        print(f"\n7. Verificando status específicos:")
        print("-" * 50)
        if 'G' in mapeamento:
            coluna_g = mapeamento['G']
            coluna_g_quoted = f'"{coluna_g}"'
            status_backlog = conn.execute(f"""
                SELECT COUNT(*) 
                FROM reservas.jira_issues 
                WHERE {coluna_g_quoted} = 'Status Backlog'
            """).fetchone()
            print(f"   'Status Backlog': {status_backlog[0]:,} registros")
            
            status_concluido = conn.execute(f"""
                SELECT COUNT(*) 
                FROM reservas.jira_issues 
                WHERE {coluna_g_quoted} = 'Status Concluído'
            """).fetchone()
            print(f"   'Status Concluído': {status_concluido[0]:,} registros")
            
            outros_status = conn.execute(f"""
                SELECT COUNT(*) 
                FROM reservas.jira_issues 
                WHERE {coluna_g_quoted} NOT IN ('Status Backlog', 'Status Concluído')
                AND {coluna_g_quoted} IS NOT NULL
            """).fetchone()
            print(f"   Outros status: {outros_status[0]:,} registros")
        
        return mapeamento
        
    except Exception as e:
        print(f"ERRO ao investigar tabela: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Funcao principal"""
    print("INVESTIGANDO TABELA JIRA_ISSUES")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        mapeamento = investigar_tabela_jira(conn)
        
        if mapeamento:
            print("\n" + "="*60)
            print("MAPEAMENTO DE COLUNAS IDENTIFICADO")
            print("="*60)
            print("Colunas que serao usadas na view:")
            for letra, nome in mapeamento.items():
                print(f"   {letra}: {nome}")
        
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
