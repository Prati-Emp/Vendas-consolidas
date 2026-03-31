#!/usr/bin/env python3
"""
Integração com API do Jira - Projeto Jurídico
Endpoint: https://prati-empreendimentos.atlassian.net/rest/api/3
Autenticação: Basic Auth (email + token) — mesmos JIRA_EMAIL / JIRA_TOKEN do DHO

Estrutura espelhada de cv_jira_dho_api.py:
- Busca todas as issues do projeto jurídico com paginação
- Busca TODOS os campos disponíveis (usando "*all")
- Processa dados e cria DataFrame para upload no MotherDuck (pipeline separado)
"""

import logging
import time
import sys
import os
import requests
from datetime import datetime
from typing import Dict, List, Any
import pandas as pd
import json

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from scripts.config import get_api_config
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurações
MAX_RESULTS = 100
MAX_RETRIES = 4
BACKOFF_BASE = 1.6

PAUSA_ENTRE_PAGINAS = 0.3

# Projeto específico
PROJETO_ALVO = "JRD"

HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}


def _get_retry(url: str, auth: tuple):
    """GET com retries exponenciais para 429/5xx e erros de conexão."""
    last_exception = None

    for i in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(url, headers=HEADERS, auth=auth, timeout=45)
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(BACKOFF_BASE ** (i - 1))
                continue
            return r
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.RequestException,
        ) as e:
            last_exception = e
            if i < MAX_RETRIES:
                wait_time = BACKOFF_BASE ** (i - 1)
                logger.warning(
                    f"Erro de conexão (tentativa {i}/{MAX_RETRIES}), aguardando {wait_time:.1f}s..."
                )
                time.sleep(wait_time)
                continue
            else:
                raise last_exception

    if last_exception:
        raise last_exception
    raise RuntimeError("Falha ao fazer requisição GET")


def _post_retry(url: str, json_data: Dict[str, Any], auth: tuple):
    """POST com retries exponenciais para 429/5xx."""
    for i in range(1, MAX_RETRIES + 1):
        r = requests.post(url, headers=HEADERS, json=json_data, auth=auth, timeout=30)
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(BACKOFF_BASE ** (i - 1))
            continue
        return r
    return r


def buscar_nomes_campos(jira_url: str, auth: tuple) -> Dict[str, str]:
    """
    Busca os nomes amigáveis de todos os campos do Jira.
    Retorna um dicionário mapeando ID do campo -> Nome amigável.
    """
    logger.info("Buscando nomes dos campos do Jira...")
    url = f"{jira_url}/rest/api/3/field"
    resp = _get_retry(url, auth)

    if resp.status_code != 200:
        logger.warning(f"Erro ao buscar campos: {resp.status_code}")
        return {}

    campos = resp.json()
    mapeamento = {}

    campos_padrao = {
        "key": "Chave",
        "summary": "Resumo",
        "issuetype": "Tipo de item",
        "assignee": "Responsável",
        "reporter": "Relator",
        "priority": "Prioridade",
        "status": "Status",
        "resolution": "Resolução",
        "created": "Criado em",
        "updated": "Atualizado em",
        "duedate": "Data limite",
        "description": "Descrição",
        "parent": "Pai",
        "project": "Projeto",
        "creator": "Criador",
        "timespent": "Tempo gasto",
        "timeestimate": "Estimativa de tempo",
        "timeoriginalestimate": "Estimativa original",
        "aggregatetimespent": "Tempo total gasto",
        "aggregatetimeestimate": "Estimativa total",
        "aggregatetimeoriginalestimate": "Estimativa original total",
        "aggregateprogress": "Progresso agregado",
        "workratio": "Taxa de trabalho",
        "progress": "Progresso",
        "votes": "Votos",
        "watches": "Observadores",
        "fixVersions": "Versões de correção",
        "versions": "Versões",
        "components": "Componentes",
        "labels": "Etiquetas",
        "attachment": "Anexos",
        "comment": "Comentários",
        "subtasks": "Subtarefas",
        "issuelinks": "Links de issues",
    }

    mapeamento.update(campos_padrao)

    for campo in campos:
        campo_id = campo.get("id", "")
        campo_name = campo.get("name", campo_id)

        if campo_id.startswith("customfield_"):
            mapeamento[campo_id] = campo_name
        elif campo_id not in mapeamento:
            mapeamento[campo_id] = campo_name

    logger.info(f"{len(mapeamento)} campos mapeados")
    return mapeamento


def buscar_issues_jira_juridico(
    jira_url: str, auth: tuple, projeto: str = None
) -> List[Dict[str, Any]]:
    """
    Busca TODAS as issues do projeto jurídico usando paginação.
    Retorna todas as colunas disponíveis (não especifica campos, busca tudo).
    """
    if projeto is None:
        projeto = PROJETO_ALVO
    logger.info(f"Buscando issues do projeto {projeto}...")
    issues: List[Dict[str, Any]] = []
    token = None
    pagina = 0

    jql = f"project = {projeto} ORDER BY key ASC"
    url = f"{jira_url}/rest/api/3/search/jql"

    logger.info(f"JQL: {jql}")

    while True:
        payload = {
            "jql": jql,
            "maxResults": MAX_RESULTS,
            "fields": ["*all"],
        }
        if token:
            payload["nextPageToken"] = token

        logger.info(f"Enviando requisição (página {pagina + 1})...")
        resp = _post_retry(url, payload, auth)

        if resp.status_code != 200:
            logger.error(f"Erro JIRA {resp.status_code}: {resp.text[:800]}")
            raise RuntimeError(f"Erro JIRA {resp.status_code}: {resp.text[:500]}")

        data = resp.json()

        total_issues = data.get("total", 0)
        logger.info(f"Total de issues na resposta: {total_issues}")

        page_items = data.get("issues") or data.get("results") or []
        token = data.get("nextPageToken")
        is_last = bool(data.get("isLast", False))

        logger.info(f"Issues nesta página: {len(page_items)}")
        logger.info(f"Next token: {token is not None}")
        logger.info(f"Is last: {is_last}")

        if not page_items:
            logger.info("Página vazia (fim do cursor).")
            if pagina == 0:
                logger.warning(f"Nenhuma issue encontrada no projeto '{projeto}'!")
            break

        issues.extend(page_items)
        pagina += 1
        logger.info(
            f"Página {pagina}: +{len(page_items)} | acumulado {len(issues)} | isLast={is_last}"
        )

        if is_last or not token:
            break

        time.sleep(PAUSA_ENTRE_PAGINAS)

    logger.info(f"Busca concluída: {len(issues)} issues encontradas")
    return issues


