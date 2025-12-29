import duckdb
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

def check_ids_intersection():
    print("Conectando ao banco de dados...")
    con = duckdb.connect("md:my_db")
    
    try:
        print("Carregando IDs de cv_repasses...")
        df_repasses = con.execute("SELECT DISTINCT referencia FROM reservas.cv_repasses").df()
        print(f"IDs únicos em Repasses: {len(df_repasses)}")
        print(f"Amostra Repasses: {df_repasses['referencia'].head(5).tolist()}")

        print("\nCarregando IDs de cv_repasses_workflow...")
        df_workflow = con.execute("SELECT DISTINCT referencia FROM reservas.cv_repasses_workflow").df()
        print(f"IDs únicos em Workflow: {len(df_workflow)}")
        print(f"Amostra Workflow: {df_workflow['referencia'].head(5).tolist()}")
        
        # Interseção
        intersection = pd.merge(df_repasses, df_workflow, on="referencia", how="inner")
        print(f"\nIDs presentes em AMBAS as tabelas: {len(intersection)}")
        
        if len(intersection) == 0:
            print("ALERTA CRÍTICO: Não há interseção de IDs entre as tabelas!")
        else:
            print(f"Proporção de cobertura: {len(intersection)/len(df_workflow):.2%}")
            
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    check_ids_intersection()









