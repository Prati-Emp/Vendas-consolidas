#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

# ========== CONFIGURAÇÕES ==========
JIRA_URL = "https://prati-empreendimentos.atlassian.net"
JIRA_EMAIL = "odair.santos@grupoprati.com"
JIRA_TOKEN = "ATATT3xFfGF01iv65L6Zp7ChRvWnvFf9p582rZkyWGlhGLswg4udjk-q_YoLN3LkGYqaB-_6f_d4_HBJZV_bL46sIKJMnCn1E3oUwIPunoav2pp3So8MX4Ulnac-n3T20XSQj06VOtgpePDJY3ymEqbxI72bsPW25zuchp3aRLW07pYC3yAlG4Y=06CCD10A"

# Se quiser buscar apenas projetos específicos, defina aqui. Deixe vazio [] para buscar todos
PROJETOS_ALVO = ["SPF01"]  # Teste com SPF01. Para buscar todos, use: []

HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}

MAX_RESULTS = 100                 # limite do Jira Cloud
MAX_RETRIES = 4                   # para 429/5xx
BACKOFF_BASE = 1.6                # fator exponencial

# Pausas entre requisições (em segundos) - aumentadas para evitar bloqueios do Jira
PAUSA_ENTRE_PAGINAS = 0.3         # pausa entre páginas de busca de issues
PAUSA_ENTRE_PROJETOS = 2.0        # pausa entre processamento de projetos

# Campos customizados configuráveis
# Ajuste estes IDs conforme os campos do seu Jira
CAMPO_DATA_ORIGINAL_INICIO = "customfield_10339"  # Data original início
CAMPO_DATA_ORIGINAL_FIM = "customfield_10338"     # Data original fim

# Campos necessários para as colunas solicitadas
FIELDS_BASE = [
    "summary",                     # C: Resumo
    "issuetype",                   # A: Tipo de item
    "assignee",                    # D: Responsável
    "reporter",                    # E: Relator
    "priority",                    # F: Prioridade
    "status",                      # G: Status
    "resolution",                  # H: Resolução
    "created",                     # (mantido por compatibilidade)
    "updated",                     # (mantido por compatibilidade)
    "duedate",                     # K: Data limite
    "description",                 # L: Descrição
    "parent",                      # AA: Pai
    "project",                     # Z: Projeto.name
    "customfield_10170",           # Y: Dias para conclusão de Tarefa
    "customfield_10370",           # U: Data Fim corrigida (Adj Finish)
    "customfield_10371",           # T: Data Início corrigida (Adj Start)
]

EXTRA_FIELDS = [
    f for f in (
        CAMPO_DATA_ORIGINAL_INICIO,
        CAMPO_DATA_ORIGINAL_FIM,
    )
    if f and f not in FIELDS_BASE
]

FIELDS = FIELDS_BASE + EXTRA_FIELDS

def _post_retry(url: str, json: Dict[str, Any]):
    """POST com retries exponenciais para 429/5xx."""
    auth = (JIRA_EMAIL, JIRA_TOKEN)
    for i in range(1, MAX_RETRIES + 1):
        r = requests.post(url, headers=HEADERS, json=json, auth=auth, timeout=30)
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(BACKOFF_BASE ** (i - 1))
            continue
        return r
    return r

def _get_retry(url: str):
    """GET com retries exponenciais para 429/5xx e erros de conexão."""
    auth = (JIRA_EMAIL, JIRA_TOKEN)
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
                print(f"    ⚠️ Erro de conexão (tentativa {i}/{MAX_RETRIES}), aguardando {wait_time:.1f}s...")
                time.sleep(wait_time)
                continue
            else:
                # Na última tentativa, levanta a exceção
                raise last_exception
    
    # Se chegou aqui, todas as tentativas falharam
    if last_exception:
        raise last_exception
    raise RuntimeError("Falha ao fazer requisição GET")

