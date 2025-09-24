# Script PowerShell para executar o Dashboard de Repasses
Write-Host "🚀 Iniciando Dashboard de Repasses..." -ForegroundColor Green
Write-Host ""

# Navegar para o diretório correto
Set-Location -Path "$PSScriptRoot\repasses"

Write-Host "📋 Diretório atual: $(Get-Location)" -ForegroundColor Yellow
Write-Host ""

# Verificar se o Streamlit está instalado
try {
    $streamlitVersion = python -m streamlit --version 2>$null
    Write-Host "✅ Streamlit encontrado" -ForegroundColor Green
} catch {
    Write-Host "❌ Streamlit não encontrado. Instalando..." -ForegroundColor Red
    python -m pip install streamlit
}

Write-Host "🔧 Executando dashboard..." -ForegroundColor Cyan
Write-Host ""

# Executar o dashboard
python -m streamlit run dashboard_app/app.py

Write-Host ""
Write-Host "✅ Dashboard finalizado!" -ForegroundColor Green
