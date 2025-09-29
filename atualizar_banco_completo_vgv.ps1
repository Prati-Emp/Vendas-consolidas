# PowerShell script para atualização completa do banco incluindo VGV Empreendimentos
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ATUALIZACAO COMPLETA DO BANCO" -ForegroundColor Cyan
Write-Host "INCLUINDO VGV EMPREENDIMENTOS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Este script atualiza TODOS os dados do banco:" -ForegroundColor Yellow
Write-Host "- CV Vendas" -ForegroundColor White
Write-Host "- CV Repasses" -ForegroundColor White
Write-Host "- CV Leads" -ForegroundColor White
Write-Host "- CV Repasses Workflow" -ForegroundColor White
Write-Host "- VGV Empreendimentos (NOVO)" -ForegroundColor Green
Write-Host "- Sienge Vendas Realizadas" -ForegroundColor White
Write-Host "- Sienge Vendas Canceladas" -ForegroundColor White
Write-Host ""
Write-Host "ATENCAO: Esta operacao pode demorar varios minutos!" -ForegroundColor Red
Write-Host ""
Read-Host "Pressione Enter para continuar"
Write-Host ""
Write-Host "Executando atualizacao completa..." -ForegroundColor Green
python atualizar_banco_completo_vgv.py
Write-Host ""
Write-Host "Atualizacao completa finalizada!" -ForegroundColor Green
Read-Host "Pressione Enter para sair"