def extrair_valor_campo(campo: Any) -> str:
    """Extrai o valor de um campo do Jira de forma genérica."""
    if campo is None:
        return ""

    if isinstance(campo, (str, int, float, bool)):
        return str(campo)

    if isinstance(campo, list):
        if not campo:
            return ""
        valores = []
        for item in campo:
            if isinstance(item, dict):
                valor = (
                    item.get("name")
                    or item.get("value")
                    or item.get("displayName")
                    or item.get("key")
                    or str(item)
                )
                valores.append(str(valor))
            else:
                valores.append(str(item))
        return "; ".join(valores)

    if isinstance(campo, dict):
        if "name" in campo:
            return str(campo["name"])
        if "displayName" in campo:
            return str(campo["displayName"])
        if "value" in campo:
            return str(campo["value"])
        if "key" in campo:
            return str(campo["key"])
        if "id" in campo:
            return str(campo["id"])
        if len(campo) == 1:
            return str(list(campo.values())[0])
        return json.dumps(campo, ensure_ascii=False)

    return str(campo)


def processar_issues(issues: List[Dict[str, Any]], projeto_nome: str) -> pd.DataFrame:
    """Processa as issues e extrai TODAS as colunas disponíveis (uma linha por issue)."""
    logger.info(f"Processando {len(issues)} issues do projeto {projeto_nome}...")
    dados_processados = []

    todos_campos = set()
    for issue in issues:
        fields = issue.get("fields", {}) or {}
        todos_campos.update(fields.keys())
        todos_campos.add("key")

    logger.info(f"Total de campos únicos encontrados: {len(todos_campos)}")

    for i, issue in enumerate(issues, start=1):
        if i % 50 == 0:
            logger.info(f"Processando {i}/{len(issues)}...")

        key = issue.get("key", "")
        fields = issue.get("fields", {}) or {}

        dados_issue = {"key": key}

        for campo_nome in sorted(todos_campos):
            if campo_nome == "key":
                continue

            valor_campo = fields.get(campo_nome)
            valor_formatado = extrair_valor_campo(valor_campo)
            dados_issue[campo_nome] = valor_formatado

        dados_processados.append(dados_issue)

    df = pd.DataFrame(dados_processados)

    df["fonte"] = "jira_juridico"
    df["processado_em"] = datetime.now()

    logger.info(f"Dados processados: {len(df)} registros, {len(df.columns)} colunas")
    return df


def obter_dados_jira_juridico(projeto: str = None) -> pd.DataFrame:
    """
    Função principal para obter dados do projeto jurídico do Jira.

    Args:
        projeto: chave do projeto Jira; se None, usa PROJETO_ALVO (env JIRA_PROJETO_JURIDICO ou padrão).
    """
    try:
        config = get_api_config("jira")
        if not config:
            logger.error("Configuração do Jira não encontrada")
            return pd.DataFrame()

        jira_url = os.environ.get(
            "JIRA_URL", "https://prati-empreendimentos.atlassian.net"
        )
        jira_email = os.environ.get("JIRA_EMAIL", "")
        jira_token = os.environ.get("JIRA_TOKEN", "")

        if not jira_email or not jira_token:
            logger.error("JIRA_EMAIL ou JIRA_TOKEN não configurados")
            return pd.DataFrame()

        auth = (jira_email, jira_token)
        projeto_key = projeto or PROJETO_ALVO

        mapeamento_campos = buscar_nomes_campos(jira_url, auth)

        issues = buscar_issues_jira_juridico(jira_url, auth, projeto_key)

        if not issues:
            logger.warning("Nenhuma issue encontrada no projeto jurídico")
            return pd.DataFrame()

        df = processar_issues(issues, projeto_key)

        if mapeamento_campos and not df.empty:
            colunas_renomeadas = {}
            for coluna_original in df.columns:
                if coluna_original in mapeamento_campos:
                    colunas_renomeadas[coluna_original] = mapeamento_campos[
                        coluna_original
                    ]
            if colunas_renomeadas:
                df = df.rename(columns=colunas_renomeadas)
                logger.info(f"Colunas renomeadas: {len(colunas_renomeadas)}")

        return df

    except Exception as e:
        logger.error(f"Erro ao obter dados do Jira Jurídico: {str(e)}")
        import traceback

        traceback.print_exc()
        return pd.DataFrame()


if __name__ == "__main__":
    print("Testando API de Jira Jurídico...")
    df = obter_dados_jira_juridico()
    print(f"Registros obtidos: {len(df)}")
    if not df.empty:
        print(f"Colunas: {list(df.columns)[:20]}...")
        print(df.head())
