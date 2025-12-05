import sys
import os

# Ajuste correto do path: adicionar a raiz do projeto ao sys.path
# O modulo é dashboard.utils.md_conn, então precisamos que a pasta onde 'dashboard' está (raiz) esteja no path.
current_dir = os.getcwd()
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    from dashboard.utils.md_conn import get_md_connection
except ImportError:
    # Fallback: se dashboard estiver no path
    sys.path.append(os.path.join(current_dir, "dashboard"))
    from utils.md_conn import get_md_connection

conn = get_md_connection()
conn.connect()

query = """
SELECT 
    COUNT(*) as total,
    COUNT(comprador) as qtd_comprador,
    COUNT(data_autoriza_o) as qtd_data_autorizacao,
    COUNT(descri_o_insumo) as qtd_insumo
FROM planilhas.relacao_de_solicitacoes_de_compras
"""
try:
    df_counts = conn.run_query(query)
    print("Contagens:")
    print(df_counts)
except Exception as e:
    print(f"Erro na query de contagem: {e}")

query_sample = """
SELECT comprador, data_autoriza_o, descri_o_insumo
FROM planilhas.relacao_de_solicitacoes_de_compras
LIMIT 5
"""
try:
    df_sample = conn.run_query(query_sample)
    print("\nAmostra:")
    print(df_sample)
except Exception as e:
    print(f"Erro na query de amostra: {e}")
