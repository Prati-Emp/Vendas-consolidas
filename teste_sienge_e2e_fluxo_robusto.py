#!/usr/bin/env python3
"""
Fluxo E2E robusto Sienge:
1) Abrir primeira página e clicar "Entrar com Sienge ID" (varrendo iframes)
2) Na página de contas, clicar na conta já "Conectado" (ou pela env RELATORIO_USERNAME)
3) Se aparecer modal de sessão ativa, clicar em "PROSSEGUIR"
4) Navegar até a URL do relatório e verificar botão "GERAR RELATÓRIO"
"""

import os
import time
from typing import Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from dotenv import load_dotenv
import glob
import pathlib

load_dotenv('config_sienge.env')

LOGIN_URL = os.environ.get('RELATORIO_LOGIN_URL') or 'https://pratiemp.sienge.com.br/sienge/8/index.html'
RELATORIO_URL = os.environ.get('RELATORIO_URL') or 'https://pratiemp.sienge.com.br/sienge/8/index.html#/suprimentos/compras/pedidos'
USERNAME = os.environ.get('RELATORIO_USERNAME', '')


def build_driver() -> webdriver.Chrome:
	chrome_options = Options()
	chrome_options.add_argument("--no-sandbox")
	chrome_options.add_argument("--disable-dev-shm-usage")
	chrome_options.add_argument("--disable-blink-features=AutomationControlled")
	chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
	chrome_options.add_experimental_option('useAutomationExtension', False)
	# Usar perfil persistente fixo para manter sessão
	perfil_path = os.path.join(os.getcwd(), "chrome_profile_sienge_persistente")
	chrome_options.add_argument(f"--user-data-dir={perfil_path}")
	chrome_options.add_argument("--profile-directory=SiengeProfile")
	# Preferências de download automático
	download_dir = os.path.join(os.getcwd(), "downloads_tmp")
	os.makedirs(download_dir, exist_ok=True)
	prefs = {
		"download.default_directory": download_dir,
		"download.prompt_for_download": False,
		"download.directory_upgrade": True,
		"safebrowsing.enabled": True,
	}
	chrome_options.add_experimental_option("prefs", prefs)
	return webdriver.Chrome(options=chrome_options)


def click_element_robust(driver: webdriver.Chrome, el) -> bool:
	try:
		driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
		time.sleep(0.6)
		try:
			ActionChains(driver).move_to_element(el).pause(0.1).click().perform()
			return True
		except Exception:
			pass
		try:
			el.click()
			return True
		except Exception:
			pass
		try:
			driver.execute_script("arguments[0].click();", el)
			return True
		except Exception:
			return False
	except Exception:
		return False


def click_center_via_js(driver: webdriver.Chrome, el) -> bool:
	"""Dispara eventos JS no centro do elemento para simular clique mesmo com overlays sutis."""
	try:
		script = (
			"const el = arguments[0];\n"
			"const rect = el.getBoundingClientRect();\n"
			"const x = rect.left + rect.width/2;\n"
			"const y = rect.top + rect.height/2;\n"
			"function fire(type){ const evt = new MouseEvent(type,{bubbles:true,cancelable:true,view:window,clientX:x,clientY:y}); el.dispatchEvent(evt);}\n"
			"fire('mousemove'); fire('mousedown'); fire('mouseup'); fire('click'); return true;"
		)
		return bool(driver.execute_script(script, el))
	except Exception:
		return False


def find_element_across_iframes_by_xpath(driver: webdriver.Chrome, wait: WebDriverWait, xpaths) -> Optional[object]:
	"""Procura um elemento por uma lista de XPaths no contexto principal e em iframes visíveis."""
	# contexto principal
	for xp in xpaths:
		try:
			el = wait.until(EC.presence_of_element_located((By.XPATH, xp)))
			if el.is_displayed():
				return el
		except Exception:
			continue
	# iframes
	iframes = driver.find_elements(By.TAG_NAME, 'iframe')
	for iframe in iframes:
		try:
			if not iframe.is_displayed():
				continue
			driver.switch_to.frame(iframe)
			for xp in xpaths:
				try:
					el = wait.until(EC.presence_of_element_located((By.XPATH, xp)))
					if el.is_displayed():
						return el
				except Exception:
					continue
		finally:
			driver.switch_to.default_content()
	return None


def ensure_loaded_with_refresh(driver: webdriver.Chrome, wait: WebDriverWait, attempts: int = 3, context: str = "") -> None:
	"""Tenta garantir que a página carregou; se detectar tela branca/SPA travada ou 404, dá refresh e tenta novamente."""
	for i in range(attempts):
		try:
			wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
			time.sleep(1.2)
			ready = driver.execute_script("return document.readyState")
			inner_text_len = driver.execute_script("return (document.body && document.body.innerText) ? document.body.innerText.trim().length : 0;")
			# Detectar 404
			is_404 = False
			try:
				is_404 = bool(driver.find_elements(By.XPATH, "//*[contains(text(),'404') and (contains(text(),'Voltar') or contains(text(),'início'))]"))
			except Exception:
				is_404 = False
			if ready == 'complete' and inner_text_len > 10 and not is_404:
				return
			print(f"AVISO: Página possivelmente em branco/404 ({context}). Tentativa {i+1}/{attempts}: dando refresh...")
			driver.refresh()
			time.sleep(2.5)
		except TimeoutException:
			print(f"AVISO: Timeout aguardando body ({context}). Refresh {i+1}/{attempts}...")
			driver.refresh()
			time.sleep(2.5)


