@echo off
echo ========================================
echo ATUALIZACAO COMPLETA DO BANCO
echo INCLUINDO VGV EMPREENDIMENTOS
echo ========================================
echo.
echo Este script atualiza TODOS os dados do banco:
echo - CV Vendas
echo - CV Repasses  
echo - CV Leads
echo - CV Repasses Workflow
echo - VGV Empreendimentos (NOVO)
echo - Sienge Vendas Realizadas
echo - Sienge Vendas Canceladas
echo.
echo ATENCAO: Esta operacao pode demorar varios minutos!
echo.
pause
echo.
echo Executando atualizacao completa...
python atualizar_banco_completo_vgv.py
echo.
echo Atualizacao completa finalizada!
pause

