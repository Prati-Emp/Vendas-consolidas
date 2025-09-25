#!/usr/bin/env python3
"""
Sistema de configuração simplificado para APIs
Versão sem loops infinitos
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass

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
    
    if api_name == 'cv_vendas':
        return APIConfig(
            name='CV Vendas',
            base_url='https://prati.cvcrm.com.br/api/v1/cvdw/vendas',
            headers={
                'accept': 'application/json',
                'email': os.environ.get('CVCRM_EMAIL', ''),
                'token': os.environ.get('CVCRM_TOKEN', '')
            },
            rate_limit=60
        )
    
    elif api_name == 'cv_repasses':
        # Mesmas credenciais de CV Vendas, endpoint diferente
        return APIConfig(
            name='CV Repasses',
            base_url='https://prati.cvcrm.com.br/api/v1/cvdw/repasses',
            headers={
                'accept': 'application/json',
                'email': os.environ.get('CVCRM_EMAIL', ''),
                'token': os.environ.get('CVCRM_TOKEN', '')
            },
            rate_limit=60
        )
    
    elif api_name == 'cv_leads':
        # Mesmas credenciais de CV Vendas, endpoint diferente
        return APIConfig(
            name='CV Leads',
            base_url='https://prati.cvcrm.com.br/api/v1/cvdw/leads',
            headers={
                'accept': 'application/json',
                'email': os.environ.get('CVCRM_EMAIL', ''),
                'token': os.environ.get('CVCRM_TOKEN', '')
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
            base_url='https://api.sienge.com.br/pratiemp/public/api/bulk-data/v1/sales',
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
            base_url='https://api.sienge.com.br/pratiemp/public/api/bulk-data/v1/sales',
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
        'cv_repasses': 60,
        'cv_leads': 60,
        'sienge_vendas_realizadas': 50,
        'sienge_vendas_canceladas': 50
    }