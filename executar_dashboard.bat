@echo off
echo 🚀 Iniciando Dashboard de Repasses...
echo.
echo 📋 Navegando para o diretório correto...
cd /d "%~dp0repasses"

echo 🔧 Executando dashboard...
python -m streamlit run dashboard_app/app.py

echo.
echo ✅ Dashboard finalizado!
pause

