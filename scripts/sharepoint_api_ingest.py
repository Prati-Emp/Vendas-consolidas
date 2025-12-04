#!/usr/bin/env python3
"""
Rotina para ingestão de planilhas do SharePoint via Microsoft Graph API.
Substitui a versão anterior que usava CSOM/REST legado.

Requer:
    pip install requests pandas openpyxl duckdb python-dotenv

Configuração (.env ou Secrets):
    SHAREPOINT_TENANT_ID=...
    SHAREPOINT_CLIENT_ID=...
    SHAREPOINT_CLIENT_SECRET=...
    SHAREPOINT_SITE_HOSTNAME=pratiemp318.sharepoint.com
    SHAREPOINT_SITE_PATH=/sites/Materialatualizaodiria
    SHAREPOINT_FOLDER_PATH=arquivosatualizacao
    MOTHERDUCK_TOKEN=...
"""

import io
import logging
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

import duckdb
import pandas as pd
import requests
from dotenv import load_dotenv

# Configuração de Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("sharepoint_graph_ingest")

METADATA_TABLE = "main.__planilhas_sharepoint_log"
DEFAULT_EXTENSIONS = {".xlsx", ".xls", ".xlsm", ".csv"}

@dataclass
class GraphFile:
    id: str
    name: str
    size: int
    last_modified: datetime
    download_url: str
    extension: str

    @property
    def table_name(self) -> str:
        """Gera nome de tabela sanitizado a partir do nome do arquivo"""
        stem = os.path.splitext(self.name)[0]
        normalized = re.sub(r"[^0-9a-zA-Z_]+", "_", stem.strip().lower())
        normalized = normalized.strip("_")
        if not normalized:
            normalized = "planilha_sp"
        if normalized[0].isdigit():
            normalized = f"t_{normalized}"
        return normalized[:60]

class GraphAPIClient:
    def __init__(self):
        self.tenant_id = os.environ.get("SHAREPOINT_TENANT_ID", "f6e5f47f-eb3e-4de3-a4e3-648d931a2eb9")
        self.client_id = os.environ.get("SHAREPOINT_CLIENT_ID")
        self.client_secret = os.environ.get("SHAREPOINT_CLIENT_SECRET")
        
        if not self.client_id or not self.client_secret:
            raise ValueError("Credenciais (CLIENT_ID/SECRET) não encontradas.")
            
        self.token = None
        self.headers = {}
        self._authenticate()
        
    def _authenticate(self):
        logger.info("Autenticando na Microsoft Graph API...")
        url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': 'https://graph.microsoft.com/.default'
        }
        resp = requests.post(url, data=data)
        resp.raise_for_status()
        self.token = resp.json().get('access_token')
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Accept': 'application/json'
        }
        
    def get_site_id(self, hostname: str, site_path: str) -> str:
        """Busca ID do site dado hostname e path"""
        url = f"https://graph.microsoft.com/v1.0/sites/{hostname}:{site_path}"
        resp = requests.get(url, headers=self.headers)
        if resp.status_code == 404:
            # Tenta busca
            logger.info("Site não encontrado por path direto, tentando busca...")
            query = site_path.split('/')[-1]
            url = f"https://graph.microsoft.com/v1.0/sites?search={query}"
            resp = requests.get(url, headers=self.headers)
            resp.raise_for_status()
            data = resp.json()
            if not data.get('value'):
                raise ValueError(f"Site não encontrado: {site_path}")
            return data['value'][0]['id']
            
        resp.raise_for_status()
        return resp.json()['id']

    def get_drive_id(self, site_id: str, drive_name: str = "Documentos") -> str:
        """Busca ID da biblioteca de documentos"""
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
        resp = requests.get(url, headers=self.headers)
        resp.raise_for_status()
        drives = resp.json().get('value', [])
        
        for d in drives:
            # Tenta nomes comuns
            if d['name'] == drive_name or d['name'] == "Documents" or d['name'] == "Shared Documents":
                return d['id']
        
        if drives:
            logger.warning(f"Drive '{drive_name}' não achado exato. Usando o primeiro: {drives[0]['name']}")
            return drives[0]['id']
            
        raise ValueError(f"Nenhum drive encontrado no site {site_id}")

    def list_files(self, drive_id: str, folder_path: str) -> List[GraphFile]:
        """Lista arquivos em uma pasta específica do drive"""
        # Endpoint para listar filhos de um caminho: /drives/{id}/root:/{path}:/children
        if folder_path and folder_path != "/":
            clean_path = folder_path.strip("/")
            url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{clean_path}:/children"
        else:
            url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root/children"
            
        logger.info(f"Listando arquivos: {url}")
        resp = requests.get(url, headers=self.headers)
        
        # Se 404, tenta listar raiz para debug
        if resp.status_code == 404:
             logger.error(f"Pasta não encontrada: {folder_path}")
             return []
             
        resp.raise_for_status()
        items = resp.json().get('value', [])
        
        files = []
        for item in items:
            if 'file' not in item: # Pula pastas
                continue
                
            name = item['name']
            ext = os.path.splitext(name)[1].lower()
            if name.startswith("~$") or ext not in DEFAULT_EXTENSIONS:
                continue
                
            last_mod_str = item['lastModifiedDateTime'] # ISO 8601
            last_mod = datetime.fromisoformat(last_mod_str.replace("Z", "+00:00"))
            
            files.append(GraphFile(
                id=item['id'],
                name=name,
                size=item['size'],
                last_modified=last_mod,
                download_url=item['@microsoft.graph.downloadUrl'],
                extension=ext
            ))
            
        return files

    def download_file(self, file_obj: GraphFile) -> pd.DataFrame:
        """Baixa arquivo e converte para DataFrame"""
        logger.info(f"Baixando {file_obj.name}...")
        resp = requests.get(file_obj.download_url)
        resp.raise_for_status()
        
        content = io.BytesIO(resp.content)
        
        if file_obj.extension in [".xlsx", ".xls", ".xlsm"]:
            return pd.read_excel(content)
        elif file_obj.extension == ".csv":
            return pd.read_csv(content)
            
        return pd.DataFrame()

