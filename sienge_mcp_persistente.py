#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Solução MCP com Sessão Persistente (Playwright via Node)
- Fluxo completo em MCP (login + navegação + filtros + paginação + exportação + download)
- Ajuste final robusto: combobox MUI ("Gerar relatório como" = CSV)
- Novas etapas: preencher datas, CONSULTAR, "Linhas por página: Todas"
"""

import os
import time
import subprocess
import glob
import pathlib
from dotenv import load_dotenv

# ====== CONFIG (.env) ======
# START_DATE_BR=01/01/2020    # opcional (dd/mm/aaaa)
# HEAVY_WAIT_MS=20000         # opcional (esperas longas: consultar/todas)
load_dotenv('config_sienge.env')

LOGIN_URL = os.environ.get('LOGIN_URL', 'https://pratiemp.sienge.com.br/sienge/8/index.html')
RELATORIO_URL = os.environ.get('RELATORIO_URL', 'https://pratiemp.sienge.com.br/sienge/8/index.html#/suprimentos/compras/pedidos-de-compra/relatorios/relacao-pedidos-compra')
DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads_tmp")

class SiengeMCPPersistente:
    def __init__(self):
        self.download_dir = DOWNLOAD_DIR
        os.makedirs(self.download_dir, exist_ok=True)

    def executar_automacao_mcp_completa(self) -> bool:
        print("📥 Executando automação completa com MCP...")

        script_js = f"""
// Verificar se o Playwright está disponível
let playwright;
try {{
  playwright = require('playwright');
  console.log('✅ Playwright carregado com sucesso');
}} catch (error) {{
  console.error('❌ Erro ao carregar Playwright:', error.message);
  console.log('📋 Tentando carregar playwright-core...');
  try {{
    playwright = require('playwright-core');
    console.log('✅ playwright-core carregado');
  }} catch (error2) {{
    console.error('❌ Erro ao carregar playwright-core:', error2.message);
    process.exit(1);
  }}
}}

const {{ chromium }} = playwright;
const path = require('path');
const fs = require('fs');

async function findInAllFrames(page, locatorFactory) {{
  try {{
    const rootResult = await locatorFactory(page);
    if (rootResult) {{
      console.log('🔎 Elemento localizado no contexto principal:', typeof page.url === 'function' ? page.url() : 'page');
      return rootResult;
    }}
  }} catch (err) {{}}

  const frames = page.frames ? page.frames().filter(f => f !== page.mainFrame?.()) : [];
  if (frames.length) {{
    console.log('🧩 Frames detectados:', frames.map(f => {{ try {{ return f.url(); }} catch {{ return '[sem URL]'; }} }}).slice(0, 10));
  }}

  for (const frame of frames) {{
    try {{
      const result = await locatorFactory(frame);
      if (result) {{
        let frameUrl = '[frame sem URL]';
        try {{ frameUrl = frame.url(); }} catch {{}}
        console.log('🔎 Elemento localizado no frame:', frameUrl);
        return result;
      }}
    }} catch (err) {{}}
  }}

  return null;
}}

