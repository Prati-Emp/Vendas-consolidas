#!/usr/bin/env python3
"""
Integração com API do CV CRM - Corretores (referência RLS)
Endpoint: GET /api/v1/cadastros/corretores
Enriquecimento: GET /api/v1/cvdw/imobiliarias (mapa id -> nome)
Credenciais: CVCRM_EMAIL e CVCRM_TOKEN

Docs: https://desenvolvedor.cvcrm.com.br/reference/retornacorretores
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

IMOBILIARIAS_URL = "https://prati.cvcrm.com.br/api/v1/cvdw/imobiliarias"

CAMPOS_RLS = (
    "idcorretor",
    "nome",
    "email",
    "idimobiliaria",
    "imobiliaria",
    "ativo_login",
    "documento",
    "tipo_corretor",
)


class CorretoresAPIClient:
    """Cliente para API de Corretores do CV CRM."""

    def __init__(self):
        self.config = get_api_config("cv_corretores")
        if not self.config:
            raise ValueError("Configuração da API CV Corretores não encontrada")
        self.base_url = self.config.base_url.rstrip("/")
        self.headers = self.config.headers

    def fetch_mapa_imobiliarias(
        self,
        page_size: int = 500,
        max_pages: int = 100,
    ) -> Dict[int, Optional[str]]:
        """Mapa idimobiliaria -> nome (CVDW). O endpoint de corretores quase sempre traz nome_fantasia vazio."""
        mapa: Dict[int, Optional[str]] = {}
        page = 1

        while page <= max_pages:
            resp = requests.get(
                IMOBILIARIAS_URL,
                headers=self.headers,
                params={"pagina": page, "registros_por_pagina": page_size},
                timeout=60,
            )
            if resp.status_code != 200:
                raise RuntimeError(
                    f"HTTP {resp.status_code} (imobiliarias): {resp.text}"
                )

            data = resp.json()
            dados = data.get("dados") or []
            if not dados:
                break

            for item in dados:
                idimob = item.get("idimobiliaria")
                nome = (item.get("nome") or "").strip()
                if idimob is not None:
                    mapa[int(idimob)] = nome or None

            total_pages = data.get("total_de_paginas")
            if total_pages and page >= total_pages:
                break
            if len(dados) < page_size:
                break
            page += 1

        logger.info(f"Imobiliárias no mapa CVDW: {len(mapa)}")
        return mapa

    def _nome_imobiliaria(self, item: Dict, mapa: Dict[int, Optional[str]]) -> Optional[str]:
        imob = item.get("imobiliaria") or {}
        if isinstance(imob, dict):
            nome = (imob.get("nome_fantasia") or "").strip()
            if nome:
                return nome

        idimob = item.get("idimobiliaria")
        if idimob is None and isinstance(imob, dict):
            idimob = imob.get("idimobiliaria")

        if idimob is None:
            return None

        return mapa.get(int(idimob))

    def buscar_corretores(
        self,
        page_size: int = 500,
        max_pages: int = 5000,
        sleep_between_calls: float = 0.0,
    ) -> List[Dict]:
        """Busca corretores paginando (limit/offset) para tabela de referência RLS."""
        logger.info("Carregando nomes das imobiliárias (CVDW)...")
        mapa_imob = self.fetch_mapa_imobiliarias()

        offset = 0
        page = 1
        results: List[Dict] = []
        total_processed = 0

        while page <= max_pages:
            payload = {"limit": page_size, "offset": offset}
            logger.info(
                f"Requisição página {page} (offset={offset}, limit={page_size})..."
            )
            resp = requests.get(
                self.base_url, headers=self.headers, params=payload, timeout=60
            )
            logger.info(f"Status: {resp.status_code}")

            if resp.status_code != 200:
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")

            data = resp.json()
            dados = data.get("corretores") or data.get("corretor") or []
            if isinstance(dados, dict):
                dados = [dados]

            logger.info(f"Registros nesta página: {len(dados)}")

            if not isinstance(dados, list) or len(dados) == 0:
                logger.info("Nenhum dado encontrado, parando paginação.")
                break

            for item in dados:
                total_processed += 1
                email = (item.get("email") or "").strip() or None
                nome = (item.get("nome") or "").strip() or None
                idcorretor = item.get("idcorretor")

                imob = item.get("imobiliaria") or {}
                idimobiliaria = item.get("idimobiliaria")
                if idimobiliaria is None and isinstance(imob, dict):
                    idimobiliaria = imob.get("idimobiliaria")

                documento = (item.get("documento") or "").strip() or None
                ativo_login = (item.get("ativo_login") or "").strip() or None
                tipo_corretor = (item.get("tipo_corretor") or "").strip() or None

                results.append(
                    {
                        "idcorretor": idcorretor,
                        "nome": nome,
                        "email": email,
                        "idimobiliaria": idimobiliaria,
                        "imobiliaria": self._nome_imobiliaria(item, mapa_imob),
                        "ativo_login": ativo_login,
                        "documento": documento,
                        "tipo_corretor": tipo_corretor,
                    }
                )

            if len(dados) < page_size:
                logger.info("Página com menos registros que o limite, parando.")
                break

            offset += page_size
            page += 1
            if sleep_between_calls > 0:
                time.sleep(sleep_between_calls)

        vistos = set()
        unicos: List[Dict] = []
        for row in results:
            key = row.get("idcorretor")
            if key in vistos:
                continue
            vistos.add(key)
            unicos.append(row)

        ativos = sum(1 for r in unicos if r.get("ativo_login") == "S")
        inativos = sum(1 for r in unicos if r.get("ativo_login") == "N")
        logger.info(
            f"Total processados: {total_processed} | Unicos: {len(unicos)} "
            f"| Ativos: {ativos} | Inativos: {inativos}"
        )
        return unicos


def obter_dados_cv_corretores(
    page_size: int = 500,
    sleep_between_calls: float = 0.0,
) -> pd.DataFrame:
    """
    Obtém corretores para carga no MotherDuck (referência RLS).

    Returns:
        DataFrame com CAMPOS_RLS + fonte, processado_em, Data_Snapshot.
    """
    try:
        client = CorretoresAPIClient()
        rows = client.buscar_corretores(
            page_size=page_size,
            sleep_between_calls=sleep_between_calls,
        )
        if not rows:
            logger.warning("Nenhum corretor encontrado")
            return pd.DataFrame()

        df = pd.DataFrame(rows, columns=list(CAMPOS_RLS))
        df["fonte"] = "cv_corretores"
        df["processado_em"] = datetime.now()
        df["Data_Snapshot"] = pd.to_datetime(date.today())

        logger.info(f"Dados processados: {len(df)} registros")
        return df
    except Exception as e:
        logger.error(f"Erro ao obter dados de corretores: {e}")
        import traceback

        traceback.print_exc()
        return pd.DataFrame()


if __name__ == "__main__":
    df = obter_dados_cv_corretores()
    print(f"Registros obtidos: {len(df)}")
    if not df.empty:
        print(df.head())