def connect_motherduck(database: str = "planilhas"):
    token = os.environ.get("MOTHERDUCK_TOKEN", "").strip()
    if not token:
        raise ValueError("MOTHERDUCK_TOKEN não definido.")
    
    duckdb.sql("INSTALL motherduck")
    duckdb.sql("LOAD motherduck")
    duckdb.sql(f"SET motherduck_token='{token}'")
    return duckdb.connect(f"md:{database}")

def ensure_metadata_table(conn: duckdb.DuckDBPyConnection):
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {METADATA_TABLE} (
            file_id TEXT PRIMARY KEY,
            file_name TEXT,
            table_name TEXT,
            file_modified TIMESTAMP,
            file_size BIGINT,
            row_count BIGINT,
            last_ingested TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

def get_stored_metadata(conn: duckdb.DuckDBPyConnection) -> Dict[str, datetime]:
    ensure_metadata_table(conn)
    try:
        rows = conn.execute(f"SELECT file_id, file_modified FROM {METADATA_TABLE}").fetchall()
        return {row[0]: row[1] for row in rows}
    except Exception:
        return {}

def ingest_file(conn: duckdb.DuckDBPyConnection, client: GraphAPIClient, file_obj: GraphFile) -> int:
    df = client.download_file(file_obj)
    
    if df.empty:
        logger.warning(f"Arquivo vazio: {file_obj.name}")
        return 0
        
    # Normalização de colunas
    df.columns = [
        re.sub(r"[^0-9a-zA-Z_]+", "_", str(c).strip().lower()).strip("_") 
        for c in df.columns
    ]
    
    df["_source_file"] = file_obj.name
    df["_ingested_at"] = datetime.now()
    
    # Upload MotherDuck
    conn.register("df_temp", df)
    conn.execute(f"CREATE OR REPLACE TABLE {file_obj.table_name} AS SELECT * FROM df_temp")
    conn.unregister("df_temp")
    
    count = len(df)
    
    # Log
    conn.execute(f"""
        INSERT OR REPLACE INTO {METADATA_TABLE} 
        (file_id, file_name, table_name, file_modified, file_size, row_count, last_ingested)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (file_obj.id, file_obj.name, file_obj.table_name, file_obj.last_modified, file_obj.size, count))
    
    return count

def main():
    load_dotenv()
    
    # Configuração via ENV ou Hardcoded (fallback)
    hostname = os.environ.get("SHAREPOINT_SITE_HOSTNAME", "pratiemp318.sharepoint.com")
    site_path = os.environ.get("SHAREPOINT_SITE_PATH", "/sites/Materialatualizaodiria")
    folder_path = os.environ.get("SHAREPOINT_FOLDER_PATH", "arquivosatualizacao")
    
    try:
        # 1. Conectar Graph API
        client = GraphAPIClient()
        site_id = client.get_site_id(hostname, site_path)
        drive_id = client.get_drive_id(site_id)
        files = client.list_files(drive_id, folder_path)
        
        if not files:
            logger.warning("Nenhum arquivo encontrado.")
            return

        # 2. Conectar MotherDuck
        conn = connect_motherduck()
        stored_meta = get_stored_metadata(conn)
        
        processed = 0
        errors = 0
        force = "--force" in sys.argv
        
        for f in files:
            stored_mod = stored_meta.get(f.id)
            
            # Lógica incremental
            should_process = force
            if not should_process:
                if not stored_mod:
                    should_process = True
                else:
                    if stored_mod.tzinfo is None:
                        stored_mod = stored_mod.replace(tzinfo=timezone.utc)
                    if f.last_modified > stored_mod:
                        should_process = True
            
            if should_process:
                try:
                    logger.info(f"Processando: {f.name}")
                    rows = ingest_file(conn, client, f)
                    logger.info(f"✅ Sucesso: {f.table_name} ({rows} linhas)")
                    processed += 1
                except Exception as e:
                    logger.error(f"❌ Falha em {f.name}: {e}")
                    errors += 1
            else:
                logger.info(f"⏭️ Pulo (sem alteração): {f.name}")
                
        logger.info(f"RESUMO: {processed} processados, {len(files)-processed-errors} pulados, {errors} erros.")
        if errors > 0:
            sys.exit(1)
            
    except Exception as e:
        logger.critical(f"Erro fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
