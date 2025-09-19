#!/usr/bin/env python3
"""
Configuração simplificada para APIs - versão sem loops
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

@dataclass
class APIConfig:
    """Configuração para uma API específica"""
    name: str
    base_url: str
    headers: Dict[str, str]
    rate_limit: int
    timeout: int = 30

def get_api_config(api_name: str) -> Optional[APIConfig]:
    """Obtém configuração de API de forma simples"""
    # Carregar .env apenas quando necessário
    load_dotenv()
    
    if api_name == 'cv_vendas':
        return APIConfig(
            name='CV Vendas',
            base_url='https://prati.cvcrm.com.br/api/v1/cvdw/vendas',
            headers={
                'accept': 'application/json',
                'email': os.environ.get('CV_VENDAS_EMAIL', ''),
                'token': os.environ.get('CV_VENDAS_TOKEN', '')
            },
            rate_limit=60
        )
    
    elif api_name == 'sienge_vendas_realizadas':
        token = os.environ.get('SIENGE_TOKEN', '')
        if token.startswith('Basic '):
            auth_header = token
        else:
            auth_header = f'Basic {token}'
            
        return APIConfig(
            name='Sienge Vendas Realizadas',
            base_url='https://api.sienge.com.br/public/api/v1/sales',
            headers={
                'accept': 'application/json',
                'authorization': auth_header
            },
            rate_limit=50
        )
    
    elif api_name == 'sienge_vendas_canceladas':
        token = os.environ.get('SIENGE_TOKEN', '')
        if token.startswith('Basic '):
            auth_header = token
        else:
            auth_header = f'Basic {token}'
            
        return APIConfig(
            name='Sienge Vendas Canceladas',
            base_url='https://api.sienge.com.br/public/api/v1/sales/cancelled',
            headers={
                'accept': 'application/json',
                'authorization': auth_header
            },
            rate_limit=50
        )
    
    return None

def get_all_rate_limits() -> Dict[str, int]:
    """Retorna limites de taxa para todas as APIs"""
    return {
        'cv_vendas': 60,
        'sienge_vendas_realizadas': 50,
        'sienge_vendas_canceladas': 50
    }

