#!/usr/bin/env python3
"""
Sistema de configuração simplificado para APIs
Versão sem loops infinitos
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

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
    
    elif api_name == 'cv_leads_workflow_tempo':
        # Mesmas credenciais de CV Vendas, endpoint diferente
        return APIConfig(
            name='CV Leads Workflow Tempo',
            base_url='https://prati.cvcrm.com.br/api/v1/cvdw/leads/workflow/tempo',
            headers={
                'accept': 'application/json',
                'email': os.environ.get('CVCRM_EMAIL', ''),
                'token': os.environ.get('CVCRM_TOKEN', '')
            },
            rate_limit=60
        )
    
    elif api_name == 'cv_repasses_workflow':
        # Mesmas credenciais de CV Vendas, endpoint diferente
        return APIConfig(
            name='CV Repasses Workflow',
            base_url='https://prati.cvcrm.com.br/api/v1/cvdw/repasses/workflow/tempo',
            headers={
                'accept': 'application/json',
                'content-type': 'application/json',
                'email': os.environ.get('CVCRM_EMAIL', ''),
                'token': os.environ.get('CVCRM_TOKEN', '')
            },
            rate_limit=60
        )
    
    elif api_name == 'cv_vgv_empreendimentos':
        # Mesmas credenciais de CV Vendas, endpoint diferente
        return APIConfig(
            name='CV VGV Empreendimentos',
            base_url='https://prati.cvcrm.com.br/api/v1/cv/tabelasdepreco',
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
    
    elif api_name == 'sienge_contratos_suprimentos':
        token = os.environ.get('SIENGE_TOKEN', '')
        # Limpar token de caracteres extras
        token = token.strip()
        if token.startswith('sBasic '):
            token = token[1:]  # Remove o 's' extra
        if token.startswith('Basic '):
            auth_header = token
        else:
            auth_header = f'Basic {token}'
            
        return APIConfig(
            name='Sienge Contratos Suprimentos',
            base_url='https://api.sienge.com.br/pratiemp/public/api/v1/supply-contracts/all',
            headers={
                'accept': 'application/json',
                'authorization': auth_header
            },
            rate_limit=50
        )
    
    elif api_name == 'sienge_pedidos_compras':
        token = os.environ.get('SIENGE_TOKEN', '')
        # Limpar token de caracteres extras
        token = token.strip()
        if token.startswith('sBasic '):
            token = token[1:]  # Remove o 's' extra
        if token.startswith('Basic '):
            auth_header = token
        else:
            auth_header = f'Basic {token}'
            
        return APIConfig(
            name='Sienge Pedidos Compras',
            base_url='https://api.sienge.com.br/pratiemp/public/api/v1/purchase-orders',
            headers={
                'accept': 'application/json',
                'authorization': auth_header
            },
            rate_limit=50
        )
    
    elif api_name == 'jira':
        # Jira usa autenticação Basic Auth (email + token)
        # base_url é a URL base do Jira (sem /rest/api/3)
        jira_url = os.environ.get('JIRA_URL', 'https://prati-empreendimentos.atlassian.net')
        return APIConfig(
            name='Jira',
            base_url=jira_url,
            headers={
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            rate_limit=30  # Jira é mais lento, usar rate limit menor
        )
    
    elif api_name == 'sienge_medicoes':
        token = os.environ.get('SIENGE_TOKEN', '')
        # Limpar token de caracteres extras
        token = token.strip()
        if token.startswith('sBasic '):
            token = token[1:]  # Remove o 's' extra
        if token.startswith('Basic '):
            auth_header = token
        else:
            auth_header = f'Basic {token}'
            
        return APIConfig(
            name='Sienge Medições',
            base_url='https://api.sienge.com.br/pratiemp/public/api/bulk-data/v1/building-cost-estimation-items',
            headers={
                'accept': 'application/json',
                'authorization': auth_header
            },
            rate_limit=50
        )
    
    elif api_name == 'sienge_contas_pagas':
        token = os.environ.get('SIENGE_TOKEN', '')
        # Limpar token de caracteres extras
        token = token.strip()
        if token.startswith('sBasic '):
            token = token[1:]  # Remove o 's' extra
        if token.startswith('Basic '):
            auth_header = token
        else:
            auth_header = f'Basic {token}'
            
        return APIConfig(
            name='Sienge Contas Pagas',
            base_url='https://api.sienge.com.br/pratiemp/public/api/bulk-data/v1/outcome',
            headers={
                'accept': 'application/json',
                'authorization': auth_header,
                'Content-Type': 'application/json'
            },
            rate_limit=50
        )

    elif api_name == 'sienge_contas_receber':
        token = os.environ.get('SIENGE_TOKEN', '')
        # Limpar token de caracteres extras
        token = token.strip()
        if token.startswith('sBasic '):
            token = token[1:]  # Remove o 's' extra
        if token.startswith('Basic '):
            auth_header = token
        else:
            auth_header = f'Basic {token}'
            
        return APIConfig(
            name='Sienge Contas Receber',
            base_url='https://api.sienge.com.br/pratiemp/public/api/bulk-data/v1/income',
            headers={
                'accept': 'application/json',
                'authorization': auth_header,
                'Content-Type': 'application/json'
            },
            rate_limit=50
        )

    elif api_name == 'sienge_stock_inventories':
        token = os.environ.get('SIENGE_TOKEN', '')
        token = token.strip()
        if token.startswith('sBasic '):
            token = token[1:]
        if token.startswith('Basic '):
            auth_header = token
        else:
            auth_header = f'Basic {token}'
        return APIConfig(
            name='Sienge Stock Inventories',
            base_url='https://api.sienge.com.br/pratiemp/public/api/v1',
            headers={
                'accept': 'application/json',
                'authorization': auth_header,
                'Content-Type': 'application/json'
            },
            rate_limit=50
        )
    
    elif api_name == 'cv_comissoes':
        # Mesmas credenciais de CV Vendas, endpoint diferente
        return APIConfig(
            name='CV Comissões',
            base_url='https://prati.cvcrm.com.br/api/v1/cv/comissoes',
            headers={
                'accept': 'application/json',
                'email': os.environ.get('CVCRM_EMAIL', ''),
                'token': os.environ.get('CVCRM_TOKEN', '')
            },
            rate_limit=60
        )
    
    return None

def get_all_rate_limits() -> Dict[str, int]:
    """Retorna limites de taxa para todas as APIs"""
    return {
        'cv_vendas': 60,
        'cv_repasses': 60,
        'cv_leads': 60,
        'cv_leads_workflow_tempo': 60,
        'cv_repasses_workflow': 60,
        'cv_vgv_empreendimentos': 60,
        'cv_comissoes': 60,
        'sienge_vendas_realizadas': 50,
        'sienge_vendas_canceladas': 50,
        'sienge_contratos_suprimentos': 50,
        'sienge_pedidos_compras': 50,
        'sienge_medicoes': 50,
        'sienge_contas_pagas': 50,
        'sienge_contas_receber': 50,
        'sienge_stock_inventories': 50,
        'jira': 30
    }