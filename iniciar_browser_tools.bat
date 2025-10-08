@echo off
echo ========================================
echo    Iniciando MCP Browser Tools
echo ========================================
echo.

echo [1/3] Verificando Node.js...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERRO: Node.js nao encontrado. Instale o Node.js primeiro.
    pause
    exit /b 1
)
echo ✓ Node.js encontrado

echo.
echo [2/3] Iniciando browser-tools-server...
echo Servidor Node.js sera executado em background...
start /b npx @agentdeskai/browser-tools-server@latest

echo.
echo [3/3] Aguardando servidor inicializar...
timeout /t 3 /nobreak >nul

echo.
echo ========================================
echo    Browser Tools MCP Pronto!
echo ========================================
echo.
echo Proximos passos:
echo 1. Instale a extensao Chrome BrowserToolsMCP
echo 2. Configure o Cursor IDE com mcp_config_completo.toml
echo 3. Abra o DevTools do Chrome (F12)
echo 4. Vá para a aba "BrowserToolsMCP"
echo 5. Use no Cursor: "Capture a screenshot"
echo.
echo Para parar o servidor, feche esta janela.
echo.
pause

