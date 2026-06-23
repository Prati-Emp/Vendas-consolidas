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

# Base de dados de usuarios — arquivo local ou PORTAL_USERS_JSON (Streamlit Cloud)
from pathlib import Path as _Path

_users_database: Optional[dict] = None
_users_load_error: Optional[str] = None

def _to_plain_dict(value):
    """Converte AttrDict / SecretDict do Streamlit em dict Python."""
    if isinstance(value, dict):
        return {str(k): _to_plain_dict(v) for k, v in value.items()}
    if hasattr(value, "_to_dict"):
        return _to_plain_dict(value._to_dict())
    if hasattr(value, "keys") and not isinstance(value, (str, bytes)):
        try:
            return {str(k): _to_plain_dict(value[k]) for k in value.keys()}
        except Exception:
            pass
    return value


def _parse_users_payload(raw) -> dict:
    if isinstance(raw, dict):
        return _to_plain_dict(raw)
    if isinstance(raw, str):
        text = raw.strip().lstrip("\ufeff")
        if text.startswith('"""') and text.endswith('"""'):
            text = text[3:-3].strip()
        elif text.startswith("'''") and text.endswith("'''"):
            text = text[3:-3].strip()
        if text:
            return json.loads(text)
    raise ValueError("Formato de usuarios invalido")


def _looks_like_users_database(data: dict) -> bool:
    if not data:
        return False
    return any(
        isinstance(value, dict) and "password" in value
        for value in data.values()
    )


def _coerce_users_database(raw) -> dict:
    data = _parse_users_payload(raw)
    if not isinstance(data, dict) or not _looks_like_users_database(data):
        raise ValueError("JSON de usuarios invalido ou incompleto")
    return data


def _load_from_secrets_file() -> Optional[dict]:
    """Fallback: le secrets.toml montado pelo Streamlit Cloud."""
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore
        except ImportError:
            return None

    root = _Path(__file__).resolve().parent.parent
    dashboard = root / "dashboard"
    candidates = [
        dashboard / ".streamlit" / "secrets.toml",
        root / ".streamlit" / "secrets.toml",
    ]
    for child in sorted(root.glob("streamlit_*")):
        if child.is_dir():
            candidates.append(child / ".streamlit" / "secrets.toml")

    for path in candidates:
        if not path.exists():
            continue
        try:
            data = tomllib.loads(path.read_bytes())
            for key in ("PORTAL_USERS_JSON", "portal_users_json", "portal_users"):
                if key in data and data[key]:
                    return _coerce_users_database(data[key])
        except Exception:
            continue
    return None


def _load_from_streamlit_secrets() -> Optional[dict]:
    errors: List[str] = []

    for key in ("PORTAL_USERS_JSON", "portal_users_json"):
        raw = os.environ.get(key, "").strip()
        if raw:
            try:
                return _coerce_users_database(raw)
            except Exception as exc:
                errors.append(f"env {key}: {exc}")

    try:
        secrets = st.secrets
    except Exception as exc:
        errors.append(f"st.secrets indisponivel: {exc}")
        secrets = None

    if secrets is not None:
        for key in ("PORTAL_USERS_JSON", "portal_users_json", "portal_users"):
            raw = None
            try:
                if hasattr(secrets, "get"):
                    raw = secrets.get(key)
            except Exception:
                raw = None
            if raw is None:
                try:
                    raw = secrets[key]
                except Exception:
                    raw = None
            if raw:
                try:
                    return _coerce_users_database(raw)
                except Exception as exc:
                    errors.append(f"secrets {key}: {exc}")

        try:
            raw = getattr(secrets, "PORTAL_USERS_JSON", None)
            if raw:
                return _coerce_users_database(raw)
        except Exception as exc:
            errors.append(f"secrets attr: {exc}")

        # Usuario colou o JSON direto na raiz dos secrets (emails como chaves)
        root_users: dict = {}
        try:
            for key in secrets:
                key_str = str(key)
                if "@" not in key_str:
                    continue
                try:
                    value = secrets[key]
                except Exception:
                    continue
                if isinstance(value, dict) and "password" in value:
                    root_users[key_str] = dict(value)
        except Exception as exc:
            errors.append(f"secrets root scan: {exc}")
        if root_users:
            return root_users

    file_users = _load_from_secrets_file()
    if file_users:
        return file_users

    if errors:
        raise ValueError("; ".join(errors))
    return None


def _load_users_database() -> dict:
    users_file = _Path(__file__).resolve().parent / "portal_users.json"

    if users_file.exists():
        with users_file.open(encoding="utf-8") as f:
            return _coerce_users_database(json.load(f))

    cloud_users = _load_from_streamlit_secrets()
    if cloud_users:
        return cloud_users

    raise FileNotFoundError(
        "Usuarios do portal nao configurados. "
        "Streamlit Cloud: cole o conteudo de dashboard/PORTAL_USERS_JSON_PARA_STREAMLIT.toml "
        "em Settings -> Secrets e salve."
    )


