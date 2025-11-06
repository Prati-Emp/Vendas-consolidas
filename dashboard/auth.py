"""
Sistema de autenticação para o Dashboard de Vendas
Protege o acesso aos dados sensíveis de vendas
"""

import streamlit as st
import hashlib
import os
from typing import Optional

# Configurações de segurança
ADMIN_USER = os.getenv("DASHBOARD_USER", "admin")
ADMIN_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "vendas2024")
SESSION_TIMEOUT = 3600  # 1 hora

def hash_password(password: str) -> str:
    """Cria hash da senha para comparação"""
    return hashlib.sha256(password.encode()).hexdigest()

def check_credentials(username: str, password: str) -> bool:
    """Verifica credenciais do usuário"""
    hashed_password = hash_password(password)
    stored_hash = hash_password(ADMIN_PASSWORD)
    
    return username == ADMIN_USER and hashed_password == stored_hash

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
            st.rerun()
    
    return st.session_state.authenticated

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
            if check_credentials(username, password):
                st.session_state.authenticated = True
                st.session_state.login_time = __import__('time').time()
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
    st.rerun()

def require_auth():
    """Decorator para proteger páginas que requerem autenticação"""
    if not is_authenticated():
        login_form()
        st.stop()
    
    # Mostrar informações da sessão na sidebar
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 👤 Sessão Ativa")
        st.markdown(f"**Usuário:** {ADMIN_USER}")
        
        if st.button("🚪 Sair", use_container_width=True):
            logout()

def setup_auth_environment():
    """Configura variáveis de ambiente para autenticação"""
    st.markdown("""
    <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 1rem; border-radius: 5px; margin: 1rem 0;">
        <h4>🔧 Configuração de Segurança</h4>
        <p>Para configurar credenciais personalizadas, adicione ao arquivo <code>.env</code>:</p>
        <pre>
DASHBOARD_USER=seu_usuario
DASHBOARD_PASSWORD=sua_senha_forte
        </pre>
        <p><strong>⚠️ Importante:</strong> Use senhas fortes e mantenha o arquivo .env seguro!</p>
    </div>
    """, unsafe_allow_html=True)
