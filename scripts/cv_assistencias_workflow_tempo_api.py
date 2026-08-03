#!/usr/bin/env python3
"""
Integração com API do CV CRM - Assistências Workflow Tempo
Endpoints:
  - GET /api/v1/cvdw/assistencias/workflow/tempo
  - GET /api/v1/cvdw/assistencias (situação / descrição / local)
  - GET /api/v1/cvdw/assistencias/itens (objeto da solicitação)
Credenciais: CVCRM_EMAIL e CVCRM_TOKEN

Docs: https://desenvolvedor.cvcrm.com.br/reference/assistenciasworkflowtempo-1
"""

import html
import logging
import os
import re
import sys
import time
from collections import defaultdict
from datetime import date, datetime
from typing import Dict, List, Optional

import pandas as pd
import requests

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from scripts.config import get_api_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ASSISTENCIAS_URL = "https://prati.cvcrm.com.br/api/v1/cvdw/assistencias"
ITENS_URL = "https://prati.cvcrm.com.br/api/v1/cvdw/assistencias/itens"

# Situacao de encerramento (nao aparece no workflow/tempo)
IDSITUACAO_FINALIZADA = 8
IDSITUACAO_CANCELADA = 7

CAMPOS = (
    # timeline
    "idassistencia",
    "idtempo",
    "idsituacao",
    "situacao",
    "tempo_minutos",
    "tempo_horas",
    "tempo_dias",
    "data_cad",
    "ativo",
    # status atual / encerramento
    "situacao_atual",
    "idsituacao_atual",
    "finalizada",
    "data_conclusao",
    "cancelada",
    # solicitacao / manutencao
    "descricao_solicitacao",
    "objetos",
    "ambiente",
    "sistema",
    "componente",
    "qtd_itens",
    "descricoes_itens",
    "itens_cobertos",
    "itens_nao_cobertos",
    "parecer_tecnico",
    "prioridade",
    "tipo_espaco",
    "area",
    # local / cliente
    "idempreendimento",
    "empreendimento",
    "etapa",
    "bloco",
    "unidade",
    "cliente",
    "documento_cliente",
    "data_cad_assistencia",
    "data_prevista_termino",
    "total_horas",
    "custo_previsto",
)


