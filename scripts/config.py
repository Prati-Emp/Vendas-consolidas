#!/usr/bin/env python3
"""
Sistema de configuração segura para APIs
Gerencia credenciais e configurações de forma centralizada e segura
"""

import os
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv, dotenv_values
from pathlib import Path
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
        # Carregar .env explicitamente da raiz do projeto
        try:
            project_root = Path(__file__).resolve().parents[1]
            env_path = project_root / '.env'
            load_dotenv(dotenv_path=env_path, override=True)
            logger.info(f".env carregado de: {env_path} (existe={env_path.exists()})")
            # Normalizar chaves com possível BOM (\ufeff) e espaços
            try:
                raw_values = dotenv_values(env_path)
                for raw_key, raw_val in raw_values.items():
                    if raw_key is None:
                        continue
                    clean_key = str(raw_key).replace('\ufeff', '').strip()
                    clean_val = '' if raw_val is None else str(raw_val).strip()
                    os.environ[clean_key] = clean_val
            except Exception as norm_err:
                logger.warning(f"Falha ao normalizar chaves do .env: {norm_err}")
            # Debug: mostrar valores lidos (mascarando token)
            cv_email = os.environ.get('CV_VENDAS_EMAIL')
            cv_token = os.environ.get('CV_VENDAS_TOKEN')
            cv_base = os.environ.get('CV_VENDAS_BASE_URL')
            logger.info(f"DEBUG ENV CV_VENDAS_EMAIL={repr(cv_email)} CV_VENDAS_BASE_URL={repr(cv_base)} TOKEN_SET={bool(cv_token)}")
        except Exception as e:
            logger.warning(f"Falha ao carregar .env: {e}")
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
        
        # API CV - Relatório de Vendas (usa mesma autenticação do CVCRM)
        configs['cv_vendas'] = APIConfig(
            name='CV Relatório de Vendas',
            base_url=os.environ.get('CV_VENDAS_BASE_URL', '').strip(),
            headers={
                'accept': 'application/json',
                'email': os.environ.get('CVCRM_EMAIL', '').strip(),  # Reutiliza email do CVCRM
                'token': os.environ.get('CVCRM_TOKEN', '').strip(),  # Reutiliza token do CVCRM
            },
            rate_limit=20
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