async function automacaoCompletaSienge() {{
  console.log('🚀 Iniciando automação completa com MCP...');

  const userDataDir = path.resolve('chrome_profile_sienge_persistente');
  const downloadPath = path.resolve('{self.download_dir}');
  if (!fs.existsSync(downloadPath)) fs.mkdirSync(downloadPath, {{ recursive: true }});

  const isCI = process.env.CI === 'true' || process.env.GITHUB_ACTIONS === 'true' || process.env.HEADLESS === 'true';
  const zoomFactor = isCI ? 0.67 : 1;

  const context = await chromium.launchPersistentContext(userDataDir, {{
    headless: isCI,
    viewport: {{ width: 1920, height: 1080 }},
    acceptDownloads: true,
    args: [
      '--no-sandbox',
      '--disable-dev-shm-usage',
      '--profile-directory=SiengeProfile',
      '--force-device-scale-factor=1',
      '--disable-zoom',
      '--disable-extensions',
      '--disable-plugins',
      '--disable-web-security',
      '--disable-background-timer-throttling',
      '--disable-backgrounding-occluded-windows',
      '--disable-renderer-backgrounding',
      '--disable-prompt-on-repost',
      '--disable-sync',
      '--disable-translate',
      '--enable-automation',
      '--password-store=basic',
      '--use-mock-keychain',
      '--disable-blink-features=AutomationControlled'
    ]
  }});

  try {{ await context.setDefaultDownloadOptions({{ downloadsPath: downloadPath }}); }} catch {{ }}

  const page = await context.newPage();

  try {{
    // ========= Navegação e preparação =========
    await page.setViewportSize({{ width: 1920, height: 1080 }});
    console.log('📱 Navegando para o relatório...');
    await page.goto('{RELATORIO_URL}', {{ waitUntil: 'domcontentloaded', timeout: 120000 }});
    await page.waitForTimeout(isCI ? 10000 : 8000);

    // Ajustes de zoom/viewport para evitar clipping
    await page.evaluate((factor) => {{
      document.body.style.zoom = String(factor);
      document.body.style.transform = `scale(${{factor}})`;
      document.body.style.transformOrigin = 'top left';
    }}, zoomFactor);

    await page.waitForTimeout(isCI ? 2500 : 1500);
    await page.reload({{ waitUntil: 'networkidle', timeout: 120000 }});
    await page.waitForTimeout(isCI ? 6000 : 4000);

    console.log('🔎 Checando render do relatório...');
    const anchorFound = await Promise.race([
      page.getByText(/Relação de pedidos/i).waitFor({ timeout: 12000 }).then(() => true).catch(() => false),
      page.getByRole('button', { name: /CONSULTAR/i }).waitFor({ timeout: 12000 }).then(() => true).catch(() => false)
    ]);

    if (!anchorFound) {
      const frameCandidates = page.frames ? page.frames().filter(f => /sienge/i.test((() => { try { return f.url(); } catch { return ''; } })())) : [];
      if (frameCandidates.length) {
        console.log('🎯 Focando frame Sienge:', frameCandidates[0].url());
      } else {
        console.log('⚠️ Anchor do relatório não encontrada; salvando evidência.');
        await page.screenshot({ path: 'debug_sem_anchor.png', fullPage: true });
      }
    }

    // ========= Detecta se está em tela de login =========
    const isLoginPage = await page.evaluate(() => {{
      const url = location.href;
      const txt = document.body.innerText.toLowerCase();
      return url.includes('login.sienge.com.br') ||
             txt.includes('entrar com sienge id') ||
             txt.includes('escolha sua conta') ||
             txt.includes('prosseguir');
    }});

    if (isLoginPage) {{
      console.log('🔐 Fluxo de login detectado...');
      const btnSienge = await Promise.race([
        page.waitForSelector('button:has-text("Entrar com Sienge ID")', {{ timeout: 8000 }}).catch(() => null),
        page.waitForSelector('button:has-text("ENTRAR COM SIENGE ID")', {{ timeout: 8000 }}).catch(() => null)
      ]);
      if (btnSienge) await btnSienge.click();

      await page.waitForTimeout(4000);

      const conta = await Promise.race([
        page.waitForSelector('button:has-text("Conectado")', {{ timeout: 8000 }}).catch(() => null),
        page.waitForSelector('div:has-text("odair.santos@grupoprati.com")', {{ timeout: 8000 }}).catch(() => null)
      ]);
      if (conta) await conta.click();

      await page.waitForTimeout(4000);

      const prosseguir = await Promise.race([
        page.waitForSelector('button:has-text("PROSSEGUIR")', {{ timeout: 8000 }}).catch(() => null),
        page.waitForSelector('button:has-text("Prosseguir")', {{ timeout: 8000 }}).catch(() => null)
      ]);
      if (prosseguir) await prosseguir.click();

      await page.waitForTimeout(8000);
      await page.goto('{RELATORIO_URL}', {{ waitUntil: 'networkidle' }});
      await page.waitForTimeout(4000);
    }}

    // ========= NOVO: Preencher datas =========
    const START = process.env.START_DATE_BR || '01/01/2020'; // dd/mm/aaaa
    const WAIT_HEAVY = parseInt(process.env.HEAVY_WAIT_MS || '20000', 10); // 20s padrão

    console.log('🗓️ Preenchendo datas...');
    const dataInicialHandle = await findInAllFrames(page, async (ctx) => {
      const candidates = [
        ctx.getByRole ? ctx.getByRole('textbox', { name: /Data inicial\*/i }) : null,
        ctx.locator ? ctx.locator('input[name*="dataInicial" i]') : null,
        ctx.locator ? ctx.locator('input[placeholder*="Data inicial" i]') : null,
        ctx.locator ? ctx.locator('label:has-text("Data inicial")').locator('..').locator('input') : null
      ].filter(Boolean);

      for (const locator of candidates) {
        try {
          const first = locator.first();
          await first.waitFor({ timeout: 8000 });
          if (await first.count()) {
            return { handle: ctx, locator: first };
          }
        } catch (err) {}
      }
      return null;
    });

    if (!dataInicialHandle || !(await dataInicialHandle.locator.count())) {
      console.log('❌ Campo "Data inicial" não encontrado (frames incluidos)');
      await page.screenshot({ path: 'debug_erro_data_inicial.png', fullPage: true });
      throw new Error('Campo "Data inicial" não encontrado');
    }

    await dataInicialHandle.locator.click({ force: true });
    await dataInicialHandle.locator.press('Control+A').catch(() => {});
    await dataInicialHandle.locator.type(START, { delay: 15 });

    const hojePtBr = new Date().toLocaleDateString('pt-BR');
    const dataFinalHandle = await findInAllFrames(page, async (ctx) => {
      const candidates = [
        ctx.getByRole ? ctx.getByRole('textbox', { name: /Data final\*/i }) : null,
        ctx.locator ? ctx.locator('input[name*="dataFinal" i]') : null,
        ctx.locator ? ctx.locator('input[placeholder*="Data final" i]') : null,
        ctx.locator ? ctx.locator('label:has-text("Data final")').locator('..').locator('input') : null
      ].filter(Boolean);

      for (const locator of candidates) {
        try {
          const first = locator.first();
          await first.waitFor({ timeout: 8000 });
          if (await first.count()) {
            return { handle: ctx, locator: first };
          }
        } catch (err) {}
      }
      return null;
    });

    if (!dataFinalHandle || !(await dataFinalHandle.locator.count())) {
      console.log('❌ Campo "Data final" não encontrado (frames incluidos)');
      await page.screenshot({ path: 'debug_erro_data_final.png', fullPage: true });
      throw new Error('Campo "Data final" não encontrado');
    }

    await dataFinalHandle.locator.click({ force: true });
    await dataFinalHandle.locator.press('Control+A').catch(() => {});
    await dataFinalHandle.locator.type(hojePtBr, { delay: 15 });

    // ========= NOVO: CONSULTAR =========
    console.log('🔎 Consultando...');
    const consultarBtn = page.getByRole('button', {{ name: /CONSULTAR/i }});
    await Promise.all([
      page.waitForLoadState('networkidle', {{ timeout: 60000 }}).catch(() => {{}}),
      consultarBtn.click()
    ]);
    await page.waitForTimeout(WAIT_HEAVY); // aguardo pesado

    // ========= NOVO: Rodapé -> "Linhas por página: Todas" =========
    console.log('📄 Ajustando "Linhas por página" para "Todas"...');
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(1000);

    let linhasCombo = null;
    try {{
      linhasCombo = page.getByRole('combobox', {{ name: /Linhas por página/i }});
      await linhasCombo.click({{ force: true }});
    }} catch (e) {{
      const alt = page.locator('div.MuiTablePagination-root [role="combobox"]').first();
      await alt.click({{ force: true }});
      linhasCombo = alt;
    }}

    let todasOpt = page.getByRole('option', {{ name: /^Todas$/i }});
    if (await todasOpt.count() === 0) {{
      todasOpt = page.locator('ul[role="listbox"] li[role="option"]', {{ hasText: 'Todas' }}).first();
    }}
    try {{ await todasOpt.click(); }}
    catch {{ await linhasCombo.press('End'); await linhasCombo.press('Enter'); }}

    await page.waitForTimeout(WAIT_HEAVY); // aguarda carregar todas

    // ========= Voltar ao topo =========
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(800);

    // ========= Botão "Gerar relatório" =========
    await page.screenshot({{ path: 'debug_antes_gerar_relatorio.png' }});
    const gerarBtn =
      (await page.$('button:has-text("Gerar Relatório")')) ||
      (await page.$('button:has-text("GERAR RELATÓRIO")')) ||
      (await page.$('button:has-text("Gerar relatório")')) ||
      (await page.$('[role="button"]:has-text("GERAR RELATÓRIO")'));

    if (!gerarBtn) {{
      await page.screenshot({{ path: 'debug_erro_botao_gerar.png' }});
      throw new Error('Botão "Gerar relatório" não encontrado');
    }}
    await gerarBtn.click();

    // ========= Modal + combobox MUI + exportar CSV =========
    console.log('⏳ Aguardando modal de exportação...');
    const dialog = page.getByRole('dialog', {{ name: /Gerar relatório/i }});
    await dialog.getByText(/Selecione o formato de exportação/i).waitFor({{ timeout: 10000 }});
    await page.screenshot({{ path: 'debug_modal_aberto.png' }});

    console.log('🔍 Abrindo combobox "Gerar relatório como"...');
    const combo = dialog.getByRole('combobox');
    await combo.click({{ force: true }});

    console.log('🔽 Selecionando CSV no portal do MUI...');
    let csvOption = page.locator('ul[role="listbox"] li[role="option"][data-value="csv"]').first();
    if (await csvOption.count() === 0) {{
      csvOption = page.getByRole('option', {{ name: /^CSV$/i }});
    }}
    try {{
      await csvOption.click();
    }} catch (e) {{
      console.log('⚠️ Clique no option falhou, usando ArrowDown+Enter...');
      await combo.press('ArrowDown');
      await combo.press('Enter');
    }}

    try {{
      await dialog.getByRole('combobox').getByText(/CSV/i).waitFor({{ timeout: 3000 }});
      console.log('✅ Combobox definido para CSV');
    }} catch {{ }}

    await page.screenshot({{ path: 'debug_combo_csv_selecionado.png' }});

    console.log('⬇️ Clicando em EXPORTAR e aguardando o download...');
    const exportBtn = dialog.getByRole('button', {{ name: /EXPORTAR/i }});

    const [download] = await Promise.all([
      page.waitForEvent('download', {{ timeout: 60000 }}),
      exportBtn.click()
    ]);

    const suggested = download.suggestedFilename() || `relatorio_pedidos_${{Date.now()}}.csv`;
    const finalPath = path.join(downloadPath, suggested);
    await download.saveAs(finalPath);
    console.log(`✅ Download concluído e salvo em: ${{finalPath}}`);

    await page.screenshot({{ path: 'debug_pos_download.png' }});
    console.log('✅ Automação completa concluída!');

  }} catch (err) {{
    console.error('❌ Erro no fluxo MCP:', err?.message || err);
    await page.screenshot({{ path: 'debug_sienge_mcp_completo.png' }});
    throw err;
  }} finally {{
    console.log('🔄 Encerrando contexto...');
    await context.close();
  }}
}}

