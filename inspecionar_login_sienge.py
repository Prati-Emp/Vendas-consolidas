#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Inspeção do Login Sienge
- Abre o navegador e pausa em cada etapa
- Você identifica os elementos
- Eu ajusto o código com os seletores corretos
"""

import os
import sys
import subprocess
import platform

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def main():
    print("=" * 70)
    print("🔍 INSPEÇÃO DO LOGIN SIENGE - IDENTIFICAÇÃO DE ELEMENTOS")
    print("=" * 70)
    print()
    print("📋 INSTRUÇÕES:")
    print()
    print("1. O navegador abrirá com a sessão persistente")
    print("2. Navegue até a tela de login")
    print("3. Para CADA elemento que aparece, me informe:")
    print("   - Texto do botão/elemento")
    print("   - Posição na tela")
    print("   - Se é obrigatório ou opcional")
    print()
    print("4. Vamos mapear TODAS as 3 possíveis etapas:")
    print()
    print("   ETAPA 1: Tela inicial de login")
    print("   ├─ Botão 'Entrar com Sienge ID'?")
    print("   ├─ Outro botão?")
    print("   └─ Campo de email/senha?")
    print()
    print("   ETAPA 2: Seleção de conta / Sessão ativa")
    print("   ├─ Botão 'Continuar' (sessão ativa)?")
    print("   ├─ Seleção de conta (email)?")
    print("   ├─ Botão 'Conectado'?")
    print("   └─ Outro elemento?")
    print()
    print("   ETAPA 3: Confirmação final")
    print("   ├─ Botão 'Prosseguir'?")
    print("   ├─ Botão 'Confirmar'?")
    print("   └─ Outro elemento?")
    print()
    print("=" * 70)
    print()
    print("🌐 Abrindo navegador com sessão persistente em 3 segundos...")
    print()
    
    import time
    time.sleep(3)
    
    # URL do Sienge
    url = 'https://pratiemp.sienge.com.br/sienge/8/index.html'
    
    # Detectar sistema operacional
    is_windows = platform.system() == 'Windows'
    shell_mode = is_windows
    
    # Diretório de perfil persistente
    user_data_dir = os.path.join(os.getcwd(), 'chrome_profile_sienge_persistente')
    os.makedirs(user_data_dir, exist_ok=True)
    
    # Comando para abrir navegador com inspeção
    cmd = [
        'npx', 'playwright', 'open',
        url,
        '--user-data-dir', user_data_dir,
        '--viewport-size', '1920,1080'
    ]
    
    print("📝 Navegador aberto!")
    print()
    print("=" * 70)
    print("🔍 AGORA FAÇA O LOGIN E ME INFORME:")
    print("=" * 70)
    print()
    print("Para cada tela/etapa que aparecer, me diga:")
    print()
    print("1️⃣ PRIMEIRA TELA:")
    print("   - Qual o texto do primeiro botão que aparece?")
    print("   - Tem campo de email/senha ou é só botão?")
    print("   - Tem mais de um botão?")
    print()
    print("2️⃣ SEGUNDA TELA (após clicar no primeiro botão):")
    print("   - Aparece mensagem de 'sessão ativa'?")
    print("   - Aparece lista de contas/emails?")
    print("   - Qual o texto dos botões disponíveis?")
    print()
    print("3️⃣ TERCEIRA TELA (se houver):")
    print("   - Qual o texto do botão final?")
    print("   - Tem alguma confirmação adicional?")
    print()
    print("💡 DICA: Use F12 para abrir DevTools e inspecionar os elementos")
    print("         Anote os atributos: id, class, data-*, aria-label, etc.")
    print()
    print("=" * 70)
    
    try:
        subprocess.run(cmd, shell=shell_mode)
    except KeyboardInterrupt:
        print()
        print("⚠️ Inspeção interrompida")
    except Exception as e:
        print(f"❌ Erro: {e}")
        sys.exit(1)
    
    print()
    print("=" * 70)
    print("✅ Navegador fechado")
    print()
    print("📋 PRÓXIMO PASSO:")
    print("   Me informe o que você viu em cada etapa")
    print("   e vou ajustar o código com os seletores corretos!")
    print("=" * 70)

if __name__ == "__main__":
    main()

