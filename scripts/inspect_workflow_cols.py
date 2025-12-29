
import sys
import os
from dotenv import load_dotenv

# Adiciona o diretório raiz ao path para encontrar os módulos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Carregar variáveis de ambiente
load_dotenv()

from dashboard.utils.md_conn import get_md_connection

def inspect():
    try:
        conn = get_md_connection()
        print("Consultando colunas de reservas.cv_repasses_workflow...")
        df = conn.run_query("SELECT * FROM reservas.cv_repasses_workflow LIMIT 1")
        print("\nColunas encontradas:")
        for col in df.columns:
            print(f"- {col}")
            
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    inspect()

