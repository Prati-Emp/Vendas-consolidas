#!/usr/bin/env python3
"""
Integração com API do CV CRM - Assistências Workflow Tempo
Endpoint: GET /api/v1/cvdw/assistencias/workflow/tempo
Enriquecimento: GET /api/v1/cvdw/assistencias (situação atual / finalização)
Credenciais: CVCRM_EMAIL e CVCRM_TOKEN

Docs: https://desenvolvedor.cvcrm.com.br/reference/assistenciasworkflowtempo-1
"""

import logging
import os
import sys
import time
from datetime import date, datetime
from typing import Dict, List, Optional

import pandas as pd
import requests

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from scripts.config import get_api_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ASSISTENCIAS_URL = "https://prati.cvcrm.com.br/api/v1/cvdw/assistencias"

# Situacao de encerramento (nao aparece no workflow/tempo)
IDSITUACAO_FINALIZADA = 8
IDSITUACAO_CANCELADA = 7

CAMPOS = (
    "idassistencia",
    "idtempo",
    "idsituacao",
    "situacao",
    "tempo_minutos",
    "tempo_horas",
    "tempo_dias",
    "data_cad",
    "ativo",
    "situacao_atual",
    "idsituacao_atual",
    "finalizada",
    "data_conclusao",
    "cancelada",
    "cliente",
    "empreendimento",
    "bloco",
    "unidade",
    "data_cad_assistencia",
)


class AssistenciasWorkflowTempoAPIClient:
    """Cliente para API de Assistencias Workflow Tempo do CV CRM."""

    def __init__(self):
        self.config = get_api_config("cv_assistencias_workflow_tempo")
        if not self.config:
            raise ValueError(
                "Configuracao da API CV Assistencias Workflow Tempo nao encontrada"
            )
        self.base_url = self.config.base_url.rstrip("/")
        self.headers = self.config.headers

    def _paginar_cvdw(
        self,
        url: str,
        page_size: int = 500,
        max_pages: int = 5000,
        sleep_between_calls: float = 0.0,
        a_partir_data_referencia: Optional[str] = None,
        ate_data_referencia: Optional[str] = None,
    ) -> List[Dict]:
        page = 1
        results: List[Dict] = []

        while page <= max_pages:
            params = {
                "pagina": page,
                "registros_por_pagina": page_size,
            }
            if a_partir_data_referencia:
                params["a_partir_data_referencia"] = a_partir_data_referencia
            if ate_data_referencia:
                params["ate_data_referencia"] = ate_data_referencia

            logger.info(f"  pagina {page}...")
            resp = requests.get(url, headers=self.headers, params=params, timeout=60)
            if resp.status_code != 200:
                raise RuntimeError(f"HTTP {resp.status_code} ({url}): {resp.text}")

            data = resp.json()
            dados = data.get("dados") or []
            total_pages = data.get("total_de_paginas")
            total_reg = data.get("total_de_registros")

            if page == 1:
                logger.info(
                    f"  total_de_registros={total_reg}, total_de_paginas={total_pages}"
                )

            if not isinstance(dados, list) or len(dados) == 0:
                break

            results.extend(dados)

            if len(dados) < page_size:
                break
            if total_pages and page >= total_pages:
                break

            page += 1
            if sleep_between_calls > 0:
                time.sleep(sleep_between_calls)

        return results

    def fetch_assistencias_mapa(
        self,
        page_size: int = 500,
        sleep_between_calls: float = 0.0,
    ) -> Dict[int, Dict]:
        """Mapa idassistencia -> dados atuais (situacao, conclusao, cliente...)."""
        logger.info("Carregando assistencias (situacao atual / finalizacao)...")
        dados = self._paginar_cvdw(
            ASSISTENCIAS_URL,
            page_size=page_size,
            sleep_between_calls=sleep_between_calls,
        )

        mapa: Dict[int, Dict] = {}
        for item in dados:
            aid = item.get("idassistencia")
            if aid is None:
                continue
            idsit = item.get("idsituacao")
            mapa[int(aid)] = {
                "situacao_atual": item.get("situacao"),
                "idsituacao_atual": idsit,
                "data_conclusao": item.get("data_conclusao"),
                "finalizada": idsit == IDSITUACAO_FINALIZADA
                or bool(item.get("data_conclusao")),
                "cancelada": idsit == IDSITUACAO_CANCELADA,
                "cliente": item.get("cliente"),
                "empreendimento": item.get("empreendimento"),
                "bloco": item.get("bloco"),
                "unidade": item.get("unidade"),
                "data_cad_assistencia": item.get("data_cad"),
            }

        finalizadas = sum(1 for v in mapa.values() if v.get("finalizada"))
        canceladas = sum(1 for v in mapa.values() if v.get("cancelada"))
        logger.info(
            f"  assistencias: {len(mapa)} | finalizadas: {finalizadas} | canceladas: {canceladas}"
        )
        return mapa

    def buscar_workflow_tempo(
        self,
        page_size: int = 500,
        sleep_between_calls: float = 0.0,
        a_partir_data_referencia: Optional[str] = None,
        ate_data_referencia: Optional[str] = None,
    ) -> List[Dict]:
        """
        Linha do tempo: tempo (minutos) que cada assistencia ficou em cada situacao.
        Cruzado com CVDW assistencias para flag/data de finalizacao.
        """
        mapa = self.fetch_assistencias_mapa(
            page_size=page_size,
            sleep_between_calls=sleep_between_calls,
        )

        logger.info("Carregando workflow/tempo...")
        dados = self._paginar_cvdw(
            self.base_url,
            page_size=page_size,
            sleep_between_calls=sleep_between_calls,
            a_partir_data_referencia=a_partir_data_referencia,
            ate_data_referencia=ate_data_referencia,
        )

        results: List[Dict] = []
        for item in dados:
            aid = item.get("idassistencia")
            tempo = item.get("tempo")
            try:
                tempo_min = int(tempo) if tempo is not None else None
            except (TypeError, ValueError):
                tempo_min = None

            info = mapa.get(int(aid)) if aid is not None else None
            info = info or {}

            results.append(
                {
                    "idassistencia": aid,
                    "idtempo": item.get("idtempo"),
                    "idsituacao": item.get("idsituacao"),
                    "situacao": item.get("situacao"),
                    "tempo_minutos": tempo_min,
                    "tempo_horas": round(tempo_min / 60, 2)
                    if tempo_min is not None
                    else None,
                    "tempo_dias": round(tempo_min / 1440, 2)
                    if tempo_min is not None
                    else None,
                    "data_cad": item.get("data_cad"),
                    "ativo": item.get("ativo"),
                    "situacao_atual": info.get("situacao_atual"),
                    "idsituacao_atual": info.get("idsituacao_atual"),
                    "finalizada": info.get("finalizada"),
                    "data_conclusao": info.get("data_conclusao"),
                    "cancelada": info.get("cancelada"),
                    "cliente": info.get("cliente"),
                    "empreendimento": info.get("empreendimento"),
                    "bloco": info.get("bloco"),
                    "unidade": info.get("unidade"),
                    "data_cad_assistencia": info.get("data_cad_assistencia"),
                }
            )

        logger.info(
            f"Passagens de status: {len(results)} | "
            f"Assistencias distintas: {len({r['idassistencia'] for r in results})}"
        )
        return results


