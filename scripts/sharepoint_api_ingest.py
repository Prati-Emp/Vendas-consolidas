#!/usr/bin/env python3
"""
Rotina para ingestão de planilhas do SharePoint via API (Client Credentials ou User/Pass).
Ideal para execução em CI/CD (GitHub Actions) onde não há sincronização de pasta local.

Requer:
    pip install Office365-REST-Python-Client pandas openpyxl duckdb

Configuração (.env ou Secrets):
    SHAREPOINT_SITE_URL=https://seu.sharepoint.com/sites/NomeSite
    SHAREPOINT_CLIENT_ID=...       (Opção A: App Principal)
    SHAREPOINT_CLIENT_SECRET=...   (Opção A: App Principal)
    SHAREPOINT_USERNAME=...        (Opção B: Usuário comum - sem MFA)
    SHAREPOINT_PASSWORD=...        (Opção B: Usuário comum - sem MFA)
    SHAREPOINT_FOLDER_REL_URL=/sites/NomeSite/Documentos Compartilhados/PastaAlvo
    MOTHERDUCK_TOKEN=...
"""

import io
import logging
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import duckdb
import pandas as pd
from dotenv import load_dotenv
from office365.runtime.auth.client_credential import ClientCredential
from office365.runtime.auth.user_credential import UserCredential
from office365.sharepoint.client_context import ClientContext
from office365.sharepoint.files.file import File

# Configuração de Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("sharepoint_api")

METADATA_TABLE = "main.__planilhas_sharepoint_log"
DEFAULT_EXTENSIONS = {".xlsx", ".xls", ".xlsm", ".csv"}

@dataclass
class SPFile:
    """Representa um arquivo no SharePoint"""
    name: str
    server_relative_url: str
    time_last_modified: datetime
    length: int
    extension: str

    @property
    def table_name(self) -> str:
        """Gera nome de tabela sanitizado a partir do nome do arquivo"""
        stem = Path(self.name).stem
        normalized = re.sub(r"[^0-9a-zA-Z_]+", "_", stem.strip().lower())
        normalized = normalized.strip("_")
        if not normalized:
            normalized = "planilha_sp"
        if normalized[0].isdigit():
            normalized = f"t_{normalized}"
        return normalized[:60]

def get_sharepoint_context() -> ClientContext:
    """Autentica e retorna o contexto do SharePoint"""
    site_url = os.environ.get("SHAREPOINT_SITE_URL")
    client_id = os.environ.get("SHAREPOINT_CLIENT_ID")
    client_secret = os.environ.get("SHAREPOINT_CLIENT_SECRET")
    username = os.environ.get("SHAREPOINT_USERNAME")
    password = os.environ.get("SHAREPOINT_PASSWORD")

    if not site_url:
        raise ValueError("SHAREPOINT_SITE_URL não definido.")

    if client_id and client_secret:
        logger.info("Autenticando via Client ID / Secret...")
        creds = ClientCredential(client_id, client_secret)
        ctx = ClientContext(site_url).with_credentials(creds)
    elif username and password:
        logger.info("Autenticando via Usuário / Senha...")
        creds = UserCredential(username, password)
        ctx = ClientContext(site_url).with_credentials(creds)
    else:
        raise ValueError("Credenciais do SharePoint não encontradas (CLIENT_ID/SECRET ou USERNAME/PASSWORD).")

    return ctx

def list_files_recursive(ctx: ClientContext, relative_url: str) -> List[SPFile]:
    """Lista arquivos recursivamente na pasta do SharePoint"""
    logger.info(f"Listando arquivos em: {relative_url}")
    
    try:
        # Garante que a URL relativa não comece com barra dupla se já tiver no site
        folder = ctx.web.get_folder_by_server_relative_url(relative_url)
        
        # Carrega arquivos e subpastas
        files = folder.files
        folders = folder.folders
        ctx.load(files)
        ctx.load(folders)
        ctx.execute_query()
        
        results = []
        
        # Processa arquivos
        for f in files:
            name = f.name
            ext = Path(name).suffix.lower()
            if name.startswith("~$") or ext not in DEFAULT_EXTENSIONS:
                continue
                
            # Converter timestamp do SharePoint para datetime
            # Formato comum: 2023-10-25T14:30:00Z
            modified_str = str(f.time_last_modified)
            try:
                # Tenta parse genérico ISO
                modified_dt = datetime.fromisoformat(modified_str.replace("Z", "+00:00"))
            except ValueError:
                modified_dt = datetime.now(timezone.utc) # Fallback

            results.append(SPFile(
                name=name,
                server_relative_url=f.server_relative_url,
                time_last_modified=modified_dt,
                length=int(f.length),
                extension=ext
            ))
            
        # Processa subpastas (recursão)
        for subfolder in folders:
            if subfolder.name in ["Forms", "_t", "_w"]: # Pastas de sistema ocultas
                continue
            results.extend(list_files_recursive(ctx, subfolder.server_relative_url))
            
        return results
        
    except Exception as e:
        logger.error(f"Erro ao listar pasta {relative_url}: {e}")
        raise

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
            file_url TEXT PRIMARY KEY,
            table_name TEXT,
            file_modified TIMESTAMP,
            file_size BIGINT,
            row_count BIGINT,
            last_ingested TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

