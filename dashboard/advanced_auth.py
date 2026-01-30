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
SESSION_TIMEOUT = 57600  # 16 horas (aumentado de 1h para garantir que a TV não desconecte)
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
        "active": True,
        "subpages": ["operacoes.jira", "operacoes.compras", "operacoes.solicitacoes", "operacoes.contratos", "administrativo.repasses", "administrativo.contas_pagas", "administrativo.saldo_em_caixa", "administrativo.rh"]  # Páginas subordinadas permitidas
    },
    "gustavo.sordi@grupoprati.com": {
        "password": "Pr@ti2024!Gustavo",
        "role": "manager",
        "name": "Gustavo Sordi", 
        "department": "Vendas",
        "created": "2024-10-21",
        "last_login": None,
        "active": True,
        "subpages": ["operacoes.jira", "operacoes.compras", "operacoes.solicitacoes", "operacoes.contratos", "administrativo.repasses", "administrativo.contas_pagas", "administrativo.saldo_em_caixa", "administrativo.rh"]
    },
    "lucas.follmann@grupoprati.com": {
        "password": "Pr@ti2024!Lucas",
        "role": "manager",
        "name": "Lucas Follmann",
        "department": "Vendas", 
        "created": "2024-10-21",
        "last_login": None,
        "active": True,
        "subpages": ["operacoes.jira", "operacoes.compras", "operacoes.solicitacoes", "operacoes.contratos", "operacoes.evolucao_obra", "administrativo.repasses"]
    },
    "jose.aquino@grupoprati.com": {
        "password": "Pr@ti2024!Jose",
        "role": "analyst",
        "name": "José Aquino",
        "department": "Análise",
        "created": "2024-10-21", 
        "last_login": None,
        "active": True,
        "subpages": ["operacoes.jira"]  # Apenas acesso ao Jira
    },
    "evelyn.padilha@grupoprati.com": {
        "password": "Pr@ti2024!Evelyn",
        "role": "analyst",
        "name": "Evelyn Padilha",
        "department": "Análise",
        "created": "2024-10-21",
        "last_login": None,
        "active": True,
        "subpages": ["operacoes.jira"]  # Apenas acesso ao Jira
    },
    "joao.fantinel@grupoprati.com": {
        "password": "0sIOnX%d9@sz",
        "role": "analyst",
        "name": "João Fantinel",
        "department": "Operações",
        "created": "2025-01-23",
        "last_login": None,
        "active": True,
        "subpages": ["operacoes.jira"],  # Apenas acesso ao Jira no Operações
        "pages": ["vendas", "operacoes", "administrativo"]  # Liberado para Vendas, Operações e Administrativo
    },
    "andre.pozza@grupoprati.com": {
        "password": "EcwSG52eL&qk",
        "role": "analyst",
        "name": "André Pozza",
        "department": "Operações",
        "created": "2025-01-23",
        "last_login": None,
        "active": True,
        "subpages": ["operacoes.jira", "operacoes.compras", "operacoes.solicitacoes", "operacoes.contratos", "operacoes.evolucao_obra"]
    },
    "raul.lunkes@grupoprati.com": {
        "password": "Pr@ti2025!Raul",
        "role": "analyst",
        "name": "Raul Lunkes",
        "department": "Operações",
        "created": "2025-12-19",
        "last_login": None,
        "active": True,
        "pages": ["operacoes"],
        "subpages": ["operacoes.jira", "operacoes.compras", "operacoes.solicitacoes", "operacoes.contratos", "operacoes.evolucao_obra"]
    },
    "michael.seidenstucker@grupoprati.com": {
        "password": "Pr@ti2025!Michael",
        "role": "analyst",
        "name": "Michael Seidenstucker",
        "department": "Operações",
        "created": "2025-12-19",
        "last_login": None,
        "active": True,
        "pages": ["operacoes"],
        "subpages": ["operacoes.jira"]
    },
    "italo.peres@grupoprati.com": {
        "password": "Pr@ti2024!Italo",
        "role": "manager",
        "name": "Ítalo Peres",
        "department": "Vendas",
        "created": "2025-11-26",
        "last_login": None,
        "active": True,
        "subpages": ["operacoes.jira", "operacoes.compras", "operacoes.solicitacoes", "operacoes.contratos", "operacoes.evolucao_obra"]
    },
    "comercial.tv@grupoprati.com": {
        "password": "comercial@TV!25",
        "role": "analyst",
        "name": "TV Comercial",
        "department": "Vendas",
        "created": "2025-12-17",
        "last_login": None,
        "active": True,
        "pages": ["tv_comercial"],  # Acesso restrito apenas à TV Comercial
        "subpages": []
    },
    "marlos.bendo@grupoprati.com": {
        "password": "Pr@ti2025!Marlos",
        "role": "analyst",
        "name": "Marlos Bendo",
        "department": "Administrativo",
        "created": "2026-01-15",
        "last_login": None,
        "active": True,
        "pages": ["vendas", "leads", "reservas", "motivo_fora_prazo", "administrativo"],  # Acesso ao dashboard de reservas e administrativo
        "subpages": ["administrativo.repasses", "administrativo.contas_pagas", "administrativo.saldo_em_caixa"]  # RH oculto
    },
    "ricardo@grupoprati.com": {
        "password": "Pr@ti2025!Ricardo",
        "role": "analyst",
        "name": "Ricardo",
        "department": "Administrativo",
        "created": "2026-01-29",
        "last_login": None,
        "active": True,
        "pages": ["vendas", "leads", "reservas", "motivo_fora_prazo", "administrativo"],  # Acesso ao dashboard de reservas e administrativo
        "subpages": ["administrativo.repasses", "administrativo.saldo_em_caixa"]  # Contas Pagas e RH ocultos
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
        user_data = USERS_DATABASE[email].copy()  # Fazer cópia para não modificar o original
        if user_data["active"] and verify_password(user_data["password"], password):
            # Atualizar último login
            user_data["last_login"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # Adicionar email aos dados do usuário
            user_data["email"] = email
            return user_data
    return None

def is_authenticated(disable_timeout: bool = False) -> bool:
    """Verifica se o usuário está autenticado"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if 'login_time' not in st.session_state:
        st.session_state.login_time = None
    
    # Verificar timeout (desabilitado se disable_timeout=True)
    if not disable_timeout and st.session_state.authenticated and st.session_state.login_time:
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

def login_form(dashboard_title: str = "Dashboard de Vendas") -> bool:
    """Exibe formulário de login avançado"""
    st.markdown(f"""
    <div style="text-align: center; padding: 1.5rem; background: linear-gradient(135deg, #1e3a8a 0%, #dc2626 100%); border-radius: 8px; margin-bottom: 1.5rem;">
        <h1 style="color: white; margin: 0; font-size: 1.8rem; font-weight: 600;">🔐 {dashboard_title}</h1>
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
    
    return False

def logout():
    """Realiza logout do usuário"""
    st.session_state.authenticated = False
    st.session_state.login_time = None
    st.session_state.user_data = None
    st.rerun()

def require_auth(disable_timeout: bool = False, dashboard_title: str = "Dashboard de Vendas"):
    """Protege páginas que requerem autenticação"""
    if not is_authenticated(disable_timeout=disable_timeout):
        login_form(dashboard_title=dashboard_title)
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
    if not user_data:
        return ['vendas']

    # Permite configuração específica por usuário quando "pages" estiver definido
    custom_pages = user_data.get("pages")
    if custom_pages:
        return custom_pages

    # Usuários cadastrados têm acesso total por padrão
    if user_data.get('email') in USERS_DATABASE:
        return ['vendas', 'leads', 'reservas', 'operacoes', 'administrativo', 'motivo_fora_prazo']
    
    # Usuários não cadastrados veem apenas Vendas
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
    
    # Verificar páginas principais
    allowed_pages = get_user_pages(user_data)
    if page_name in allowed_pages:
        return True
    
    # Verificar páginas subordinadas (ex: "operacoes.jira")
    if "." in page_name:
        # Se o usuário tem acesso à página principal, verificar subpáginas
        main_page = page_name.split(".")[0]
        if main_page in allowed_pages:
            # Verificar se o usuário tem acesso específico à subpágina
            user_subpages = user_data.get("subpages", [])
            # Se não há subpages definidas, dar acesso total (compatibilidade)
            if not user_subpages:
                return True

            # Se não há subpáginas específicas para este domínio, liberar acesso por padrão
            has_specific_for_main = any(sp.startswith(f"{main_page}.") for sp in user_subpages)
            if not has_specific_for_main:
                return True

            # Verificar se a subpágina está na lista permitida
            return page_name in user_subpages
    
    return False

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
            <li>Ítalo Peres (manager) - italo.peres@grupoprati.com</li>
            <li>José Aquino (analyst) - jose.aquino@grupoprati.com</li>
            <li>Evelyn Padilha (analyst) - evelyn.padilha@grupoprati.com</li>
            <li>João Fantinel (analyst) - joao.fantinel@grupoprati.com</li>
            <li>André Pozza (analyst) - andre.pozza@grupoprati.com</li>
            <li>Raul Lunkes (analyst) - raul.lunkes@grupoprati.com</li>
            <li>Michael Seidenstucker (analyst) - michael.seidenstucker@grupoprati.com</li>
            <li>Marlos Bendo (analyst) - marlos.bendo@grupoprati.com</li>
            <li>Ricardo (analyst) - ricardo@grupoprati.com</li>
        </ul>
        <p><strong>⚠️ Importante:</strong> Senhas são fornecidas individualmente por segurança!</p>
    </div>
    """, unsafe_allow_html=True)
