#!/usr/bin/env python3
"""
Controle de Concorrência para GitHub Actions
Evita execução simultânea de múltiplos workflows que podem causar conflitos
"""

import os
import time
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

class ConcurrencyControl:
    """Controle de concorrência para evitar execução simultânea de workflows"""
    
    def __init__(self, lock_file: str = "/tmp/vendas_consolidadas.lock", timeout_minutes: int = 30):
        self.lock_file = lock_file
        self.timeout_minutes = timeout_minutes
        self.timeout_seconds = timeout_minutes * 60
    
    def acquire_lock(self) -> bool:
        """
        Tenta adquirir o lock para execução exclusiva
        
        Returns:
            bool: True se conseguiu adquirir o lock, False caso contrário
        """
        try:
            # Verificar se já existe um lock ativo
            if os.path.exists(self.lock_file):
                # Verificar se o lock não expirou
                lock_time = os.path.getmtime(self.lock_file)
                current_time = time.time()
                
                if current_time - lock_time < self.timeout_seconds:
                    logger.warning(f"Lock ativo encontrado (criado há {int((current_time - lock_time)/60)} minutos)")
                    logger.warning("Outro workflow pode estar executando. Aguardando...")
                    
                    # Aguardar um pouco e tentar novamente
                    time.sleep(30)
                    
                    if os.path.exists(self.lock_file):
                        lock_time = os.path.getmtime(self.lock_file)
                        if current_time - lock_time < self.timeout_seconds:
                            logger.error("Lock ainda ativo após aguardar. Abortando execução.")
                            return False
                else:
                    logger.warning("Lock expirado encontrado. Removendo...")
                    os.remove(self.lock_file)
            
            # Criar novo lock
            with open(self.lock_file, 'w') as f:
                f.write(f"Lock criado em: {datetime.now().isoformat()}\n")
                f.write(f"PID: {os.getpid()}\n")
                f.write(f"Timeout: {self.timeout_minutes} minutos\n")
            
            logger.info(f"Lock adquirido com sucesso: {self.lock_file}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao adquirir lock: {e}")
            return False
    
    def release_lock(self) -> bool:
        """
        Libera o lock após execução
        
        Returns:
            bool: True se conseguiu liberar o lock, False caso contrário
        """
        try:
            if os.path.exists(self.lock_file):
                os.remove(self.lock_file)
                logger.info("Lock liberado com sucesso")
                return True
            else:
                logger.warning("Lock não encontrado para liberação")
                return False
        except Exception as e:
            logger.error(f"Erro ao liberar lock: {e}")
            return False
    
    def is_locked(self) -> bool:
        """
        Verifica se há um lock ativo
        
        Returns:
            bool: True se há lock ativo, False caso contrário
        """
        if not os.path.exists(self.lock_file):
            return False
        
        try:
            lock_time = os.path.getmtime(self.lock_file)
            current_time = time.time()
            
            # Se o lock expirou, consideramos como não ativo
            if current_time - lock_time >= self.timeout_seconds:
                logger.warning("Lock expirado encontrado")
                os.remove(self.lock_file)
                return False
            
            return True
        except Exception as e:
            logger.error(f"Erro ao verificar lock: {e}")
            return False

def check_concurrency() -> bool:
    """
    Verifica se é seguro executar o workflow atual
    
    Returns:
        bool: True se é seguro executar, False se deve aguardar
    """
    control = ConcurrencyControl()
    
    if control.is_locked():
        logger.warning("Outro workflow está executando. Aguardando...")
        time.sleep(60)  # Aguardar 1 minuto
        
        if control.is_locked():
            logger.error("Ainda há lock ativo após aguardar. Abortando execução.")
            return False
    
    return control.acquire_lock()

def release_concurrency():
    """Libera o controle de concorrência"""
    control = ConcurrencyControl()
    control.release_lock()

if __name__ == "__main__":
    # Teste do controle de concorrência
    print("=== TESTE DE CONTROLE DE CONCORRÊNCIA ===")
    
    if check_concurrency():
        print("✅ Lock adquirido com sucesso")
        print("Simulando execução...")
        time.sleep(5)
        release_concurrency()
        print("✅ Lock liberado com sucesso")
    else:
        print("❌ Não foi possível adquirir o lock")
