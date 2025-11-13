#!/usr/bin/env python3
"""
Integração com API do Jira
Endpoint: https://prati-empreendimentos.atlassian.net/rest/api/3
Autenticação: Basic Auth (email + token)

Adaptação do código exportar_issues_jira.py:
- Busca todos os projetos ou projetos específicos
- Busca todas as issues de cada projeto com paginação
- Busca changelog de cada issue para transições de status
- Processa dados e cria uma linha por transição de status
- Upload para MotherDuck
"""

import asyncio
import logging
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd

import sys
import os
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
PAUSA_ENTRE_CHANGELOG = 0.5
PAUSA_ENTRE_PAGINAS = 0.3
PAUSA_ENTRE_PROJETOS = 2.0

# Campos necessários para as colunas
FIELDS = [
    "summary",                     # C: Resumo
    "issuetype",                   # A: Tipo de item
    "assignee",                    # D: Responsável
    "reporter",                    # E: Relator
    "priority",                    # F: Prioridade
    "status",                      # G: Status
    "resolution",                  # H: Resolução
    "created",                     # I: Criado
    "updated",                     # J: Atualizado(a)
    "duedate",                     # K: Data limite
    "description",                 # L: Descrição
    "parent",                      # AA: Pai
    "project",                     # Z: Projeto.name
    "customfield_10015",          # V, X: Start date / Data original início
    "customfield_10170",           # Y: Dias para conclusão de Tarefa
    "customfield_10370",           # U: Data Fim corrigida (Adj Finish)
    "customfield_10371",           # T: Data Início corrigida (Adj Start)
]

HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}