def buscar_projetos_jira() -> List[str]:
    """
    Busca todos os projetos ou retorna a lista de projetos alvo.
    """
    if PROJETOS_ALVO:
        print(f"📋 Usando projetos específicos: {', '.join(PROJETOS_ALVO)}")
        return PROJETOS_ALVO
    
    print("🔍 Buscando todos os projetos do Jira...")
    url = f"{JIRA_URL}/rest/api/3/project"
    resp = _get_retry(url)
    
    if resp.status_code != 200:
        print(f"❌ Erro ao buscar projetos: {resp.status_code}")
        raise RuntimeError(f"Erro JIRA {resp.status_code}")
    
    projetos = resp.json()
    project_keys = [p.get('key', '') for p in projetos if p.get('key')]
    print(f"✅ {len(project_keys)} projetos encontrados")
    return project_keys

def buscar_issues_jira(projeto: str) -> List[Dict[str, Any]]:
    """
    Busca TODAS as issues do projeto usando paginação.
    """
    print(f"🔍 Buscando issues do projeto {projeto}...")
    issues: List[Dict[str, Any]] = []
    token = None
    pagina = 0

    jql = f"project = {projeto} ORDER BY key ASC"
    url = f"{JIRA_URL}/rest/api/3/search/jql"

    while True:
        payload = {
            "jql": jql,
            "maxResults": MAX_RESULTS,
            "fields": FIELDS,
        }
        if token:
            payload["nextPageToken"] = token

        resp = _post_retry(url, payload)
        if resp.status_code != 200:
            print(f"❌ Erro JIRA {resp.status_code}: {resp.text[:800]}")
            raise RuntimeError(f"Erro JIRA {resp.status_code}")

        data = resp.json()
        page_items = data.get("issues") or data.get("results") or []
        token = data.get("nextPageToken")
        is_last = bool(data.get("isLast", False))

        if not page_items:
            print("🏁 Página vazia (fim do cursor).")
            break

        issues.extend(page_items)
        pagina += 1
        print(f"✅ Página {pagina}: +{len(page_items)} | acumulado {len(issues)} | isLast={is_last}")

        if is_last or not token:
            break
        
        # Pausa entre páginas para evitar bloqueios
        time.sleep(PAUSA_ENTRE_PAGINAS)

    print(f"✅ Busca concluída: {len(issues)} issues encontradas")
    return issues

def formatar_data_simples(data_str: Optional[str]) -> str:
    """Formata data do Jira para formato brasileiro simples (sem hora)."""
    if not data_str:
        return ''
    try:
        dt = datetime.strptime(data_str[:10], "%Y-%m-%d")
        return dt.strftime("%d/%m/%Y")
    except:
        return data_str

def processar_issues(issues: List[Dict[str, Any]], projeto_nome: str) -> List[Dict[str, Any]]:
    """
    Processa as issues e extrai todas as colunas solicitadas (uma linha por issue).
    """
    print(f"📊 Processando {len(issues)} issues do projeto {projeto_nome}...")
    dados_processados = []
    
    for i, issue in enumerate(issues, start=1):
        if i % 50 == 0:
            print(f"  Processando {i}/{len(issues)}...")
        
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
        start_date = fields.get(CAMPO_DATA_ORIGINAL_INICIO) if CAMPO_DATA_ORIGINAL_INICIO else None
        start_date = start_date or fields.get('customfield_10015')
        data_original_fim_campo = fields.get(CAMPO_DATA_ORIGINAL_FIM) if CAMPO_DATA_ORIGINAL_FIM else None
        duration = fields.get('customfield_10170')    # Duração
        adj_finish = fields.get('customfield_10370')  # Adj Finish
        adj_start = fields.get('customfield_10371')   # Adj Start
        
        # Calcula data original fim (W)
        data_original_fim = ''
        if data_original_fim_campo:
            data_original_fim = formatar_data_simples(data_original_fim_campo)
        elif start_date and duration:
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
            "I - Data original fim": data_original_fim,
            "J - Data original início": formatar_data_simples(start_date),
            "K - Data limite": formatar_data_simples(fields.get('duedate')),
            "L - Descrição": fields.get('description', ''),
            "T - Data Início corrigida": formatar_data_simples(adj_start),
            "U - Data Fim corrigida": formatar_data_simples(adj_finish),
            "Y - Dias para conclusão de Tarefa": duration if duration else '',
            "Z - Projeto.name": project.get('name', projeto_nome),
            "AA - Pai": parent.get('key', ''),
        }
        
        dados_processados.append(dados_base)
    
    return dados_processados

