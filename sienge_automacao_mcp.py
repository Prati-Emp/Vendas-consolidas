#!/usr/bin/env python3
"""
Automação Sienge usando MCP Browser Tools
Abordagem híbrida: Python + MCP para máxima robustez e eficiência
"""

import os
import time
import subprocess
import json
import glob
import pathlib
from datetime import datetime
from dotenv import load_dotenv

# Carregar configurações
load_dotenv('config_sienge.env')

# URLs e configurações
LOGIN_URL = os.environ.get('LOGIN_URL', 'https://pratiemp.sienge.com.br/sienge/8/index.html')
RELATORIO_URL = os.environ.get('RELATORIO_URL', 'https://pratiemp.sienge.com.br/sienge/8/index.html#/suprimentos/compras/pedidos-de-compra/relatorios/relacao-pedidos-compra')
DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads_tmp")

class SiengeAutomacaoMCP:
    """Classe para automação do Sienge usando MCP Browser Tools"""
    
    def __init__(self):
        self.download_dir = DOWNLOAD_DIR
        self.ensure_download_dir()
        
    def ensure_download_dir(self):
        """Garantir que o diretório de download existe"""
        os.makedirs(self.download_dir, exist_ok=True)
        
    def iniciar_mcp_server(self):
        """Iniciar o servidor MCP Browser Tools"""
        print("🚀 Iniciando servidor MCP Browser Tools...")
        try:
            # Verificar se já está rodando
            result = subprocess.run(['netstat', '-an'], capture_output=True, text=True)
            if ':3025' in result.stdout or ':3026' in result.stdout:
                print("✅ Servidor MCP já está rodando")
                return True
                
            # Iniciar servidor em background
            process = subprocess.Popen(
                ["npx", "@agentdeskai/browser-tools-server@latest"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Aguardar inicialização
            time.sleep(5)
            print("✅ Servidor MCP iniciado com sucesso")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao iniciar servidor MCP: {e}")
            return False
    
    def executar_automacao_mcp(self):
        """Executar automação usando MCP Browser Tools via JavaScript"""
        
        script_js = f"""
const {{ chromium }} = require('playwright');

async function automatizarSienge() {{
    console.log('🚀 Iniciando automação Sienge...');
    
    const browser = await chromium.launch({{
        headless: false,
        args: [
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-blink-features=AutomationControlled',
            '--user-data-dir=chrome_profile_sienge_persistente',
            '--profile-directory=SiengeProfile',
            '--download-directory={self.download_dir}',
            '--disable-web-security',
            '--disable-features=VizDisplayCompositor'
        ]
    }});
    
    const context = await browser.newContext({{
        viewport: {{ width: 1920, height: 1080 }},
        acceptDownloads: true
    }});
    
    const page = await context.newPage();
    
    try {{
        console.log('📱 Navegando para o relatório...');
        await page.goto('{RELATORIO_URL}');
        
        // Aguardar página carregar
        await page.waitForTimeout(5000);
        
        // Refresh para estabilizar (conforme observado)
        console.log('🔄 Aplicando refresh para estabilizar...');
        await page.reload();
        await page.waitForTimeout(5000);
        
        console.log('🔍 Procurando botão GERAR RELATÓRIO...');
        
        // Buscar botão GERAR RELATÓRIO
        const btnGerar = await page.waitForSelector('button:has-text("Gerar Relatório")', {{ timeout: 30000 }});
        console.log('✅ Botão GERAR RELATÓRIO encontrado');
        
        // Clicar no botão
        await btnGerar.click();
        console.log('✅ Botão GERAR RELATÓRIO clicado');
        
        // Aguardar modal aparecer
        await page.waitForTimeout(3000);
        
        console.log('🔍 Procurando modal de exportação...');
        
        // Buscar dropdown de formato
        console.log('🔍 Procurando dropdown de formato...');
        const dropdown = await page.waitForSelector('input[placeholder*="Gerar relatório"], [role="combobox"]', {{ timeout: 10000 }});
        console.log('✅ Dropdown de formato encontrado');
        
        // Clicar no dropdown
        await dropdown.click();
        await page.waitForTimeout(2000);
        
        // Selecionar CSV
        console.log('📋 Selecionando CSV...');
        const csvOption = await page.waitForSelector('li:has-text("CSV"), option:has-text("CSV")', {{ timeout: 5000 }});
        await csvOption.click();
        console.log('✅ CSV selecionado');
        
        await page.waitForTimeout(2000);
        
        // Buscar botão EXPORTAR
        console.log('🔍 Procurando botão EXPORTAR...');
        const btnExportar = await page.waitForSelector('button:has-text("Exportar")', {{ timeout: 10000 }});
        console.log('✅ Botão EXPORTAR encontrado');
        
        // Clicar no botão EXPORTAR
        await btnExportar.click();
        console.log('✅ Botão EXPORTAR clicado');
        
        // Aguardar download
        console.log('⏳ Aguardando download...');
        await page.waitForTimeout(10000);
        
        console.log('✅ Automação concluída com sucesso!');
        
        // Manter janela aberta por um tempo para verificação
        await page.waitForTimeout(5000);
        
    }} catch (error) {{
        console.error('❌ Erro na automação:', error);
        
        // Capturar screenshot para debug
        await page.screenshot({{ path: 'debug_automacao_mcp.png' }});
        console.log('📸 Screenshot salvo como debug_automacao_mcp.png');
        
        throw error;
    }} finally {{
        await browser.close();
    }}
}}

automatizarSienge().catch(console.error);
"""
        
        # Salvar script temporário
        script_path = 'automacao_sienge_mcp.js'
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_js)
        
        try:
            print("🔧 Executando automação MCP...")
            
            # Instalar playwright se necessário
            print("📦 Verificando dependências...")
            subprocess.run(['npm', 'install', 'playwright'], check=True, capture_output=True)
            subprocess.run(['npx', 'playwright', 'install', 'chromium'], check=True, capture_output=True)
            
            # Executar o script
            result = subprocess.run(['node', script_path], 
                                  capture_output=True, text=True, timeout=300)
            
            print("📋 Saída da automação:")
            print(result.stdout)
            
            if result.stderr:
                print("⚠️ Avisos/Erros:")
                print(result.stderr)
                
            return result.returncode == 0
            
        except subprocess.TimeoutExpired:
            print("❌ Automação expirou (timeout)")
            return False
        except Exception as e:
            print(f"❌ Erro ao executar automação: {e}")
            return False
        finally:
            # Limpar arquivo temporário
            try:
                os.remove(script_path)
            except:
                pass
    
    def verificar_download(self):
        """Verificar se o download foi realizado"""
        print("🔍 Verificando downloads...")
        
        # Buscar arquivos CSV recentes
        csv_files = glob.glob(os.path.join(self.download_dir, "*.csv"))
        recent_files = []
        
        for file_path in csv_files:
            # Verificar se foi criado nos últimos 5 minutos
            if os.path.getmtime(file_path) > time.time() - 300:
                recent_files.append(file_path)
        
        if recent_files:
            # Pegar o mais recente
            latest_file = max(recent_files, key=os.path.getmtime)
            file_size = os.path.getsize(latest_file)
            print(f"✅ Download encontrado: {pathlib.Path(latest_file).name}")
            print(f"📊 Tamanho: {file_size} bytes")
            print(f"📍 Local: {latest_file}")
            return latest_file
        else:
            print("❌ Nenhum download recente encontrado")
            return None
    
    def executar_automacao_completa(self):
        """Executar automação completa"""
        print("=" * 60)
        print("🚀 AUTOMAÇÃO SIENGE COM MCP BROWSER TOOLS")
        print("=" * 60)
        
        try:
            # 1. Iniciar servidor MCP
            if not self.iniciar_mcp_server():
                return False
            
            # 2. Executar automação
            if not self.executar_automacao_mcp():
                return False
            
            # 3. Verificar download
            arquivo_baixado = self.verificar_download()
            if arquivo_baixado:
                print("🎉 AUTOMAÇÃO CONCLUÍDA COM SUCESSO!")
                return True
            else:
                print("⚠️ Automação executada, mas download não detectado")
                return False
                
        except Exception as e:
            print(f"❌ Erro na automação: {e}")
            return False

def main():
    """Função principal"""
    automacao = SiengeAutomacaoMCP()
    success = automacao.executar_automacao_completa()
    
    if success:
        print("\n✅ Processo concluído com sucesso!")
        exit(0)
    else:
        print("\n❌ Processo falhou")
        exit(1)

if __name__ == "__main__":
    main()






