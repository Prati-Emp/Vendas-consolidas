#!/usr/bin/env python3
"""
Integração com API do CV CRM - Gestão de Times x Imobiliárias
Endpoint: GET /api/v2/configuracoes/gestoes-time/{idtime}
Credenciais: CVCRM_EMAIL e CVCRM_TOKEN (mesmas das demais APIs CV)

Não há endpoint de listagem: varre IDs de time e consolida imobiliárias por time.
"""

import html
import logging
import os
import sys
import time
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from scripts.config import get_api_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Faixa padrão de IDs de time (sem endpoint de listagem)
ID_TIME_INICIO = 1
ID_TIME_FIM = 50
SLEEP_BETWEEN_CALLS = 0.1


class TimesImobiliariasAPIClient:
    """Cliente para API de Gestão de Times do CV CRM."""

    def __init__(self):
        self.config = get_api_config("cv_times_imobiliarias")
        if not self.config:
            raise ValueError("Configuração da API CV Times Imobiliárias não encontrada")
        self.base_url = self.config.base_url.rstrip("/")
        self.headers = self.config.headers

    def _limpar_nome(self, valor: Optional[str]) -> str:
        if not valor:
            return ""
        return html.unescape(str(valor)).strip()

    def fetch_gestao_time(self, idtime: int) -> Optional[Dict]:
        """Retorna dados de um time (Gestão de Times) pelo ID."""
        url = f"{self.base_url}/{idtime}"
        resp = requests.get(url, headers=self.headers, timeout=60)

        if resp.status_code in (204, 404):
            return None
        if resp.status_code != 200:
            raise RuntimeError(
                f"HTTP {resp.status_code} (idtime={idtime}): {resp.text}"
            )

        payload = resp.json()
        data = payload.get("data") or []
        if not data:
            return None

        return data[0]

    def buscar_times_e_imobiliarias(
        self,
        id_inicio: int = ID_TIME_INICIO,
        id_fim: int = ID_TIME_FIM,
        ids_conhecidos: Optional[List[int]] = None,
        sleep_between_calls: float = SLEEP_BETWEEN_CALLS,
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Retorna:
          - lista de times encontrados (resumo)
          - lista plana de imobiliárias com o time ao qual pertencem
        """
        ids_para_consultar = sorted(
            set(ids_conhecidos or list(range(id_inicio, id_fim + 1)))
        )
        times: List[Dict] = []
        imobiliarias: List[Dict] = []

        for idtime in ids_para_consultar:
            logger.info(f"Buscando imobiliárias do time ID {idtime}...")
            time_data = self.fetch_gestao_time(idtime)
            if not time_data:
                continue

            idtime_real = time_data.get("idtime", idtime)
            nome_time = self._limpar_nome(time_data.get("time"))
            imobs = time_data.get("imobiliarias") or []

            times.append(
                {
                    "idtime": idtime_real,
                    "time": nome_time,
                    "qtd_imobiliarias": len(imobs),
                    "qtd_usuarios": len(time_data.get("usuarios") or []),
                    "qtd_corretores": len(time_data.get("corretores") or []),
                    "qtd_empreendimentos": len(time_data.get("empreendimentos") or []),
                    "qtd_regioes": len(time_data.get("regioes") or []),
                }
            )

            for imob in imobs:
                imobiliarias.append(
                    {
                        "idtime": idtime_real,
                        "time": nome_time,
                        "idimobiliaria": imob.get("idimobiliaria"),
                        "imobiliaria": self._limpar_nome(imob.get("imobiliaria")),
                    }
                )

            logger.info(f"  -> {nome_time}: {len(imobs)} imobiliárias")

            if sleep_between_calls > 0:
                time.sleep(sleep_between_calls)

        logger.info(
            f"Times encontrados: {len(times)} | Imobiliárias mapeadas: {len(imobiliarias)}"
        )
        return times, imobiliarias


def obter_dados_cv_times_imobiliarias(
    id_inicio: int = ID_TIME_INICIO,
    id_fim: int = ID_TIME_FIM,
) -> pd.DataFrame:
    """
    Obtém mapeamento plano time x imobiliária para carga no MotherDuck.

    Returns:
        DataFrame com colunas idtime, time, idimobiliaria, imobiliaria,
        fonte, processado_em, Data_Snapshot.
    """
    try:
        client = TimesImobiliariasAPIClient()
        _, imobiliarias = client.buscar_times_e_imobiliarias(
            id_inicio=id_inicio, id_fim=id_fim
        )

        if not imobiliarias:
            logger.warning("Nenhuma imobiliária encontrada")
            return pd.DataFrame()

        df = pd.DataFrame(imobiliarias)
        df["fonte"] = "cv_times_imobiliarias"
        df["processado_em"] = datetime.now()
        df["Data_Snapshot"] = pd.to_datetime(date.today())

        logger.info(f"Dados processados: {len(df)} registros")
        return df

    except Exception as e:
        logger.error(f"Erro ao obter dados de times/imobiliárias: {e}")
        import traceback

        traceback.print_exc()
        return pd.DataFrame()


if __name__ == "__main__":
    df = obter_dados_cv_times_imobiliarias()
    print(f"Registros obtidos: {len(df)}")
    if not df.empty:
        print(df.head())
