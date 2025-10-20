#!/usr/bin/env python3
"""
Verificar se ID 29 existe na tabela reservas_abril
"""

import os
import sys
from dotenv import load_dotenv

# Adiciona o diretório raiz do projeto ao sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

def verificar_id_29():
    print("🔍 VERIFICANDO ID 29")
    print("=" * 30)
    
    # Carregar variáveis de ambiente
    load_dotenv()
    
    try:
        import duckdb
        
        # Configurar DuckDB
        duckdb.sql("INSTALL motherduck")
        duckdb.sql("LOAD motherduck")
        
        token = os.environ.get('MOTHERDUCK_TOKEN', '').strip()
        if not token:
            print("❌ MOTHERDUCK_TOKEN não encontrado")
            return
        
        os.environ['motherduck_token'] = token
        
        # Conectar ao MotherDuck
        conn = duckdb.connect('md:reservas')
        
        # Verificar se ID 29 existe
        print("🔍 Verificando ID 29...")
        query = """
        SELECT DISTINCT 
            idempreendimento,
            empreendimento
        FROM reservas.main.reservas_abril 
        WHERE idempreendimento = 29
        """
        
        result = conn.execute(query).fetchall()
        
        if result:
            print(f"✅ ID 29 encontrado:")
            for row in result:
                print(f"   - ID: {row[0]} | Nome: {row[1]}")
        else:
            print("❌ ID 29 NÃO encontrado na tabela reservas_abril")
        
        # Verificar todos os IDs únicos
        print("\n🔍 Todos os IDs únicos na tabela:")
        query_all = """
        SELECT DISTINCT 
            idempreendimento,
            empreendimento
        FROM reservas.main.reservas_abril 
        WHERE idempreendimento IS NOT NULL
        ORDER BY idempreendimento
        """
        
        result_all = conn.execute(query_all).fetchall()
        print(f"📊 Total de IDs únicos: {len(result_all)}")
        
        for row in result_all:
            print(f"   - ID: {row[0]} | Nome: {row[1]}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verificar_id_29()
