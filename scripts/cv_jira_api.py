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
from io import StringIO
import requests
from datetime import datetime
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
PAUSA_ENTRE_PAGINAS = 0.3
PAUSA_ENTRE_PROJETOS = 2.0

DEFAULT_SHEET_CSV_URL = (
    os.environ.get(
        "JIRA_PROJECTS_SHEET_URL",
        "https://docs.google.com/spreadsheets/d/1i927uMKgiX-rDvKVQKb-JP9NAA4KcjWHzGcZG61y35s/export?format=csv&gid=0",
    )
)

# Campos necessários (fluxo simplificado conforme exportação validada)
FIELDS = [
    "summary",                     # C: Resumo
    "issuetype",                   # A: Tipo de item
    "assignee",                    # D: Responsável
    "reporter",                    # E: Relator
    "priority",                    # F: Prioridade
    "status",                      # G: Status
    "resolution",                  # H: Resolução
    "duedate",                     # K: Data limite
    "description",                 # L: Descrição
    "parent",                      # AA: Pai
    "project",                     # Z: Projeto.name
    "customfield_10339",           # Data original início
    "customfield_10338",           # Data original fim
    "customfield_10371",           # Data Início corrigida (Adj Start)
    "customfield_10370",           # Data Fim corrigida (Adj Finish)
    "customfield_10015",           # Start date
    "customfield_10170",           # Dias para conclusão de Tarefa
]

HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}


def _format_duration(value: Any) -> str:
    """Normaliza duração para string."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return ""
    if isinstance(value, (int, float)):
        return str(int(value))
    return str(value)


def obter_lista_projetos_planilha(sheet_url: str = DEFAULT_SHEET_CSV_URL) -> List[str]:
    """
    Busca a lista de projetos a partir da planilha Google Sheets (CSV export).
    Espera uma coluna chamada 'Projeto.key' (case insensitive).
    """
    if not sheet_url:
        return []

    try:
        resp = requests.get(sheet_url, timeout=30)
        resp.raise_for_status()

        csv_buffer = StringIO(resp.text)
        df = pd.read_csv(csv_buffer)

        colunas_normalizadas = {col.strip().lower(): col for col in df.columns}
        chave_coluna = None
        for candidato in ("projeto.key", "projeto_key", "project.key", "project_key"):
            if candidato in colunas_normalizadas:
                chave_coluna = colunas_normalizadas[candidato]
                break

        if not chave_coluna:
            logger.warning("Coluna 'Projeto.key' não encontrada na planilha.")
            return []

        projetos = (
            df[chave_coluna]
            .dropna()
            .astype(str)
            .str.strip()
            .replace("", pd.NA)
            .dropna()
            .unique()
            .tolist()
        )

        logger.info(f"Planilha retornou {len(projetos)} projetos do Jira.")
        return projetos

    except Exception as exc:
        logger.warning(f"Falha ao carregar planilha de projetos Jira: {exc}")
        return []


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
    
    def buscar_projetos_jira(self, projetos_alvo: Optional[List[str]] = None) -> List[str]:
        """
        Determina quais projetos serão processados.
        Prioridade:
            1. Lista recebida via argumento
            2. Lista da planilha (DEFAULT_SHEET_CSV_URL)
            3. Todos os projetos da instância Jira (fallback)
        """
        if projetos_alvo:
            logger.info(f"Usando projetos fornecidos: {', '.join(projetos_alvo)}")
            return projetos_alvo

        projetos_planilha = obter_lista_projetos_planilha()
        if projetos_planilha:
            return projetos_planilha

        logger.info("Planilha indisponível. Buscando todos os projetos do Jira (fallback).")
        url = f"{self.base_url}/rest/api/3/project"
        resp = self._get_retry(url)

        if resp.status_code != 200:
            logger.error(f"Erro ao buscar projetos: {resp.status_code}")
            raise RuntimeError(f"Erro JIRA {resp.status_code}")

        projetos = resp.json()
        project_keys = [p.get('key', '') for p in projetos if p.get('key')]
        logger.info(f"{len(project_keys)} projetos encontrados (fallback).")
        return project_keys
    
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
    
    @staticmethod
    def formatar_data_simples(data_str: Optional[str]) -> str:
        """Formata data do Jira para formato brasileiro simples (sem hora)."""
        if not data_str:
            return ''
        try:
            dt = datetime.strptime(str(data_str)[:10], "%Y-%m-%d")
            return dt.strftime("%d/%m/%Y")
        except Exception:
            return str(data_str) if data_str is not None else ''
    
    def processar_issues(self, issues: List[Dict[str, Any]], projeto_nome: str) -> List[Dict[str, Any]]:
        """
        Processa issues e retorna apenas as colunas necessárias (uma linha por issue).
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
            
            data_original_inicio = fields.get('customfield_10339')
            data_original_fim = fields.get('customfield_10338')
            adj_start = fields.get('customfield_10371')
            adj_finish = fields.get('customfield_10370')
            start_date = fields.get('customfield_10015')
            duration = fields.get('customfield_10170')

            dados_processados.append({
                "A - Tipo de item": issuetype.get('name', ''),
                "B - Chave": key,
                "C - Resumo": fields.get('summary', ''),
                "D - Responsável": assignee.get('displayName', ''),
                "E - Relator": reporter.get('displayName', ''),
                "F - Prioridade": priority.get('name', ''),
                "G - Status": status.get('name', ''),
                "H - Resolução": resolution.get('name', ''),
                "I - Data original fim": self.formatar_data_simples(data_original_fim),
                "J - Data original início": self.formatar_data_simples(data_original_inicio),
                "K - Data limite": self.formatar_data_simples(fields.get('duedate')),
                "L - Descrição": fields.get('description', ''),
                "T - Data Início corrigida": self.formatar_data_simples(adj_start),
                "U - Data Fim corrigida": self.formatar_data_simples(adj_finish),
                "X - Start date": self.formatar_data_simples(start_date),
                "Y - Dias para conclusão de Tarefa": _format_duration(duration),
                "Z - Projeto.name": project.get('name', projeto_nome),
                "AA - Pai": parent.get('key', ''),
            })
        
        return dados_processados
    
    def processar_dados(self, dados: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Processa a lista de dicionários para um DataFrame do pandas.
        """
        if not dados:
            logger.warning("Nenhum dado para processar")
            return pd.DataFrame()
        
        df = pd.DataFrame(dados)
        colunas_descartar = [
            "M - Status Transition",
            "N - Status Transition.to",
            "O - Status Transition.from",
            "P - Status Transition.authorDisplayName",
            "Q - Status Transition.authorEmail",
            "R - Status Transition.date",
            "S - Status Transition.id",
        ]
        df = df.drop(columns=colunas_descartar, errors="ignore")
        
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
        projetos = list(dict.fromkeys(projetos))  # remove duplicados preservando ordem

        if not projetos:
            logger.warning("Nenhum projeto encontrado")
            return pd.DataFrame()

        logger.info(f"Projetos selecionados ({len(projetos)}): {', '.join(projetos)}")
        
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




