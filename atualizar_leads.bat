@echo off
echo ========================================
echo    ATUALIZACAO COMPLETA DA TABELA LEADS
echo ========================================
echo.
echo Este script ira coletar TODOS os dados de leads
echo e atualizar a tabela main.cv_leads no MotherDuck
echo.
echo Tempo estimado: 5-15 minutos
echo.
pause
echo.
echo Iniciando coleta de dados...
python -u atualizar_leads_completo.py
echo.
echo Processo concluido!
pause



