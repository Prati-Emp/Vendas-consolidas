# Dashboard de Vendas Consolidadas
# Script PowerShell para executar o dashboard

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Dashboard de Vendas Consolidadas" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verificar se o arquivo .env existe
if (-not (Test-Path ".env")) {
    Write-Host "AVISO: Arquivo .env não encontrado!" -ForegroundColor Yellow
    Write-Host "Copie o arquivo .env.example para .env e configure seu token." -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Pressione Enter para sair"
    exit 1
}

Write-Host "Iniciando o dashboard..." -ForegroundColor Green
Write-Host ""

# Executar o dashboard
streamlit run app.py

Read-Host "Pressione Enter para sair"

