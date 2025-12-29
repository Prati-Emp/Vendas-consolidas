
import duckdb
import os
from dotenv import load_dotenv

load_dotenv()

def check_join():
    token = os.getenv('MOTHERDUCK_TOKEN')
    
    # Configurar token via variavel de ambiente ou parametro (mas aqui estamos usando dsn md:)
    # O python client le env var MOTHERDUCK_TOKEN automaticamente se estiver setada.
    
    con = duckdb.connect("md:") # Conectar no default ou usar md:my_db
    
    print("--- Amostra Pedidos (reservas.main.sienge_pedidos_compras) ---")
    try:
        # Tentar ler do reservas via MD (se o token tiver acesso a ambos)
        # con.sql("ATTACH 'md:reservas' AS reservas")
        
        df_pedidos = con.sql("""
            SELECT ID_Empreendimento, COUNT(*) as qtd 
            FROM reservas.main.sienge_pedidos_compras 
            GROUP BY ID_Empreendimento 
            LIMIT 5
        """).df()
        print(df_pedidos)
        
        print("\n--- Amostra View (planilhas.main.relacao_empreendimentos_pedidos_de_compras) ---")
        df_view = con.sql("""
            SELECT codigo_da_obra, obra 
            FROM planilhas.main.relacao_empreendimentos_pedidos_de_compras 
            LIMIT 5
        """).df()
        print(df_view)
        
        print("\n--- Teste de JOIN ---")
        df_join = con.sql("""
            SELECT 
                pc.ID_Empreendimento, 
                re.codigo_da_obra, 
                re.obra 
            FROM reservas.main.sienge_pedidos_compras pc
            LEFT JOIN planilhas.main.relacao_empreendimentos_pedidos_de_compras re
            ON CAST(pc.ID_Empreendimento AS VARCHAR) = CAST(re.codigo_da_obra AS VARCHAR)
            LIMIT 5
        """).df()
        print(df_join)
        
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    check_join()

