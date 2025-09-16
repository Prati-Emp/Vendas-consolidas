#!/usr/bin/env python3
"""
Orquestrador de APIs
Gerencia limites de requisições e coordena chamadas para múltiplas APIs
"""

import time
import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from collections import defaultdict, deque
import threading

from config import get_api_config, get_all_rate_limits

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class RequestInfo:
    """Informações sobre uma requisição"""
    timestamp: datetime
    api_name: str
    success: bool
    response_time: float

class RateLimiter:
    """Controlador de taxa de requisições por API"""
    
    def __init__(self, api_name: str, rate_limit: int):
        self.api_name = api_name
        self.rate_limit = rate_limit  # requests per minute
        self.requests = deque()
        self.lock = threading.Lock()
    
    def can_make_request(self) -> bool:
        """Verifica se pode fazer uma nova requisição"""
        with self.lock:
            now = datetime.now()
            # Remove requisições antigas (mais de 1 minuto)
            while self.requests and (now - self.requests[0]).total_seconds() > 60:
                self.requests.popleft()
            
            return len(self.requests) < self.rate_limit
    
    def record_request(self):
        """Registra uma nova requisição"""
        with self.lock:
            self.requests.append(datetime.now())
    
    def wait_time(self) -> float:
        """Calcula tempo de espera necessário"""
        with self.lock:
            if len(self.requests) < self.rate_limit:
                return 0
            
            # Tempo até a requisição mais antiga expirar
            oldest_request = self.requests[0]
            wait_seconds = 60 - (datetime.now() - oldest_request).total_seconds()
            return max(0, wait_seconds)

class APIOrchestrator:
    """Orquestrador principal para gerenciar chamadas de APIs"""
    
    def __init__(self):
        self.rate_limiters = {}
        self.request_history = []
        self.lock = threading.Lock()
        
        # Inicializar rate limiters para cada API
        rate_limits = get_all_rate_limits()
        for api_name, limit in rate_limits.items():
            self.rate_limiters[api_name] = RateLimiter(api_name, limit)
        
        logger.info(f"Inicializado orquestrador para {len(self.rate_limiters)} APIs")
    
    async def make_request(self, api_name: str, url: str, headers: Dict[str, str], 
                          params: Optional[Dict] = None, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Faz uma requisição respeitando os limites de taxa"""
        
        rate_limiter = self.rate_limiters.get(api_name)
        if not rate_limiter:
            raise ValueError(f"Rate limiter não encontrado para API: {api_name}")
        
        # Aguardar se necessário
        wait_time = rate_limiter.wait_time()
        if wait_time > 0:
            logger.info(f"Aguardando {wait_time:.2f}s para API {api_name} (limite de taxa)")
            await asyncio.sleep(wait_time)
        
        # Registrar requisição
        rate_limiter.record_request()
        
        # Fazer a requisição
        start_time = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                if data:
                    async with session.post(url, headers=headers, json=data, params=params) as response:
                        result = await response.json()
                        success = response.status == 200
                else:
                    async with session.get(url, headers=headers, params=params) as response:
                        result = await response.json()
                        success = response.status == 200
                
                response_time = time.time() - start_time
                
                # Registrar histórico
                with self.lock:
                    self.request_history.append(RequestInfo(
                        timestamp=datetime.now(),
                        api_name=api_name,
                        success=success,
                        response_time=response_time
                    ))
                
                if success:
                    logger.info(f"✅ {api_name}: {response_time:.2f}s")
                else:
                    logger.warning(f"⚠️ {api_name}: Status {response.status}")
                
                return {
                    'success': success,
                    'data': result,
                    'response_time': response_time,
                    'status_code': response.status if 'response' in locals() else None
                }
                
        except Exception as e:
            response_time = time.time() - start_time
            logger.error(f"❌ {api_name}: Erro - {str(e)}")
            
            with self.lock:
                self.request_history.append(RequestInfo(
                    timestamp=datetime.now(),
                    api_name=api_name,
                    success=False,
                    response_time=response_time
                ))
            
            return {
                'success': False,
                'error': str(e),
                'response_time': response_time
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas das requisições"""
        with self.lock:
            now = datetime.now()
            recent_requests = [r for r in self.request_history 
                             if (now - r.timestamp).total_seconds() < 300]  # últimos 5 minutos
            
            stats = {
                'total_requests': len(recent_requests),
                'successful_requests': len([r for r in recent_requests if r.success]),
                'failed_requests': len([r for r in recent_requests if not r.success]),
                'avg_response_time': sum(r.response_time for r in recent_requests) / len(recent_requests) if recent_requests else 0,
                'by_api': defaultdict(lambda: {'total': 0, 'success': 0, 'failed': 0})
            }
            
            for req in recent_requests:
                stats['by_api'][req.api_name]['total'] += 1
                if req.success:
                    stats['by_api'][req.api_name]['success'] += 1
                else:
                    stats['by_api'][req.api_name]['failed'] += 1
            
            return dict(stats)
    
    def print_stats(self):
        """Imprime estatísticas das requisições"""
        stats = self.get_stats()
        print("\n=== Estatísticas do Orquestrador ===")
        print(f"Total de requisições (5min): {stats['total_requests']}")
        print(f"Sucessos: {stats['successful_requests']}")
        print(f"Falhas: {stats['failed_requests']}")
        print(f"Tempo médio de resposta: {stats['avg_response_time']:.2f}s")
        
        print("\nPor API:")
        for api_name, api_stats in stats['by_api'].items():
            success_rate = (api_stats['success'] / api_stats['total'] * 100) if api_stats['total'] > 0 else 0
            print(f"  {api_name}: {api_stats['total']} req, {success_rate:.1f}% sucesso")

# Instância global do orquestrador
orchestrator = APIOrchestrator()

async def make_api_request(api_name: str, endpoint: str, params: Optional[Dict] = None, 
                          data: Optional[Dict] = None) -> Dict[str, Any]:
    """Função helper para fazer requisições via orquestrador"""
    config = get_api_config(api_name)
    if not config:
        return {'success': False, 'error': f'Configuração não encontrada para {api_name}'}
    
    url = f"{config.base_url}{endpoint}"
    return await orchestrator.make_request(api_name, url, config.headers, params, data)

if __name__ == "__main__":
    # Teste do orquestrador
    async def test_orchestrator():
        print("=== Testando Orquestrador ===")
        
        # Teste com API de reservas
        result = await make_api_request('reservas', '', {'pagina': 1, 'registros_por_pagina': 10})
        print(f"Resultado: {result['success']}")
        
        # Imprimir estatísticas
        orchestrator.print_stats()
    
    asyncio.run(test_orchestrator())
