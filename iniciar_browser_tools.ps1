# Script PowerShell para iniciar MCP Browser Tools
# Execute com: .\iniciar_browser_tools.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "    Iniciando MCP Browser Tools" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verificar Node.js
Write-Host "[1/3] Verificando Node.js..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version
    Write-Host "✓ Node.js encontrado: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "ERRO: Node.js não encontrado. Instale o Node.js primeiro." -ForegroundColor Red
    Read-Host "Pressione Enter para sair"
    exit 1
}

Write-Host ""
Write-Host "[2/3] Iniciando browser-tools-server..." -ForegroundColor Yellow
Write-Host "Servidor Node.js será executado em background..." -ForegroundColor Gray

# Iniciar servidor em background
$job = Start-Job -ScriptBlock {
    npx @agentdeskai/browser-tools-server@latest
}

Write-Host ""
Write-Host "[3/3] Aguardando servidor inicializar..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "    Browser Tools MCP Pronto!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Próximos passos:" -ForegroundColor Yellow
Write-Host "1. Instale a extensão Chrome BrowserToolsMCP" -ForegroundColor White
Write-Host "2. Configure o Cursor IDE com mcp_config_completo.toml" -ForegroundColor White
Write-Host "3. Abra o DevTools do Chrome (F12)" -ForegroundColor White
Write-Host "4. Vá para a aba 'BrowserToolsMCP'" -ForegroundColor White
Write-Host "5. Use no Cursor: 'Capture a screenshot'" -ForegroundColor White
Write-Host ""
Write-Host "Para parar o servidor, execute: Stop-Job $($job.Id)" -ForegroundColor Gray
Write-Host ""

# Manter janela aberta
Read-Host "Pressione Enter para sair"

