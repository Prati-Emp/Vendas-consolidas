
import duckdb
import os
from dotenv import load_dotenv

load_dotenv()

def check_cols():
    token = os.getenv('MOTHERDUCK_TOKEN')
    con = duckdb.connect("md:")
    
    try:
        df = con.sql("DESCRIBE planilhas.main.relacao_de_pedidos_de_compras").df()
        print(df)
    except Exception as e:
        print(e)

if __name__ == "__main__":
    check_cols()


























