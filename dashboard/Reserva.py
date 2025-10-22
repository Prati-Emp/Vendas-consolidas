import streamlit as st
import sys
from pathlib import Path

# Adicionar o diretório pai ao path para importar auth
sys.path.append(str(Path(__file__).parent))

# Importar sistema de autenticação avançado
from advanced_auth import require_auth

# Proteger com autenticação
require_auth()

# Redirecionar para a página de Reservas
st.switch_page("Reservas.py")
