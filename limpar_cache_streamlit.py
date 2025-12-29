"""
Script para limpar cache do Streamlit
"""
import os
import shutil
import glob

# Limpar cache do Streamlit
cache_dirs = [
    ".streamlit/cache",
    "__pycache__",
    "dashboard/__pycache__",
    "dashboard/apps/__pycache__",
    "dashboard/pages/__pycache__",
    "dashboard/utils/__pycache__",
]

print("Limpando cache do Streamlit...")

for cache_dir in cache_dirs:
    if os.path.exists(cache_dir):
        try:
            if os.path.isdir(cache_dir):
                shutil.rmtree(cache_dir)
                print(f"✓ Removido: {cache_dir}")
            else:
                os.remove(cache_dir)
                print(f"✓ Removido: {cache_dir}")
        except Exception as e:
            print(f"✗ Erro ao remover {cache_dir}: {e}")

# Limpar arquivos .pyc
for root, dirs, files in os.walk('.'):
    for file in files:
        if file.endswith('.pyc'):
            try:
                os.remove(os.path.join(root, file))
                print(f"✓ Removido: {os.path.join(root, file)}")
            except Exception as e:
                print(f"✗ Erro ao remover {file}: {e}")

print("\nCache limpo! Reinicie o servidor Streamlit para aplicar as mudanças.")























