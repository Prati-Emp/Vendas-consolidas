#!/usr/bin/env python3
"""Inspeciona tabela data_entrega_empreendimentos_prosoluto_antes_pos_chaves"""
import os
from dotenv import load_dotenv
load_dotenv()

def main():
    import duckdb
    duckdb.sql("INSTALL motherduck")
    duckdb.sql("LOAD motherduck")
    token = os.environ.get("MOTHERDUCK_TOKEN", "").strip()
    if not token:
        print("ERRO: MOTHERDUCK_TOKEN nao encontrado")
        return
    duckdb.sql(f"SET motherduck_token='{token}'")
    
    # Conectar ao administracao e anexar planilhas
    conn = duckdb.connect("md:administracao")
    try:
        conn.execute("ATTACH 'md:planilhas' AS planilhas")
    except Exception as e:
        print(f"ATTACH planilhas: {e}")
    
    print("=== Estrutura data_entrega_empreendimentos_prosoluto_antes_pos_chaves ===")
    try:
        r = conn.execute("DESCRIBE planilhas.data_entrega_empreendimentos_prosoluto_antes_pos_chaves").fetchall()
        for row in r:
            print(f"  {row[0]}: {row[1]}")
    except Exception as e:
        print(f"  ERRO: {e}")
    
    print("\n=== Amostra (5 linhas) ===")
    try:
        r = conn.execute("SELECT * FROM planilhas.data_entrega_empreendimentos_prosoluto_antes_pos_chaves LIMIT 5").fetchall()
        cols = [d[0] for d in conn.execute("DESCRIBE planilhas.data_entrega_empreendimentos_prosoluto_antes_pos_chaves").fetchall()]
        print("  Colunas:", cols)
        for row in r:
            print("  ", row)
    except Exception as e:
        print(f"  ERRO: {e}")
    
    conn.close()

if __name__ == "__main__":
    main()
