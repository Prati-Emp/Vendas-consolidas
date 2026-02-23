#!/usr/bin/env python3
"""
Integração com API do Sienge - Stock Inventories (Estoque por empreendimento)
Documentação: https://api.sienge.com.br/docs/#/stock-inventories-v1
Endpoint: GET /stock-inventories/{costCenterId}/items?offset=0&limit=200
Credenciais: SIENGE_TOKEN (mesmo das vendas/medições) - já configurado no GitHub

- Busca itens de estoque por costCenterId (empreendimento)
- Atualização incremental mensal: execução no dia 5, Data_Snapshot = último dia do mês anterior
- Integra com MotherDuck (tabela operacoes.sienge_stock_inventories)
"""

import logging
import os
import sys
import time
from datetime import date, datetime, timedelta
from typing import List, Dict, Any

import pandas as pd
import requests

# Garante import do projeto quando rodar via Actions
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from scripts.config import get_api_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lista de IDs de empreendimento (costCenterId). Pode ser ampliada conforme necessário.
COST_CENTER_IDS = [21, 29, 30, 31, 32]


class StockInventoriesAPIClient:
    """Cliente para API de Stock Inventories do Sienge."""

    def __init__(self):
        self.config = get_api_config('sienge_stock_inventories')
        if not self.config:
            raise ValueError("Configuração da API Sienge Stock Inventories não encontrada")
        self.base_url = self.config.base_url.rstrip('/')
        self.headers = self.config.headers

    def _url_items(self, cost_center_id: int) -> str:
        return f"{self.base_url}/stock-inventories/{cost_center_id}/items"

    def buscar_pagina(
        self, cost_center_id: int, offset: int = 0, limit: int = 200
    ) -> dict:
        """Chama o endpoint com costCenterId, offset e limit. Retorna o JSON ou dict vazio."""
        url = self._url_items(cost_center_id)
        params = {"offset": offset, "limit": limit}
        try:
            response = requests.get(
                url, headers=self.headers, params=params, timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.warning(f"Erro HTTP costCenterId={cost_center_id} offset={offset}: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.debug(f"Response: {e.response.text}")
            return {}

    def buscar_todos_itens(
        self, cost_center_id: int, limit_por_pagina: int = 200
    ) -> List[Dict]:
        """Busca todas as páginas do estoque de um costCenterId. Retorna lista de itens."""
        todos = []
        offset = 0
        while True:
            dados = self.buscar_pagina(
                cost_center_id, offset=offset, limit=limit_por_pagina
            )
            if not dados or "results" not in dados:
                break
            results = dados.get("results", [])
            todos.extend(results)
            meta = dados.get("resultSetMetadata", {})
            total = meta.get("count", 0)
            logger.debug(
                f"  costCenterId={cost_center_id} offset={offset}: "
                f"{len(results)} itens (total: {len(todos)}/{total})"
            )
            if offset + len(results) >= total or len(results) == 0:
                break
            offset += limit_por_pagina
            time.sleep(0.2)  # leve throttle entre páginas
        return todos

    def obter_data_snapshot(self, data_referencia: date = None) -> date:
        """
        Data de referência do snapshot: último dia do mês anterior.
        Quando o job roda no dia 5, representa o estoque "fechado" no mês anterior.
        """
        if data_referencia is None:
            data_referencia = date.today()
        primeiro_dia_mes_atual = date(
            data_referencia.year, data_referencia.month, 1
        )
        ultimo_dia_mes_anterior = primeiro_dia_mes_atual - timedelta(days=1)
        return ultimo_dia_mes_anterior

    def buscar_todos_empreendimentos(
        self, cost_center_ids: List[int] = None
    ) -> pd.DataFrame:
        """
        Busca estoque de todos os empreendimentos e consolida em um DataFrame.
        Não inclui Data_Snapshot/fonte/processado_em; isso é feito em obter_dados_*.
        """
        ids = cost_center_ids or COST_CENTER_IDS
        listas_df = []
        for cost_center_id in ids:
            logger.info(f"Buscando estoque costCenterId = {cost_center_id}...")
            itens = self.buscar_todos_itens(cost_center_id, limit_por_pagina=200)
            if not itens:
                logger.warning(f"  Nenhum item para {cost_center_id}. Pulando.")
                continue
            df = pd.DataFrame(itens)
            df["ID_Empreendimento"] = cost_center_id
            if "quantity" in df.columns and "averagePrice" in df.columns:
                df["Valor_total_estoque"] = df["quantity"] * df["averagePrice"]
            listas_df.append(df)
            logger.info(f"  Total: {len(itens)} itens")
        if not listas_df:
            return pd.DataFrame()
        df = pd.concat(listas_df, ignore_index=True)
        col_order = [
            "ID_Empreendimento",
            "resourceId",
            "resourceName",
            "detailId",
            "detailDescription",
            "trademarkId",
            "trademarkDescription",
            "quantity",
            "unitOfMeasure",
            "averagePrice",
            "Valor_total_estoque",
        ]
        col_order = [c for c in col_order if c in df.columns]
        outras = [c for c in df.columns if c not in col_order]
        df = df[col_order + outras]
        return df


def obter_dados_sienge_stock_inventories(
    data_snapshot: date = None,
    cost_center_ids: List[int] = None,
) -> pd.DataFrame:
    """
    Obtém dados de Stock Inventories do Sienge para atualização (incremental) no MotherDuck.

    Args:
        data_snapshot: Data de referência do snapshot (último dia do mês anterior).
                       Se None, usa último dia do mês anterior à hoje.
        cost_center_ids: Lista de costCenterId. Se None, usa COST_CENTER_IDS.

    Returns:
        DataFrame com colunas padrão + Data_Snapshot, fonte, processado_em.
    """
    try:
        client = StockInventoriesAPIClient()
        if data_snapshot is None:
            data_snapshot = client.obter_data_snapshot()
        df = client.buscar_todos_empreendimentos(cost_center_ids=cost_center_ids)
        if df.empty:
            logger.warning("Nenhum dado de estoque retornado")
            return pd.DataFrame()
        df["Data_Snapshot"] = pd.to_datetime(data_snapshot)
        df["fonte"] = "sienge_stock_inventories"
        df["processado_em"] = datetime.now()
        logger.info(f"Dados processados: {len(df)} registros (Data_Snapshot={data_snapshot})")
        return df
    except Exception as e:
        logger.error(f"Erro ao obter dados de stock inventories: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


if __name__ == "__main__":
    logger.info("Testando API de Stock Inventories do Sienge...")
    df = obter_dados_sienge_stock_inventories()
    print(f"Registros obtidos: {len(df)}")
    if not df.empty:
        print(f"Colunas: {list(df.columns)}")
        print(df.head())
