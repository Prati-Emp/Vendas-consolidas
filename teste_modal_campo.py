#!/usr/bin/env python3
"""
Teste Modal Campo - Específico para testar o campo dentro do modal
"""

import os
import time
import subprocess
from dotenv import load_dotenv

# Carregar configurações
load_dotenv('config_sienge.env')

RELATORIO_URL = os.environ.get('RELATORIO_URL', 'https://pratiemp.sienge.com.br/sienge/8/index.html#/suprimentos/compras/pedidos-de-compra/relatorios/relacao-pedidos-compra')

def teste_modal_campo():
    """Teste específico para o campo dentro do modal"""
    print("🔍 Teste Modal Campo - Específico para o campo dentro do modal")
    
    script_js = f"""
const {{ chromium }} = require('playwright');
const path = require('path');

async function testeModalCampo() {{
    console.log('🚀 Iniciando teste do campo dentro do modal...');
    
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

        // 4. Verificar se modal está visível
        console.log('🔍 Verificando se modal está visível...');
        const modalVisivel = await page.evaluate(() => {{
            const modals = document.querySelectorAll('[role="dialog"], .modal, [class*="modal"], [class*="popup"]');
            return modals.length > 0;
        }});
        
        if (!modalVisivel) {{
            console.log('❌ Modal não está visível');
            await page.screenshot({{ path: 'debug_modal_nao_visivel.png' }});
            return;
        }}
        
        console.log('✅ Modal está visível');

        // 5. Screenshot do modal completo
        await page.screenshot({{ path: 'debug_modal_completo.png' }});
        console.log('📸 Screenshot do modal completo salvo');

        // 6. Listar todos os elementos do modal
        console.log('🔍 Listando todos os elementos do modal...');
        const elementosModal = await page.evaluate(() => {{
            const modal = document.querySelector('[role="dialog"], .modal, [class*="modal"], [class*="popup"]');
            if (!modal) return [];
            
            const elementos = Array.from(modal.querySelectorAll('input, select, button, div, span, li, option'));
            return elementos.map(el => ({{
                tag: el.tagName,
                text: el.textContent?.trim(),
                placeholder: el.placeholder,
                value: el.value,
                classes: el.className,
                id: el.id,
                visible: el.offsetParent !== null,
                rect: el.getBoundingClientRect()
            }})).filter(el => el.visible);
        }});
        
        console.log('Elementos do modal encontrados:', elementosModal.length);
        elementosModal.forEach((el, i) => {{
            console.log(`  ${{i+1}}. ${{el.tag}} - "${{el.text}}" (placeholder: "${{el.placeholder}}", value: "${{el.value}}", classes: "${{el.classes}}")`);
        }});

        // 7. Procurar campo "Gerar relatório como" com múltiplas estratégias
        console.log('🔍 Procurando campo "Gerar relatório como"...');
        const campoSelectors = [
            'input[placeholder*="Gerar relatório como"]',
            'input[placeholder*="gerar relatório como"]',
            'input[placeholder*="Gerar relatório"]',
            'input[placeholder*="gerar relatório"]',
            '[role="combobox"]',
            'input[type="text"]',
            'input:not([type="hidden"])',
            'div[class*="select"]',
            'div[class*="dropdown"]'
        ];
        
        let campoRelatorio = null;
        for (const selector of campoSelectors) {{
            try {{
                campoRelatorio = await page.waitForSelector(selector, {{ timeout: 2000 }});
                if (campoRelatorio) {{
                    const placeholder = await campoRelatorio.getAttribute('placeholder');
                    const value = await campoRelatorio.getAttribute('value');
                    const text = await campoRelatorio.textContent;
                    
                    console.log(`Campo encontrado - placeholder: "${{placeholder}}", value: "${{value}}", text: "${{text}}"`);
                    
                    if (placeholder && (placeholder.includes('Gerar relatório') || placeholder.includes('gerar relatório'))) {{
                        console.log(`✅ Campo "Gerar relatório como" encontrado com seletor: ${{selector}}`);
                        break;
                    }} else if (value && (value.includes('Gerar relatório') || value.includes('gerar relatório'))) {{
                        console.log(`✅ Campo "Gerar relatório como" encontrado por value com seletor: ${{selector}}`);
                        break;
                    }} else {{
                        console.log(`Campo encontrado mas não é o correto: "${{placeholder}}"`);
                        campoRelatorio = null;
                    }}
                }}
            }} catch (e) {{
                continue;
            }}
        }}
        
        if (campoRelatorio) {{
            // Screenshot antes de clicar no campo
            await page.screenshot({{ path: 'debug_antes_clicar_campo.png' }});
            console.log('📸 Screenshot antes de clicar no campo salvo');
            
            // Clicar no campo
            await campoRelatorio.click();
            console.log('✅ Campo "Gerar relatório como" clicado');
            
            await page.waitForTimeout(2000);
            
            // Screenshot após clicar no campo
            await page.screenshot({{ path: 'debug_apos_clicar_campo.png' }});
            console.log('📸 Screenshot após clicar no campo salvo');
            
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
            await page.screenshot({{ path: 'debug_final_modal_campo.png' }});
            console.log('📸 Screenshot final salvo');
            
        }} else {{
            console.log('❌ Campo "Gerar relatório como" não encontrado');
            await page.screenshot({{ path: 'debug_erro_campo_nao_encontrado.png' }});
        }}
        
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

testeModalCampo().catch(console.error);
"""
    
    # Salvar e executar script
    with open('teste_modal_campo_temp.js', 'w', encoding='utf-8') as f:
        f.write(script_js)
    
    try:
        result = subprocess.run(['node', 'teste_modal_campo_temp.js'], 
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
            os.remove('teste_modal_campo_temp.js')
        except:
            pass

if __name__ == "__main__":
    teste_modal_campo()




