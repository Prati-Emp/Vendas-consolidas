#!/usr/bin/env python3
"""
Integração com API do Jira - Projeto DHO
Endpoint: https://prati-empreendimentos.atlassian.net/rest/api/3
Autenticação: Basic Auth (email + token)

Adaptação do código exportar_issues_jira_dho.py:
- Busca todas as issues do projeto DHO com paginação
- Busca TODOS os campos disponíveis (usando "*all")
- Processa dados e cria DataFrame para upload no MotherDuck
"""

import logging
import time
import sys
import os
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd
import json

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from scripts.config import get_api_config
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurações
MAX_RESULTS = 100  # limite do Jira Cloud
MAX_RETRIES = 4    # para 429/5xx
BACKOFF_BASE = 1.6  # fator exponencial

# Pausas entre requisições (em segundos)
PAUSA_ENTRE_PAGINAS = 0.3

# Projeto específico
PROJETO_ALVO = "DHO"

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
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, 
                requests.exceptions.RequestException) as e:
            last_exception = e
            if i < MAX_RETRIES:
                wait_time = BACKOFF_BASE ** (i - 1)
                logger.warning(f"Erro de conexão (tentativa {i}/{MAX_RETRIES}), aguardando {wait_time:.1f}s...")
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
    
    # Mapeamento de campos padrão do Jira para nomes amigáveis
    campos_padrao = {
        'key': 'Chave',
        'summary': 'Resumo',
        'issuetype': 'Tipo de item',
        'assignee': 'Responsável',
        'reporter': 'Relator',
        'priority': 'Prioridade',
        'status': 'Status',
        'resolution': 'Resolução',
        'created': 'Criado em',
        'updated': 'Atualizado em',
        'duedate': 'Data limite',
        'description': 'Descrição',
        'parent': 'Pai',
        'project': 'Projeto',
        'creator': 'Criador',
        'timespent': 'Tempo gasto',
        'timeestimate': 'Estimativa de tempo',
        'timeoriginalestimate': 'Estimativa original',
        'aggregatetimespent': 'Tempo total gasto',
        'aggregatetimeestimate': 'Estimativa total',
        'aggregatetimeoriginalestimate': 'Estimativa original total',
        'aggregateprogress': 'Progresso agregado',
        'workratio': 'Taxa de trabalho',
        'progress': 'Progresso',
        'votes': 'Votos',
        'watches': 'Observadores',
        'fixVersions': 'Versões de correção',
        'versions': 'Versões',
        'components': 'Componentes',
        'labels': 'Etiquetas',
        'attachment': 'Anexos',
        'comment': 'Comentários',
        'subtasks': 'Subtarefas',
        'issuelinks': 'Links de issues',
    }
    
    # Adiciona campos padrão
    mapeamento.update(campos_padrao)
    
    # Processa campos retornados pela API
    for campo in campos:
        campo_id = campo.get('id', '')
        campo_name = campo.get('name', campo_id)
        
        # Se for um campo customizado, usa o nome retornado pela API
        if campo_id.startswith('customfield_'):
            mapeamento[campo_id] = campo_name
        # Se for um campo padrão que não está no nosso mapeamento, usa o nome da API
        elif campo_id not in mapeamento:
            mapeamento[campo_id] = campo_name
    
    logger.info(f"{len(mapeamento)} campos mapeados")
    return mapeamento


def buscar_issues_jira_dho(jira_url: str, auth: tuple, projeto: str = PROJETO_ALVO) -> List[Dict[str, Any]]:
    """
    Busca TODAS as issues do projeto DHO usando paginação.
    Retorna todas as colunas disponíveis (não especifica campos, busca tudo).
    """
    logger.info(f"Buscando issues do projeto {projeto}...")
    issues: List[Dict[str, Any]] = []
    token = None
    pagina = 0

    jql = f"project = {projeto} ORDER BY key ASC"
    url = f"{jira_url}/rest/api/3/search/jql"
    
    logger.info(f"JQL: {jql}")

    while True:
        # Especifica "*all" para buscar TODOS os campos disponíveis
        payload = {
            "jql": jql,
            "maxResults": MAX_RESULTS,
            "fields": ["*all"]  # Especifica para obter todos os campos
        }
        if token:
            payload["nextPageToken"] = token

        logger.info(f"Enviando requisição (página {pagina + 1})...")
        resp = _post_retry(url, payload, auth)
        
        if resp.status_code != 200:
            logger.error(f"Erro JIRA {resp.status_code}: {resp.text[:800]}")
            raise RuntimeError(f"Erro JIRA {resp.status_code}: {resp.text[:500]}")

        data = resp.json()
        
        # Logs de debug
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
        logger.info(f"Página {pagina}: +{len(page_items)} | acumulado {len(issues)} | isLast={is_last}")

        if is_last or not token:
            break
        
        # Pausa entre páginas para evitar bloqueios
        time.sleep(PAUSA_ENTRE_PAGINAS)

    logger.info(f"Busca concluída: {len(issues)} issues encontradas")
    return issues


