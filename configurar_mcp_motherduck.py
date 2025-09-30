#!/usr/bin/env python3
"""
Script para configurar o MCP do MotherDuck
"""

import os
import sys
import subprocess
from pathlib import Path

def find_mcp_server():
    """Encontra o caminho do servidor MCP"""
    try:
        # Tentar encontrar o executável
        result = subprocess.run(['where', 'mcp-server-motherduck'], 
                              capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            return result.stdout.strip().split('\n')[0]
    except:
        pass
    
    # Tentar caminhos comuns do Python
    python_scripts = Path.home() / "AppData" / "Local" / "Packages" / "PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0" / "LocalCache" / "local-packages" / "Python313" / "Scripts"
    mcp_path = python_scripts / "mcp-server-motherduck.exe"
    
    if mcp_path.exists():
        return str(mcp_path)
    
    return None

def create_mcp_config():
    """Cria arquivo de configuração do MCP"""
    mcp_path = find_mcp_server()
    if not mcp_path:
        print("ERRO: Servidor MCP nao encontrado!")
        return False
    
    print(f"Servidor MCP encontrado em: {mcp_path}")
    
    # Criar arquivo de configuração do MCP
    config_content = f"""# Configuração do MCP MotherDuck
# Para usar com Cursor ou outros clientes MCP

# Configuração do servidor
[mcp.servers.motherduck]
command = "{mcp_path}"
args = ["--token", "${{MOTHERDUCK_TOKEN}}"]
env = {{"MOTHERDUCK_TOKEN": "${{MOTHERDUCK_TOKEN}}"}}

# Exemplo de uso:
# 1. Configure a variável de ambiente MOTHERDUCK_TOKEN
# 2. Use este arquivo de configuração no seu cliente MCP
"""
    
    with open('mcp_config.toml', 'w', encoding='utf-8') as f:
        f.write(config_content)
    
    print("Arquivo de configuracao MCP criado: mcp_config.toml")
    return True

def test_mcp_server():
    """Testa o servidor MCP"""
    mcp_path = find_mcp_server()
    if not mcp_path:
        print("ERRO: Servidor MCP nao encontrado!")
        return False
    
    try:
        # Carregar token
        from dotenv import load_dotenv
        load_dotenv('motherduck_config.env')
        token = os.getenv('MOTHERDUCK_TOKEN')
        
        if not token:
            print("ERRO: Token do MotherDuck nao encontrado!")
            return False
        
        # Testar servidor MCP
        print("Testando servidor MCP...")
        result = subprocess.run([mcp_path, '--help'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("Servidor MCP esta funcionando!")
            return True
        else:
            print(f"ERRO no servidor MCP: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"ERRO ao testar servidor MCP: {e}")
        return False

def main():
    print("Configurando MCP do MotherDuck")
    print("=" * 40)
    
    # Encontrar servidor MCP
    print("1. Procurando servidor MCP...")
    mcp_path = find_mcp_server()
    if mcp_path:
        print(f"   Encontrado: {mcp_path}")
    else:
        print("   ERRO: Servidor MCP nao encontrado!")
        print("   Execute: pip install mcp-server-motherduck")
        return False
    
    # Criar configuração
    print("\n2. Criando arquivo de configuracao...")
    if create_mcp_config():
        print("   Arquivo de configuracao criado com sucesso!")
    else:
        print("   ERRO ao criar configuracao!")
        return False
    
    # Testar servidor
    print("\n3. Testando servidor MCP...")
    if test_mcp_server():
        print("   Servidor MCP esta funcionando!")
    else:
        print("   AVISO: Servidor MCP pode ter problemas")
    
    print("\n" + "=" * 40)
    print("Configuracao concluida!")
    print("\nPara usar o MCP:")
    print("1. Configure a variavel MOTHERDUCK_TOKEN")
    print("2. Use o arquivo mcp_config.toml no seu cliente MCP")
    print("3. Ou execute diretamente: mcp-server-motherduck --token SEU_TOKEN")
    
    return True

if __name__ == "__main__":
    main()



