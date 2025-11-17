"""Helpers para ler listas do Google Sheets publicadas como CSV."""

from __future__ import annotations

import logging
import os
from typing import List, Optional
from urllib.parse import urlparse, parse_qs

import pandas as pd

logger = logging.getLogger(__name__)


def _normalize_sheet_url(url: str) -> str:
    """
    Converte URLs “normais” do Google Sheets em links de exportação CSV.

    Exemplos aceitos:
        https://docs.google.com/spreadsheets/d/<ID>/edit#gid=0
        https://docs.google.com/spreadsheets/d/<ID>/export?format=csv&gid=0
    """
    if not url:
        raise ValueError("URL do Google Sheets vazia")

    url = url.strip()
    if "/export" in url and "format=csv" in url:
        return url

    parsed = urlparse(url)
    path_parts = parsed.path.split("/")
    try:
        doc_index = path_parts.index("d")
        doc_id = path_parts[doc_index + 1]
    except (ValueError, IndexError) as exc:
        raise ValueError("URL do Google Sheets inválida") from exc

    query = parse_qs(parsed.fragment.replace("gid=", "gid=")) if parsed.fragment else {}
    gid = query.get("gid", ["0"])[0]

    export_url = f"https://docs.google.com/spreadsheets/d/{doc_id}/export?format=csv&gid={gid}"
    return export_url


def load_project_keys_from_sheet(
    url_env_var: str = "JIRA_PROJECTS_SHEET_URL",
) -> Optional[List[str]]:
    """
    Carrega chaves de projeto do Google Sheets.

    Espera uma coluna chamada “Projeto.key”, “Project.key” ou similar.
    """
    sheet_url = os.environ.get(url_env_var)
    if not sheet_url:
        logger.info("Variável %s não configurada; usando todos os projetos", url_env_var)
        return None

    try:
        csv_url = _normalize_sheet_url(sheet_url)
        df = pd.read_csv(csv_url)
    except Exception as exc:
        logger.warning("Não foi possível ler o Google Sheets: %s", exc)
        return None

    if df.empty:
        logger.warning("Planilha de projetos está vazia")
        return []

    coluna_alvo = None
    candidatos = ["projeto.key", "project.key", "projeto", "project"]
    colunas_norm = {col.lower().strip(): col for col in df.columns}

    for candidato in candidatos:
        if candidato in colunas_norm:
            coluna_alvo = colunas_norm[candidato]
            break

    if coluna_alvo is None:
        coluna_alvo = df.columns[0]
        logger.info(
            "Coluna 'Projeto.key' não encontrada; usando primeira coluna: %s",
            coluna_alvo,
        )

    chaves = (
        df[coluna_alvo]
        .astype(str)
        .str.strip()
        .str.upper()
        .replace("", pd.NA)
        .dropna()
        .drop_duplicates()
        .tolist()
    )

    logger.info("Projetos carregados do Sheets: %d entradas únicas", len(chaves))
    return chaves

