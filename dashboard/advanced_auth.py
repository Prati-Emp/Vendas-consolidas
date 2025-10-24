"""
Sistema de autenticação avançado multi-usuário para o Dashboard
Login por email com senhas complexas geradas automaticamente
"""

import streamlit as st
import hashlib
import secrets
import string
import os
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta

# Configurações de segurança
SESSION_TIMEOUT = 3600  # 1 hora
PASSWORD_LENGTH = 12
REQUIRE_SPECIAL_CHARS = True

# Base de dados de usuários (em produção, use banco de dados)
USERS_DATABASE = {
    "odair.santos@grupoprati.com": {
        "password": "Pr@ti2024!Odair",
        "role": "admin",
        "name": "Odair Santos",
        "department": "TI",
        "created": "2024-10-21",
        "last_login": None,
        "active": True
    },
    "gustavo.sordi@grupoprati.com": {
        "password": "Pr@ti2024!Gustavo",
        "role": "manager",
        "name": "Gustavo Sordi", 
        "department": "Vendas",
        "created": "2024-10-21",
        "last_login": None,
        "active": True
    },
    "lucas.follmann@grupoprati.com": {
        "password": "Pr@ti2024!Lucas",
        "role": "manager",
        "name": "Lucas Follmann",
        "department": "Vendas", 
        "created": "2024-10-21",
        "last_login": None,
        "active": True
    },
    "jose.aquino@grupoprati.com": {
        "password": "Pr@ti2024!Jose",
        "role": "analyst",
        "name": "José Aquino",
        "department": "Análise",
        "created": "2024-10-21", 
        "last_login": None,
        "active": True
    },
    "evelyn.padilha@grupoprati.com": {
        "password": "Pr@ti2024!Evelyn",
        "role": "analyst",
        "name": "Evelyn Padilha",
        "department": "Análise",
        "created": "2024-10-21",
        "last_login": None,
        "active": True
    }
}

def generate_strong_password(length: int = PASSWORD_LENGTH) -> str:
    """Gera senha forte com letras, números e símbolos"""
    characters = string.ascii_letters + string.digits
    
    if REQUIRE_SPECIAL_CHARS:
        characters += "!@#$%&*"
    
    # Garantir pelo menos um de cada tipo
    password = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase), 
        secrets.choice(string.digits),
        secrets.choice("!@#$%&*") if REQUIRE_SPECIAL_CHARS else secrets.choice(string.ascii_letters)
    ]
    
    # Completar com caracteres aleatórios
    for _ in range(length - len(password)):
        password.append(secrets.choice(characters))
    
    # Embaralhar a senha
    secrets.SystemRandom().shuffle(password)
    return ''.join(password)

def hash_password(password: str) -> str:
    """Cria hash seguro da senha"""
    salt = os.urandom(32)
    pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return salt.hex() + pwdhash.hex()

def verify_password(stored_password: str, provided_password: str) -> bool:
    """Verifica senha usando hash seguro"""
    try:
        salt = bytes.fromhex(stored_password[:64])
        stored_hash = stored_password[64:]
        pwdhash = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), salt, 100000)
        return pwdhash.hex() == stored_hash
    except:
        # Fallback para senhas não hasheadas (migração)
        return stored_password == provided_password

