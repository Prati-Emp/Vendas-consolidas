import duckdb
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

def check_orphans():
    con = duckdb.connect("md:my_db")
    
    # IDs com Demanda Mínima em 2025
    query_target = """
    SELECT DISTINCT referencia 
    FROM reservas.cv_repasses_workflow
    WHERE situacao ILIKE '%Demanda Mínima%'
      AND data_cad >= '2025-01-01'
    """
    df_target_ids = con.execute(query_target).df()
    target_ids = df_target_ids["referencia"].tolist()
    print(f"IDs com Demanda Mínima em 2025: {len(target_ids)}")
    
    if not target_ids:
        return

    # IDs em Repasses
    query_repasses = """
    SELECT DISTINCT referencia 
    FROM reservas.cv_repasses
    """
    df_repasses_ids = con.execute(query_repasses).df()
    repasses_ids = set(df_repasses_ids["referencia"].astype(str).tolist())
    
    # Verificar interseção
    found = 0
    for tid in target_ids:
        if str(tid) in repasses_ids:
            found += 1
            
    print(f"IDs encontrados na tabela cv_repasses: {found}")
    print(f"IDs órfãos (apenas no workflow): {len(target_ids) - found}")

if __name__ == "__main__":
    check_orphans()









