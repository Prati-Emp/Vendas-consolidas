import pandas as pd

def inspect_csv():
    try:
        df = pd.read_csv(r"c:\Users\Odair_Santos\Downloads\work_flow.csv")
        print("Colunas:", df.columns.tolist())
        
        # Filtrar por Demanda
        mask = df['situacao'].astype(str).str.contains("Demanda", case=False, na=False)
        df_demanda = df[mask]
        
        print(f"\nRegistros com 'Demanda': {len(df_demanda)}")
        if not df_demanda.empty:
            print(df_demanda[['situacao', 'tempo', 'data_cad']].head(10))
            print("\nEstatísticas de Tempo (minutos):")
            print(df_demanda['tempo'].describe())
            
        # Listar todas situações únicas para ver grafia
        print("\nSituações Únicas:")
        print(df['situacao'].unique())
        
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    inspect_csv()









