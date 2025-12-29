import os
import duckdb
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

def inspect_workflow_tempo():
    print("Conectando ao banco de dados...")
    # Verificar token
    if "MOTHERDUCK_TOKEN" not in os.environ:
        print("Erro: MOTHERDUCK_TOKEN não encontrado nas variáveis de ambiente.")
        return

    try:
        con = duckdb.connect("md:my_db")
        
        print("\n--- Estatísticas para 'Espera - Demanda Mínima' (2025) ---")
        query_stats_2025 = """
        SELECT
            situacao,
            COUNT(*) as qtd,
            AVG(tempo) as media_minutos,
            MIN(tempo) as min_minutos,
            MAX(tempo) as max_minutos
        FROM reservas.cv_repasses_workflow
        WHERE situacao ILIKE '%Demanda Mínima%'
          AND data_cad >= '2025-01-01'
        GROUP BY situacao;
        """
        df_stats_2025 = con.execute(query_stats_2025).df()
        print(df_stats_2025)

        print("\n--- Amostra de dados brutos (Top 10 - 2025) ---")
        query_sample_2025 = """
        SELECT situacao, tempo, data_cad
        FROM reservas.cv_repasses_workflow
        WHERE situacao ILIKE '%Demanda Mínima%'
          AND data_cad >= '2025-01-01'
        LIMIT 10;
        """
        df_sample_2025 = con.execute(query_sample_2025).df()
        print(df_sample_2025)
        
    except Exception as e:
        print(f"Erro ao consultar banco de dados: {e}")

if __name__ == "__main__":
    inspect_workflow_tempo()