def obter_dados_cv_assistencias_workflow_tempo(
    page_size: int = 500,
    sleep_between_calls: float = 0.0,
    a_partir_data_referencia: Optional[str] = None,
    ate_data_referencia: Optional[str] = None,
) -> pd.DataFrame:
    """
    Obtem tempo por status das assistencias para carga no MotherDuck.

    Returns:
        DataFrame com CAMPOS + fonte, processado_em, Data_Snapshot.
    """
    try:
        client = AssistenciasWorkflowTempoAPIClient()
        rows = client.buscar_workflow_tempo(
            page_size=page_size,
            sleep_between_calls=sleep_between_calls,
            a_partir_data_referencia=a_partir_data_referencia,
            ate_data_referencia=ate_data_referencia,
        )
        if not rows:
            logger.warning("Nenhum registro de workflow/tempo encontrado")
            return pd.DataFrame()

        df = pd.DataFrame(rows, columns=list(CAMPOS))
        df["fonte"] = "cv_assistencias_workflow_tempo"
        df["processado_em"] = datetime.now()
        df["Data_Snapshot"] = pd.to_datetime(date.today())

        logger.info(f"Dados processados: {len(df)} registros")
        return df
    except Exception as e:
        logger.error(f"Erro ao obter dados de assistencias workflow tempo: {e}")
        import traceback

        traceback.print_exc()
        return pd.DataFrame()


if __name__ == "__main__":
    df = obter_dados_cv_assistencias_workflow_tempo()
    print(f"Registros obtidos: {len(df)}")
    if not df.empty:
        print(df.head())
