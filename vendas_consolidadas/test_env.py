#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from pathlib import Path

# Obter o diretório atual
current_dir = Path('.').resolve()
env_path = current_dir / '.env'

print(f"Caminho do .env: {env_path}")
print(f"Arquivo existe: {env_path.exists()}")

if env_path.exists():
    print(f"Conteúdo do arquivo:")
    with open(env_path, 'r', encoding='utf-8-sig') as f:
        content = f.read()
        print(f"Primeiros 50 caracteres: {repr(content[:50])}...")
    
    # Carregar o .env
    load_dotenv(env_path)
    
    # Verificar se o token foi carregado
    token = os.getenv('MOTHERDUCK_TOKEN')
    if token:
        print(f"Token carregado com sucesso! Primeiros 20 caracteres: {token[:20]}...")
    else:
        print("Token NÃO foi carregado!")
        
    # Verificar também Token_MD
    token_md = os.getenv('Token_MD')
    if token_md:
        print(f"Token_MD carregado com sucesso! Primeiros 20 caracteres: {token_md[:20]}...")
    else:
        print("Token_MD NÃO foi carregado!")
else:
    print("Arquivo .env não encontrado!")
