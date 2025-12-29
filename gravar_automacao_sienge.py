#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para gravar automação do Sienge usando Playwright Codegen
- Abre o navegador com gravação ativada
- Você executa os passos manualmente
- O código gerado será salvo automaticamente
"""

import os
import subprocess
import sys
import platform

def main():
    print("=" * 60)
    print("🎬 GRAVADOR DE AUTOMAÇÃO SIENGE - PLAYWRIGHT CODECEN")
    print("=" * 60)
    print()
    print("📋 INSTRUÇÕES:")
    print("1. O navegador abrirá com gravação ativada")
    print("2. Execute TODOS os passos manualmente:")
    print("   - Login no Sienge")
    print("   - Navegar para o relatório")
    print("   - Preencher data inicial")
    print("   - Preencher data final")
    print("   - Clicar em CONSULTAR")
    print("   - Ajustar 'Linhas por página' para 'Todas'")
    print("   - Clicar em 'Gerar Relatório'")
    print("   - Selecionar CSV no modal")
    print("   - Clicar em EXPORTAR")
    print("   - Aguardar download")
    print("3. Feche o navegador quando terminar")
    print("4. O código será salvo em 'codigo_gravado.js'")
    print()
    print("🚀 Iniciando gravação em 3 segundos...")
    print()
    
    import time
    time.sleep(3)
    
    # URL do relatório
    relatorio_url = os.environ.get(
        'RELATORIO_URL', 
        'https://pratiemp.sienge.com.br/sienge/8/index.html#/suprimentos/compras/pedidos-de-compra/relatorios/relacao-pedidos-compra'
    )
    
    # Detectar sistema operacional
    is_windows = platform.system() == 'Windows'
    shell_mode = is_windows
    
    # Diretório de perfil persistente
    user_data_dir = os.path.join(os.getcwd(), 'chrome_profile_sienge_persistente')
    os.makedirs(user_data_dir, exist_ok=True)
    
    # Comando para iniciar codegen com sessão persistente
    cmd = [
        'npx', 'playwright', 'codegen',
        relatorio_url,
        '--target', 'javascript',
        '--output', 'codigo_gravado.js',
        '--user-data-dir', user_data_dir,
        '--save-trace', 'trace.zip',
        '--viewport-size', '1920,1080'
    ]
    
    print(f"📝 Gravando para: codigo_gravado.js")
    print(f"🌐 URL: {relatorio_url}")
    print()
    print("=" * 60)
    print()
    
    try:
        subprocess.run(cmd, shell=shell_mode)
        print()
        print("=" * 60)
        print("✅ Gravação concluída!")
        print("📄 Código salvo em: codigo_gravado.js")
        print("📦 Trace salvo em: trace.zip")
        print()
        print("📋 PRÓXIMOS PASSOS:")
        print("1. Revise o arquivo 'codigo_gravado.js'")
        print("2. Adapte o código para nosso sistema")
        print("3. Integre com sienge_mcp_persistente.py")
        print("=" * 60)
    except KeyboardInterrupt:
        print()
        print("⚠️ Gravação interrompida pelo usuário")
    except Exception as e:
        print(f"❌ Erro: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