class JiraAPIClient:
    """Cliente para API do Jira"""
    
    def __init__(self):
        self.config = get_api_config('jira')
        
        if not self.config:
            raise ValueError("Configuração da API Jira não encontrada")
        
        self.base_url = self.config.base_url
        self.email = os.environ.get('JIRA_EMAIL', '')
        self.token = os.environ.get('JIRA_TOKEN', '')
        
        if not self.email or not self.token:
            raise ValueError("JIRA_EMAIL e JIRA_TOKEN devem estar configurados")
        
        self.auth = (self.email, self.token)
    
    def _post_retry(self, url: str, json: Dict[str, Any]):
        """POST com retries exponenciais para 429/5xx."""
        for i in range(1, MAX_RETRIES + 1):
            r = requests.post(url, headers=HEADERS, json=json, auth=self.auth, timeout=30)
            if r.status_code in (429, 500, 502, 503, 504):
                wait_time = BACKOFF_BASE ** (i - 1)
                logger.warning(f"Erro {r.status_code} (tentativa {i}/{MAX_RETRIES}), aguardando {wait_time:.1f}s...")
                time.sleep(wait_time)
                continue
            return r
        return r
    
    def _get_retry(self, url: str):
        """GET com retries exponenciais para 429/5xx e erros de conexão."""
        last_exception = None
        
        for i in range(1, MAX_RETRIES + 1):
            try:
                r = requests.get(url, headers=HEADERS, auth=self.auth, timeout=45)
                if r.status_code in (429, 500, 502, 503, 504):
                    wait_time = BACKOFF_BASE ** (i - 1)
                    logger.warning(f"Erro {r.status_code} (tentativa {i}/{MAX_RETRIES}), aguardando {wait_time:.1f}s...")
                    time.sleep(wait_time)
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
    
    def buscar_projetos_jira(self, projetos_alvo: List[str] = None) -> List[str]:
        """
        Busca todos os projetos ou retorna a lista de projetos alvo.
        """
        if projetos_alvo:
            logger.info(f"Usando projetos específicos: {', '.join(projetos_alvo)}")
            return projetos_alvo
        
        logger.info("Buscando todos os projetos do Jira...")
        url = f"{self.base_url}/rest/api/3/project"
        resp = self._get_retry(url)
        
        if resp.status_code != 200:
            logger.error(f"Erro ao buscar projetos: {resp.status_code}")
            raise RuntimeError(f"Erro JIRA {resp.status_code}")
        
        projetos = resp.json()
        project_keys = [p.get('key', '') for p in projetos if p.get('key')]
        logger.info(f"{len(project_keys)} projetos encontrados")
        return project_keys
    
    def buscar_changelog(self, issue_key: str) -> List[Dict[str, Any]]:
        """
        Busca o changelog (histórico de mudanças) de uma issue para obter transições de status.
        """
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}?expand=changelog"
        
        try:
            resp = self._get_retry(url)
            
            if resp.status_code != 200:
                return []
            
            data = resp.json()
            changelog = data.get('changelog', {})
            histories = changelog.get('histories', [])
            
            transicoes = []
            for history in histories:
                author = history.get('author', {}) or {}
                created = history.get('created', '')
                
                for item in history.get('items', []):
                    if item.get('field') == 'status':
                        transicoes.append({
                            'to': item.get('toString', ''),
                            'from': item.get('fromString', ''),
                            'authorDisplayName': author.get('displayName', ''),
                            'authorEmail': author.get('emailAddress', ''),
                            'date': created,
                            'id': history.get('id', ''),
                        })
            
            return transicoes
            
        except Exception as e:
            logger.warning(f"Erro ao buscar changelog de {issue_key}: {e}")
            return []
    
    def buscar_issues_jira(self, projeto: str) -> List[Dict[str, Any]]:
        """
        Busca TODAS as issues do projeto usando paginação.
        """
        logger.info(f"Buscando issues do projeto {projeto}...")
        issues: List[Dict[str, Any]] = []
        token = None
        pagina = 0
        
        jql = f"project = {projeto} ORDER BY key ASC"
        url = f"{self.base_url}/rest/api/3/search/jql"
        
        while True:
            payload = {
                "jql": jql,
                "maxResults": MAX_RESULTS,
                "fields": FIELDS,
            }
            if token:
                payload["nextPageToken"] = token
            
            resp = self._post_retry(url, payload)
            if resp.status_code != 200:
                logger.error(f"Erro JIRA {resp.status_code}: {resp.text[:800]}")
                raise RuntimeError(f"Erro JIRA {resp.status_code}")
            
            data = resp.json()
            page_items = data.get("issues") or data.get("results") or []
            token = data.get("nextPageToken")
            is_last = bool(data.get("isLast", False))
            
            if not page_items:
                logger.info("Página vazia (fim do cursor).")
                break
            
            issues.extend(page_items)
            pagina += 1
            logger.info(f"Página {pagina}: +{len(page_items)} | acumulado {len(issues)} | isLast={is_last}")
            
            if is_last or not token:
                break
            
            time.sleep(PAUSA_ENTRE_PAGINAS)
        
        logger.info(f"Busca concluída: {len(issues)} issues encontradas")
        return issues
    
    def formatar_data(self, data_str: Optional[str]) -> str:
        """Formata data do Jira para formato brasileiro."""
        if not data_str:
            return ''
        try:
            # Jira retorna: "2025-10-29T10:07:46.000-0300"
            dt = datetime.strptime(data_str[:19], "%Y-%m-%dT%H:%M:%S")
            return dt.strftime("%d/%m/%Y %H:%M:%S")
        except:
            try:
                # Tenta formato de data simples
                dt = datetime.strptime(data_str[:10], "%Y-%m-%d")
                return dt.strftime("%d/%m/%Y")
            except:
                return data_str
    
    def formatar_data_simples(self, data_str: Optional[str]) -> str:
        """Formata data do Jira para formato brasileiro simples (sem hora)."""
        if not data_str:
            return ''
        try:
            dt = datetime.strptime(data_str[:10], "%Y-%m-%d")
            return dt.strftime("%d/%m/%Y")
        except:
            return data_str
    
    def processar_issues(self, issues: List[Dict[str, Any]], projeto_nome: str) -> List[Dict[str, Any]]:
        """
        Processa as issues e extrai todas as colunas solicitadas.
        Para cada issue, busca o changelog e cria uma linha por transição de status.
        Se não houver transições, cria uma linha com a issue.
        """
        logger.info(f"Processando {len(issues)} issues do projeto {projeto_nome}...")
        dados_processados = []
        
        for i, issue in enumerate(issues, start=1):
            if i % 50 == 0:
                logger.info(f"  Processando {i}/{len(issues)}...")
            
            key = issue.get('key', '')
            fields = issue.get('fields', {}) or {}
            
            # Extrai campos básicos
            issuetype = fields.get('issuetype', {}) or {}
            assignee = fields.get('assignee', {}) or {}
            reporter = fields.get('reporter', {}) or {}
            priority = fields.get('priority', {}) or {}
            status = fields.get('status', {}) or {}
            resolution = fields.get('resolution', {}) or {}
            parent = fields.get('parent', {}) or {}
            project = fields.get('project', {}) or {}
            
            # Campos customizados
            start_date = fields.get('customfield_10015')  # Start date
            duration = fields.get('customfield_10170')    # Duração
            adj_finish = fields.get('customfield_10370')  # Adj Finish
            adj_start = fields.get('customfield_10371')   # Adj Start
            
            # Calcula data original fim (W)
            data_original_fim = ''
            if start_date and duration:
                try:
                    dt_start = datetime.strptime(start_date[:10], "%Y-%m-%d")
                    dt_fim = dt_start + timedelta(days=int(duration))
                    data_original_fim = dt_fim.strftime("%d/%m/%Y")
                except:
                    pass
            
            # Dados base da issue
            dados_base = {
                "A - Tipo de item": issuetype.get('name', ''),
                "B - Chave": key,
                "C - Resumo": fields.get('summary', ''),
                "D - Responsável": assignee.get('displayName', ''),
                "E - Relator": reporter.get('displayName', ''),
                "F - Prioridade": priority.get('name', ''),
                "G - Status": status.get('name', ''),
                "H - Resolução": resolution.get('name', ''),
                "I - Criado": self.formatar_data(fields.get('created')),
                "J - Atualizado(a)": self.formatar_data(fields.get('updated')),
                "K - Data limite": self.formatar_data_simples(fields.get('duedate')),
                "L - Descrição": fields.get('description', ''),
                "T - Data Início corrigida": self.formatar_data_simples(adj_start),
                "U - Data Fim corrigida": self.formatar_data_simples(adj_finish),
                "V - Data original início": self.formatar_data_simples(start_date),
                "W - Data original fim": data_original_fim,
                "X - Start date": self.formatar_data_simples(start_date),
                "Y - Dias para conclusão de Tarefa": duration if duration else '',
                "Z - Projeto.name": project.get('name', projeto_nome),
                "AA - Pai": parent.get('key', ''),
            }
            
            # Busca transições de status
            transicoes = self.buscar_changelog(key)
            time.sleep(PAUSA_ENTRE_CHANGELOG)
            
            # Se não houver transições, cria uma linha sem dados de transição
            if not transicoes:
                linha = dados_base.copy()
                linha.update({
                    "M - Status Transition": '',
                    "N - Status Transition.to": '',
                    "O - Status Transition.from": '',
                    "P - Status Transition.authorDisplayName": '',
                    "Q - Status Transition.authorEmail": '',
                    "R - Status Transition.date": '',
                    "S - Status Transition.id": '',
                })
                dados_processados.append(linha)
            else:
                # Cria uma linha para cada transição
                for trans in transicoes:
                    linha = dados_base.copy()
                    linha.update({
                        "M - Status Transition": f"{trans.get('from', '')} → {trans.get('to', '')}",
                        "N - Status Transition.to": trans.get('to', ''),
                        "O - Status Transition.from": trans.get('from', ''),
                        "P - Status Transition.authorDisplayName": trans.get('authorDisplayName', ''),
                        "Q - Status Transition.authorEmail": trans.get('authorEmail', ''),
                        "R - Status Transition.date": self.formatar_data(trans.get('date')),
                        "S - Status Transition.id": trans.get('id', ''),
                    })
                    dados_processados.append(linha)
        
        return dados_processados
    
    def processar_dados(self, dados: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Processa a lista de dicionários para um DataFrame do pandas.
        """
        if not dados:
            logger.warning("Nenhum dado para processar")
            return pd.DataFrame()
        
        df = pd.DataFrame(dados)
        
        # Adicionar colunas de controle
        df['fonte'] = 'jira'
        df['processado_em'] = datetime.now()
        
        logger.info(f"Dados processados - Jira: {len(df)} registros")
        return df


async def obter_dados_jira(projetos_alvo: List[str] = None) -> pd.DataFrame:
    """
    Função principal para obter dados do Jira
    
    Args:
        projetos_alvo (List[str]): Lista de projetos específicos. Se None, busca todos.
        
    Returns:
        pd.DataFrame: DataFrame com os dados processados
    """
    logger.info("Buscando dados do Jira")
    
    try:
        client = JiraAPIClient()
        
        # Buscar projetos
        projetos = client.buscar_projetos_jira(projetos_alvo)
        
        if not projetos:
            logger.warning("Nenhum projeto encontrado")
            return pd.DataFrame()
        
        todas_issues = []
        
        # Busca issues de cada projeto
        for projeto in projetos:
            logger.info(f"Processando projeto: {projeto}")
            
            try:
                issues = client.buscar_issues_jira(projeto)
                
                if issues:
                    # Busca nome do projeto
                    projeto_info_url = f"{client.base_url}/rest/api/3/project/{projeto}"
                    projeto_info = client._get_retry(projeto_info_url)
                    time.sleep(0.2)
                    projeto_nome = projeto
                    if projeto_info.status_code == 200:
                        projeto_nome = projeto_info.json().get('name', projeto)
                    
                    # Processa issues
                    dados_projeto = client.processar_issues(issues, projeto_nome)
                    todas_issues.extend(dados_projeto)
                    
                    logger.info(f"{projeto}: {len(dados_projeto)} linhas processadas")
                else:
                    logger.warning(f"{projeto}: Nenhuma issue encontrada")
                
                # Pausa entre projetos
                if projeto != projetos[-1]:
                    time.sleep(PAUSA_ENTRE_PROJETOS)
                    
            except Exception as e:
                logger.error(f"Erro ao processar projeto {projeto}: {e}")
                if projeto != projetos[-1]:
                    time.sleep(PAUSA_ENTRE_PROJETOS)
                continue
        
        # Processar dados finais
        df_processado = client.processar_dados(todas_issues)
        
        logger.info(f"Dados processados - Jira: {len(df_processado)} registros")
        return df_processado
        
    except Exception as e:
        logger.error(f"Erro ao obter dados do Jira: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


if __name__ == "__main__":
    async def main_test():
        df = await obter_dados_jira()
        print(f"Teste concluído: {len(df)} registros")
        if not df.empty:
            print("Colunas:")
            print(df.columns.tolist())
            print("\nPrimeiros registros:")
            print(df.head().to_markdown(index=False))
    
    asyncio.run(main_test())