def get_stored_metadata(conn: duckdb.DuckDBPyConnection) -> Dict[str, datetime]:
    ensure_metadata_table(conn)
    rows = conn.execute(f"SELECT file_url, file_modified FROM {METADATA_TABLE}").fetchall()
    return {row[0]: row[1] for row in rows}

def download_and_read(ctx: ClientContext, sp_file: SPFile) -> pd.DataFrame:
    """Baixa arquivo para memória e lê com Pandas"""
    logger.info(f"Baixando: {sp_file.name} ({sp_file.length / 1024:.1f} KB)")
    
    response = File.open_binary(ctx, sp_file.server_relative_url)
    
    # Grava em buffer de bytes
    file_content = io.BytesIO(response.content)
    
    if sp_file.extension in [".xlsx", ".xls", ".xlsm"]:
        return pd.read_excel(file_content)
    elif sp_file.extension == ".csv":
        # Tenta detectar separador
        return pd.read_csv(file_content, sep=None, engine='python')
    
    return pd.DataFrame()

def ingest_file(conn: duckdb.DuckDBPyConnection, ctx: ClientContext, sp_file: SPFile) -> int:
    df = download_and_read(ctx, sp_file)
    
    if df.empty:
        logger.warning(f"Arquivo vazio ou inválido: {sp_file.name}")
        return 0
        
    # Normalização básica de colunas
    df.columns = [
        re.sub(r"[^0-9a-zA-Z_]+", "_", str(c).strip().lower()).strip("_") 
        for c in df.columns
    ]
    
    # Adiciona colunas de metadados
    df["_source_file"] = sp_file.name
    df["_ingested_at"] = datetime.now()
    
    # Upload para MotherDuck
    conn.register("df_temp", df)
    conn.execute(f"CREATE OR REPLACE TABLE {sp_file.table_name} AS SELECT * FROM df_temp")
    conn.unregister("df_temp")
    
    count = len(df)
    
    # Atualiza log
    conn.execute(f"""
        INSERT OR REPLACE INTO {METADATA_TABLE} 
        (file_url, table_name, file_modified, file_size, row_count, last_ingested)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (sp_file.server_relative_url, sp_file.table_name, sp_file.time_last_modified, sp_file.length, count))
    
    return count

def main():
    load_dotenv()
    
    # Parâmetros
    folder_rel_url = os.environ.get("SHAREPOINT_FOLDER_REL_URL")
    if not folder_rel_url:
        # Tenta inferir da URL completa se fornecida, ou erro
        logger.error("SHAREPOINT_FOLDER_REL_URL não definido (ex: /sites/NomeSite/Shared Documents/Pasta)")
        sys.exit(1)
        
    force_update = "--force" in sys.argv
    
    try:
        # Conexões
        ctx = get_sharepoint_context()
        conn = connect_motherduck()
        
        # Listar arquivos
        files = list_files_recursive(ctx, folder_rel_url)
        if not files:
            logger.warning("Nenhum arquivo encontrado na pasta especificada.")
            return

        # Verificar metadados (incremental)
        stored_meta = get_stored_metadata(conn)
        
        processed = 0
        errors = 0
        
        for sp_file in files:
            stored_mod = stored_meta.get(sp_file.server_relative_url)
            
            # Lógica incremental: se modificado no SP > modificado no Banco
            # SP retorna com timezone, stored pode não ter. Ajustar comparação.
            should_process = force_update
            
            if not should_process:
                if not stored_mod:
                    should_process = True
                else:
                    # Converter stored para UTC se naive
                    if stored_mod.tzinfo is None:
                        stored_mod = stored_mod.replace(tzinfo=timezone.utc)
                    if sp_file.time_last_modified > stored_mod:
                        should_process = True
            
            if should_process:
                try:
                    logger.info(f"Processando atualização: {sp_file.name}")
                    rows = ingest_file(conn, ctx, sp_file)
                    logger.info(f"Sucesso: {sp_file.table_name} ({rows} linhas)")
                    processed += 1
                except Exception as e:
                    logger.error(f"Falha ao processar {sp_file.name}: {e}")
                    errors += 1
            else:
                logger.info(f"Pulo (sem alteração): {sp_file.name}")
                
        logger.info(f"Resumo: {processed} processados, {len(files) - processed - errors} pulados, {errors} erros.")
        
        if errors > 0:
            sys.exit(1)
            
    except Exception as e:
        logger.critical(f"Erro fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()


