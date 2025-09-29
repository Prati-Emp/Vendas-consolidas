# PowerShell script para atualização VGV Empreendimentos
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ATUALIZACAO VGV EMPREENDIMENTOS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Este script atualiza os dados VGV Empreendimentos no MotherDuck" -ForegroundColor Yellow
Write-Host ""
Read-Host "Pressione Enter para continuar"
Write-Host ""
Write-Host "Executando atualizacao..." -ForegroundColor Green
python atualizar_vgv_empreendimentos.py
Write-Host ""
Write-Host "Atualizacao finalizada!" -ForegroundColor Green
Read-Host "Pressione Enter para sair"

