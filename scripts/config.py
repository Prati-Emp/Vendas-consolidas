#!/usr/bin/env python3
"""
Sistema de configuração segura para APIs
Gerencia credenciais e configurações de forma centralizada e segura
"""

import os
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class APIConfig:
    """Configuração para uma API específica"""
    name: str
    base_url: str
    headers: Dict[str, str]
    rate_limit: int  # requests per minute
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: int = 5

class APIConfigManager:
    """Gerenciador de configurações das APIs"""
    
    def __init__(self):
        load_dotenv()
        self.configs = self._load_configs()
    
    def _load_configs(self) -> Dict[str, APIConfig]:
        """Carrega configurações das APIs do ambiente"""
        configs = {}
        
        # API de Reservas (existente)
        configs['reservas'] = APIConfig(
            name='CVCRM Reservas',
            base_url='https://prati.cvcrm.com.br/api/v1/cvdw/reservas',
            headers={
                'accept': 'application/json',
                'email': os.environ.get('CVCRM_EMAIL', '').strip(),
                'token': os.environ.get('CVCRM_TOKEN', '').strip(),
            },
            rate_limit=20  # 20 requests per minute
        )
        
        # API de Workflow (existente)
        configs['workflow'] = APIConfig(
            name='CVCRM Workflow',
            base_url='https://prati.cvcrm.com.br/api/v1/cvdw/reservas/workflow/tempo',
            headers={
                'accept': 'application/json',
                'email': os.environ.get('CVCRM_EMAIL', '').strip(),
                'token': os.environ.get('CVCRM_TOKEN', '').strip(),
            },
            rate_limit=20
        )
        
        # API Sienge - Vendas Realizadas
        configs['sienge_vendas_realizadas'] = APIConfig(
            name='Sienge Vendas Realizadas',
            base_url=os.environ.get('SIENGE_BASE_URL', '').strip(),
            headers={
                'accept': 'application/json',
                'Authorization': f"Bearer {os.environ.get('SIENGE_TOKEN', '').strip()}",
                'Content-Type': 'application/json'
            },
            rate_limit=30  # 30 requests per minute
        )
        
        # API Sienge - Vendas Canceladas
        configs['sienge_vendas_canceladas'] = APIConfig(
            name='Sienge Vendas Canceladas',
            base_url=os.environ.get('SIENGE_BASE_URL', '').strip(),
            headers={
                'accept': 'application/json',
                'Authorization': f"Bearer {os.environ.get('SIENGE_TOKEN', '').strip()}",
                'Content-Type': 'application/json'
            },
            rate_limit=30
        )
        
        # API CV - Relatório de Vendas
        configs['cv_vendas'] = APIConfig(
            name='CV Relatório de Vendas',
            base_url=os.environ.get('CV_VENDAS_BASE_URL', '').strip(),
            headers={
                'accept': 'application/json',
                'email': os.environ.get('CV_VENDAS_EMAIL', '').strip(),
                'token': os.environ.get('CV_VENDAS_TOKEN', '').strip(),
            },
            rate_limit=25
        )
        
        return configs
    
    def get_config(self, api_name: str) -> Optional[APIConfig]:
        """Retorna configuração de uma API específica"""
        config = self.configs.get(api_name)
        if not config:
            logger.error(f"Configuração não encontrada para API: {api_name}")
            return None
        
        # Validar se as credenciais estão presentes
        if not self._validate_credentials(config):
            logger.error(f"Credenciais inválidas para API: {api_name}")
            return None
            
        return config
    
    def _validate_credentials(self, config: APIConfig) -> bool:
        """Valida se as credenciais estão presentes"""
        for key, value in config.headers.items():
            if not value or value.strip() == '':
                logger.warning(f"Credencial vazia: {key} para API {config.name}")
                return False
        return True
    
    def get_all_configs(self) -> Dict[str, APIConfig]:
        """Retorna todas as configurações"""
        return self.configs
    
    def get_rate_limits(self) -> Dict[str, int]:
        """Retorna limites de taxa para orquestração"""
        return {name: config.rate_limit for name, config in self.configs.items()}

# Instância global do gerenciador
config_manager = APIConfigManager()

def get_api_config(api_name: str) -> Optional[APIConfig]:
    """Função helper para obter configuração de API"""
    return config_manager.get_config(api_name)

def get_all_rate_limits() -> Dict[str, int]:
    """Função helper para obter limites de taxa"""
    return config_manager.get_rate_limits()

if __name__ == "__main__":
    # Teste das configurações
    print("=== Testando Configurações das APIs ===")
    
    for api_name in config_manager.get_all_configs().keys():
        config = config_manager.get_config(api_name)
        if config:
            print(f"✅ {config.name}: Configurada")
            print(f"   Rate Limit: {config.rate_limit} req/min")
        else:
            print(f"❌ {api_name}: Configuração inválida")
    
    print(f"\nLimites de taxa: {get_all_rate_limits()}")