automacaoCompletaSienge().catch(e => {{
  console.error(e);
  process.exitCode = 1;
}});
"""

        with open('sienge_mcp_completo_temp.js', 'w', encoding='utf-8') as f:
            f.write(script_js)

        try:
            # Detectar sistema operacional
            import platform
            is_windows = platform.system() == 'Windows'
            shell_mode = is_windows
            
            print("📦 Verificando dependências do Playwright...")
            
            # Forçar reinstalação completa do Playwright
            print("🔄 Forçando reinstalação completa do Playwright...")
            try:
                # Remover node_modules se existir
                if os.path.exists('node_modules'):
                    print("🗑️ Removendo node_modules existente...")
                    import shutil
                    shutil.rmtree('node_modules', ignore_errors=True)
                
                # Reinstalar do zero
                print("📦 Reinstalando npm packages...")
                install_result = subprocess.run(['npm', 'install'], 
                             capture_output=True, text=True, shell=shell_mode, timeout=180)
                if install_result.returncode != 0:
                    print(f"⚠️ Erro no npm install: {install_result.stderr}")
                else:
                    print("✅ npm install concluído")
                
                # Instalar browsers do Playwright
                print("🌐 Instalando browsers do Playwright...")
                browser_result = subprocess.run(['npx', 'playwright', 'install', 'chromium', '--with-deps'], 
                             capture_output=True, text=True, shell=shell_mode, timeout=300)
                if browser_result.returncode != 0:
                    print(f"⚠️ Erro na instalação do browser: {browser_result.stderr}")
                else:
                    print("✅ Browsers instalados")
                
                # Verificar se lib/inprocess existe agora
                inprocess_path = 'node_modules/playwright/lib/inprocess'
                if os.path.exists(inprocess_path):
                    print("✅ Playwright completamente instalado")
                else:
                    print("⚠️ lib/inprocess ainda não encontrado, mas continuando...")
                    
            except Exception as e:
                print(f"⚠️ Erro na reinstalação: {e}")
                print("📋 Continuando mesmo assim...")
            
            result = subprocess.run(
                ['node', 'sienge_mcp_completo_temp.js'],
                capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=1200
            )
            print("📋 Saída MCP:\n", result.stdout)
            if result.stderr:
                print("⚠️ Avisos MCP:\n", result.stderr)
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            print("⏱️ Timeout na execução MCP")
            return False
        except Exception as e:
            print(f"❌ Erro MCP: {e}")
            return False
        finally:
            try: os.remove('sienge_mcp_completo_temp.js')
            except: pass

    def verificar_download(self):
        print("🔍 Verificando downloads...")
        os.makedirs(self.download_dir, exist_ok=True)
        arquivos = [p for p in glob.glob(os.path.join(self.download_dir, "*")) if os.path.isfile(p)]
        if not arquivos:
            print("❌ Nenhum arquivo encontrado")
            return None
        latest = max(arquivos, key=os.path.getmtime)
        print(f"✅ Último arquivo: {pathlib.Path(latest).name} ({os.path.getsize(latest)} bytes)")
        print(f"📍 Local: {latest}")
        return latest

def main():
    print("="*60)
    print("🚀 AUTOMAÇÃO SIENGE MCP COMPLETA (datas + consultar + todas + CSV)")
    print("="*60)

    bot = SiengeMCPPersistente()
    ok = bot.executar_automacao_mcp_completa()
    if not ok:
        print("\n❌ Processo MCP falhou")
        raise SystemExit(1)

    arquivo = bot.verificar_download()
    if arquivo:
        print("\n✅ Processo finalizado com sucesso!")
        raise SystemExit(0)
    else:
        print("\n⚠️ Automação executada, mas download não localizado")
        raise SystemExit(2)

if __name__ == "__main__":
    main()