def extrair_valor_campo(campo: Any) -> str:
    """
    Extrai o valor de um campo do Jira de forma genérica.
    Lida com objetos, listas, strings, números, etc.
    """
    if campo is None:
        return ''
    
    # Se for string ou número, retorna direto
    if isinstance(campo, (str, int, float, bool)):
        return str(campo)
    
    # Se for lista, junta os valores
    if isinstance(campo, list):
        if not campo:
            return ''
        # Se a lista contém objetos, tenta extrair nomes/valores
        valores = []
        for item in campo:
            if isinstance(item, dict):
                # Tenta pegar 'name', 'value', 'displayName', 'key', ou o primeiro valor string
                valor = item.get('name') or item.get('value') or item.get('displayName') or item.get('key') or str(item)
                valores.append(str(valor))
            else:
                valores.append(str(item))
        return '; '.join(valores)
    
    # Se for dicionário, tenta extrair informações relevantes
    if isinstance(campo, dict):
        # Prioriza campos comuns do Jira
        if 'name' in campo:
            return str(campo['name'])
        if 'displayName' in campo:
            return str(campo['displayName'])
        if 'value' in campo:
            return str(campo['value'])
        if 'key' in campo:
            return str(campo['key'])
        if 'id' in campo:
            return str(campo['id'])
        # Se tiver apenas um campo, retorna o valor
        if len(campo) == 1:
            return str(list(campo.values())[0])
        # Caso contrário, retorna representação JSON
        return json.dumps(campo, ensure_ascii=False)
    
    # Fallback: converte para string
    return str(campo)


def processar_issues(issues: List[Dict[str, Any]], projeto_nome: str) -> pd.DataFrame:
    """
    Processa as issues e extrai TODAS as colunas disponíveis (uma linha por issue).
    """
    logger.info(f"Processando {len(issues)} issues do projeto {projeto_nome}...")
    dados_processados = []
    
    # Coleta todos os campos únicos de todas as issues para garantir todas as colunas
    todos_campos = set()
    for issue in issues:
        fields = issue.get('fields', {}) or {}
        todos_campos.update(fields.keys())
        # Adiciona também a chave da issue
        todos_campos.add('key')
    
    logger.info(f"Total de campos únicos encontrados: {len(todos_campos)}")
    
    for i, issue in enumerate(issues, start=1):
        if i % 50 == 0:
            logger.info(f"Processando {i}/{len(issues)}...")
        
        key = issue.get('key', '')
        fields = issue.get('fields', {}) or {}
        
        # Cria um dicionário com todos os campos
        dados_issue = {
            'key': key  # Chave da issue sempre primeiro
        }
        
        # Processa todos os campos disponíveis
        for campo_nome in sorted(todos_campos):
            if campo_nome == 'key':
                continue  # Já adicionamos acima
            
            valor_campo = fields.get(campo_nome)
            valor_formatado = extrair_valor_campo(valor_campo)
            dados_issue[campo_nome] = valor_formatado
        
        dados_processados.append(dados_issue)
    
    # Converte para DataFrame
    df = pd.DataFrame(dados_processados)
    
    # Adiciona colunas padrão do sistema
    df['fonte'] = 'jira_dho'
    df['processado_em'] = datetime.now()
    
    logger.info(f"✅ Dados processados: {len(df)} registros, {len(df.columns)} colunas")
    return df


def obter_dados_jira_dho() -> pd.DataFrame:
    """
    Função principal para obter dados do projeto DHO do Jira
    
    Returns:
        pd.DataFrame: DataFrame com todas as issues do projeto DHO
    """
    try:
        # Obter configuração do Jira
        config = get_api_config('jira')
        if not config:
            logger.error("Configuração do Jira não encontrada")
            return pd.DataFrame()
        
        jira_url = os.environ.get('JIRA_URL', 'https://prati-empreendimentos.atlassian.net')
        jira_email = os.environ.get('JIRA_EMAIL', '')
        jira_token = os.environ.get('JIRA_TOKEN', '')
        
        if not jira_email or not jira_token:
            logger.error("JIRA_EMAIL ou JIRA_TOKEN não configurados")
            return pd.DataFrame()
        
        auth = (jira_email, jira_token)
        
        # Buscar nomes dos campos (opcional, para melhor legibilidade)
        mapeamento_campos = buscar_nomes_campos(jira_url, auth)
        
        # Buscar issues do projeto DHO
        issues = buscar_issues_jira_dho(jira_url, auth, PROJETO_ALVO)
        
        if not issues:
            logger.warning("Nenhuma issue encontrada no projeto DHO")
            return pd.DataFrame()
        
        # Processar issues
        df = processar_issues(issues, PROJETO_ALVO)
        
        # Opcional: renomear colunas com nomes amigáveis
        if mapeamento_campos and not df.empty:
            colunas_renomeadas = {}
            for coluna_original in df.columns:
                if coluna_original in mapeamento_campos:
                    colunas_renomeadas[coluna_original] = mapeamento_campos[coluna_original]
            if colunas_renomeadas:
                df = df.rename(columns=colunas_renomeadas)
                logger.info(f"Colunas renomeadas: {len(colunas_renomeadas)}")
        
        return df
        
    except Exception as e:
        logger.error(f"Erro ao obter dados do Jira DHO: {str(e)}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


if __name__ == "__main__":
    # Teste local
    print("Testando API de Jira DHO...")
    df = obter_dados_jira_dho()
    print(f"Registros obtidos: {len(df)}")
    if not df.empty:
        print(f"Colunas: {list(df.columns)[:20]}...")  # Mostra primeiras 20 colunas
        print(df.head())

