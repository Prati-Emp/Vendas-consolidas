#!/usr/bin/env python3
"""
Script para criar a view apropriacao_horizont_tratada
com dados tratados: promover cabeçalhos e remover colunas nulas
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
        # 1. Contar registros
        print("1. Contando registros...")
        result = conn.execute("SELECT COUNT(*) FROM planilhas.apropriacao_horizont").fetchone()
        total_registros = result[0]
        print(f"   Total de registros: {total_registros:,}")
        
        # 2. Descrever estrutura
        print("\n2. Estrutura da tabela:")
        print("-" * 50)
        result = conn.execute("DESCRIBE planilhas.apropriacao_horizont").fetchall()
        
        colunas_originais = []
        for row in result:
            colunas_originais.append(row[0])
        
        print(f"   Total de colunas: {len(colunas_originais)}")
        print(f"   Primeiras 10 colunas: {', '.join(colunas_originais[:10])}")
        
        # 3. Verificar primeira linha (possível cabeçalho)
        print("\n3. Verificando primeira linha (possivel cabecalho):")
        print("-" * 50)
        result = conn.execute(f"""
            SELECT * 
            FROM planilhas.apropriacao_horizont 
            LIMIT 1
        """).fetchone()
        
        if result:
            print("   Primeiros valores da primeira linha:")
            for i, (col, val) in enumerate(zip(colunas_originais[:15], result[:15])):
                val_str = str(val)[:50] if val is not None else "NULL"
                print(f"   {col}: {val_str}")
        
        # 4. Verificar segunda linha (primeira linha de dados)
        print("\n4. Verificando segunda linha (primeira linha de dados):")
        print("-" * 50)
        result = conn.execute(f"""
            SELECT * 
            FROM planilhas.apropriacao_horizont 
            LIMIT 1 OFFSET 1
        """).fetchone()
        
        if result:
            print("   Primeiros valores da segunda linha:")
            for i, (col, val) in enumerate(zip(colunas_originais[:15], result[:15])):
                val_str = str(val)[:50] if val is not None else "NULL"
                print(f"   {col}: {val_str}")
        
        # 5. Identificar colunas completamente nulas
        print("\n5. Identificando colunas completamente nulas:")
        print("-" * 50)
        colunas_nulas = []
        
        for col in colunas_originais:
            try:
                result = conn.execute(f"""
                    SELECT COUNT(*) - COUNT({col}) as nulos
                    FROM planilhas.apropriacao_horizont
                """).fetchone()
                
                nulos = result[0]
                if nulos == total_registros:  # Coluna completamente nula
                    colunas_nulas.append(col)
            except Exception as e:
                # Se houver erro, pode ser que a coluna tenha caracteres especiais
                try:
                    result = conn.execute(f"""
                        SELECT COUNT(*) - COUNT("{col}") as nulos
                        FROM planilhas.apropriacao_horizont
                    """).fetchone()
                    nulos = result[0]
                    if nulos == total_registros:
                        colunas_nulas.append(col)
                except:
                    pass
        
        print(f"   Colunas completamente nulas encontradas: {len(colunas_nulas)}")
        if colunas_nulas:
            print(f"   Primeiras 10: {', '.join(colunas_nulas[:10])}")
        
        return {
            'colunas_originais': colunas_originais,
            'colunas_nulas': colunas_nulas,
            'total_registros': total_registros,
            'primeira_linha': result if 'result' in locals() else None
        }
        
    except Exception as e:
        print(f"ERRO ao investigar: {e}")
        import traceback
        traceback.print_exc()
        return None

def criar_view_tratada(conn, info_tabela):
    """Cria a view apropriacao_horizont_tratada"""
    print("\n" + "="*60)
    print("CRIANDO VIEW apropriacao_horizont_tratada")
    print("="*60)
    
    try:
        colunas_originais = info_tabela['colunas_originais']
        colunas_nulas = info_tabela['colunas_nulas']
        total_registros = info_tabela['total_registros']
        
        # 1. Filtrar colunas: remover as completamente nulas
        colunas_validas = [col for col in colunas_originais if col not in colunas_nulas]
        print(f"1. Colunas validas (apos remover nulas): {len(colunas_validas)}")
        print(f"   Colunas removidas (nulas): {len(colunas_nulas)}")
        
        # 2. Buscar primeira linha para usar como cabeçalho
        print("\n2. Buscando primeira linha para promover como cabecalho...")
        result = conn.execute(f"""
            SELECT * 
            FROM planilhas.apropriacao_horizont 
            LIMIT 1
        """).fetchone()
        
        if not result:
            print("   ERRO: Nenhum registro encontrado!")
            return False
        
        # 3. Criar mapeamento de colunas antigas para novos nomes
        # A primeira linha contém os novos nomes de colunas
        mapeamento_colunas = {}
        novos_nomes = []
        
        for i, col_original in enumerate(colunas_validas):
            novo_nome = result[i] if i < len(result) and result[i] is not None else col_original
            # Limpar o nome: remover espaços extras, caracteres especiais problemáticos
            novo_nome_limpo = str(novo_nome).strip().replace(' ', '_').replace('-', '_')
            novo_nome_limpo = ''.join(c for c in novo_nome_limpo if c.isalnum() or c == '_')
            
            # Se o nome ficou vazio ou é inválido, usar o nome original
            if not novo_nome_limpo or novo_nome_limpo[0].isdigit():
                novo_nome_limpo = f"col_{i+1}"
            
            # Garantir que não há duplicatas
            nome_final = novo_nome_limpo
            contador = 1
            while nome_final in novos_nomes:
                nome_final = f"{novo_nome_limpo}_{contador}"
                contador += 1
            
            mapeamento_colunas[col_original] = nome_final
            novos_nomes.append(nome_final)
        
        print(f"   Mapeamento criado para {len(mapeamento_colunas)} colunas")
        print(f"   Primeiros 10 novos nomes: {', '.join(novos_nomes[:10])}")
        
        # 4. Construir SELECT com novos nomes de colunas
        print("\n3. Construindo SELECT da view...")
        selects = []
        
        for col_original in colunas_validas:
            novo_nome = mapeamento_colunas[col_original]
            # Sempre usar aspas para o nome original para evitar problemas com números, espaços, etc.
            selects.append(f'"{col_original}" as "{novo_nome}"')
        
        # 5. Criar view pulando a primeira linha (cabeçalho)
        print("\n4. Criando view (pulando primeira linha)...")
        
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
        
        # 6. Executar criação da view
        conn.execute(sql_view)
        print("   View criada com sucesso!")
        
        # 7. Verificar resultado
        print("\n5. Verificando view criada...")
        result = conn.execute("SELECT COUNT(*) FROM planilhas.apropriacao_horizont_tratada").fetchone()
        print(f"   Total de registros na view: {result[0]:,}")
        
        # 8. Mostrar estrutura da view
        print("\n6. Estrutura da view:")
        print("-" * 50)
        result = conn.execute("DESCRIBE planilhas.apropriacao_horizont_tratada").fetchall()
        
        colunas_view = []
        for row in result:
            colunas_view.append(row[0])
        
        print(f"   Total de colunas na view: {len(colunas_view)}")
        print(f"   Primeiras 15 colunas: {', '.join(colunas_view[:15])}")
        
        # 9. Mostrar amostra de dados
        print("\n7. Amostra de dados da view:")
        print("-" * 50)
        result = conn.execute(f"""
            SELECT * 
            FROM planilhas.apropriacao_horizont_tratada 
            LIMIT 3
        """).fetchall()
        
        if result:
            print("   Primeiras 3 linhas (primeiras 10 colunas):")
            for i, row in enumerate(result, 1):
                valores = [str(val)[:30] if val is not None else "NULL" for val in row[:10]]
                print(f"   Linha {i}: {', '.join(valores)}" + ("..." if len(row) > 10 else ""))
        
        return True
        
    except Exception as e:
        print(f"ERRO ao criar view: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Funcao principal"""
    print("CRIANDO VIEW apropriacao_horizont_tratada")
    print("="*60)
    print("Transformacoes:")
    print("  - Promover primeira linha como cabecalho")
    print("  - Remover colunas completamente nulas")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        # 1. Investigar tabela
        info_tabela = investigar_tabela(conn)
        if not info_tabela:
            return False
        
        # 2. Criar view tratada
        if not criar_view_tratada(conn, info_tabela):
            return False
        
        print("\n" + "="*60)
        print("VIEW CRIADA COM SUCESSO!")
        print("="*60)
        print("View: planilhas.apropriacao_horizont_tratada")
        print("Transformacoes aplicadas:")
        print("  - Primeira linha promovida como cabecalho")
        print(f"  - {len(info_tabela['colunas_nulas'])} colunas nulas removidas")
        print(f"  - {len(info_tabela['colunas_originais']) - len(info_tabela['colunas_nulas'])} colunas mantidas")
        
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
