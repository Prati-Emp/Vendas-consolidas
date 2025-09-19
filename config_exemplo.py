#!/usr/bin/env python3
"""
Arquivo de exemplo para configuração das credenciais
Copie este arquivo e renomeie para config_credenciais.py
"""

# Configurações das APIs
# Preencha com suas credenciais reais

# API CV Vendas (usa as mesmas credenciais do CVCrm)
CVCRM_EMAIL = "seu_email@exemplo.com"
CVCRM_TOKEN = "seu_token_cvcrm"

# API Sienge
SIENGE_TOKEN = "seu_token_sienge_basic"

# MotherDuck
MOTHERDUCK_TOKEN = "seu_token_motherduck"

# Modo teste para Sienge (opcional)
SIENGE_MODO_TESTE = False

def configurar_ambiente():
    """Configura as variáveis de ambiente com as credenciais"""
    import os
    
    os.environ['CVCRM_EMAIL'] = CVCRM_EMAIL
    os.environ['CVCRM_TOKEN'] = CVCRM_TOKEN
    os.environ['SIENGE_TOKEN'] = SIENGE_TOKEN
    os.environ['MOTHERDUCK_TOKEN'] = MOTHERDUCK_TOKEN
    os.environ['SIENGE_MODO_TESTE'] = str(SIENGE_MODO_TESTE)
    
    print("✅ Variáveis de ambiente configuradas")