def exportar_excel(dados: List[Dict[str, Any]], nome_arquivo: str = None):
    """
    Exporta os dados para um arquivo Excel.
    """
    try:
        import pandas as pd
    except ImportError:
        print("❌ Erro: pandas não está instalado. Instale com: pip install pandas openpyxl")
        return
    
    if nome_arquivo is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo = f"issues_jira_{timestamp}.xlsx"
    
    if not dados:
        print("⚠️ Nenhum dado para exportar.")
        return
    
    print(f"\n💾 Exportando para {nome_arquivo}...")
    
    # Define a ordem das colunas conforme solicitado
    colunas_ordem = [
        "A - Tipo de item",
        "B - Chave",
        "C - Resumo",
        "D - Responsável",
        "E - Relator",
        "F - Prioridade",
        "G - Status",
        "H - Resolução",
        "I - Data original fim",
        "J - Data original início",
        "K - Data limite",
        "L - Descrição",
        "T - Data Início corrigida",
        "U - Data Fim corrigida",
        "Y - Dias para conclusão de Tarefa",
        "Z - Projeto.name",
        "AA - Pai",
    ]
    
    df = pd.DataFrame(dados)
    
    # Reordena as colunas conforme a ordem especificada
    colunas_existentes = [c for c in colunas_ordem if c in df.columns]
    df = df[colunas_existentes]
    
    df.to_excel(nome_arquivo, index=False, engine='openpyxl')
    
    print(f"✅ Exportação concluída: {len(dados)} linhas salvas em {nome_arquivo}")
    print(f"   Colunas: {len(colunas_existentes)}")

if __name__ == "__main__":
    try:
        # Busca projetos
        projetos = buscar_projetos_jira()
        
        if not projetos:
            print("⚠️ Nenhum projeto encontrado.")
            exit(0)
        
        todas_issues = []
        
        # Busca issues de cada projeto
        for projeto in projetos:
            print(f"\n{'='*60}")
            print(f"🔄 Processando projeto: {projeto}")
            print(f"{'='*60}")
            
            try:
                issues = buscar_issues_jira(projeto)
                
                if issues:
                    # Busca nome do projeto
                    projeto_info = _get_retry(f"{JIRA_URL}/rest/api/3/project/{projeto}")
                    time.sleep(0.2)  # Pequena pausa após buscar info do projeto
                    projeto_nome = projeto
                    if projeto_info.status_code == 200:
                        projeto_nome = projeto_info.json().get('name', projeto)
                    
                    # Processa issues
                    dados_projeto = processar_issues(issues, projeto_nome)
                    todas_issues.extend(dados_projeto)
                    
                    print(f"✅ {projeto}: {len(dados_projeto)} linhas processadas")
                else:
                    print(f"⚠️ {projeto}: Nenhuma issue encontrada")
                
                # Pausa entre projetos para evitar bloqueios
                if projeto != projetos[-1]:  # Não pausa após o último projeto
                    print(f"⏸️  Aguardando {PAUSA_ENTRE_PROJETOS}s antes do próximo projeto...")
                    time.sleep(PAUSA_ENTRE_PROJETOS)
                    
            except Exception as e:
                print(f"❌ Erro ao processar projeto {projeto}: {e}")
                # Pausa mesmo em caso de erro antes de tentar próximo projeto
                if projeto != projetos[-1]:
                    time.sleep(PAUSA_ENTRE_PROJETOS)
                continue
        
        # Exporta tudo para Excel
        if todas_issues:
            exportar_excel(todas_issues)
            print(f"\n✅ Processo concluído! Total: {len(todas_issues)} linhas exportadas")
        else:
            print("\n⚠️ Nenhuma issue foi processada.")
        
    except Exception as e:
        print(f"\n❌ Erro durante a execução: {e}")
        import traceback
        traceback.print_exc()