def _diagnose_users_config() -> str:
    hints: List[str] = []
    env_val = os.environ.get("PORTAL_USERS_JSON", "")
    hints.append(f"env PORTAL_USERS_JSON: {'sim' if env_val else 'nao'} ({len(env_val)} chars)")

    try:
        in_secrets = "PORTAL_USERS_JSON" in st.secrets
        hints.append(f"st.secrets PORTAL_USERS_JSON: {'sim' if in_secrets else 'nao'}")
        if in_secrets:
            raw = st.secrets["PORTAL_USERS_JSON"]
            hints.append(f"tipo={type(raw).__name__}, chars={len(str(raw))}")
    except Exception as exc:
        hints.append(f"st.secrets erro: {exc}")

    secrets_file = _Path(__file__).resolve().parent / ".streamlit" / "secrets.toml"
    hints.append(f"secrets.toml: {'sim' if secrets_file.exists() else 'nao'}")
    return " | ".join(hints)


def reset_users_database_cache() -> None:
    """Limpa cache apos alterar secrets (util em testes)."""
    global _users_database, _users_load_error
    _users_database = None
    _users_load_error = None


def get_users_database() -> dict:
    """Carrega usuarios sob demanda (evita erro na importacao do modulo)."""
    global _users_database, _users_load_error
    if _users_database is not None:
        return _users_database
    try:
        _users_database = _load_users_database()
        _users_load_error = None
    except Exception as exc:
        _users_load_error = str(exc)
        _users_database = {}
    return _users_database


def _ensure_users_configured() -> bool:
    db = get_users_database()
    if db:
        return True

    st.error("Configuracao de usuarios do portal ausente.")
    st.markdown(
        """
**Para o administrador:**

1. Abra **Manage app → Settings → Secrets** no Streamlit Cloud
2. Cole o conteúdo de `dashboard/PORTAL_USERS_JSON_PARA_STREAMLIT.toml`
3. **Importante:** use o formato com aspas simples por fora (`PORTAL_USERS_JSON = '...'`)
   — não use aspas duplas `"` envolvendo o JSON diretamente, isso invalida o TOML
4. Mantenha também os outros secrets do app (ex.: `MOTHERDUCK_TOKEN`)
5. Salve e aguarde o app reiniciar
        """
    )
    st.caption(_diagnose_users_config())
    if _users_load_error:
        st.caption(f"Detalhe: {_users_load_error}")
    return False


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
    users_db = get_users_database()
    if email in users_db:
        user_data = users_db[email].copy()  # Fazer cópia para não modificar o original
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
    if not _ensure_users_configured():
        return False

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
    if user_data.get('email') in get_users_database():
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
    return get_users_database()

def add_user(email: str, name: str, role: str, department: str) -> str:
    """Adiciona novo usuário (apenas para admin)"""
    if not is_admin():
        return "Acesso negado"

    users_db = get_users_database()
    if email in users_db:
        return "Usuário já existe"
    
    password = generate_strong_password()
    users_db[email] = {
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
    
    users_db = get_users_database()
    if email in users_db:
        users_db[email]["active"] = False
        return "Usuário desativado"
    return "Usuário não encontrado"

def export_user_credentials() -> str:
    """Exporta credenciais dos usuários (apenas para admin)"""
    if not is_admin():
        return "Acesso negado"
    
    credentials = []
    for email, data in get_users_database().items():
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
            <li>Frederico Ferreira (analyst) - frederico.ferreira@grupoprati.com</li>
            <li>Allana Oliveira (analyst) - allana.oliveira@grupoprati.com</li>
            <li>Fernanda Tomio (analyst) - fernanda.tomio@grupoprati.com</li>
            <li>Vitoria Almeida (analyst) - vitoria.almeida@grupoprati.com</li>
            <li>Raul Lunkes (analyst) - raul.lunkes@grupoprati.com</li>
            <li>Michael Seidenstucker (analyst) - michael.seidenstucker@grupoprati.com</li>
            <li>Marlos Bendo (analyst) - marlos.bendo@grupoprati.com</li>
            <li>Ricardo (analyst) - ricardo@grupoprati.com</li>
            <li>Gustavo Prati (analyst) - GustavoPrati@Pratiemp318.onmicrosoft.com</li>
            <li>Lucas Moura (analyst) - lucas.moura@grupoprati.com</li>
            <li>Guilherme Stenzel (analyst) - guilherme.stenzel@grupoprati.com</li>
            <li>Camila Almeida (analyst) - camila.almeida@grupoprati.com</li>
            <li>Pamela Elias (analyst) - pamela.elias@grupoprati.com</li>
            <li>Cristiane Barbosa (analyst) - cristiane.barbosa@grupoprati.com</li>
            <li>Diogo Senise (analyst) - diogo.senise@grupoprati.com</li>
            <li>Jackson Frey (analyst) - jackson.frey@grupoprati.com</li>
            <li>Tarcisio Costa (analyst) - tarcisio.costa@grupoprati.com</li>
            <li>Karina Amorim (analyst) - karina.amorim@grupoprati.com</li>
            <li>Patricia Cruz (analyst) - patricia.cruz@grupoprati.com</li>
        </ul>
        <p><strong>⚠️ Importante:</strong> Senhas são fornecidas individualmente por segurança!</p>
    </div>
    """, unsafe_allow_html=True)
