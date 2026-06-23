#!/usr/bin/env python3
"""Gera o valor de PORTAL_USERS_JSON para colar nos Secrets do Streamlit Cloud."""

import json
from pathlib import Path

USERS_FILE = Path(__file__).resolve().parent.parent / "dashboard" / "portal_users.json"


def main() -> None:
    if not USERS_FILE.exists():
        raise SystemExit(
            f"Arquivo nao encontrado: {USERS_FILE}\n"
            "Copie dashboard/portal_users.example.json para portal_users.json primeiro."
        )

    users = json.loads(USERS_FILE.read_text(encoding="utf-8"))
    compact = json.dumps(users, ensure_ascii=False, separators=(",", ":"))

    print("Adicione no Streamlit Cloud (Settings -> Secrets):\n")
    print(f'PORTAL_USERS_JSON = """{compact}"""')
    print(f"\n({len(users)} usuarios, {len(compact)} caracteres)")


if __name__ == "__main__":
    main()
