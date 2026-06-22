"""Garante acesso aos modulos compartilhados em `dashboard/`."""

import sys
from pathlib import Path


def ensure_dashboard_on_path() -> None:
    root = Path(__file__).resolve().parent.parent
    dashboard = root / "dashboard"
    for path in (root, dashboard):
        if str(path) not in sys.path:
            sys.path.append(str(path))
