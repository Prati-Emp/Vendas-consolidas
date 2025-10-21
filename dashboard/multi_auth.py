"""
Sistema de autenticação multi-usuário para o Dashboard
Permite gerenciar múltiplos usuários com diferentes níveis de acesso
"""

import streamlit as st
import hashlib
import os
import json
from typing import Dict, List, Optional

# Configurações de segurança
SESSION_TIMEOUT = 3600  # 1 hora

# Estrutura de usuários (em produção, use banco de dados)
USERS_DATABASE = {
    "admin": {
        "password": "vendas2024",
        "role": "admin",
        "name": "Administrador",
        "email": "admin@empresa.com"
    },
    "gerente": {
        "password": "gerente2024",
        "role": "manager", 
        "name": "Gerente de Vendas",
        "email": "gerente@empresa.com"
    },
    "analista": {
        "password": "analista2024",
        "role": "analyst",
        "name": "Analista de Dados",
        "email": "analista@empresa.com"
    }
}

def hash_password(password: str) -> str:
    """Cria hash da senha para comparação"""
    return hashlib.sha256(password.encode()).hexdigest()

def check_credentials(username: str, password: str) -> Optional[Dict]:
    """Verifica credenciais do usuário"""
    if username in USERS_DATABASE:
        user_data = USERS_DATABASE[username]
        if user_data["password"] == password:
            return user_data
    return None

def is_authenticated() -> bool:
    """Verifica se o usuário está autenticado"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if 'login_time' not in st.session_state:
        st.session_state.login_time = None
    
    # Verificar timeout
    if st.session_state.authenticated and st.session_state.login_time:
        import time
        if time.time() - st.session_state.login_time > SESSION_TIMEOUT:
            st.session_state.authenticated = False
            st.session_state.login_time = None
            st.session_state.user_data = None
            st.rerun()
    
    return st.session_state.authenticated

def get_current_user() -> Optional[Dict]:
    """Retorna dados do usuário atual"""
    return st.session_state.get('user_data', None)

def login_form() -> bool:
    """Exibe formulário de login e retorna True se autenticado"""
    st.markdown("""
    <div style="text-align: center; padding: 2rem;">
        <h1>🔐 Acesso ao Dashboard</h1>
        <p style="color: #666;">Digite suas credenciais para acessar os dados de vendas</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("login_form"):
        st.subheader("🔑 Autenticação")
        
        username = st.text_input(
            "👤 Usuário",
            placeholder="Digite seu usuário",
            help="Usuário autorizado para acesso ao dashboard"
        )
        
        password = st.text_input(
            "🔒 Senha",
            type="password",
            placeholder="Digite sua senha",
            help="Senha de acesso ao sistema"
        )
        
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col2:
            submitted = st.form_submit_button(
                "🚀 Entrar",
                use_container_width=True,
                type="primary"
            )
        
        if submitted:
            user_data = check_credentials(username, password)
            if user_data:
                st.session_state.authenticated = True
                st.session_state.login_time = __import__('time').time()
                st.session_state.user_data = user_data
                st.success("✅ Login realizado com sucesso!")
                st.rerun()
            else:
                st.error("❌ Credenciais inválidas. Tente novamente.")
                return False
    
    # Informações de segurança
    st.markdown("---")
    st.markdown("""
    <div style="background-color: #f8f9fa; padding: 1rem; border-radius: 5px; margin-top: 2rem;">
        <h4>🛡️ Informações de Segurança</h4>
        <ul>
            <li>Este dashboard contém dados sensíveis de vendas</li>
            <li>O acesso é restrito a usuários autorizados</li>
            <li>A sessão expira automaticamente após 1 hora</li>
            <li>Para suporte, entre em contato com o administrador</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    return False

def logout():
    """Realiza logout do usuário"""
    st.session_state.authenticated = False
    st.session_state.login_time = None
    st.session_state.user_data = None
    st.rerun()

def require_auth():
    """Decorator para proteger páginas que requerem autenticação"""
    if not is_authenticated():
        login_form()
        st.stop()
    
    # Mostrar informações da sessão na sidebar
    user_data = get_current_user()
    if user_data:
        with st.sidebar:
            st.markdown("---")
            st.markdown("### 👤 Sessão Ativa")
            st.markdown(f"**Usuário:** {user_data['name']}")
            st.markdown(f"**Função:** {user_data['role'].title()}")
            
            if st.session_state.login_time:
                import time
                elapsed = int(time.time() - st.session_state.login_time)
                remaining = SESSION_TIMEOUT - elapsed
                minutes = remaining // 60
                seconds = remaining % 60
                
                st.markdown(f"**Tempo restante:** {minutes:02d}:{seconds:02d}")
            
            if st.button("🚪 Sair", use_container_width=True):
                logout()

def add_user(username: str, password: str, role: str, name: str, email: str):
    """Adiciona novo usuário ao sistema (apenas para admin)"""
    USERS_DATABASE[username] = {
        "password": password,
        "role": role,
        "name": name,
        "email": email
    }

def list_users() -> Dict:
    """Lista todos os usuários (apenas para admin)"""
    return USERS_DATABASE

def is_admin() -> bool:
    """Verifica se o usuário atual é admin"""
    user_data = get_current_user()
    return user_data and user_data.get('role') == 'admin'

def setup_auth_environment():
    """Configura variáveis de ambiente para autenticação"""
    st.markdown("""
    <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 1rem; border-radius: 5px; margin: 1rem 0;">
        <h4>🔧 Configuração de Usuários</h4>
        <p>Para adicionar novos usuários, edite o arquivo <code>multi_auth.py</code>:</p>
        <pre>
USERS_DATABASE = {
    "novo_usuario": {
        "password": "senha_forte",
        "role": "analyst",
        "name": "Nome do Usuário",
        "email": "email@empresa.com"
    }
}
        </pre>
        <p><strong>⚠️ Importante:</strong> Use senhas fortes e mantenha o arquivo seguro!</p>
    </div>
    """, unsafe_allow_html=True)
