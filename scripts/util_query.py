import duckdb
import os
from dotenv import load_dotenv

load_dotenv('.env')
token = os.getenv('MOTHERDUCK_TOKEN')
if not token:
    raise SystemExit('MOTHERDUCK_TOKEN not found')

con = duckdb.connect(f'md:?motherduck_token={token}')
con.execute('USE informacoes_consolidadas')

query = """
SELECT Resumo, Subtarefa, Indice
FROM de_para_situacoes_operacoes_jira
WHERE lower(Resumo) LIKE '%cef%'
"""

print(con.execute(query).fetchdf())







