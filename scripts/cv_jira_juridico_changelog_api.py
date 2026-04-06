#!/usr/bin/env python3
"""
Integração Jira Jurídico — issues com changelog (tempo por status).

Endpoint principal: GET /rest/api/3/issue/{issueKey}?expand=changelog&fields=...

Baseado em exportar_issues_jira_com_changelog.py; mesmo projeto JRD e credenciais
do cv_jira_juridico_api (JIRA_URL, JIRA_EMAIL, JIRA_TOKEN).
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
from dotenv import load_dotenv

from scripts.config import get_api_config
from scripts.cv_jira_juridico_api import (
    MAX_RESULTS,
    PAUSA_ENTRE_PAGINAS,
    PROJETO_ALVO,
    _get_retry,
    _post_retry,
)

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Campo do add-on [CHART] Time in Status (comparar com cálculo pelo changelog)
CAMPO_CHART_TIME_STATUS = "customfield_10027"

PAUSA_ENTRE_ISSUES = 0.35


def _parse_jira_datetime(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    elif len(s) >= 5 and s[-5] in "+-" and s[-3] != ":":
        s = s[:-2] + ":" + s[-2:]
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        if "." in s:
            base, rest = s.split(".", 1)
            frac, tz = rest[:6], rest[6:]
            if tz.startswith(("+", "-")) and len(tz) == 5:
                tz = tz[:-2] + ":" + tz[-2:]
            try:
                return datetime.fromisoformat(f"{base}.{frac[:6]}{tz}")
            except ValueError:
                pass
        return None


def _coletar_transicoes_status(changelog: Dict[str, Any]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for hist in changelog.get("histories") or []:
        created = hist.get("created") or ""
        for it in hist.get("items") or []:
            if it.get("field") == "status":
                out.append(
                    {
                        "created": created,
                        "from": it.get("fromString") or "",
                        "to": it.get("toString") or "",
                    }
                )
    out.sort(key=lambda x: x["created"])
    return out


def _calcular_segundos_por_status(
    created_issue: str,
    transicoes: List[Dict[str, str]],
    agora: Optional[datetime] = None,
) -> Tuple[Dict[str, float], str]:
    if agora is None:
        agora = datetime.now(timezone.utc)

    t_created = _parse_jira_datetime(created_issue)
    if not transicoes:
        return {}, ""

    totais: Dict[str, float] = defaultdict(float)
    linha_tempo: List[str] = []

    prev_t = t_created
    for tr in transicoes:
        t = _parse_jira_datetime(tr["created"])
        de = tr["from"] or ""
        para = tr["to"] or ""
        linha_tempo.append(f"{de} -> {para} @ {tr['created']}")
        if prev_t and t and de:
            totais[de] += (t - prev_t).total_seconds()
        prev_t = t

    ultimo = transicoes[-1]
    t_last = _parse_jira_datetime(ultimo["created"])
    ultimo_status = ultimo["to"] or ""
    if t_last and ultimo_status:
        tot = (agora - t_last).total_seconds()
        if tot >= 0:
            totais[ultimo_status] += tot

    return dict(totais), " | ".join(linha_tempo)


def buscar_keys_projeto(jira_url: str, auth: tuple, projeto: str) -> List[str]:
    keys: List[str] = []
    token = None
    pagina = 0
    url = f"{jira_url}/rest/api/3/search/jql"
    jql = f"project = {projeto} ORDER BY key ASC"

    while True:
        payload: Dict[str, Any] = {
            "jql": jql,
            "maxResults": MAX_RESULTS,
            "fields": ["key"],
        }
        if token:
            payload["nextPageToken"] = token
        resp = _post_retry(url, payload, auth)
        if resp.status_code != 200:
            raise RuntimeError(f"Erro JQL {resp.status_code}: {resp.text[:500]}")
        data = resp.json()
        page = data.get("issues") or data.get("results") or []
        for issue in page:
            k = issue.get("key")
            if k:
                keys.append(k)
        token = data.get("nextPageToken")
        is_last = bool(data.get("isLast", False))
        pagina += 1
        logger.info(f"Listagem (só chaves): página {pagina}, +{len(page)}")
        if is_last or not token:
            break
        time.sleep(PAUSA_ENTRE_PAGINAS)
    return keys


def _passou_por_conferencia(transicoes: List[Dict[str, str]]) -> str:
    for tr in transicoes:
        for label in (tr.get("from") or "", tr.get("to") or ""):
            n = label.lower()
            if "conferência" in n or "conferencia" in n:
                return "Sim"
    return "Não"


def buscar_issue_com_changelog(
    jira_url: str, auth: tuple, issue_key: str
) -> Dict[str, Any]:
    qs = urlencode(
        {
            "expand": "changelog",
            "fields": f"summary,status,created,updated,{CAMPO_CHART_TIME_STATUS}",
        }
    )
    url = f"{jira_url}/rest/api/3/issue/{issue_key}?{qs}"
    r = _get_retry(url, auth)
    if r.status_code != 200:
        raise RuntimeError(f"Issue {issue_key}: {r.status_code} {r.text[:400]}")
    return r.json()


def _montar_linha(dados_issue: Dict[str, Any]) -> Dict[str, Any]:
    fields = dados_issue.get("fields") or {}
    changelog = dados_issue.get("changelog") or {}
    key = dados_issue.get("key", "")
    summary = fields.get("summary") or ""
    st = fields.get("status") or {}
    status_name = st.get("name") or ""
    created = fields.get("created") or ""
    updated = fields.get("updated") or ""
    chart_raw = fields.get(CAMPO_CHART_TIME_STATUS)

    trans = _coletar_transicoes_status(changelog)
    segundos_por_status, timeline = _calcular_segundos_por_status(created, trans)

    minutos_por_status = {
        nome: round(seg / 60.0, 2)
        for nome, seg in sorted(segundos_por_status.items())
    }

    status_visitados = set()
    for tr in trans:
        if tr["from"]:
            status_visitados.add(tr["from"])
        if tr["to"]:
            status_visitados.add(tr["to"])

    return {
        "Chave": key,
        "Resumo": summary,
        "Status atual": status_name,
        "Criado em": created,
        "Atualizado em": updated,
        "[CHART] Time in Status (API)": chart_raw if chart_raw is not None else "",
        "Chart preenchido (API)?": "Sim" if chart_raw else "Não",
        "Minutos por status (changelog JSON)": json.dumps(
            minutos_por_status, ensure_ascii=False
        ),
        "Status distintos (changelog)": "; ".join(sorted(status_visitados)),
        "Passou por Conferência?": _passou_por_conferencia(trans),
        "Quantidade transições status": len(trans),
        "Linha do tempo (status)": timeline[:30000],
    }


def obter_dados_jira_juridico_changelog(
    projeto: Optional[str] = None,
    limite_issues: Optional[int] = None,
) -> pd.DataFrame:
    """
    Obtém uma linha por issue do projeto com métricas derivadas do changelog.

    Args:
        projeto: chave Jira; default JRD (PROJETO_ALVO).
        limite_issues: se definido, só processa as N primeiras issues (teste).
    """
    try:
        if not get_api_config("jira"):
            logger.error("Configuração do Jira não encontrada")
            return pd.DataFrame()

        jira_url = os.environ.get(
            "JIRA_URL", "https://prati-empreendimentos.atlassian.net"
        ).rstrip("/")
        jira_email = os.environ.get("JIRA_EMAIL", "")
        jira_token = os.environ.get("JIRA_TOKEN", "")

        if not jira_email or not jira_token:
            logger.error("JIRA_EMAIL ou JIRA_TOKEN não configurados")
            return pd.DataFrame()

        auth = (jira_email, jira_token)
        projeto_key = projeto or PROJETO_ALVO

        logger.info(f"Buscando chaves do projeto {projeto_key}...")
        keys = buscar_keys_projeto(jira_url, auth, projeto_key)
        if not keys:
            return pd.DataFrame()

        if limite_issues is not None:
            keys = keys[:limite_issues]

        linhas: List[Dict[str, Any]] = []
        for i, key in enumerate(keys, start=1):
            if i == 1 or i % 25 == 0:
                logger.info(f"Changelog {i}/{len(keys)}: {key}")
            try:
                dados = buscar_issue_com_changelog(jira_url, auth, key)
                linhas.append(_montar_linha(dados))
            except Exception as ex:
                logger.warning(f"ERRO {key}: {ex}")
            time.sleep(PAUSA_ENTRE_ISSUES)

        if not linhas:
            return pd.DataFrame()

        df = pd.DataFrame(linhas)
        df["fonte"] = "jira_juridico_changelog"
        df["processado_em"] = datetime.now()
        logger.info(f"Changelog: {len(df)} registros")
        return df
    except Exception as e:
        logger.error(f"Erro changelog jurídico: {e}")
        import traceback

        traceback.print_exc()
        return pd.DataFrame()


if __name__ == "__main__":
    df = obter_dados_jira_juridico_changelog(limite_issues=5)
    print(f"Registros: {len(df)}")
    if not df.empty:
        print(df[["Chave", "Status atual", "Quantidade transições status"]].head())
