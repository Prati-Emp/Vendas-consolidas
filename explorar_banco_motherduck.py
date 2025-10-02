#!/usr/bin/env python3
"""
Script para explorar o banco de dados MotherDuck
"""

import os
import sys
from dotenv import load_dotenv
import duckdb

def explorar_banco():
    """Explora o banco de dados MotherDuck"""
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
        
        # Explorar database informacoes_consolidadas
        db_name = "informacoes_consolidadas"
        print(f"\n2. EXPLORANDO DATABASE: {db_name}")
        
        # Usar o database
        conn.execute(f"USE {db_name}")
        
        # Listar tabelas
        print("\n3. TABELAS DISPONÍVEIS:")
        tables = conn.execute("SHOW TABLES").fetchall()
        if tables:
            for table in tables:
                print(f"   - {table[0]}")
        else:
            print("   Nenhuma tabela encontrada.")
        
        # Procurar por tabelas relacionadas a suprimentos
        print("\n4. PROCURANDO TABELAS RELACIONADAS A SUPRIMENTOS:")
        if tables:
            tabelas_suprimentos = []
            for table in tables:
                table_name = table[0].lower()
                if any(palavra in table_name for palavra in ['suprimento', 'contrato', 'sienge', 'fornecedor']):
                    tabelas_suprimentos.append(table[0])
                
            if tabelas_suprimentos:
                for tabela in tabelas_suprimentos:
                    print(f"   - {tabela}")
                    
                    # Explorar estrutura da tabela
                    print(f"\n   ESTRUTURA DA TABELA {tabela}:")
                    try:
                        schema = conn.execute(f"DESCRIBE {tabela}").fetchall()
                        for col in schema:
                            print(f"      {col[0]:<30} {col[1]:<20}")
                        
                        # Contar registros
                        count = conn.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
                        print(f"      Total de registros: {count:,}")
                        
                    except Exception as e:
                        print(f"      ERRO ao explorar tabela: {e}")
            else:
                print("   Nenhuma tabela relacionada a suprimentos encontrada.")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"ERRO: {e}")
        return False

if __name__ == "__main__":
    print("EXPLORAÇÃO DO BANCO DE DADOS MOTHERDUCK")
    print("="*50)
    explorar_banco()
