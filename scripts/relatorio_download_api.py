#!/usr/bin/env python3
"""
Coleta de dados de relatórios com download automático
Suporta: Download CSV/Excel, Web Scraping de tela, Processamento automático
"""

import asyncio
import logging
import time
import os
import shutil
from datetime import datetime, date
from typing import Dict, List, Any, Optional
import pandas as pd
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import json
import glob

from scripts.config import get_api_config

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RelatorioDownloadClient:
    """
    Cliente para coleta de dados de relatórios com download automático
    """
    
    def __init__(
        self,
        download_path: str = "./downloads",
        headless: bool = True,
        chrome_profile: Optional[str] = None,
        chrome_binary: Optional[str] = None,
    ):
        self.download_path = download_path
        self.headless = headless
        self.chrome_profile = chrome_profile
        self.chrome_binary = chrome_binary
        self.driver = None
        
        # Criar diretório de downloads se não existir
        os.makedirs(download_path, exist_ok=True)
    
    async def configurar_webdriver_download(self):
        """Configura o WebDriver para download automático"""
        chrome_options = Options()
        if self.chrome_binary:
            chrome_options.binary_location = self.chrome_binary
        
        if self.headless:
            chrome_options.add_argument("--headless")  # Executar sem interface
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-popup-blocking")
        
        if self.chrome_profile:
            chrome_options.add_argument(f"--user-data-dir={self.chrome_profile}")
            chrome_options.add_argument("--profile-directory=Default")
        
        # Configurar download automático
        prefs = {
            "download.default_directory": os.path.abspath(self.download_path),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        return self.driver
    
    async def fazer_login_sistema(self, config_relatorio: Dict) -> bool:
        """
        Faz login no sistema do relatório
        
        Args:
            config_relatorio: Configuração com credenciais e URLs
        """
        try:
            logger.info("Fazendo login no sistema...")
            self.driver.get(config_relatorio['login_url'])
            
            # Aguardar página carregar
            await asyncio.sleep(2)

            # Fluxo opcional Sienge ID
            if config_relatorio.get('usar_sienge_id'):
                logger.info("Fluxo Sienge ID habilitado")
                await self._fluxo_login_sienge_id(config_relatorio)
                await asyncio.sleep(config_relatorio.get('tempo_pos_login', 3))
                return True
            
            # Preencher credenciais
            username_field = self.driver.find_element(By.NAME, config_relatorio['username_field'])
            password_field = self.driver.find_element(By.NAME, config_relatorio['password_field'])
            
            username_field.clear()
            password_field.clear()
            
            username_field.send_keys(config_relatorio['username'])
            password_field.send_keys(config_relatorio['password'])
            
            # Submeter login
            login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            
            # Aguardar redirecionamento
            await asyncio.sleep(3)
            
            # Verificar se login foi bem-sucedido
            if 'dashboard' in self.driver.current_url or 'home' in self.driver.current_url or config_relatorio.get('login_sem_redirecionamento'):
                logger.info("Login realizado com sucesso")
                return True
            else:
                logger.error("Falha no login - URL não redirecionou corretamente")
                return False
                
        except Exception as e:
            logger.error(f"Erro no login: {e}")
            return False
    
    async def _fluxo_login_sienge_id(self, config_relatorio: Dict) -> None:
        """Executa fluxo específico do Sienge ID."""
        try:
            # 1. Clicar no botão "Entrar com Sienge ID"
            seletor_botao_sienge = config_relatorio.get('seletor_botao_sienge_id')
            botao = None
            if seletor_botao_sienge:
                try:
                    # Tentar CSS selector primeiro
                    botao = self.driver.find_element(By.CSS_SELECTOR, seletor_botao_sienge)
                except Exception:
                    # Se falhar, tentar XPath
                    botao = self.driver.find_element(By.XPATH, seletor_botao_sienge)
            else:
                # Buscar por texto usando XPath
                try:
                    botao = self.driver.find_element(By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'entrar com sienge id')]")
                except Exception:
                    try:
                        botao = self.driver.find_element(By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'sienge id')]")
                    except Exception:
                        # Última tentativa: buscar qualquer botão que contenha "sienge"
                        botao = self.driver.find_element(By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'sienge')]")
            botao.click()
            logger.info("Botão 'Entrar com Sienge ID' clicado")
            await asyncio.sleep(2)

            # 2. Aguardar redirecionamento para login.sienge.com.br
            logger.info("Aguardando redirecionamento para login.sienge.com.br...")
            for _ in range(15):  # Aumentar tempo de espera
                if 'login.sienge.com.br' in self.driver.current_url:
                    logger.info(f"Redirecionado para: {self.driver.current_url}")
                    break
                await asyncio.sleep(1)
            
            # Aguardar carregamento completo da página
            await asyncio.sleep(10)  # Aumentar tempo de espera
            logger.info("Aguardando carregamento completo da página...")

            # 3. Se houver seleção de conta já logada
            seletor_conta = config_relatorio.get('seletor_conta_salva')
            if seletor_conta:
                try:
                    conta = self.driver.find_element(By.CSS_SELECTOR, seletor_conta)
                    conta.click()
                    logger.info("Conta existente selecionada")
                    await asyncio.sleep(3)
                    return
                except Exception as e:
                    logger.debug(f"Conta salva não encontrada: {e}")

            # 4. Preencher email - com clique no campo primeiro
            email_selector = config_relatorio.get('sienge_id_email_selector', 'input[type="email"]')
            senha_selector = config_relatorio.get('sienge_id_password_selector', 'input[type="password"]')
            botao_email_proximo = config_relatorio.get('sienge_id_email_submit_selector')
            botao_senha_submit = config_relatorio.get('sienge_id_password_submit_selector')

            try:
                logger.info("Procurando campo de email...")
                
                # Aguardar campo de email aparecer com WebDriverWait
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                
                wait = WebDriverWait(self.driver, 15)  # Aguardar até 15 segundos
                campo_email = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, email_selector)))
                logger.info("Campo de email encontrado e clicável")
                
                # Clicar no campo primeiro e aguardar
                campo_email.click()
                logger.info("Campo de email clicado")
                await asyncio.sleep(2)  # Aguardar campo ficar ativo
                
                # Limpar e preencher
                campo_email.clear()
                await asyncio.sleep(1)
                campo_email.send_keys(config_relatorio.get('username'))
                logger.info("Email Sienge ID preenchido")
                await asyncio.sleep(3)  # Aguardar mais tempo
                
                # Clicar no botão próximo/continuar
                if botao_email_proximo:
                    self.driver.find_element(By.CSS_SELECTOR, botao_email_proximo).click()
                else:
                    # Tentar diferentes seletores de botão
                    botoes_proximo = [
                        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'continuar')]",
                        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'próximo')]",
                        "//button[@type='submit']",
                        "//input[@type='submit']"
                    ]
                    
                    for seletor in botoes_proximo:
                        try:
                            self.driver.find_element(By.XPATH, seletor).click()
                            logger.info(f"Botão próximo clicado com seletor: {seletor}")
                            break
                        except Exception:
                            continue
                
                await asyncio.sleep(3)
                logger.info("Aguardando próxima página...")
                
            except Exception as e:
                logger.debug(f"Campo de email não encontrado automaticamente: {e}")

            # 5. Preencher senha (se solicitado) - com clique no campo primeiro
            try:
                logger.info("Procurando campo de senha...")
                
                # Aguardar campo de senha aparecer com WebDriverWait
                wait = WebDriverWait(self.driver, 15)  # Aguardar até 15 segundos
                campo_senha = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, senha_selector)))
                logger.info("Campo de senha encontrado e clicável")
                
                # Clicar no campo primeiro e aguardar
                campo_senha.click()
                logger.info("Campo de senha clicado")
                await asyncio.sleep(2)  # Aguardar campo ficar ativo
                
                # Limpar e preencher
                campo_senha.clear()
                await asyncio.sleep(1)
                campo_senha.send_keys(config_relatorio.get('password'))
                logger.info("Senha Sienge ID preenchida")
                await asyncio.sleep(3)  # Aguardar mais tempo
                
                # Clicar no botão de login
                if botao_senha_submit:
                    self.driver.find_element(By.CSS_SELECTOR, botao_senha_submit).click()
                else:
                    # Tentar diferentes seletores de botão
                    botoes_login = [
                        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'entrar')]",
                        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'sign in')]",
                        "//button[@type='submit']",
                        "//input[@type='submit']"
                    ]
                    
                    for seletor in botoes_login:
                        try:
                            self.driver.find_element(By.XPATH, seletor).click()
                            logger.info(f"Botão de login clicado com seletor: {seletor}")
                            break
                        except Exception:
                            continue
                
                await asyncio.sleep(3)
                logger.info("Aguardando login ser processado...")
                
            except Exception as e:
                logger.debug(f"Campo de senha não encontrado automaticamente: {e}")

            # 6. Caso MFA seja necessário, aguardar confirmação manual
            if config_relatorio.get('pausa_para_mfa') and not self.headless:
                logger.info("Aguardando confirmação manual do MFA. Complete a autenticação no dispositivo móvel.")
                input("Pressione ENTER após concluir a autenticação MFA...")

        except Exception as e:
            logger.error(f"Erro no fluxo Sienge ID: {e}")
            raise

    async def navegar_para_relatorio(self, config_relatorio: Dict) -> bool:
        """
        Navega para a página do relatório
        
        Args:
            config_relatorio: Configuração com URL do relatório
        """
        try:
            logger.info("Navegando para o relatório...")
            self.driver.get(config_relatorio['url'])
            
            # Aguardar página carregar completamente
            logger.info("Aguardando carregamento completo da página do relatório...")
            await asyncio.sleep(10)  # Aumentar tempo de espera
            
            # Verificar se precisa fazer segunda autenticação
            if await self._verificar_segunda_autenticacao(config_relatorio):
                logger.info("Segunda autenticação necessária - processando...")
                if not await self._processar_segunda_autenticacao(config_relatorio):
                    logger.error("Falha na segunda autenticação")
                    return False
            
            # Aguardar elementos específicos carregarem
            try:
                # Aguardar botão "GERAR RELATÓRIO" aparecer
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                
                wait = WebDriverWait(self.driver, 30)
                wait.until(EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'GERAR RELATÓRIO')]")))
                logger.info("Botão 'GERAR RELATÓRIO' encontrado - página carregada")
            except Exception as e:
                logger.warning(f"Botão 'GERAR RELATÓRIO' não encontrado: {e}")
                # Continuar mesmo assim
            
            # Verificar se chegou na página correta
            if 'relatorio' in self.driver.current_url.lower() or 'report' in self.driver.current_url.lower() or 'pedidos' in self.driver.current_url.lower():
                logger.info("Página do relatório carregada com sucesso")
                return True
            else:
                logger.warning("Pode não ter chegado na página do relatório")
                return True  # Continuar mesmo assim
                
        except Exception as e:
            logger.error(f"Erro ao navegar para relatório: {e}")
            return False
    
    async def _verificar_segunda_autenticacao(self, config_relatorio: Dict) -> bool:
        """
        Verifica se é necessária uma segunda autenticação
        
        Args:
            config_relatorio: Configuração do relatório
            
        Returns:
            bool: True se segunda autenticação é necessária
        """
        try:
            # Verificar se há campos de login na página
            seletores_login = [
                "input[type='email']",
                "input[type='text'][placeholder*='email']",
                "input[type='text'][placeholder*='Email']",
                "input[name='username']",
                "input[name='email']",
                "input[type='password']"
            ]
            
            for seletor in seletores_login:
                try:
                    elemento = self.driver.find_element(By.CSS_SELECTOR, seletor)
                    if elemento.is_displayed():
                        logger.info(f"Segunda autenticação detectada - campo encontrado: {seletor}")
                        return True
                except Exception:
                    continue
            
            # Verificar se há botões de login
            botoes_login = [
                "//button[contains(text(), 'Entrar')]",
                "//button[contains(text(), 'Login')]",
                "//button[contains(text(), 'Sign In')]",
                "//button[@type='submit']"
            ]
            
            for seletor in botoes_login:
                try:
                    elemento = self.driver.find_element(By.XPATH, seletor)
                    if elemento.is_displayed():
                        logger.info(f"Segunda autenticação detectada - botão encontrado: {seletor}")
                        return True
                except Exception:
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Erro ao verificar segunda autenticação: {e}")
            return False
    
    async def _processar_segunda_autenticacao(self, config_relatorio: Dict) -> bool:
        """
        Processa a segunda autenticação (email + senha + MFA)
        
        Args:
            config_relatorio: Configuração do relatório
            
        Returns:
            bool: True se autenticação foi bem-sucedida
        """
        try:
            logger.info("Iniciando segunda autenticação...")
            
            # 1. Preencher email
            seletores_email = [
                "input[type='email']",
                "input[type='text'][placeholder*='email']",
                "input[type='text'][placeholder*='Email']",
                "input[name='username']",
                "input[name='email']"
            ]
            
            campo_email = None
            seletor_email_usado = None
            for seletor in seletores_email:
                try:
                    campo_email = self.driver.find_element(By.CSS_SELECTOR, seletor)
                    if campo_email.is_displayed():
                        seletor_email_usado = seletor
                        break
                except Exception:
                    continue
            
            if campo_email:
                logger.info("Preenchendo email na segunda autenticação...")
                
                # Aguardar campo ficar interativo
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                
                wait = WebDriverWait(self.driver, 15)
                campo_email = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, seletor_email_usado)))
                
                campo_email.click()
                await asyncio.sleep(2)
                campo_email.clear()
                await asyncio.sleep(1)
                campo_email.send_keys(config_relatorio.get('username'))
                await asyncio.sleep(3)
            else:
                logger.warning("Campo de email não encontrado na segunda autenticação")
            
            # 2. Preencher senha
            try:
                campo_senha = self.driver.find_element(By.CSS_SELECTOR, "input[type='password']")
                if campo_senha.is_displayed():
                    logger.info("Preenchendo senha na segunda autenticação...")
                    campo_senha.click()
                    await asyncio.sleep(1)
                    campo_senha.clear()
                    campo_senha.send_keys(config_relatorio.get('password'))
                    await asyncio.sleep(2)
                else:
                    logger.warning("Campo de senha não encontrado na segunda autenticação")
            except Exception as e:
                logger.warning(f"Erro ao preencher senha: {e}")
            
            # 3. Clicar em entrar/login
            botoes_login = [
                "//button[contains(text(), 'Entrar')]",
                "//button[contains(text(), 'Login')]",
                "//button[contains(text(), 'Sign In')]",
                "//button[@type='submit']"
            ]
            
            for seletor in botoes_login:
                try:
                    botao = self.driver.find_element(By.XPATH, seletor)
                    if botao.is_displayed() and botao.is_enabled():
                        logger.info("Clicando no botão de login da segunda autenticação...")
                        botao.click()
                        break
                except Exception:
                    continue
            
            await asyncio.sleep(5)
            
            # 4. Verificar se MFA é necessário
            if config_relatorio.get('pausa_para_mfa') and not self.headless:
                logger.info("Aguardando confirmação manual do MFA...")
                logger.info("Complete a autenticação no dispositivo móvel e pressione ENTER...")
                input("Pressione ENTER após concluir a autenticação MFA...")
            
            # 5. Aguardar redirecionamento
            logger.info("Aguardando processamento da segunda autenticação...")
            await asyncio.sleep(10)
            
            logger.info("Segunda autenticação processada com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro na segunda autenticação: {e}")
            return False
    
    async def configurar_filtros_relatorio(self, config_relatorio: Dict) -> bool:
        """
        Configura filtros do relatório (data, período, etc.)
        
        Args:
            config_relatorio: Configuração com filtros
        """
        try:
            if 'filtros' not in config_relatorio:
                logger.info("Nenhum filtro configurado")
                return True
            
            logger.info("Configurando filtros do relatório...")
            filtros = config_relatorio['filtros']
            
            # Filtro de data (mais comum)
            if 'data_inicio' in filtros:
                try:
                    # Tentar diferentes seletores para campo de data inicial
                    seletores_data_inicio = [
                        f"input[name='{filtros['campo_data_inicio']}']",
                        f"input[id='{filtros['campo_data_inicio']}']",
                        f"input[placeholder*='{filtros['campo_data_inicio']}']",
                        "input[placeholder*='Data inicial']",
                        "input[type='date']"
                    ]
                    
                    data_inicio_field = None
                    for seletor in seletores_data_inicio:
                        try:
                            data_inicio_field = self.driver.find_element(By.CSS_SELECTOR, seletor)
                            break
                        except Exception:
                            continue
                    
                    if data_inicio_field:
                        data_inicio_field.clear()
                        data_inicio_field.send_keys(filtros['data_inicio'])
                        logger.info(f"Data início configurada: {filtros['data_inicio']}")
                    else:
                        logger.warning("Campo de data inicial não encontrado")
                except Exception as e:
                    logger.warning(f"Erro ao configurar data inicial: {e}")
            
            if 'data_fim' in filtros:
                try:
                    # Tentar diferentes seletores para campo de data final
                    seletores_data_fim = [
                        f"input[name='{filtros['campo_data_fim']}']",
                        f"input[id='{filtros['campo_data_fim']}']",
                        f"input[placeholder*='{filtros['campo_data_fim']}']",
                        "input[placeholder*='Data final']",
                        "input[type='date']"
                    ]
                    
                    data_fim_field = None
                    for seletor in seletores_data_fim:
                        try:
                            data_fim_field = self.driver.find_element(By.CSS_SELECTOR, seletor)
                            break
                        except Exception:
                            continue
                    
                    if data_fim_field:
                        data_fim_field.clear()
                        data_fim_field.send_keys(filtros['data_fim'])
                        logger.info(f"Data fim configurada: {filtros['data_fim']}")
                    else:
                        logger.warning("Campo de data final não encontrado")
                except Exception as e:
                    logger.warning(f"Erro ao configurar data final: {e}")
            
            # Outros filtros
            for campo, valor in filtros.items():
                if campo.startswith('filtro_'):
                    try:
                        campo_element = self.driver.find_element(By.NAME, campo)
                        campo_element.clear()
                        campo_element.send_keys(valor)
                        logger.info(f"Filtro {campo} configurado: {valor}")
                    except:
                        logger.warning(f"Campo {campo} não encontrado")
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao configurar filtros: {e}")
            return False
    
    async def baixar_arquivo_relatorio(self, config_relatorio: Dict) -> Optional[str]:
        """
        Baixa arquivo do relatório (CSV ou Excel)
        
        Args:
            config_relatorio: Configuração com tipo de arquivo e seletores
        """
        try:
            logger.info("Iniciando download do arquivo...")
            
            # Limpar downloads anteriores
            arquivos_anteriores = glob.glob(os.path.join(self.download_path, "*"))
            for arquivo in arquivos_anteriores:
                try:
                    os.remove(arquivo)
                except:
                    pass
            
            # 1. Clicar no botão "GERAR RELATÓRIO"
            seletor_botao = config_relatorio.get('seletor_botao_download', '//button[contains(text(), "GERAR RELATÓRIO")]')
            try:
                botao_gerar = self.driver.find_element(By.XPATH, seletor_botao)
                botao_gerar.click()
                logger.info("Botão 'GERAR RELATÓRIO' clicado")
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Erro ao clicar no botão GERAR RELATÓRIO: {e}")
                return None
            
            # 2. Aguardar modal de exportação aparecer
            logger.info("Aguardando modal de exportação...")
            await asyncio.sleep(3)
            
            # 3. Selecionar formato no dropdown
            tipo_arquivo = config_relatorio.get('tipo_arquivo', 'csv')
            try:
                # Procurar dropdown de formato
                dropdown_seletores = [
                    "//select[contains(@label, 'Gerar relatório como')]",
                    "//select[contains(@name, 'formato')]",
                    "//select[contains(@id, 'formato')]",
                    "//select"
                ]
                
                dropdown_encontrado = False
                for seletor in dropdown_seletores:
                    try:
                        dropdown = self.driver.find_element(By.XPATH, seletor)
                        from selenium.webdriver.support.ui import Select
                        select = Select(dropdown)
                        
                        if tipo_arquivo.upper() == 'CSV':
                            select.select_by_visible_text('CSV')
                        elif tipo_arquivo.upper() == 'EXCEL':
                            select.select_by_visible_text('EXCEL')
                        else:
                            select.select_by_index(0)  # Selecionar primeira opção
                        
                        logger.info(f"Formato {tipo_arquivo.upper()} selecionado no dropdown")
                        dropdown_encontrado = True
                        break
                    except Exception:
                        continue
                
                if not dropdown_encontrado:
                    logger.warning("Dropdown de formato não encontrado, continuando...")
                
            except Exception as e:
                logger.warning(f"Erro ao selecionar formato: {e}")
            
            # 4. Clicar no botão EXPORTAR
            try:
                botao_exportar_seletores = [
                    "//button[contains(text(), 'EXPORTAR')]",
                    "//button[contains(text(), 'Exportar')]",
                    "//button[contains(text(), 'Download')]",
                    "//button[@type='submit']"
                ]
                
                botao_exportar_encontrado = False
                for seletor in botao_exportar_seletores:
                    try:
                        botao_exportar = self.driver.find_element(By.XPATH, seletor)
                        botao_exportar.click()
                        logger.info("Botão EXPORTAR clicado")
                        botao_exportar_encontrado = True
                        break
                    except Exception:
                        continue
                
                if not botao_exportar_encontrado:
                    logger.error("Botão EXPORTAR não encontrado")
                    return None
                
            except Exception as e:
                logger.error(f"Erro ao clicar no botão EXPORTAR: {e}")
                return None
            
            # 5. Aguardar download
            logger.info("Aguardando download...")
            await asyncio.sleep(10)  # Aumentar tempo de espera
            
            # 6. Verificar se arquivo foi baixado
            arquivos_baixados = glob.glob(os.path.join(self.download_path, "*"))
            if arquivos_baixados:
                arquivo_baixado = max(arquivos_baixados, key=os.path.getctime)
                logger.info(f"Arquivo baixado: {arquivo_baixado}")
                return arquivo_baixado
            else:
                logger.error("Nenhum arquivo foi baixado")
                return None
                
        except Exception as e:
            logger.error(f"Erro no download: {e}")
            return None
    
    async def extrair_dados_tela(self, config_relatorio: Dict) -> pd.DataFrame:
        """
        Extrai dados diretamente da tela (fallback se download falhar)
        
        Args:
            config_relatorio: Configuração com seletores da tabela
        """
        try:
            logger.info("Extraindo dados da tela...")
            
            # Aguardar tabela carregar
            if 'aguardar_elemento' in config_relatorio:
                wait = WebDriverWait(self.driver, 30)
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, config_relatorio['aguardar_elemento'])))
            
            # Encontrar tabela
            tabela = self.driver.find_element(By.CSS_SELECTOR, config_relatorio['tabela_selector'])
            
            # Extrair cabeçalhos
            cabecalhos = []
            for th in tabela.find_elements(By.TAG_NAME, "th"):
                cabecalhos.append(th.text.strip())
            
            # Extrair linhas de dados
            dados = []
            for tr in tabela.find_elements(By.TAG_NAME, "tr")[1:]:  # Pular cabeçalho
                linha = []
                for td in tr.find_elements(By.TAG_NAME, "td"):
                    linha.append(td.text.strip())
                if linha:  # Só adicionar linhas não vazias
                    dados.append(linha)
            
            # Converter para DataFrame
            df = pd.DataFrame(dados, columns=cabecalhos)
            
            logger.info(f"Dados extraídos da tela: {len(df)} registros")
            return df
            
        except Exception as e:
            logger.error(f"Erro na extração da tela: {e}")
            return pd.DataFrame()
    
    def processar_arquivo_baixado(self, caminho_arquivo: str, config_relatorio: Dict) -> pd.DataFrame:
        """
        Processa arquivo baixado (CSV ou Excel)
        
        Args:
            caminho_arquivo: Caminho do arquivo baixado
            config_relatorio: Configuração de processamento
        """
        try:
            logger.info(f"Processando arquivo: {caminho_arquivo}")
            
            # Determinar tipo de arquivo
            extensao = os.path.splitext(caminho_arquivo)[1].lower()
            
            if extensao == '.csv':
                separador = config_relatorio.get('separador_csv', ',')
                encoding = config_relatorio.get('encoding', 'utf-8')
                df = pd.read_csv(caminho_arquivo, sep=separador, encoding=encoding)
            elif extensao in ['.xlsx', '.xls']:
                df = pd.read_excel(caminho_arquivo)
            else:
                logger.error(f"Formato de arquivo não suportado: {extensao}")
                return pd.DataFrame()
            
            # Processar dados
            df = self.processar_dados_relatorio(df, config_relatorio)
            
            logger.info(f"Arquivo processado: {len(df)} registros")
            return df
            
        except Exception as e:
            logger.error(f"Erro ao processar arquivo: {e}")
            return pd.DataFrame()
    
    def processar_dados_relatorio(self, df: pd.DataFrame, config: Dict) -> pd.DataFrame:
        """
        Processa e padroniza dados do relatório
        
        Args:
            df: DataFrame com dados brutos
            config: Configuração do processamento
        """
        if df.empty:
            return df
        
        # Adicionar colunas padrão
        df['fonte'] = config.get('nome_fonte', 'relatorio_download')
        df['processado_em'] = datetime.now()
        df['data_coleta'] = date.today()
        
        # Mapear colunas se especificado
        if 'mapeamento_colunas' in config:
            mapeamento = config['mapeamento_colunas']
            df = df.rename(columns=mapeamento)
        
        # Filtrar dados se especificado
        if 'filtros_dados' in config:
            for campo, valor in config['filtros_dados'].items():
                if campo in df.columns:
                    df = df[df[campo] == valor]
        
        # Converter tipos de dados
        if 'tipos_dados' in config:
            for campo, tipo in config['tipos_dados'].items():
                if campo in df.columns:
                    try:
                        if tipo == 'datetime':
                            df[campo] = pd.to_datetime(df[campo], errors='coerce')
                        elif tipo == 'numeric':
                            df[campo] = pd.to_numeric(df[campo], errors='coerce')
                        else:
                            df[campo] = df[campo].astype(tipo)
                    except Exception as e:
                        logger.warning(f"Erro ao converter {campo} para {tipo}: {e}")
        
        return df
    
    async def coletar_dados_completos(self, config_relatorio: Dict) -> pd.DataFrame:
        """
        Coleta dados completos do relatório (download + fallback para tela)
        
        Args:
            config_relatorio: Configuração completa do relatório
        """
        try:
            # 1. Configurar WebDriver
            await self.configurar_webdriver_download()
            
            # 2. Fazer login
            if not await self.fazer_login_sistema(config_relatorio):
                return pd.DataFrame()
            
            # 3. Navegar para relatório
            if not await self.navegar_para_relatorio(config_relatorio):
                return pd.DataFrame()
            
            # 4. Configurar filtros
            await self.configurar_filtros_relatorio(config_relatorio)
            
            # 5. Tentar baixar arquivo
            arquivo_baixado = await self.baixar_arquivo_relatorio(config_relatorio)
            
            if arquivo_baixado:
                # Processar arquivo baixado
                df = self.processar_arquivo_baixado(arquivo_baixado, config_relatorio)
                if not df.empty:
                    logger.info("Dados coletados via download de arquivo")
                    return df
            
            # 6. Fallback: extrair da tela
            logger.info("Tentando extrair dados da tela como fallback...")
            df = await self.extrair_dados_tela(config_relatorio)
            
            return df
            
        except Exception as e:
            logger.error(f"Erro na coleta completa: {e}")
            return pd.DataFrame()
        finally:
            if self.driver:
                self.driver.quit()

