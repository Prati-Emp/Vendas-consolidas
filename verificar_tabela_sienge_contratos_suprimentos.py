#!/usr/bin/env python3
"""
Script para verificar se a tabela sienge_contratos_suprimentos existe no banco
"""

import os
import sys
from dotenv import load_dotenv
import duckdb

def verificar_tabela_suprimentos():
    """Verifica se a tabela sienge_contratos_suprimentos existe"""
    try:
        # Carregar variáveis de ambiente
        load_dotenv('motherduck_config.env')
        
        # Obter token do MotherDuck
        token = os.getenv('MOTHERDUCK_TOKEN')
        if not token:
            print("ERRO: Token do MotherDuck não encontrado!")
            return False
        
        print("Conectando ao MotherDuck...")
        conn = duckdb.connect(f'md:?motherduck_token={token}')
        print("Conexão estabelecida com sucesso!")
        
        # Listar databases
        print("\n1. DATABASES DISPONÍVEIS:")
        databases = conn.execute("SHOW DATABASES").fetchall()
        for db in databases:
            print(f"   - {db[0]}")
        
        # Explorar cada database
        for db_name in [db[0] for db in databases]:
            print(f"\n2. EXPLORANDO DATABASE: {db_name}")
            
            try:
                # Usar o database
                conn.execute(f"USE {db_name}")
                
                # Listar tabelas
                tables = conn.execute("SHOW TABLES").fetchall()
                table_names = [t[0] for t in tables]
                
                print(f"   Tabelas disponíveis: {len(table_names)}")
                
                # Procurar por tabelas relacionadas a suprimentos
                tabelas_suprimentos = []
                for table in table_names:
                    table_lower = table.lower()
                    if any(palavra in table_lower for palavra in ['suprimento', 'contrato', 'sienge']):
                        tabelas_suprimentos.append(table)
                
                if tabelas_suprimentos:
                    print(f"   Tabelas relacionadas a suprimentos encontradas:")
                    for tabela in tabelas_suprimentos:
                        print(f"      - {tabela}")
                        
                        # Verificar se é exatamente sienge_contratos_suprimentos
                        if tabela.lower() == 'sienge_contratos_suprimentos':
                            print(f"      *** ENCONTRADA A TABELA SOLICITADA: {tabela} ***")
                            
                            # Explorar estrutura
                            print(f"\n   ESTRUTURA DA TABELA {tabela}:")
                            try:
                                schema = conn.execute(f"DESCRIBE {tabela}").fetchall()
                                for col in schema:
                                    print(f"      {col[0]:<30} {col[1]:<20}")
                                
                                # Contar registros
                                count = conn.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
                                print(f"      Total de registros: {count:,}")
                                
                                # Verificar se tem coluna data_contrato
                                colunas = [col[0] for col in schema]
                                if 'data_contrato' in colunas:
                                    print(f"      ✓ Coluna 'data_contrato' encontrada!")
                                else:
                                    print(f"      ⚠ Coluna 'data_contrato' NÃO encontrada")
                                    print(f"      Colunas disponíveis: {colunas}")
                                
                                return True, db_name, tabela
                                
                            except Exception as e:
                                print(f"      ERRO ao explorar tabela: {e}")
                
                if not tabelas_suprimentos:
                    print(f"   Nenhuma tabela relacionada a suprimentos encontrada em {db_name}")
                    
            except Exception as e:
                print(f"   ERRO ao explorar database {db_name}: {e}")
        
        conn.close()
        return False, None, None
        
    except Exception as e:
        print(f"ERRO: {e}")
        return False, None, None

if __name__ == "__main__":
    print("VERIFICAÇÃO DA TABELA SIENGE_CONTRATOS_SUPRIMENTOS")
    print("="*60)
    
    resultado = verificar_tabela_suprimentos()
    if resultado[0]:
        print(f"\n✓ TABELA ENCONTRADA!")
        print(f"Database: {resultado[1]}")
        print(f"Tabela: {resultado[2]}")
    else:
        print(f"\n✗ TABELA 'sienge_contratos_suprimentos' NÃO ENCONTRADA")
        print("Verifique se o nome da tabela está correto ou se ela existe no banco de dados.")


