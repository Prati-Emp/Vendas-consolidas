#!/usr/bin/env python3
"""
Script para corrigir a view apropriacao_horizont_tratada
garantindo que os cabeçalhos sejam corretamente promovidos
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

def investigar_estrutura_completa(conn):
    """Investiga a estrutura completa da tabela original"""
    print("\n" + "="*60)
    print("INVESTIGANDO ESTRUTURA COMPLETA")
    print("="*60)
    
    try:
        # 1. Obter todas as colunas
        result = conn.execute("DESCRIBE planilhas.apropriacao_horizont").fetchall()
        colunas_originais = [row[0] for row in result]
        
        # 2. Obter primeira linha (cabeçalhos)
        result = conn.execute("SELECT * FROM planilhas.apropriacao_horizont LIMIT 1").fetchone()
        valores_cabecalho = list(result) if result else []
        
        # 3. Obter segunda linha (primeira linha de dados)
        result = conn.execute("SELECT * FROM planilhas.apropriacao_horizont LIMIT 1 OFFSET 1").fetchone()
        valores_dados = list(result) if result else []
        
        # 4. Criar mapeamento completo
        mapeamento = []
        for i, col_original in enumerate(colunas_originais):
            valor_cabecalho = valores_cabecalho[i] if i < len(valores_cabecalho) else None
            valor_dado = valores_dados[i] if i < len(valores_dados) else None
            
            # Verificar se a coluna é completamente nula
            result_count = conn.execute(f"""
                SELECT COUNT(*) - COUNT("{col_original}") as nulos
                FROM planilhas.apropriacao_horizont
            """).fetchone()
            nulos = result_count[0] if result_count else 0
            total = conn.execute("SELECT COUNT(*) FROM planilhas.apropriacao_horizont").fetchone()[0]
            eh_nula = (nulos == total)
            
            mapeamento.append({
                'col_original': col_original,
                'valor_cabecalho': valor_cabecalho,
                'valor_dado': valor_dado,
                'eh_nula': eh_nula,
                'indice': i
            })
        
        return mapeamento
        
    except Exception as e:
        print(f"ERRO ao investigar: {e}")
        import traceback
        traceback.print_exc()
        return None

def criar_view_corrigida(conn, mapeamento):
    """Cria a view corrigida com cabeçalhos corretos"""
    print("\n" + "="*60)
    print("CRIANDO VIEW CORRIGIDA")
    print("="*60)
    
    try:
        # 1. Filtrar apenas colunas não nulas
        colunas_validas = [m for m in mapeamento if not m['eh_nula']]
        print(f"1. Colunas validas (nao nulas): {len(colunas_validas)}")
        print(f"   Colunas removidas (nulas): {len(mapeamento) - len(colunas_validas)}")
        
        # 2. Criar mapeamento de nomes de colunas
        print("\n2. Criando mapeamento de nomes de colunas...")
        selects = []
        novos_nomes = []
        
        for m in colunas_validas:
            col_original = m['col_original']
            valor_cabecalho = m['valor_cabecalho']
            
            # Determinar o nome da coluna
            if valor_cabecalho and str(valor_cabecalho).strip() and str(valor_cabecalho).strip().upper() != 'NULL':
                # Usar o valor do cabeçalho
                novo_nome = str(valor_cabecalho).strip()
            else:
                # Se não tiver cabeçalho, usar o nome original da coluna
                novo_nome = col_original
            
            # Limpar o nome: remover espaços extras, caracteres especiais problemáticos
            novo_nome_limpo = novo_nome.replace(' ', '_').replace('-', '_').replace('/', '_')
            novo_nome_limpo = ''.join(c if c.isalnum() or c == '_' else '_' for c in novo_nome_limpo)
            
            # Remover underscores duplicados
            while '__' in novo_nome_limpo:
                novo_nome_limpo = novo_nome_limpo.replace('__', '_')
            
            # Remover underscore no início/fim
            novo_nome_limpo = novo_nome_limpo.strip('_')
            
            # Se o nome ficou vazio ou é inválido, usar o nome original
            if not novo_nome_limpo or novo_nome_limpo[0].isdigit():
                novo_nome_limpo = col_original.replace(' ', '_').replace('-', '_')
            
            # Garantir que não há duplicatas
            nome_final = novo_nome_limpo
            contador = 1
            while nome_final in novos_nomes:
                nome_final = f"{novo_nome_limpo}_{contador}"
                contador += 1
            
            novos_nomes.append(nome_final)
            
            # Criar SELECT
            selects.append(f'"{col_original}" as "{nome_final}"')
            
            print(f"   {col_original} -> {nome_final} (cabecalho: '{valor_cabecalho}')")
        
        # 3. Criar view
        print("\n3. Criando view...")
        total_registros = conn.execute("SELECT COUNT(*) FROM planilhas.apropriacao_horizont").fetchone()[0]
        
        sql_view = f"""
        CREATE OR REPLACE VIEW planilhas.apropriacao_horizont_tratada AS
        SELECT
            {', '.join(selects)}
        FROM (
            SELECT *
            FROM planilhas.apropriacao_horizont
            LIMIT {total_registros} OFFSET 1
        ) t
        """
        
        conn.execute(sql_view)
        print("   View criada com sucesso!")
        
        # 4. Verificar resultado
        print("\n4. Verificando view criada...")
        result = conn.execute("SELECT COUNT(*) FROM planilhas.apropriacao_horizont_tratada").fetchone()
        print(f"   Total de registros: {result[0]:,}")
        
        # 5. Mostrar estrutura
        print("\n5. Estrutura da view:")
        print("-" * 50)
        result = conn.execute("DESCRIBE planilhas.apropriacao_horizont_tratada").fetchall()
        colunas_view = [row[0] for row in result]
        print(f"   Total de colunas: {len(colunas_view)}")
        print(f"   Colunas: {', '.join(colunas_view[:10])}" + ("..." if len(colunas_view) > 10 else ""))
        
        # 6. Mostrar amostra
        print("\n6. Amostra de dados (primeira linha):")
        print("-" * 50)
        result = conn.execute("SELECT * FROM planilhas.apropriacao_horizont_tratada LIMIT 1").fetchone()
        if result:
            for i, (col, val) in enumerate(zip(colunas_view[:10], result[:10])):
                val_str = str(val)[:40] if val is not None else "NULL"
                print(f"   {col}: {val_str}")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao criar view: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Funcao principal"""
    print("CORRIGINDO VIEW apropriacao_horizont_tratada")
    print("="*60)
    print("Garantindo que os cabeçalhos sejam corretamente promovidos")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        # 1. Investigar estrutura
        mapeamento = investigar_estrutura_completa(conn)
        if not mapeamento:
            return False
        
        # 2. Criar view corrigida
        if not criar_view_corrigida(conn, mapeamento):
            return False
        
        print("\n" + "="*60)
        print("VIEW CORRIGIDA COM SUCESSO!")
        print("="*60)
        print("View: planilhas.apropriacao_horizont_tratada")
        print("Cabeçalhos corretamente promovidos da primeira linha")
        
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







