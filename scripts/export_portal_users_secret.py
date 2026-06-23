#!/usr/bin/env python3
"""Gera o valor de PORTAL_USERS_JSON para colar nos Secrets do Streamlit Cloud."""

import json
from pathlib import Path

USERS_FILE = Path(__file__).resolve().parent.parent / "dashboard" / "portal_users.json"
OUTPUT_FILE = Path(__file__).resolve().parent.parent / "dashboard" / "PORTAL_USERS_JSON_PARA_STREAMLIT.toml"


def main() -> None:
    if not USERS_FILE.exists():
        raise SystemExit(
            f"Arquivo nao encontrado: {USERS_FILE}\n"
            "Copie dashboard/portal_users.example.json para portal_users.json primeiro."
        )

    users = json.loads(USERS_FILE.read_text(encoding="utf-8"))
    compact = json.dumps(users, ensure_ascii=False, separators=(",", ":"))
    # Aspas simples por fora: JSON interno usa aspas duplas sem conflito com TOML
    escaped = compact.replace("'", "''")
    content = (
        "# Cole este bloco em Streamlit Cloud -> Settings -> Secrets\n"
        "# Mantenha os outros secrets do app (ex.: MOTHERDUCK_TOKEN)\n"
        f"PORTAL_USERS_JSON = '{escaped}'\n"
    )
    OUTPUT_FILE.write_text(content, encoding="utf-8")

    print(f"Arquivo gerado: {OUTPUT_FILE}")
    print(f"Usuarios: {len(users)} | Tamanho: {len(compact)} caracteres")
    print("\nCopie TODO o arquivo e cole nos Secrets do app.")


if __name__ == "__main__":
    main()
