#!/usr/bin/env python3
"""
Teste Modal Exportação - Específico para testar o modal de exportação
"""

import os
import time
import subprocess
from dotenv import load_dotenv

# Carregar configurações
load_dotenv('config_sienge.env')

RELATORIO_URL = os.environ.get('RELATORIO_URL', 'https://pratiemp.sienge.com.br/sienge/8/index.html#/suprimentos/compras/pedidos-de-compra/relatorios/relacao-pedidos-compra')

def teste_modal_exportacao():
    """Teste específico para o modal de exportação"""
    print("🔍 Teste Modal Exportação - Específico para modal de exportação")
    
    script_js = f"""
const {{ chromium }} = require('playwright');
const path = require('path');

async function testeModalExportacao() {{
    console.log('🚀 Iniciando teste do modal de exportação...');
    
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

        // 2. Screenshot inicial
        await page.screenshot({{ path: 'debug_tela_inicial_modal.png' }});
        console.log('📸 Screenshot inicial salvo');

        // 3. Procurar e clicar no botão "GERAR RELATÓRIO"
        console.log('🔍 Procurando botão "GERAR RELATÓRIO"...');
        const btnGerarSelectors = [
            'button:has-text("Gerar Relatório")',
            'button:has-text("GERAR RELATÓRIO")', 
            'button:has-text("Gerar relatório")',
            'a:has-text("GERAR RELATÓRIO")',
            '[role="button"]:has-text("GERAR RELATÓRIO")',
            'button[class*="button"]:has-text("GERAR")',
            'a[href*="relatorio"]:has-text("GERAR")'
        ];
        
        let btnGerar = null;
        for (const selector of btnGerarSelectors) {{
            try {{
                btnGerar = await page.waitForSelector(selector, {{ timeout: 3000 }});
                if (btnGerar) {{
                    console.log(`✅ Botão GERAR RELATÓRIO encontrado com seletor: ${{selector}}`);
                    break;
                }}
            }} catch (e) {{
                continue;
            }}
        }}
        
        if (btnGerar) {{
            // Screenshot antes do clique
            await page.screenshot({{ path: 'debug_antes_clicar_gerar.png' }});
            console.log('📸 Screenshot antes de clicar em GERAR RELATÓRIO salvo');
            
            await btnGerar.click();
            console.log('✅ Botão GERAR RELATÓRIO clicado');
            
            // Aguardar modal aparecer
            await page.waitForTimeout(5000);
            
            // Screenshot após clique
            await page.screenshot({{ path: 'debug_apos_clicar_gerar.png' }});
            console.log('📸 Screenshot após clicar em GERAR RELATÓRIO salvo');
        }} else {{
            console.log('❌ Botão GERAR RELATÓRIO não encontrado');
            await page.screenshot({{ path: 'debug_erro_nao_encontrou_gerar.png' }});
            return;
        }}

        // 4. Estabilizar tela
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

        // 5. Procurar campo "Gerar relatório como"
        console.log('🔍 Procurando campo "Gerar relatório como"...');
        const campoSelectors = [
            'input[placeholder*="Gerar relatório como"]',
            'input[placeholder*="gerar relatório como"]',
            'input[placeholder*="Gerar relatório"]',
            'input[placeholder*="gerar relatório"]',
            '[role="combobox"]',
            'input[type="text"]'
        ];
        
        let campoRelatorio = null;
        for (const selector of campoSelectors) {{
            try {{
                campoRelatorio = await page.waitForSelector(selector, {{ timeout: 2000 }});
                if (campoRelatorio) {{
                    const placeholder = await campoRelatorio.getAttribute('placeholder');
                    console.log(`Campo encontrado com placeholder: "${{placeholder}}"`);
                    
                    if (placeholder && placeholder.includes('Gerar relatório')) {{
                        console.log(`✅ Campo "Gerar relatório como" encontrado`);
                        break;
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
            
            // PRIMEIRO CLIQUE no campo
            await campoRelatorio.click();
            console.log('✅ Campo "Gerar relatório como" clicado (1º clique)');
            await page.waitForTimeout(1000);
            
            // SEGUNDO CLIQUE no campo para abrir dropdown
            await campoRelatorio.click();
            console.log('✅ Campo "Gerar relatório como" clicado (2º clique)');
            await page.waitForTimeout(2000);
            
            // Screenshot após os dois cliques
            await page.screenshot({{ path: 'debug_apos_dois_cliques_campo.png' }});
            console.log('📸 Screenshot após dois cliques no campo salvo');
            
            // 6. Procurar opção CSV
            console.log('🔍 Procurando opção CSV...');
            const csvSelectors = [
                'li:has-text("CSV")',
                'option:has-text("CSV")',
                'li:has-text("csv")',
                'option:has-text("csv")',
                'div:has-text("CSV")',
                'span:has-text("CSV")',
                'button:has-text("CSV")'
            ];
            
            let csvOption = null;
            for (const selector of csvSelectors) {{
                try {{
                    csvOption = await page.waitForSelector(selector, {{ timeout: 2000 }});
                    if (csvOption) {{
                        console.log(`✅ Opção CSV encontrada com seletor: ${{selector}}`);
                        break;
                    }}
                }} catch (e) {{
                    continue;
                }}
            }}
            
            if (csvOption) {{
                await csvOption.click();
                console.log('✅ CSV selecionado');
                await page.waitForTimeout(2000);
            }} else {{
                console.log('⚠️ Opção CSV não encontrada, tentando digitar...');
                await campoRelatorio.clear();
                await campoRelatorio.type('CSV');
                console.log('✅ CSV digitado no campo');
            }}
            
            // Screenshot após selecionar CSV
            await page.screenshot({{ path: 'debug_apos_selecionar_csv.png' }});
            console.log('📸 Screenshot após selecionar CSV salvo');
            
        }} else {{
            console.log('❌ Campo "Gerar relatório como" não encontrado');
            await page.screenshot({{ path: 'debug_erro_campo_nao_encontrado.png' }});
        }}

        // 7. Procurar botão EXPORTAR
        console.log('🔍 Procurando botão EXPORTAR...');
        const exportSelectors = [
            'button:has-text("Exportar")',
            'button:has-text("EXPORTAR")',
            'button:has-text("exportar")',
            '[role="button"]:has-text("EXPORTAR")',
            'button[class*="button"]:has-text("EXPORTAR")'
        ];
        
        let btnExportar = null;
        for (const selector of exportSelectors) {{
            try {{
                btnExportar = await page.waitForSelector(selector, {{ timeout: 3000 }});
                if (btnExportar) {{
                    console.log(`✅ Botão EXPORTAR encontrado com seletor: ${{selector}}`);
                    break;
                }}
            }} catch (e) {{
                continue;
            }}
        }}
        
        if (btnExportar) {{
            // Screenshot antes do clique no EXPORTAR
            await page.screenshot({{ path: 'debug_antes_clicar_exportar.png' }});
            console.log('📸 Screenshot antes de clicar em EXPORTAR salvo');
            
            await btnExportar.click();
            console.log('✅ Botão EXPORTAR clicado');
            
            // Screenshot após clique
            await page.waitForTimeout(3000);
            await page.screenshot({{ path: 'debug_apos_clicar_exportar.png' }});
            console.log('📸 Screenshot após clicar em EXPORTAR salvo');
            
        }} else {{
            console.log('❌ Botão EXPORTAR não encontrado');
            await page.screenshot({{ path: 'debug_erro_nao_encontrou_exportar.png' }});
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

testeModalExportacao().catch(console.error);
"""
    
    # Salvar e executar script
    with open('teste_modal_exportacao_temp.js', 'w', encoding='utf-8') as f:
        f.write(script_js)
    
    try:
        result = subprocess.run(['node', 'teste_modal_exportacao_temp.js'], 
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
            os.remove('teste_modal_exportacao_temp.js')
        except:
            pass

if __name__ == "__main__":
    teste_modal_exportacao()