def check_credentials(email: str, password: str) -> Optional[Dict]:
    """Verifica credenciais do usuário"""
    if email in USERS_DATABASE:
        user_data = USERS_DATABASE[email]
        if user_data["active"] and verify_password(user_data["password"], password):
            # Atualizar último login
            user_data["last_login"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
    """Exibe formulário de login avançado"""
    st.markdown("""
    <div style="text-align: center; padding: 1.5rem; background: linear-gradient(135deg, #1e3a8a 0%, #dc2626 100%); border-radius: 8px; margin-bottom: 1.5rem;">
        <h1 style="color: white; margin: 0; font-size: 1.8rem; font-weight: 600;">🔐 Dashboard de Vendas</h1>
        <p style="color: #f3f4f6; margin: 0.5rem 0 0 0; font-size: 0.95rem;">Grupo Prati - Acesso restrito</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("login_form"):
        st.markdown("""
        <div style="background-color: #f8fafc; padding: 1rem; border-radius: 6px; border-left: 3px solid #dc2626; margin-bottom: 0.8rem;">
            <h3 style="color: #1e3a8a; margin: 0; font-size: 1.1rem;">🔑 Autenticação</h3>
        </div>
        """, unsafe_allow_html=True)
        
        email = st.text_input(
            "📧 Email",
            placeholder="seu.email@grupoprati.com",
            help="Email corporativo"
        )
        
        password = st.text_input(
            "🔒 Senha",
            type="password",
            placeholder="Digite sua senha",
            help="Senha de acesso"
        )
        
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col2:
            submitted = st.form_submit_button(
                "Entrar",
                use_container_width=True,
                type="primary"
            )
        
        if submitted:
            if not email or not password:
                st.error("❌ Por favor, preencha todos os campos.")
                return False
                
            user_data = check_credentials(email, password)
            if user_data:
                st.session_state.authenticated = True
                st.session_state.login_time = __import__('time').time()
                st.session_state.user_data = user_data
                st.success(f"✅ Bem-vindo, {user_data['name']}!")
                st.rerun()
            else:
                st.error("❌ Credenciais inválidas ou usuário inativo.")
                return False
    
    # Informações de segurança
    st.markdown("---")
    st.markdown("""
    <div style="background-color: #f8fafc; padding: 1rem; border-radius: 6px; border-left: 3px solid #1e3a8a; margin-top: 1.5rem;">
        <h4 style="color: #1e3a8a; margin: 0 0 0.8rem 0; font-size: 1rem;">🛡️ Informações de Segurança</h4>
        <ul style="color: #4b5563; margin: 0; padding-left: 1rem; font-size: 0.9rem;">
            <li style="margin-bottom: 0.3rem;">Dados confidenciais do Grupo Prati</li>
            <li style="margin-bottom: 0.3rem;">Acesso restrito a funcionários autorizados</li>
            <li style="margin-bottom: 0.3rem;">Sessão expira em 1 hora</li>
            <li style="margin-bottom: 0;">Para suporte, procure o responsável pelo desenvolvimento</li>
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
    """Protege páginas que requerem autenticação"""
    if not is_authenticated():
        login_form()
        st.stop()
    
    # Mostrar informações da sessão na sidebar
    user_data = get_current_user()
    if user_data:
        with st.sidebar:
            st.markdown("---")
            st.markdown("""
            <div style="background-color: #f8fafc; padding: 0.8rem; border-radius: 6px; border-left: 3px solid #dc2626; margin-bottom: 0.8rem;">
                <h3 style="color: #1e3a8a; margin: 0; font-size: 0.95rem;">👤 Sessão Ativa</h3>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(f"**{user_data['name']}**")
            st.markdown(f"*{user_data['role'].title()}*")
            
            if st.session_state.login_time:
                import time
                elapsed = int(time.time() - st.session_state.login_time)
                remaining = SESSION_TIMEOUT - elapsed
                minutes = remaining // 60
                seconds = remaining % 60
                
                st.markdown(f"⏱️ {minutes:02d}:{seconds:02d}")
            
            if st.button("🚪 Sair", use_container_width=True, type="primary"):
                logout()

def get_user_permissions(user_data: Dict) -> List[str]:
    """Retorna permissões do usuário baseado no role"""
    permissions = {
        'admin': ['view_all', 'edit_users', 'export_data', 'admin_panel'],
        'manager': ['view_all', 'export_data', 'view_reports'],
        'analyst': ['view_reports', 'view_dashboards']
    }
    return permissions.get(user_data['role'], ['view_dashboards'])

def get_user_pages(user_data: Dict) -> List[str]:
    """Retorna páginas que o usuário pode acessar baseado no role"""
    # Debug: mostrar dados do usuário
    import streamlit as st
    st.sidebar.info(f"🔍 Debug - Email: {user_data.get('email')}")
    st.sidebar.info(f"🔍 Debug - Nome: {user_data.get('name')}")
    
    # Odair tem acesso total
    if user_data.get('email') == 'odair.santos@grupoprati.com':
        st.sidebar.success("✅ Odair detectado - Acesso total!")
        return ['vendas', 'leads', 'reservas', 'motivo_fora_prazo']
    
    # Todos os demais usuários veem apenas Vendas
    st.sidebar.warning("⚠️ Usuário limitado - Apenas Vendas")
    return ['vendas']

def has_permission(permission: str) -> bool:
    """Verifica se usuário atual tem permissão específica"""
    user_data = get_current_user()
    if not user_data:
        return False
    return permission in get_user_permissions(user_data)

def can_access_page(page_name: str) -> bool:
    """Verifica se usuário atual pode acessar uma página específica"""
    user_data = get_current_user()
    if not user_data:
        return False
    allowed_pages = get_user_pages(user_data)
    return page_name in allowed_pages

def require_page_access(page_name: str):
    """Protege uma página específica - redireciona se usuário não tem acesso"""
    if not can_access_page(page_name):
        st.error(f"🚫 Acesso negado! Você não tem permissão para acessar esta página.")
        st.info("💡 Entre em contato com o administrador para solicitar acesso.")
        
        # Mostrar páginas disponíveis para o usuário
        user_data = get_current_user()
        if user_data:
            allowed_pages = get_user_pages(user_data)
            st.markdown("### 📋 Páginas disponíveis para você:")
            for page in allowed_pages:
                st.markdown(f"- {page.title()}")
        
        st.stop()

def is_admin() -> bool:
    """Verifica se o usuário atual é admin"""
    user_data = get_current_user()
    return user_data and user_data.get('role') == 'admin'

def get_all_users() -> Dict:
    """Retorna todos os usuários (apenas para admin)"""
    if not is_admin():
        return {}
    return USERS_DATABASE

def add_user(email: str, name: str, role: str, department: str) -> str:
    """Adiciona novo usuário (apenas para admin)"""
    if not is_admin():
        return "Acesso negado"
    
    if email in USERS_DATABASE:
        return "Usuário já existe"
    
    password = generate_strong_password()
    USERS_DATABASE[email] = {
        "password": password,
        "role": role,
        "name": name,
        "department": department,
        "created": datetime.now().strftime("%Y-%m-%d"),
        "last_login": None,
        "active": True
    }
    return f"Usuário criado com senha: {password}"

def deactivate_user(email: str) -> str:
    """Desativa usuário (apenas para admin)"""
    if not is_admin():
        return "Acesso negado"
    
    if email in USERS_DATABASE:
        USERS_DATABASE[email]["active"] = False
        return "Usuário desativado"
    return "Usuário não encontrado"

def export_user_credentials() -> str:
    """Exporta credenciais dos usuários (apenas para admin)"""
    if not is_admin():
        return "Acesso negado"
    
    credentials = []
    for email, data in USERS_DATABASE.items():
        credentials.append(f"Email: {email}")
        credentials.append(f"Senha: {data['password']}")
        credentials.append(f"Nome: {data['name']}")
        credentials.append(f"Função: {data['role']}")
        credentials.append("---")
    
    return "\n".join(credentials)

def setup_auth_environment():
    """Configura informações do sistema de autenticação"""
    st.markdown("""
    <div style="background-color: #e7f3ff; border: 1px solid #b3d9ff; padding: 1rem; border-radius: 5px; margin: 1rem 0;">
        <h4>🔧 Sistema de Autenticação - Grupo Prati</h4>
        <p><strong>Usuários Cadastrados:</strong></p>
        <ul>
            <li>Odair Santos (admin) - odair.santos@grupoprati.com</li>
            <li>Gustavo Sordi (manager) - gustavo.sordi@grupoprati.com</li>
            <li>Lucas Follmann (manager) - lucas.follmann@grupoprati.com</li>
            <li>José Aquino (analyst) - jose.aquino@grupoprati.com</li>
            <li>Evelyn Padilha (analyst) - evelyn.padilha@grupoprati.com</li>
        </ul>
        <p><strong>⚠️ Importante:</strong> Senhas são fornecidas individualmente por segurança!</p>
    </div>
    """, unsafe_allow_html=True)
