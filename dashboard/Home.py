"""
Ponto de entrada legado: o fluxo principal do painel está em Reserva.py.

Deploys no Streamlit Cloud (ou scripts) que ainda usam `streamlit run dashboard/Home.py`
precisam deste arquivo; sem ele o processo termina na subida e aparece o ícone de erro.
"""
from pathlib import Path
import importlib.util


def _run_reserva() -> None:
    path = Path(__file__).resolve().parent / "Reserva.py"
    spec = importlib.util.spec_from_file_location("dashboard_reserva_entry", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Não foi possível carregar {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


_run_reserva()
