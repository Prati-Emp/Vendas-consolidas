#!/usr/bin/env python3
"""
Teste Dois Cliques - Específico para testar dois cliques no campo
"""

import os
import time
import subprocess
from dotenv import load_dotenv

# Carregar configurações
load_dotenv('config_sienge.env')

RELATORIO_URL = os.environ.get('RELATORIO_URL', 'https://pratiemp.sienge.com.br/sienge/8/index.html#/suprimentos/compras/pedidos-de-compra/relatorios/relacao-pedidos-compra')

def teste_dois_cliques():
    """Teste específico para dois cliques no campo"""
    print("🔍 Teste Dois Cliques - Específico para dois cliques no campo")
    
    script_js = f"""
const {{ chromium }} = require('playwright');
const path = require('path');

async function testeDoisCliques() {{
    console.log('🚀 Iniciando teste de dois cliques no campo...');
    
    const userDataDir = path.resolve('chrome_profile_sienge_persistente');
    
    const context = await chromium.launchPersistentContext(userDataDir, {{
        headless: false,
        viewport: {{ width: 1920, height: 1080 }},
        args: [
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--profile-directory=SiengeProfile',
            '--force-device-scale-factor=1',
            '--disable-zoom',
            '--disable-extensions',
            '--disable-plugins',
            '--disable-web-security',
            '--disable-features=VizDisplayCompositor'
        ]
    }});

    const page = await context.newPage();

    try {{
        // 1. Navegar para o relatório
        console.log('📱 Navegando para o relatório...');
        await page.goto('{RELATORIO_URL}', {{ 
            waitUntil: 'domcontentloaded',
            timeout: 60000 
        }});
        await page.waitForTimeout(5000);

        // 2. Procurar e clicar no botão "GERAR RELATÓRIO"
        console.log('🔍 Procurando botão "GERAR RELATÓRIO"...');
        const btnGerar = await page.waitForSelector('button:has-text("GERAR RELATÓRIO"), button:has-text("Gerar Relatório")', {{ timeout: 10000 }});
        
        await page.screenshot({{ path: 'debug_antes_clicar_gerar.png' }});
        console.log('📸 Screenshot antes de clicar em GERAR RELATÓRIO salvo');
        
        await btnGerar.click();
        console.log('✅ Botão GERAR RELATÓRIO clicado');
        
        // Aguardar modal aparecer
        await page.waitForTimeout(5000);
        
        await page.screenshot({{ path: 'debug_apos_clicar_gerar.png' }});
        console.log('📸 Screenshot após clicar em GERAR RELATÓRIO salvo');

        // 3. Estabilizar tela
        console.log('🔧 Estabilizando tela...');
        await page.evaluate(() => {{
            const style = document.createElement('style');
            style.textContent = `
                *, *::before, *::after {{
                    animation-duration: 0s !important;
                    animation-delay: 0s !important;
                    transition-duration: 0s !important;
                    transition-delay: 0s !important;
                }}
            `;
            document.head.appendChild(style);
            document.body.style.overflow = 'hidden';
        }});
        
        await page.waitForTimeout(3000);

        // 4. Procurar campo "Gerar relatório como"
        console.log('🔍 Procurando campo "Gerar relatório como"...');
        const campoRelatorio = await page.waitForSelector('input[placeholder*="Gerar relatório"], [role="combobox"]', {{ timeout: 10000 }});
        
        // Screenshot antes de clicar no campo
        await page.screenshot({{ path: 'debug_antes_clicar_campo.png' }});
        console.log('📸 Screenshot antes de clicar no campo salvo');
        
        // 5. PRIMEIRO CLIQUE no campo
        console.log('🖱️ Executando 1º clique no campo...');
        await campoRelatorio.click();
        console.log('✅ 1º clique executado');
        await page.waitForTimeout(1000);
        
        // Screenshot após primeiro clique
        await page.screenshot({{ path: 'debug_apos_primeiro_clique.png' }});
        console.log('📸 Screenshot após 1º clique salvo');
        
        // 6. SEGUNDO CLIQUE no campo
        console.log('🖱️ Executando 2º clique no campo...');
        await campoRelatorio.click();
        console.log('✅ 2º clique executado');
        await page.waitForTimeout(2000);
        
        // Screenshot após segundo clique
        await page.screenshot({{ path: 'debug_apos_segundo_clique.png' }});
        console.log('📸 Screenshot após 2º clique salvo');
        
        // 7. Verificar se dropdown abriu
        console.log('🔍 Verificando se dropdown abriu...');
        const dropdownAberto = await page.evaluate(() => {{
            // Verificar se há elementos de dropdown visíveis
            const dropdowns = document.querySelectorAll('[role="listbox"], [role="menu"], .dropdown-menu, [class*="dropdown"], [class*="select"]');
            return Array.from(dropdowns).some(dropdown => dropdown.offsetParent !== null);
        }});
        
        if (dropdownAberto) {{
            console.log('✅ Dropdown parece estar aberto');
        }} else {{
            console.log('⚠️ Dropdown pode não estar aberto');
        }}
        
        // 8. Procurar opções CSV/EXCEL
        console.log('🔍 Procurando opções CSV/EXCEL...');
        const opcoes = await page.evaluate(() => {{
            const elementos = Array.from(document.querySelectorAll('li, option, div, span, button'));
            return elementos
                .filter(el => el.textContent && (el.textContent.includes('CSV') || el.textContent.includes('EXCEL')))
                .map(el => ({{
                    tag: el.tagName,
                    text: el.textContent.trim(),
                    visible: el.offsetParent !== null
                }}));
        }});
        
        console.log('Opções encontradas:', opcoes.length);
        opcoes.forEach((opcao, i) => {{
            console.log(`  ${{i+1}}. ${{opcao.tag}} - "${{opcao.text}}" (visível: ${{opcao.visible}})`);
        }});
        
        // 9. Tentar clicar em CSV se encontrado
        if (opcoes.length > 0) {{
            const csvOpcao = opcoes.find(opcao => opcao.text.includes('CSV'));
            if (csvOpcao) {{
                console.log('🔍 Tentando clicar em CSV...');
                try {{
                    await page.click(`text="${{csvOpcao.text}}"`);
                    console.log('✅ CSV clicado');
                    await page.waitForTimeout(2000);
                }} catch (e) {{
                    console.log('❌ Erro ao clicar em CSV:', e.message);
                }}
            }}
        }}
        
        // Screenshot final
        await page.screenshot({{ path: 'debug_final_dois_cliques.png' }});
        console.log('📸 Screenshot final salvo');
        
        // Manter aberto para inspeção
        console.log('🔄 Mantendo aberto por 30 segundos para inspeção...');
        await page.waitForTimeout(30000);
        
    }} catch (error) {{
        console.error('❌ Erro:', error);
        await page.screenshot({{ path: 'debug_erro_geral.png' }});
    }} finally {{
        await context.close();
    }}
}}

testeDoisCliques().catch(console.error);
"""
    
    # Salvar e executar script
    with open('teste_dois_cliques_temp.js', 'w', encoding='utf-8') as f:
        f.write(script_js)
    
    try:
        result = subprocess.run(['node', 'teste_dois_cliques_temp.js'], 
                              capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=180)
        
        print("📋 Saída MCP:")
        print(result.stdout)
        
        if result.stderr:
            print("⚠️ Avisos MCP:")
            print(result.stderr)
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("❌ Timeout na execução MCP")
        return False
    except Exception as e:
        print(f"❌ Erro MCP: {e}")
        return False
    finally:
        try:
            os.remove('teste_dois_cliques_temp.js')
        except:
            pass

if __name__ == "__main__":
    teste_dois_cliques()