def _limpar_texto(valor: Optional[str]) -> Optional[str]:
    if valor is None:
        return None
    texto = html.unescape(str(valor))
    texto = re.sub(r"<[^>]+>", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto or None


def _explodir_objeto(texto: Optional[str]) -> Dict[str, Optional[str]]:
    """
    Quebra um objeto em ambiente / sistema / componente.
    Separadores aceitos: '|' ou ' - ' (mais comum na Prati).
    """
    vazio = {"ambiente": None, "sistema": None, "componente": None}
    if not texto:
        return vazio

    if "|" in texto:
        partes = [p.strip() for p in texto.split("|") if p.strip()]
    else:
        partes = [p.strip() for p in re.split(r"\s+-\s+", texto) if p.strip()]

    if not partes:
        return vazio
    if len(partes) == 1:
        return {"ambiente": partes[0], "sistema": None, "componente": None}
    if len(partes) == 2:
        return {"ambiente": partes[0], "sistema": None, "componente": partes[1]}
    return {
        "ambiente": partes[0],
        "sistema": partes[1],
        "componente": " - ".join(partes[2:]),
    }


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

    def fetch_itens_mapa(
        self,
        page_size: int = 500,
        sleep_between_calls: float = 0.0,
    ) -> Dict[int, Dict]:
        """
        Agrega itens por assistencia.
        Campo `item` = objeto da solicitacao (ex.: "Sala | Eletrica | Interruptor").
        """
        logger.info("Carregando itens das assistencias (objeto da solicitacao)...")
        dados = self._paginar_cvdw(
            ITENS_URL,
            page_size=page_size,
            sleep_between_calls=sleep_between_calls,
        )

        por_ass: Dict[int, List[Dict]] = defaultdict(list)
        for item in dados:
            aid = item.get("idassistencia")
            if aid is None:
                continue
            por_ass[int(aid)].append(item)

        mapa: Dict[int, Dict] = {}
        for aid, itens in por_ass.items():
            nomes = []
            descricoes = []
            cobertos = 0
            nao_cobertos = 0
            for it in itens:
                nome = _limpar_texto(it.get("item"))
                if nome:
                    nomes.append(nome)
                desc = _limpar_texto(it.get("descricao"))
                if desc:
                    descricoes.append(desc)
                if (it.get("coberto") or "").upper() == "S":
                    cobertos += 1
                elif (it.get("coberto") or "").upper() == "N":
                    nao_cobertos += 1

            explodido = _explodir_objeto(nomes[0] if nomes else None)

            mapa[aid] = {
                "objetos": " | ".join(nomes) if nomes else None,
                "ambiente": explodido["ambiente"],
                "sistema": explodido["sistema"],
                "componente": explodido["componente"],
                "qtd_itens": len(itens),
                "descricoes_itens": " | ".join(descricoes) if descricoes else None,
                "itens_cobertos": cobertos,
                "itens_nao_cobertos": nao_cobertos,
            }

        logger.info(f"  itens: {len(dados)} | assistencias com item: {len(mapa)}")
        return mapa

    def fetch_assistencias_mapa(
        self,
        page_size: int = 500,
        sleep_between_calls: float = 0.0,
    ) -> Dict[int, Dict]:
        """Mapa idassistencia -> dados atuais + contexto da solicitacao."""
        logger.info("Carregando assistencias (situacao / descricao / local)...")
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
                "descricao_solicitacao": _limpar_texto(item.get("descricao_area")),
                "parecer_tecnico": _limpar_texto(item.get("parecer_tecnico")),
                "prioridade": item.get("prioridade"),
                "tipo_espaco": item.get("unidade_area"),
                "area": item.get("area"),
                "idempreendimento": item.get("idempreendimento"),
                "empreendimento": item.get("empreendimento"),
                "etapa": item.get("etapa"),
                "bloco": item.get("bloco"),
                "unidade": item.get("unidade"),
                "cliente": item.get("cliente"),
                "documento_cliente": item.get("documento_cliente"),
                "data_cad_assistencia": item.get("data_cad"),
                "data_prevista_termino": item.get("data_prevista_termino"),
                "total_horas": item.get("total_horas"),
                "custo_previsto": item.get("custo_previsto"),
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
        Linha do tempo + contexto da solicitacao/manutencao.
        - tempo: /assistencias/workflow/tempo
        - finalizacao/local/descricao: /assistencias
        - objeto: /assistencias/itens (campo item)
        """
        mapa_ass = self.fetch_assistencias_mapa(
            page_size=page_size,
            sleep_between_calls=sleep_between_calls,
        )
        mapa_itens = self.fetch_itens_mapa(
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

            info = mapa_ass.get(int(aid), {}) if aid is not None else {}
            itens = mapa_itens.get(int(aid), {}) if aid is not None else {}

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
                    "descricao_solicitacao": info.get("descricao_solicitacao"),
                    "objetos": itens.get("objetos"),
                    "ambiente": itens.get("ambiente"),
                    "sistema": itens.get("sistema"),
                    "componente": itens.get("componente"),
                    "qtd_itens": itens.get("qtd_itens", 0),
                    "descricoes_itens": itens.get("descricoes_itens"),
                    "itens_cobertos": itens.get("itens_cobertos", 0),
                    "itens_nao_cobertos": itens.get("itens_nao_cobertos", 0),
                    "parecer_tecnico": info.get("parecer_tecnico"),
                    "prioridade": info.get("prioridade"),
                    "tipo_espaco": info.get("tipo_espaco"),
                    "area": info.get("area"),
                    "idempreendimento": info.get("idempreendimento"),
                    "empreendimento": info.get("empreendimento"),
                    "etapa": info.get("etapa"),
                    "bloco": info.get("bloco"),
                    "unidade": info.get("unidade"),
                    "cliente": info.get("cliente"),
                    "documento_cliente": info.get("documento_cliente"),
                    "data_cad_assistencia": info.get("data_cad_assistencia"),
                    "data_prevista_termino": info.get("data_prevista_termino"),
                    "total_horas": info.get("total_horas"),
                    "custo_previsto": info.get("custo_previsto"),
                }
            )

        com_objeto = sum(1 for r in results if r.get("objetos"))
        logger.info(
            f"Passagens de status: {len(results)} | "
            f"Assistencias distintas: {len({r['idassistencia'] for r in results})} | "
            f"Linhas com objeto: {com_objeto}"
        )
        return results


def obter_dados_cv_assistencias_workflow_tempo(
    page_size: int = 500,
    sleep_between_calls: float = 0.0,
    a_partir_data_referencia: Optional[str] = None,
    ate_data_referencia: Optional[str] = None,
) -> pd.DataFrame:
    """
    Obtem tempo por status + contexto da solicitacao para carga no MotherDuck.

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