def dismiss_overlays(driver: webdriver.Chrome):
	"""Fecha overlays comuns que podem bloquear cliques (push notification/ajuda)."""
	try:
		btn_nao = driver.find_elements(By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚÃÕÇ', 'abcdefghijklmnopqrstuvwxyzáéíóúãõç'), 'não, obrigado')]")
		for b in btn_nao:
			if b.is_displayed():
				click_element_robust(driver, b)
				break
	except Exception:
		pass
	try:
		btn_entendi = driver.find_elements(By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚÃÕÇ', 'abcdefghijklmnopqrstuvwxyzáéíóúãõç'), 'entendi')]")
		for b in btn_entendi:
			if b.is_displayed():
				click_element_robust(driver, b)
				break
	except Exception:
		pass


def click_entrar_com_sienge_id(driver: webdriver.Chrome, wait: WebDriverWait) -> bool:
	cands = [
		"//button[@id='btnEntrarComSiengeID']",
		"//*[@id='btnEntrarComSiengeID']",
		"//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚÃÕÇ', 'abcdefghijklmnopqrstuvwxyzáéíóúãõç'), 'entrar com sienge id')]",
		"//*[@role='button' and contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚÃÕÇ', 'abcdefghijklmnopqrstuvwxyzáéíóúãõç'), 'entrar com sienge id')]",
		"//*[@data-gx-automation-id='btnEntrarSiengeId']",
	]
	# contexto principal
	for xp in cands:
		try:
			btn = wait.until(EC.element_to_be_clickable((By.XPATH, xp)))
			if btn.is_displayed():
				print("Botão 'Entrar com Sienge ID' encontrado (principal)")
				return click_element_robust(driver, btn)
		except Exception:
			pass
	# iframes
	iframes = driver.find_elements(By.TAG_NAME, 'iframe')
	for idx, iframe in enumerate(iframes):
		try:
			if not iframe.is_displayed():
				continue
			driver.switch_to.frame(iframe)
			for xp in cands:
				try:
					btn = wait.until(EC.element_to_be_clickable((By.XPATH, xp)))
					if btn.is_displayed():
						print(f"Botão 'Entrar com Sienge ID' encontrado no iframe {idx}")
						ok = click_element_robust(driver, btn)
						driver.switch_to.default_content()
						return ok
				except Exception:
					pass
		finally:
			driver.switch_to.default_content()
	# fallback por texto
	try:
		btns = driver.find_elements(By.XPATH, "//button|//*[@role='button']")
		for b in btns:
			try:
				if not b.is_displayed():
					continue
				t = (b.text or '').strip().lower()
				if 'sienge id' in t:
					print("Botão 'Entrar com Sienge ID' encontrado (fallback texto)")
					return click_element_robust(driver, b)
			except StaleElementReferenceException:
				continue
	except Exception:
		pass
	return False


def choose_connected_account(driver: webdriver.Chrome, wait: WebDriverWait) -> bool:
	# Preferir por 'Conectado'/'Connected'
	variants = [
		"//*[contains(text(), 'Conectado') or contains(text(), 'Connected')]",
		f"//*[@data-account-email='{USERNAME}']",
		f"//div[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{USERNAME.lower()}')]",
	]
	for xp in variants:
		try:
			el = wait.until(EC.element_to_be_clickable((By.XPATH, xp)))
			print("Conta conectada localizada. Clicando...")
			return click_element_robust(driver, el)
		except TimeoutException:
			continue
		except Exception:
			continue
	return False


def click_modal_prosseguir(driver: webdriver.Chrome, wait: WebDriverWait) -> Optional[bool]:
    """Tenta clicar no botão PROSSEGUIR com alta robustez.
    - Busca case-insensitive por texto e por classe
    - Procura no contexto principal e em iframes
    - Tenta clicar por Actions, .click() e JS
    - Usa o link específico do servlet como fallback
    Retorna True se clicou; False se não encontrou; None se erro inesperado.
    """
    xpaths = [
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚÃÕÇ', 'abcdefghijklmnopqrstuvwxyzáéíóúãõç'), 'prosseguir')]",
        "//*[@role='button' and contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚÃÕÇ', 'abcdefghijklmnopqrstuvwxyzáéíóúãõç'), 'prosseguir')]",
        "//button[.//span[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚÃÕÇ', 'abcdefghijklmnopqrstuvwxyzáéíóúãõç'), 'prosseguir')]]",
        "//button[contains(@class,'Button-prim') and contains(., 'PROSSEGUIR')]",
        "//a[contains(@href, 'removerUsuarioLogadoServlet')]",
        "//*[@href='https://pratiemp.sienge.com.br/sienge/removerUsuarioLogadoServlet?acao=S']",
    ]

    end_time = time.time() + 25  # aguarda até 25s o aparecimento
    while time.time() < end_time:
        try:
            el = find_element_across_iframes_by_xpath(driver, wait, xpaths)
            if el and el.is_displayed():
                print("Clicando em PROSSEGUIR...")
                if click_element_robust(driver, el):
                    return True
                # Fallback: tentar enviar ENTER
                try:
                    el.send_keys(Keys.ENTER)
                    time.sleep(0.5)
                    return True
                except Exception:
                    pass
                # Fallback: JS click direto no centro
                try:
                    driver.execute_script("arguments[0].click();", el)
                    time.sleep(0.5)
                    return True
                except Exception:
                    pass
                # Fallback: eventos JS no centro do botão
                if click_center_via_js(driver, el):
                    return True
        except Exception:
            pass
        time.sleep(0.5)

    # Fallback varredura por JS
    try:
        js = (
            "const els = Array.from(document.querySelectorAll('button, [role=\\'button\\']'));\n"
            "for (const el of els) {\n"
            "  const t = (el.textContent||'').toLowerCase();\n"
            "  if (t.includes('prosseguir') && el.offsetParent !== null) { return el; }\n"
            "}\n"
            "return null;"
        )
        el = driver.execute_script(js)
        if el:
            print("Botão PROSSEGUIR encontrado via JS (fallback). Clicando...")
            if click_element_robust(driver, el):
                return True
            if click_center_via_js(driver, el):
                return True
            return False
    except Exception:
        pass

    # Último recurso: navegar diretamente para o servlet
    try:
        print("Tentando navegar diretamente para o servlet de remoção de usuário...")
        servlet_url = "https://pratiemp.sienge.com.br/sienge/removerUsuarioLogadoServlet?acao=S"
        driver.get(servlet_url)
        time.sleep(3)
        print("Navegação direta para servlet executada")
        return True
    except Exception as e:
        print(f"Erro ao navegar para servlet: {e}")
        pass

    # Último recurso: localizar o modal e o botão primário dentro dele
    try:
        modal = find_element_across_iframes_by_xpath(
            driver,
            wait,
            [
                "//div[contains(., 'Bem-vindo!')]/ancestor::div[contains(@class,'modal')][1]",
                "//div[contains(@class,'modal') and .//button[contains(., 'PROSSEGUIR')]]",
            ],
        )
        if modal:
            # procurar botão de classe primária ou maior largura
            try:
                btns = modal.find_elements(By.XPATH, ".//button")
                candidate = None
                max_w = -1
                for b in btns:
                    if not b.is_displayed():
                        continue
                    cls = (b.get_attribute('class') or '').lower()
                    if 'button-prim' in cls:
                        candidate = b
                        break
                    w = b.size.get('width', 0)
                    if w > max_w:
                        max_w = w
                        candidate = b
                if candidate:
                    print("Clicando no botão primário do modal (heurística de classe/tamanho)...")
                    if click_element_robust(driver, candidate):
                        return True
                    if click_center_via_js(driver, candidate):
                        return True
            except Exception:
                pass
    except Exception:
        pass
    return False


def main():
	driver = build_driver()
	wait = WebDriverWait(driver, 20)
	try:
		print("=== Fluxo E2E robusto Sienge ===")
		print(f"Abrindo: {LOGIN_URL}")
		driver.get(LOGIN_URL)
		# Forçar um refresh no primeiro acesso para garantir estado limpo
		time.sleep(1.0)
		driver.refresh()
		ensure_loaded_with_refresh(driver, wait, attempts=3, context="login inicial")
		dismiss_overlays(driver)

		# 1) botão Sienge ID (com tentativas e refresh se necessário)
		ok = click_entrar_com_sienge_id(driver, wait)
		if not ok:
			print("Tentativa 1 falhou. Dando refresh e tentando novamente...")
			driver.refresh()
			ensure_loaded_with_refresh(driver, wait, attempts=2, context="login retry 1")
			dismiss_overlays(driver)
			ok = click_entrar_com_sienge_id(driver, wait)
		if not ok:
			print("Tentativa 2 falhou. Recarregando URL e tentando pela terceira vez...")
			driver.get(LOGIN_URL)
			ensure_loaded_with_refresh(driver, wait, attempts=2, context="login retry 2")
			dismiss_overlays(driver)
			ok = click_entrar_com_sienge_id(driver, wait)
		print(f"Clique 'Entrar com Sienge ID': {'OK' if ok else 'FALHOU'}")
		time.sleep(3)
		print(f"URL após clique: {driver.current_url}")

		# 2) escolher conta
		if 'login.sienge.com.br' in driver.current_url:
			print("Página de contas/login Sienge detectada")
			if choose_connected_account(driver, wait):
				print("Conta conectada clicada com sucesso")
				time.sleep(4)
			else:
				print("AVISO: Não encontrei conta conectada visível. Verifique a página.")

		# 3) modal PROSSEGUIR
		clicked = click_modal_prosseguir(driver, wait)
		if clicked:
			print("PROSSEGUIR clicado com sucesso")
			time.sleep(5)
		elif clicked is False:
			print("Sem modal PROSSEGUIR ou não localizado — seguindo...")
		else:
			print("AVISO: Erro ao tratar modal PROSSEGUIR")

		# 4) ir para relatório
		print(f"Indo para relatório: {RELATORIO_URL}")
		driver.get(RELATORIO_URL)
		# Refresh automático para resolver travamentos do Sienge
		print("Aplicando refresh automático para estabilizar página...")
		time.sleep(3)
		driver.refresh()
		time.sleep(5)
		ensure_loaded_with_refresh(driver, wait, attempts=4, context="relatório")
		dismiss_overlays(driver)
		print(f"URL atual: {driver.current_url}")

		# 5) verificar botão GERAR RELATÓRIO e clicar (inclui busca em iframes)
		# Refresh adicional antes de procurar botão para garantir estabilidade
		print("Aplicando refresh adicional antes de procurar botão GERAR RELATÓRIO...")
		time.sleep(2)
		driver.refresh()
		time.sleep(5)
		dismiss_overlays(driver)
		
		cands_gerar = [
			"//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚÃÕÇ', 'abcdefghijklmnopqrstuvwxyzáéíóúãõç'), 'gerar relatório')]",
			"//button[contains(., 'GERAR RELATÓRIO')]",
			"//*[@role='button' and (contains(., 'GERAR') or contains(., 'Gerar'))]",
			"//button[contains(., 'Gerar relatório')]",
			"//*[contains(@class, 'button') and contains(., 'GERAR')]",
		]
		btn_gerar = find_element_across_iframes_by_xpath(driver, wait, cands_gerar)
		if btn_gerar is None:
			print("AVISO: 'GERAR RELATÓRIO' não localizado. A UI pode ter outro texto.")
			# Tentar busca mais ampla
			try:
				btns = driver.find_elements(By.XPATH, "//button")
				for btn in btns:
					if btn.is_displayed():
						text = (btn.text or '').strip().lower()
						if 'gerar' in text or 'relatório' in text:
							print(f"Botão encontrado por texto: '{btn.text}'")
							btn_gerar = btn
							break
			except Exception:
				pass
		
		if btn_gerar:
			print("Clicando em GERAR RELATÓRIO...")
			click_element_robust(driver, btn_gerar)
			time.sleep(3)
		else:
			print("ERRO: Não foi possível localizar o botão GERAR RELATÓRIO")
			return

		# 6) modal de exportação
		print("Aguardando modal de exportação aparecer...")
			time.sleep(2)

		# Buscar modal de exportação - recriar referência após interação
		print("Recriando referência do modal após interação...")
		modal_xpaths = [
			"//div[contains(@class, 'modal')]",
			"//div[contains(., 'Gerar relatório')]",
			"//div[contains(., 'Selecione o formato')]",
			"//div[contains(., 'exportação')]",
			"//div[contains(@class, 'MuiDialog')]",
			"//div[contains(@class, 'MuiModal')]",
		]
		
		modal = None
		for xpath in modal_xpaths:
			try:
				modal = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
				if modal and modal.is_displayed():
				print("Modal de exportação detectado")
					break
			except Exception:
				continue
		
		if not modal:
			print("AVISO: Modal de exportação não encontrado")
			return
		
		# Buscar dropdown de formato - procurar especificamente pelo placeholder "Gerar relatório como" DENTRO DO MODAL
		print("Procurando dropdown de formato DENTRO DO MODAL...")
		formato_xpaths = [
			".//input[@placeholder='Gerar relatório como']",
			".//input[contains(@placeholder, 'Gerar relatório como')]",
			".//input[contains(@placeholder, 'gerar relatório como')]",
			".//*[@placeholder='Gerar relatório como']",
			".//*[contains(@placeholder, 'Gerar relatório como')]",
			".//*[@role='combobox' and not(contains(@placeholder, 'Pesquise'))]",
			".//div[contains(@class, 'MuiSelect-select')]",
			".//div[contains(@class, 'MuiSelect-outlined')]",
			".//div[contains(@class, 'MuiInputBase-input') and not(contains(@placeholder, 'Pesquise'))]",
			".//select",
			".//select[contains(@class, 'form-control')]",
			".//select[contains(., 'CSV') or contains(., 'Excel')]",
			".//div[contains(@class, 'dropdown')]",
			".//div[contains(@class, 'select')]",
		]
		
		formato_select = None
		for xpath in formato_xpaths:
			try:
				formato_select = modal.find_element(By.XPATH, xpath)
				if formato_select and formato_select.is_displayed():
					print("Dropdown de formato encontrado")
					break
			except Exception:
				continue
		
		# Se não encontrou no modal, buscar especificamente por elementos que NÃO sejam o campo de pesquisa
		if not formato_select:
			print("Buscando dropdown específico (evitando campo de pesquisa)...")
			# Buscar apenas elementos que não sejam o campo de pesquisa do Sienge
			formato_xpaths_especificos = [
				"//input[@placeholder='Gerar relatório como']",
				"//input[contains(@placeholder, 'Gerar relatório como')]",
				"//input[contains(@placeholder, 'gerar relatório como')]",
				"//*[@placeholder='Gerar relatório como']",
				"//*[contains(@placeholder, 'Gerar relatório como')]",
				"//*[@role='combobox' and not(contains(@placeholder, 'Pesquise'))]",
				"//div[contains(@class, 'MuiSelect-select')]",
				"//div[contains(@class, 'MuiSelect-outlined')]",
				"//div[contains(@class, 'MuiInputBase-input') and not(contains(@placeholder, 'Pesquise'))]",
			]
			for xpath in formato_xpaths_especificos:
				try:
					formato_select = driver.find_element(By.XPATH, xpath)
					if formato_select and formato_select.is_displayed():
						placeholder = formato_select.get_attribute('placeholder') or ''
						if 'Pesquise' not in placeholder:
							print(f"Dropdown de formato encontrado na página: {placeholder}")
							break
						else:
							print(f"Campo de pesquisa ignorado: {placeholder}")
							formato_select = None
							continue
				except Exception:
					continue
		
		if formato_select:
			print("Interagindo com dropdown de formato...")
			
			# Verificar se é um dropdown Material-UI customizado
			tag_name = formato_select.tag_name.lower()
			role = formato_select.get_attribute('role')
			classes = formato_select.get_attribute('class') or ''
			placeholder = formato_select.get_attribute('placeholder') or ''
			print(f"Tipo de elemento: {tag_name}, role: {role}, classes: {classes}")
			print(f"Placeholder: {placeholder}")
			
			# Primeiro, clicar no dropdown para abrir as opções
			print("Clicando no dropdown para abrir opções...")
			try:
				# Múltiplas tentativas de clique
				clicked = False
				for attempt in range(3):
					try:
						click_element_robust(driver, formato_select)
						time.sleep(3)  # Aumentar tempo de espera
						print(f"Tentativa {attempt + 1}: Dropdown clicado para abrir opções")
						clicked = True
						break
					except Exception as e:
						print(f"Tentativa {attempt + 1} falhou: {e}")
						time.sleep(2)  # Aumentar tempo entre tentativas
				
				if not clicked:
					print("Tentando clique direto...")
					formato_select.click()
					time.sleep(2)
					print("Clique direto realizado")
				
			except Exception as e:
				print(f"Erro ao clicar no dropdown: {e}")
			
			# Dar Enter diretamente após abrir o dropdown
			print("Pressionando Enter para selecionar CSV...")
			try:
				formato_select.send_keys(Keys.ENTER)
				time.sleep(3)
				print("✅ CSV selecionado com Enter!")
			except Exception as e:
				print(f"Erro ao pressionar Enter: {e}")
			
			# Aguardar um pouco para o dropdown processar a seleção
			print("Aguardando processamento da seleção...")
			time.sleep(3)
		
		if tag_name == 'input':
			print("É um input customizado - tentando digitar CSV")
			try:
				# Limpar o campo e digitar CSV
				formato_select.clear()
				formato_select.send_keys("CSV")
				time.sleep(1)
				print("CSV digitado no campo")
			except Exception as e:
				print(f"Erro ao digitar CSV: {e}")
		else:
			# Tentar selecionar CSV usando Select
					from selenium.webdriver.support.ui import Select
					try:
				select_obj = Select(formato_select)
				# Listar opções disponíveis
				options = select_obj.options
				print(f"Opções disponíveis: {[opt.text for opt in options]}")
				
				# Tentar selecionar CSV
				success = False
				for opt_text in ["CSV", "csv", "Csv"]:
					try:
						select_obj.select_by_visible_text(opt_text)
						print(f"Formato {opt_text} selecionado")
						success = True
						break
					except Exception:
						continue
				
				if not success:
					# Tentar primeira opção
					select_obj.select_by_index(0)
					print("Primeira opção selecionada")
					
			except Exception as e:
				print(f"Erro ao usar Select: {e}")
				# Fallback: tentar clicar diretamente nas opções
				try:
					# Buscar opções CSV
					csv_options = driver.find_elements(By.XPATH, "//option[contains(., 'CSV') or contains(., 'csv')]")
					if csv_options:
						for opt in csv_options:
							if opt.is_displayed():
								click_element_robust(driver, opt)
								print("Opção CSV clicada diretamente")
								break
				except Exception as e2:
					print(f"Erro no fallback: {e2}")
		
		if not formato_select:
			print("AVISO: Dropdown de formato não encontrado")
			# Listar elementos de seleção visíveis para debug
			try:
				selects = driver.find_elements(By.XPATH, "//select | //div[contains(@class, 'dropdown')] | //div[contains(@class, 'select')]")
				print("Elementos de seleção visíveis:")
				for i, sel in enumerate(selects):
					if sel.is_displayed():
						text = (sel.text or '').strip()
						classes = sel.get_attribute('class') or ''
						print(f"  {i+1}: '{text}' (classes: {classes})")
				except Exception:
					pass
		
		# Buscar botão EXPORTAR com estratégias robustas baseadas na análise do DOM
		print("Procurando botão EXPORTAR...")
		
		# Aguardar explicitamente o botão estar habilitado e visível
		print("Aguardando botão EXPORTAR estar habilitado...")
		time.sleep(3)
		
		# Estratégia 1: Buscar especificamente pelo botão EXPORTAR no modal
		exportar_xpaths = [
			# Buscar pelo texto exato "Exportar" (como mostrado no DOM)
			"//button[text()='Exportar']",
			"//button[contains(., 'Exportar')]",
			"//button[contains(., 'EXPORTAR')]",
			# Buscar por classes específicas do Material-UI contained primary
			"//button[contains(@class, 'MuiButton-contained') and contains(@class, 'MuiButton-containedPrimary')]",
			"//button[contains(@class, 'MuiButton-containedPrimary')]",
			# Buscar por botão que não seja o CANCELAR no modal
			"//button[contains(@class, 'MuiButton-contained') and not(contains(., 'CANCELAR')) and not(contains(., 'CANCEL'))]",
			# Fallback: buscar qualquer botão contained no modal
			"//button[contains(@class, 'MuiButton-contained')]",
		]
		
		btn_exportar = None
		for xpath in exportar_xpaths:
			try:
				btn_exportar = modal.find_element(By.XPATH, xpath)
				if btn_exportar and btn_exportar.is_displayed():
					print("Botão EXPORTAR encontrado no modal")
					break
			except Exception:
				continue
		
		# Se encontrou o botão, pular todas as outras estratégias
		if btn_exportar:
			print("✅ Botão EXPORTAR encontrado - prosseguindo com o clique")
		else:
			# Estratégia adicional: buscar no modal por botões e filtrar pelo que não é CANCELAR
			print("Tentando estratégia adicional: buscar botões no modal e filtrar...")
			try:
				btns_modal = modal.find_elements(By.XPATH, ".//button")
				for btn in btns_modal:
					if btn.is_displayed():
						text = (btn.text or '').strip()
						classes = btn.get_attribute('class') or ''
						print(f"  Botão encontrado: '{text}' (classes: {classes[:50]}...)")
						
						# Verificar se é o botão EXPORTAR (não CANCELAR e tem classes contained)
						if (text == 'Exportar' or 
							('MuiButton-contained' in classes and 'CANCELAR' not in text.upper() and 'CANCEL' not in text.upper())):
							print(f"✅ Botão EXPORTAR identificado: '{text}'")
							btn_exportar = btn
							break
			except Exception as e:
				print(f"Erro na estratégia adicional: {e}")
		
		# Estratégia para iframes (conforme sugerido pelo Comet)
		if not btn_exportar:
			print("Buscando botão EXPORTAR em iframes...")
			try:
				iframes = driver.find_elements(By.TAG_NAME, 'iframe')
				for idx, iframe in enumerate(iframes):
					try:
						if not iframe.is_displayed():
							continue
						driver.switch_to.frame(iframe)
						print(f"Verificando iframe {idx}...")
						
						# Buscar botão EXPORTAR no iframe
						for xpath in exportar_xpaths:
							try:
								btn_iframe = driver.find_element(By.XPATH, xpath)
								if btn_iframe and btn_iframe.is_displayed():
									print(f"✅ Botão EXPORTAR encontrado no iframe {idx}")
									btn_exportar = btn_iframe
									break
							except Exception:
								continue
						if btn_exportar:
							break
					finally:
						driver.switch_to.default_content()
			except Exception as e:
				print(f"Erro ao buscar em iframes: {e}")
		
		# Estratégia 2: Buscar por classes Material-UI específicas (apenas se não encontrou)
		if not btn_exportar:
			print("Buscando por classes Material-UI...")
			mui_xpaths = [
				"//button[contains(@class, 'MuiButton-contained')]",
				"//button[contains(@class, 'MuiButton-root') and contains(@class, 'MuiButton-contained')]",
			]
			for xpath in mui_xpaths:
				try:
					btns = modal.find_elements(By.XPATH, xpath)
					for btn in btns:
						if btn.is_displayed():
							text = (btn.text or '').strip().upper()
							if 'EXPORTAR' in text or 'EXPORT' in text:
								print(f"Botão EXPORTAR encontrado por classe MUI: '{btn.text}'")
								btn_exportar = btn
								break
					if btn_exportar:
						break
				except Exception:
					continue
		
		# Estratégia 3: Buscar em toda a página se não encontrou no modal
		if not btn_exportar:
			print("Buscando botão EXPORTAR em toda a página...")
			for xpath in exportar_xpaths:
				try:
					btn_exportar = driver.find_element(By.XPATH, xpath)
					if btn_exportar and btn_exportar.is_displayed():
						print("Botão EXPORTAR encontrado na página")
						break
				except Exception:
					continue
		
		# Estratégia 4: Busca por texto em todos os botões do modal (com recriação de referência)
		if not btn_exportar:
			print("Fazendo busca manual por botões no modal...")
			try:
				# Recriar referência do modal para evitar stale element
				modal_refresh = None
				for xpath in modal_xpaths:
					try:
						modal_refresh = driver.find_element(By.XPATH, xpath)
						if modal_refresh and modal_refresh.is_displayed():
							break
					except Exception:
						continue
				
				if modal_refresh:
					btns = modal_refresh.find_elements(By.XPATH, ".//button")
					print(f"Botões encontrados no modal: {len(btns)}")
					for i, btn in enumerate(btns):
						try:
							if btn.is_displayed():
								text = (btn.text or '').strip().upper()
								classes = btn.get_attribute('class') or ''
								print(f"  Botão {i+1}: '{text}' (classes: {classes})")
								if 'EXPORTAR' in text or 'EXPORT' in text:
									print(f"Botão EXPORTAR encontrado por texto: '{btn.text}'")
									btn_exportar = btn
									break
						except StaleElementReferenceException:
							print(f"  Botão {i+1}: Elemento stale, pulando...")
							continue
				else:
					print("Modal não encontrado para busca de botões")
			except Exception as e:
				print(f"Erro na busca manual no modal: {e}")
		
		# Estratégia 5: Busca específica por botões azuis (primários) no modal
		if not btn_exportar:
			print("Buscando botões primários (azuis) no modal...")
			try:
				# Buscar botões com classes de botão primário
				primario_xpaths = [
					".//button[contains(@class, 'MuiButton-contained')]",
					".//button[contains(@class, 'MuiButton-root') and contains(@class, 'MuiButton-contained')]",
					".//button[contains(@class, 'MuiButton-colorPrimary')]",
				]
				
				for xpath in primario_xpaths:
					try:
						btns = modal.find_elements(By.XPATH, xpath)
						for btn in btns:
							if btn.is_displayed():
								text = (btn.text or '').strip().upper()
								classes = btn.get_attribute('class') or ''
								print(f"  Botão primário: '{text}' (classes: {classes})")
								if 'EXPORTAR' in text or 'EXPORT' in text:
									print(f"Botão EXPORTAR encontrado por classe primária: '{btn.text}'")
									btn_exportar = btn
									break
						if btn_exportar:
							break
					except Exception:
						continue
			except Exception as e:
				print(f"Erro na busca por botões primários: {e}")
		
		# Estratégia 6: Busca por texto em todos os botões da página
		if not btn_exportar:
			print("Fazendo busca manual por botões na página...")
			try:
				btns = driver.find_elements(By.XPATH, "//button")
				for btn in btns:
					if btn.is_displayed():
						text = (btn.text or '').strip().upper()
						if 'EXPORTAR' in text or 'EXPORT' in text:
							print(f"Botão encontrado por texto: '{btn.text}'")
							btn_exportar = btn
							break
			except Exception as e:
				print(f"Erro na busca manual: {e}")
		
		# Estratégia 7: Busca por botões azuis (primários) em toda a página
		if not btn_exportar:
			print("Buscando botões azuis (primários) em toda a página...")
			try:
				primario_xpaths = [
					"//button[contains(@class, 'MuiButton-contained')]",
					"//button[contains(@class, 'MuiButton-root') and contains(@class, 'MuiButton-contained')]",
					"//button[contains(@class, 'MuiButton-colorPrimary')]",
				]
				
				for xpath in primario_xpaths:
					try:
						btns = driver.find_elements(By.XPATH, xpath)
						for btn in btns:
							if btn.is_displayed():
								text = (btn.text or '').strip().upper()
								classes = btn.get_attribute('class') or ''
								print(f"  Botão primário: '{text}' (classes: {classes})")
								if 'EXPORTAR' in text or 'EXPORT' in text:
									print(f"Botão EXPORTAR encontrado por classe primária: '{btn.text}'")
									btn_exportar = btn
									break
						if btn_exportar:
							break
					except Exception:
						continue
			except Exception as e:
				print(f"Erro na busca por botões primários: {e}")
		
		# Estratégia 4: Buscar por classe CSS comum de botões primários
		if not btn_exportar:
			print("Buscando por classes CSS de botões primários...")
			css_selectors = [
				"button.btn-primary",
				"button[class*='primary']",
				"button[class*='export']",
				"button[class*='submit']",
			]
			for selector in css_selectors:
				try:
					btn_exportar = driver.find_element(By.CSS_SELECTOR, selector)
					if btn_exportar and btn_exportar.is_displayed():
						print(f"Botão encontrado por CSS: {selector}")
						break
				except Exception:
					continue
		
		if btn_exportar:
			print("Clicando em EXPORTAR...")
			
			# Aguardar explicitamente o botão estar habilitado e visível
			print("Aguardando botão estar habilitado...")
			try:
				wait_exportar = WebDriverWait(driver, 10)
				btn_exportar = wait_exportar.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Exportar') or contains(., 'EXPORTAR')]")))
				print("✅ Botão EXPORTAR está habilitado e pronto para clique")
			except TimeoutException:
				print("⚠️ Botão não ficou habilitado no tempo esperado, tentando mesmo assim...")
			
			# Fechar overlays antes do clique (conforme sugerido)
			dismiss_overlays(driver)
			time.sleep(1)
			
			# Tentar múltiplas formas de clique com mais robustez
			success = False
			attempts = [
				("Clique robusto", lambda: click_element_robust(driver, btn_exportar)),
				("Clique direto", lambda: btn_exportar.click()),
				("Clique JavaScript", lambda: driver.execute_script("arguments[0].click();", btn_exportar)),
				("Clique ActionChains", lambda: ActionChains(driver).move_to_element(btn_exportar).click().perform()),
				("Clique via JS com scroll", lambda: driver.execute_script("arguments[0].scrollIntoView(); arguments[0].click();", btn_exportar)),
			]
			
			for attempt_name, attempt_func in attempts:
				try:
					print(f"Tentando {attempt_name}...")
					attempt_func()
					time.sleep(3)  # Aguardar mais tempo após cada tentativa
					success = True
					print(f"✅ {attempt_name} bem-sucedido!")
					break
			except Exception as e:
					print(f"❌ {attempt_name} falhou: {e}")
					continue
			
			if success:
				print("✅ Botão EXPORTAR clicado com sucesso!")
				# Aguardar mais tempo para o download iniciar
				print("Aguardando download iniciar...")
				time.sleep(5)
			else:
				print("❌ AVISO: Não foi possível clicar no botão EXPORTAR")
		else:
			print("ERRO: Botão EXPORTAR não encontrado em nenhuma estratégia")
			# Listar todos os botões visíveis para debug
			try:
				btns = driver.find_elements(By.XPATH, "//button")
				print("Botões visíveis na página:")
				for i, btn in enumerate(btns):
					if btn.is_displayed():
						text = (btn.text or '').strip()
						classes = btn.get_attribute('class') or ''
						print(f"  {i+1}: '{text}' (classes: {classes})")
			except Exception:
				pass
			return

		# 7) aguardar download com tempo aumentado
			download_dir = os.path.join(os.getcwd(), "downloads_tmp")
			ext = os.environ.get('RELATORIO_TIPO_ARQUIVO', 'csv').lower()
			print("Aguardando download de arquivo ." + ext)
		
		# Aguardar um pouco mais após clicar no botão EXPORTAR
		print("Aguardando processamento do download...")
		time.sleep(10)
		
			start = time.time()
			found_file = None
		download_timeout = 120  # Aumentar para 2 minutos
		
		while time.time() - start < download_timeout:
			# Verificar arquivos .crdownload (download em progresso)
			crdownload_files = glob.glob(os.path.join(download_dir, "*.crdownload"))
			if crdownload_files:
				print(f"Download em progresso: {len(crdownload_files)} arquivo(s) .crdownload")
			
			# Verificar arquivos completos
				cands = glob.glob(os.path.join(download_dir, f"*.{ext}"))
				# Ignorar .crdownload
				cands = [p for p in cands if not p.endswith('.crdownload')]
			
				if cands:
					# pegar o mais recente
					cands.sort(key=lambda p: os.path.getmtime(p), reverse=True)
					found_file = cands[0]
				file_size = os.path.getsize(found_file)
				print(f"Arquivo encontrado: {pathlib.Path(found_file).name} ({file_size} bytes)")
					break
			
			# Verificar se há arquivos com nomes diferentes (sienge pode usar nomes específicos)
			all_files = glob.glob(os.path.join(download_dir, "*"))
			recent_files = [f for f in all_files if not f.endswith('.crdownload') and os.path.getmtime(f) > start - 10]
			if recent_files:
				print(f"Arquivos recentes encontrados: {[os.path.basename(f) for f in recent_files]}")
			
			time.sleep(3)  # Verificar a cada 3 segundos
		
			if found_file:
			print("✅ Download concluído com sucesso!")
			print(f"Arquivo: {pathlib.Path(found_file).name}")
			print(f"Tamanho: {os.path.getsize(found_file)} bytes")
			print(f"Caminho: {found_file}")
		else:
			print("❌ AVISO: Nenhum arquivo baixado detectado em 120s")
			# Listar arquivos no diretório para debug
			all_files = glob.glob(os.path.join(download_dir, "*"))
			if all_files:
				print("Arquivos no diretório de download:")
				for f in all_files:
					print(f"  - {os.path.basename(f)} ({os.path.getsize(f)} bytes)")
			else:
				print("Diretório de download vazio")

		# manter para inspeção
		print("Janela ficará aberta 90s para inspeção...")
		time.sleep(90)
	finally:
		driver.quit()

if __name__ == "__main__":
	main()
