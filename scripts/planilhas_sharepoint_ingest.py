#!/usr/bin/env python3
"""
Rotina para ler todas as planilhas da pasta sincronizada do SharePoint/OneDrive
e criar/atualizar tabelas correspondentes no MotherDuck (database "planilhas").

Uso:
    python scripts/planilhas_sharepoint_ingest.py \
        --root "C:/Users/.../SharePoint/Pasta" \
        --force

Ou configure a variável de ambiente SHAREPOINT_PLANILHAS_DIR e rode sem flags.
"""

from __future__ import annotations

import argparse
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

import duckdb
import pandas as pd
from dotenv import load_dotenv


logger = logging.getLogger("planilhas_sharepoint")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

DEFAULT_EXTENSIONS = {".xlsx", ".xls", ".xlsm", ".csv"}
METADATA_TABLE = "main.__planilhas_ingest_log"


@dataclass(frozen=True)
class PlanilhaFile:
    """Representa um arquivo de planilha pronto para ingestão."""

    path: Path
    table_name: str
    modified: datetime
    size_bytes: int
    extension: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sincroniza planilhas da pasta do SharePoint com o MotherDuck."
    )
    parser.add_argument(
        "--root",
        help="Pasta base sincronizada com o SharePoint (default: SHAREPOINT_PLANILHAS_DIR).",
    )
    parser.add_argument(
        "--database",
        default=os.environ.get("PLANILHAS_DATABASE", "planilhas"),
        help="Nome do database MotherDuck (default: planilhas).",
    )
    parser.add_argument(
        "--extensions",
        help="Lista de extensões separadas por vírgula (ex: .xlsx,.csv).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reprocessa todos os arquivos mesmo sem alteração.",
    )
    parser.add_argument(
        "--include-subdirs",
        action="store_true",
        help="Percorre subpastas (default: apenas a pasta raiz).",
    )
    parser.add_argument(
        "--csv-separator",
        default=os.environ.get("PLANILHAS_CSV_SEPARATOR", ","),
        help="Separador padrão para CSV (default: ,).",
    )
    return parser.parse_args()


def sanitize_table_name(name: str) -> str:
    normalized = re.sub(r"[^0-9a-zA-Z_]+", "_", name.strip().lower())
    normalized = normalized.strip("_")
    if not normalized:
        normalized = "planilha"
    if normalized[0].isdigit():
        normalized = f"t_{normalized}"
    return normalized[:60]


def build_planilha_list(
    root: Path, extensions: Set[str], include_subdirs: bool
) -> List[PlanilhaFile]:
    if not root.exists():
        raise FileNotFoundError(f"Pasta não encontrada: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Caminho não é diretório: {root}")

    logger.info("Procurando arquivos em %s", root)
    candidates: Iterable[Path]
    if include_subdirs:
        candidates = root.rglob("*")
    else:
        candidates = root.glob("*")

    files: List[Path] = [
        path
        for path in candidates
        if path.is_file()
        and not path.name.startswith("~$")
        and path.suffix.lower() in extensions
    ]

    files.sort()
    if not files:
        logger.warning("Nenhuma planilha encontrada nas extensões %s", extensions)
        return []

    used_names: Set[str] = set()
    planilhas: List[PlanilhaFile] = []
    for file_path in files:
        stem = file_path.stem
        base_name = sanitize_table_name(stem)
        table_name = base_name
        idx = 2
        while table_name in used_names:
            table_name = f"{base_name}_{idx}"
            idx += 1
        used_names.add(table_name)

        stat = file_path.stat()
        modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
        planilhas.append(
            PlanilhaFile(
                path=file_path,
                table_name=table_name,
                modified=modified,
                size_bytes=stat.st_size,
                extension=file_path.suffix.lower(),
            )
        )
    logger.info("Encontrados %d arquivos elegíveis", len(planilhas))
    return planilhas


def connect_motherduck(database: str):
    token = os.environ.get("MOTHERDUCK_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Variável MOTHERDUCK_TOKEN não encontrada.")

    duckdb.sql("INSTALL motherduck")
    duckdb.sql("LOAD motherduck")
    duckdb.sql(f"SET motherduck_token='{token}'")
    return duckdb.connect(f"md:{database}")


