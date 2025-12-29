import duckdb
import pandas as pd
import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv()

# Mocks e Helpers
def load_workflow_raw():
    con = duckdb.connect("md:my_db")
    query = """
    SELECT
        referencia,
        situacao,
        tempo,
        data_cad
    FROM reservas.cv_repasses_workflow
    """
    return con.execute(query).df()

def prepare_workflow(df: pd.DataFrame) -> pd.DataFrame:
    # Converter colunas de data
    if "data_cad" in df.columns:
        df["data_cad"] = pd.to_datetime(df["data_cad"], errors="coerce")
    
    # Normalizar strings
    if "situacao" in df.columns:
        df["situacao"] = df["situacao"].astype(str).str.strip()
        
    # Converter tempo de minutos para dias
    if "tempo" in df.columns:
        df["tempo"] = pd.to_numeric(df["tempo"], errors="coerce").fillna(0)
        df["tempo"] = df["tempo"] / 1440
        
    return df

def debug():
    print("Carregando dados...")
    df = load_workflow_raw()
    print(f"Linhas carregadas: {len(df)}")
    
    print("Preparando dados...")
    df_prep = prepare_workflow(df)
    
    # Simular Filtro de Data (Padrão: Ano Corrente)
    start_date = pd.to_datetime("2025-01-01")
    end_date = pd.to_datetime("2025-12-31")
    
    mask = (df_prep["data_cad"] >= start_date) & (df_prep["data_cad"] <= end_date)
    df_filtered = df_prep.loc[mask]
    
    print(f"Linhas após filtro de data (2025): {len(df_filtered)}")
    
    # Filtrar Situacao Específica
    target = "Espera - Demanda Mínima"
    df_target = df_filtered[df_filtered["situacao"] == target]
    
    print(f"\n--- Análise para '{target}' ---")
    print(f"Quantidade: {len(df_target)}")
    if not df_target.empty:
        print(f"Média (dias): {df_target['tempo'].mean()}")
        print(f"Min (dias): {df_target['tempo'].min()}")
        print(f"Max (dias): {df_target['tempo'].max()}")
        print("\nAmostra de valores (dias):")
        print(df_target["tempo"].head(10).tolist())
    else:
        print("Nenhum registro encontrado para essa situação.")
        
        # Verificar se existe com grafia parecida
        uniques = df_filtered["situacao"].unique()
        matches = [s for s in uniques if "Demanda" in s]
        print(f"Situações encontradas com 'Demanda': {matches}")

if __name__ == "__main__":
    debug()

