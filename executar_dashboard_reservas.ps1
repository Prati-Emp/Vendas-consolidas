# Script PowerShell para executar o Dashboard de Reservas
Write-Host "🚀 Iniciando Dashboard de Reservas..." -ForegroundColor Green
Write-Host ""

# Navegar para o diretório correto
Set-Location -Path $PSScriptRoot

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

# Verificar outras dependências
Write-Host "🔍 Verificando dependências..." -ForegroundColor Cyan
try {
    python -c "import pandas, duckdb, plotly" 2>$null
    Write-Host "✅ Dependências encontradas" -ForegroundColor Green
} catch {
    Write-Host "❌ Dependências não encontradas. Instalando..." -ForegroundColor Red
    python -m pip install -r requirements.txt
}

Write-Host "🔧 Executando dashboard de reservas..." -ForegroundColor Cyan
Write-Host ""

# Executar o dashboard
python -m streamlit run dashboard/Home.py --server.port 8501

Write-Host ""
Write-Host "✅ Dashboard finalizado!" -ForegroundColor Green

