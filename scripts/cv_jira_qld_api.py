#!/usr/bin/env python3
"""
Integração com API do Jira - Projeto QLD (NC - Não Conformidade)
Board: https://prati-empreendimentos.atlassian.net/jira/software/c/projects/QLD/boards/948
Endpoint: https://prati-empreendimentos.atlassian.net/rest/api/3
Autenticação: Basic Auth (email + token) — mesmos JIRA_EMAIL / JIRA_TOKEN do DHO

Espelha cv_jira_dho_api.py, mas descarta campos vazios e ruído da instância Jira
(o DHO grava ~315 colunas porque *all* traz campos de todos os projetos).
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from scripts.config import get_api_config

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_RESULTS = 100
MAX_RETRIES = 4
BACKOFF_BASE = 1.6
PAUSA_ENTRE_PAGINAS = 0.3

PROJETO_ALVO = "QLD"

HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}

# Sempre manter, mesmo se vazios nesta carga (campos do próprio projeto NC).
CAMPOS_CORE = {
    "key",
    "summary",
    "issuetype",
    "assignee",
    "reporter",
    "priority",
    "status",
    "statusCategory",
    "statuscategorychangedate",
    "resolution",
    "resolutiondate",
    "created",
    "updated",
    "duedate",
    "description",
    "parent",
    "project",
    "creator",
    "labels",
    "subtasks",
    "security",
    "customfield_10015",  # Data de início
    "customfield_10026",  # [CHART] Date of First Response
    "customfield_10027",  # [CHART] Time in Status
    "customfield_10307",  # Área
    "customfield_10467",  # Pessoa movimenta Pausa
    "customfield_11021",  # Data de Finalização
    "customfield_12476",  # NC - Origem da NC
    "customfield_12478",  # NC - Atividade
    "customfield_12479",  # NC - Disposição
    "customfield_12480",  # NC - Concessões Obtidas
    "customfield_12481",  # NC - Ações de Correção
    "customfield_12483",  # NC - Necessidade de eliminar a Causa Raiz
    "customfield_12484",  # NC - Análise Critica
    "customfield_12486",  # NC - Causa Raiz
    "customfield_12487",  # NC - Eliminação da Causa Raiz
    "customfield_12488",  # NC - Origem
    "customfield_12521",  # NC - Processo
    "customfield_12554",  # NC - Eficácia das ações
    "customfield_12620",  # NC - Não Conformidade Similares
    "customfield_12829",  # Área Envolvida
    "customfield_12863",  # Nível de Impacto
}

# Sempre presentes no *all* da instância e inúteis para esta tabela.
CAMPOS_RUIDO = {
    "aggregateprogress",
    "aggregatetimeestimate",
    "aggregatetimeoriginalestimate",
    "aggregatetimespent",
    "attachment",
    "comment",
    "customfield_10019",  # Rank / Classificação
    "customfield_12372",  # PDA - ONDE
    "customfield_12374",  # PDA - COMO
    "customfield_12375",  # PDA - CUSTO
    "issuelinks",
    "lastViewed",
    "progress",
    "timeestimate",
    "timeoriginalestimate",
    "timespent",
    "votes",
    "watches",
    "worklog",
    "workratio",
}


def _get_retry(url: str, auth: tuple):
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
            raise last_exception
    if last_exception:
        raise last_exception
    raise RuntimeError("Falha ao fazer requisição GET")


def _post_retry(url: str, json_data: Dict[str, Any], auth: tuple):
    for i in range(1, MAX_RETRIES + 1):
        r = requests.post(url, headers=HEADERS, json=json_data, auth=auth, timeout=30)
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(BACKOFF_BASE ** (i - 1))
            continue
        return r
    return r


def buscar_nomes_campos(jira_url: str, auth: tuple) -> Dict[str, str]:
    logger.info("Buscando nomes dos campos do Jira...")
    url = f"{jira_url}/rest/api/3/field"
    resp = _get_retry(url, auth)
    if resp.status_code != 200:
        logger.warning(f"Erro ao buscar campos: {resp.status_code}")
        return {}

    mapeamento = {
        "key": "Chave",
        "summary": "Resumo",
        "issuetype": "Tipo de item",
        "assignee": "Responsável",
        "reporter": "Relator",
        "priority": "Prioridade",
        "status": "Status",
        "resolution": "Resolução",
        "resolutiondate": "Resolvido",
        "created": "Criado em",
        "updated": "Atualizado em",
        "duedate": "Data limite",
        "description": "Descrição",
        "parent": "Pai",
        "project": "Projeto",
        "creator": "Criador",
        "labels": "Etiquetas",
        "subtasks": "Subtarefas",
        "security": "Nível de Segurança",
        "statusCategory": "Categoria do status",
        "statuscategorychangedate": "Categoria do status alterada",
    }

    for campo in resp.json():
        campo_id = campo.get("id", "")
        campo_name = campo.get("name", campo_id)
        if campo_id.startswith("customfield_"):
            mapeamento[campo_id] = campo_name
        elif campo_id not in mapeamento:
            mapeamento[campo_id] = campo_name

    logger.info(f"{len(mapeamento)} campos mapeados")
    return mapeamento


def buscar_issues_jira_qld(
    jira_url: str, auth: tuple, projeto: str = PROJETO_ALVO
) -> List[Dict[str, Any]]:
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
        page_items = data.get("issues") or data.get("results") or []
        token = data.get("nextPageToken")
        is_last = bool(data.get("isLast", False))

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


def _texto_adf(campo: Any) -> Optional[str]:
    if not isinstance(campo, dict):
        return None
    if campo.get("type") != "doc" and "content" not in campo:
        return None
    texts: List[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if isinstance(node.get("text"), str):
                texts.append(node["text"])
            for child in node.get("content") or []:
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(campo)
    return "\n".join(texts).strip() if texts else ""


def extrair_valor_campo(campo: Any) -> str:
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
        adf = _texto_adf(campo)
        if adf is not None:
            return adf
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


def _campo_preenchido(valor: str) -> bool:
    return bool(valor) and valor.strip() not in ("", "[]", "{}", "null", "-1")


def processar_issues(issues: List[Dict[str, Any]], projeto_nome: str) -> pd.DataFrame:
    logger.info(f"Processando {len(issues)} issues do projeto {projeto_nome}...")
    todos_campos = set()
    for issue in issues:
        fields = issue.get("fields", {}) or {}
        todos_campos.update(fields.keys())
    todos_campos.add("key")
    todos_campos -= CAMPOS_RUIDO

    dados_processados = []
    preenchidos = {campo: False for campo in todos_campos if campo != "key"}

    for i, issue in enumerate(issues, start=1):
        if i % 50 == 0:
            logger.info(f"Processando {i}/{len(issues)}...")
        fields = issue.get("fields", {}) or {}
        dados_issue = {"key": issue.get("key", "")}
        for campo_nome in sorted(todos_campos):
            if campo_nome == "key":
                continue
            valor_formatado = extrair_valor_campo(fields.get(campo_nome))
            dados_issue[campo_nome] = valor_formatado
            if _campo_preenchido(valor_formatado):
                preenchidos[campo_nome] = True
        dados_processados.append(dados_issue)

    df = pd.DataFrame(dados_processados)
    cols_keep = [
        c for c in df.columns if c == "key" or c in CAMPOS_CORE or preenchidos.get(c)
    ]
    df = df[cols_keep]

    df["fonte"] = "jira_qld"
    df["processado_em"] = datetime.now()
    logger.info(f"Dados processados: {len(df)} registros, {len(df.columns)} colunas")
    return df


def obter_dados_jira_qld(projeto: str = None) -> pd.DataFrame:
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
        issues = buscar_issues_jira_qld(jira_url, auth, projeto_key)
        if not issues:
            logger.warning("Nenhuma issue encontrada no projeto QLD")
            return pd.DataFrame()

        df = processar_issues(issues, projeto_key)
        if mapeamento_campos and not df.empty:
            colunas_renomeadas = {
                col: mapeamento_campos[col]
                for col in df.columns
                if col in mapeamento_campos
            }
            if colunas_renomeadas:
                df = df.rename(columns=colunas_renomeadas)
                logger.info(f"Colunas renomeadas: {len(colunas_renomeadas)}")
        return df
    except Exception as e:
        logger.error(f"Erro ao obter dados do Jira QLD: {str(e)}")
        import traceback

        traceback.print_exc()
        return pd.DataFrame()


if __name__ == "__main__":
    print("Testando API de Jira QLD (NC - Não Conformidade)...")
    df = obter_dados_jira_qld()
    print(f"Registros obtidos: {len(df)}")
    if not df.empty:
        print(f"Colunas ({len(df.columns)}): {list(df.columns)}")
        print(df.head())