# Funções de integração com o sistema atual
def processar_dados_relatorio_download(df: pd.DataFrame) -> pd.DataFrame:
    """
    Processa dados de relatório download no padrão do sistema
    """
    if df.empty:
        logger.warning("Nenhum dado para processar - Relatório Download")
        return pd.DataFrame()
    
    # Adicionar coluna de fonte
    df['fonte'] = 'relatorio_download'
    
    # Adicionar timestamp de processamento
    df['processado_em'] = datetime.now()
    
    logger.info(f"Dados processados - Relatório Download: {len(df)} registros")
    return df

async def obter_dados_relatorio_download(config_relatorio: Dict) -> pd.DataFrame:
    """
    Obtém dados de relatório via download automático
    
    Args:
        config_relatorio: Configuração do relatório
    """
    logger.info("Buscando dados via Relatório Download")
    
    client = RelatorioDownloadClient()
    df = await client.coletar_dados_completos(config_relatorio)
    
    return processar_dados_relatorio_download(df)

# Configurações de exemplo para diferentes tipos de relatórios
CONFIGURACOES_EXEMPLO = {
    'relatorio_vendas_download': {
        'nome_fonte': 'sistema_vendas_download',
        'login_url': 'https://sistema.com.br/login',
        'url': 'https://sistema.com.br/relatorios/vendas',
        'username_field': 'email',
        'password_field': 'senha',
        'username': 'usuario@empresa.com',
        'password': 'senha123',
        'tipo_arquivo': 'csv',  # ou 'excel'
        'seletor_botao_download': '#btn-download-csv',
        'separador_csv': ';',
        'encoding': 'utf-8',
        'filtros': {
            'data_inicio': '2024-01-01',
            'data_fim': '2024-12-31',
            'campo_data_inicio': 'data_inicio',
            'campo_data_fim': 'data_fim'
        },
        'mapeamento_colunas': {
            'id_venda': 'ID_Venda',
            'data_venda': 'Data_Venda',
            'valor': 'Valor',
            'cliente': 'Cliente'
        },
        'tipos_dados': {
            'ID_Venda': 'int64',
            'Data_Venda': 'datetime',
            'Valor': 'numeric'
        },
        # Fallback para extração da tela
        'tabela_selector': '#tabela-vendas',
        'aguardar_elemento': '#tabela-vendas tbody tr'
    }
}

if __name__ == "__main__":
    # Teste da coleta de relatórios
    async def test_relatorio_download():
        print("=== Testando Coleta de Relatórios com Download ===")
        
        # Exemplo de uso
        config = CONFIGURACOES_EXEMPLO['relatorio_vendas_download']
        
        try:
            df = await obter_dados_relatorio_download(config)
            
            print(f"Registros encontrados: {len(df)}")
            
            if not df.empty:
                print("\nColunas:", list(df.columns))
                print(df.head())
            
        except Exception as e:
            print(f"Erro no teste: {str(e)}")
    
    asyncio.run(test_relatorio_download())
