
import os
import duckdb
from dotenv import load_dotenv

load_dotenv()

def inspect_tables():
    token = os.getenv("MOTHERDUCK_TOKEN")
    if not token:
        print("Erro: MOTHERDUCK_TOKEN não encontrado.")
        return

    try:
        con = duckdb.connect(f'md:?token={token}')
        
        print("=== Tabela: reservas.cv_repasses ===")
        # Colunas
        df_cols_repasses = con.sql("DESCRIBE reservas.cv_repasses").df()
        print(df_cols_repasses[['column_name', 'column_type']])
        
        # Amostra
        print("\n--- Amostra (cv_repasses) ---")
        df_sample_repasses = con.sql("SELECT * FROM reservas.cv_repasses LIMIT 3").df()
        print(df_sample_repasses.to_string())

        print("\n\n=== Tabela: reservas.cv_repasses_workflow ===")
        # Colunas
        df_cols_workflow = con.sql("DESCRIBE reservas.cv_repasses_workflow").df()
        print(df_cols_workflow[['column_name', 'column_type']])
        
        # Amostra
        print("\n--- Amostra (cv_repasses_workflow) ---")
        df_sample_workflow = con.sql("SELECT * FROM reservas.cv_repasses_workflow LIMIT 3").df()
        print(df_sample_workflow.to_string())
        
    except Exception as e:
        print(f"Erro ao conectar ou consultar: {e}")

if __name__ == "__main__":
    inspect_tables()