def ensure_metadata_table(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {METADATA_TABLE} (
            file_path TEXT PRIMARY KEY,
            file_name TEXT,
            table_name TEXT,
            file_modified TIMESTAMP,
            file_size BIGINT,
            row_count BIGINT,
            last_ingested TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def load_metadata(conn: duckdb.DuckDBPyConnection) -> Dict[str, datetime]:
    ensure_metadata_table(conn)
    rows = conn.execute(
        f"SELECT file_path, file_modified FROM {METADATA_TABLE}"
    ).fetchall()
    return {row[0]: row[1] for row in rows}


def read_planilha(planilha: PlanilhaFile, csv_separator: str) -> pd.DataFrame:
    if planilha.extension in {".xlsx", ".xls", ".xlsm"}:
        return pd.read_excel(planilha.path, engine="openpyxl")
    if planilha.extension == ".csv":
        return pd.read_csv(planilha.path, sep=csv_separator)
    raise ValueError(f"Extensão não suportada: {planilha.extension}")


def upsert_table(
    conn: duckdb.DuckDBPyConnection, planilha: PlanilhaFile, df: pd.DataFrame
) -> int:
    temp_view = f"df_{planilha.table_name}"
    conn.register(temp_view, df)
    conn.execute(
        f'CREATE OR REPLACE TABLE main."{planilha.table_name}" AS SELECT * FROM "{temp_view}"'
    )
    conn.unregister(temp_view)
    return len(df)


def persist_metadata(
    conn: duckdb.DuckDBPyConnection, planilha: PlanilhaFile, row_count: int
) -> None:
    conn.execute(
        f"""
        INSERT OR REPLACE INTO {METADATA_TABLE}
        (file_path, file_name, table_name, file_modified, file_size, row_count, last_ingested)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (
            planilha.path.as_posix(),
            planilha.path.name,
            planilha.table_name,
            planilha.modified,
            planilha.size_bytes,
            row_count,
        ),
    )


def process_planilhas(
    planilhas: List[PlanilhaFile],
    conn: duckdb.DuckDBPyConnection,
    metadata: Dict[str, datetime],
    force: bool,
    csv_separator: str,
) -> Tuple[List[Tuple[PlanilhaFile, int]], List[PlanilhaFile], List[Tuple[PlanilhaFile, str]]]:
    ingested: List[Tuple[PlanilhaFile, int]] = []
    skipped: List[PlanilhaFile] = []
    failed: List[Tuple[PlanilhaFile, str]] = []

    for planilha in planilhas:
        stored_modified = metadata.get(planilha.path.as_posix())
        if not force and stored_modified and stored_modified >= planilha.modified:
            skipped.append(planilha)
            continue

        try:
            df = read_planilha(planilha, csv_separator)
            row_count = upsert_table(conn, planilha, df)
            persist_metadata(conn, planilha, row_count)
            metadata[planilha.path.as_posix()] = planilha.modified
            ingested.append((planilha, row_count))
            logger.info(
                "Atualizada tabela %s com %d linhas (arquivo: %s)",
                planilha.table_name,
                row_count,
                planilha.path.name,
            )
        except Exception as exc:
            logger.exception("Falha ao processar %s", planilha.path)
            failed.append((planilha, str(exc)))

    return ingested, skipped, failed


def main():
    load_dotenv()
    args = parse_args()

    root_path = args.root or os.environ.get("SHAREPOINT_PLANILHAS_DIR")
    if not root_path:
        raise RuntimeError(
            "Informe a pasta com --root ou defina SHAREPOINT_PLANILHAS_DIR no .env."
        )

    extensions = (
        {ext.strip().lower() if ext.strip().startswith(".") else f".{ext.strip().lower()}"
         for ext in args.extensions.split(",")}
        if args.extensions
        else DEFAULT_EXTENSIONS
    )

    planilhas = build_planilha_list(Path(root_path).expanduser(), extensions, args.include_subdirs)
    if not planilhas:
        logger.info("Nenhuma planilha para processar. Encerrando.")
        return 0

    conn = connect_motherduck(args.database)
    metadata = load_metadata(conn)
    ingested, skipped, failed = process_planilhas(
        planilhas,
        conn,
        metadata,
        force=args.force,
        csv_separator=args.csv_separator,
    )
    conn.close()

    logger.info("Resumo: %d atualizadas, %d sem alteração, %d com erro", len(ingested), len(skipped), len(failed))
    if failed:
        for planilha, error in failed:
            logger.error("Arquivo %s falhou: %s", planilha.path, error)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())










