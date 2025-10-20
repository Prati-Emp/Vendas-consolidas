@echo off
echo 🚀 Iniciando Dashboard de Reservas...
echo.

echo 📋 Navegando para o diretório correto...
cd /d "%~dp0"

echo 🔧 Verificando dependências...
python -c "import streamlit, pandas, duckdb, plotly" 2>nul
if errorlevel 1 (
    echo ❌ Dependências não encontradas. Instalando...
    pip install -r requirements.txt
)

echo 🔧 Executando dashboard de reservas...
python -m streamlit run dashboard/Home.py --server.port 8501

echo.
echo ✅ Dashboard finalizado!
pause

