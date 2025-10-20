@echo off
echo ========================================
echo   Dashboard de Vendas Consolidadas
echo ========================================
echo.
echo Iniciando o dashboard...
echo.

REM Verificar se o arquivo .env existe
if not exist .env (
    echo AVISO: Arquivo .env nao encontrado!
    echo Copie o arquivo .env.example para .env e configure seu token.
    echo.
    pause
    exit /b 1
)

REM Executar o dashboard
streamlit run app.py

pause

