"""
Script local para extrair estoque (Stock Inventories) da API Sienge por empreendimento.
Documentação: https://api.sienge.com.br/docs/#/stock-inventories-v1
Endpoint: GET /stock-inventories/{costCenterId}/items?offset=0&limit=200
Gera um único Excel com itens de todos os empreendimentos (lista de costCenterId).

Integração completa (incremental mensal, dia 5, MotherDuck):
  - scripts/cv_sienge_stock_inventories_api.py  (API + Data_Snapshot)
  - scripts/update_motherduck_stock_inventories.py  (upload incremental)
  - .github/workflows/update-database-stock-inventories.yml  (agendamento)
"""
import requests
import pandas as pd

# Mesmo token utilizado em contas_pagas_sienge.py
TOKEN = "Basic cHJhdGllbXAtYmlkam9udGFoYW46c2pvYnJuaWVad1dSQ1AwbWtRRDBCdGRUNGF4Sk9OcFY="

BASE_URL = "https://api.sienge.com.br/pratiemp/public/api/v1"
OUTPUT_EXCEL = "stock_inventories_items.xlsx"

# Lista de IDs de empreendimento (costCenterId). Pode aumentar ao longo do tempo.
COST_CENTER_IDS = [21, 29, 30, 31, 32]

HEADERS = {
    "Authorization": TOKEN,
    "Content-Type": "application/json",
}


def buscar_pagina(cost_center_id: int, offset: int = 0, limit: int = 200) -> dict:
    """Chama o endpoint com costCenterId, offset e limit. Retorna o JSON ou dict vazio."""
    url = f"{BASE_URL}/stock-inventories/{cost_center_id}/items"
    params = {"offset": offset, "limit": limit}
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        print(f"  Erro HTTP: {e}")
        if hasattr(e.response, "text"):
            print(f"  Resposta: {e.response.text}")
        return {}
    except requests.exceptions.RequestException as e:
        print(f"  Erro na requisição: {e}")
        return {}


def buscar_todos_itens(cost_center_id: int, limit_por_pagina: int = 200) -> list:
    """Busca todas as páginas do estoque de um costCenterId. Retorna lista de itens."""
    todos = []
    offset = 0
    while True:
        dados = buscar_pagina(cost_center_id, offset=offset, limit=limit_por_pagina)
        if not dados or "results" not in dados:
            break
        results = dados.get("results", [])
        todos.extend(results)
        meta = dados.get("resultSetMetadata", {})
        total = meta.get("count", 0)
        print(f"    offset {offset}: {len(results)} itens (total: {len(todos)}/{total})")
        if offset + len(results) >= total or len(results) == 0:
            break
        offset += limit_por_pagina
    return todos


def main():
    print("=== Stock Inventories - Items -> Excel ===\n")
    print(f"Empreendimentos (costCenterId): {COST_CENTER_IDS}\n")

    listas_df = []

    for cost_center_id in COST_CENTER_IDS:
        print(f"Buscando estoque costCenterId = {cost_center_id}...")
        itens = buscar_todos_itens(cost_center_id, limit_por_pagina=200)

        if not itens:
            print(f"  Nenhum item para {cost_center_id}. Pulando.\n")
            continue

        df = pd.DataFrame(itens)
        df["ID_Empreendimento"] = cost_center_id
        df["Valor total estoque"] = df["quantity"] * df["averagePrice"]
        listas_df.append(df)
        print(f"  Total: {len(itens)} itens\n")

    if not listas_df:
        print("Nenhum item retornado para nenhum empreendimento.")
        return

    df = pd.concat(listas_df, ignore_index=True)

    col_order = [
        "ID_Empreendimento",
        "resourceId", "resourceName", "detailId", "detailDescription",
        "trademarkId", "trademarkDescription", "quantity", "unitOfMeasure", "averagePrice",
        "Valor total estoque"
    ]
    df = df[[c for c in col_order if c in df.columns]]

    df.to_excel(OUTPUT_EXCEL, index=False, sheet_name="Itens Estoque")
    print(f"Arquivo gerado: {OUTPUT_EXCEL}")
    print(f"Total de linhas: {len(df)}")


if __name__ == "__main__":
    main()
