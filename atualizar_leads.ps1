# Script PowerShell para atualizar tabela de Leads
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   ATUALIZACAO COMPLETA DA TABELA LEADS" -ForegroundColor Cyan  
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Este script ira coletar TODOS os dados de leads" -ForegroundColor Yellow
Write-Host "e atualizar a tabela main.cv_leads no MotherDuck" -ForegroundColor Yellow
Write-Host ""
Write-Host "Tempo estimado: 5-15 minutos" -ForegroundColor Green
Write-Host ""
Read-Host "Pressione Enter para continuar"
Write-Host ""
Write-Host "Iniciando coleta de dados..." -ForegroundColor Green
python -u atualizar_leads_completo.py
Write-Host ""
Write-Host "Processo concluido!" -ForegroundColor Green
Read-Host "Pressione Enter para sair"





