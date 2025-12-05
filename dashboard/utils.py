import streamlit as st
import os
import sys
from pathlib import Path

# Adicionar o diretório pai ao path para importar auth
sys.path.append(str(Path(__file__).parent.parent))

def display_navigation():
    """Display a horizontal navigation bar at the top of the page with access control"""
    # Importar sistema de autenticação avançado dentro da função para evitar importação circular
    try:
        from advanced_auth import can_access_page, get_current_user
    except ImportError:
        # Se não conseguir importar, usar navegação básica sem controle de acesso
        st.warning("⚠️ Sistema de autenticação não disponível. Usando navegação básica.")
        return
    
    # Custom CSS for the navigation bar
    st.markdown("""
        <style>
        .stButton button {
            width: 100%;
            background-color: transparent;
            padding: 10px;
            border-radius: 5px;
            border: 1px solid rgba(128, 128, 128, 0.4);
            transition: all 0.3s ease;
        }
        
        .stButton button:hover {
            border-color: rgba(128, 128, 128, 0.8);
        }
        
        .stButton button:disabled {
            opacity: 0.3;
            cursor: not-allowed;
        }
        
        .nav-container {
            margin-bottom: 2rem;
            padding: 1rem;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Get current user and their permissions
    user_data = get_current_user()
    
    # Create navigation container
    with st.container():
        st.markdown('<div class="nav-container">', unsafe_allow_html=True)
        
        # Define navigation items with their access requirements
        nav_items = [
            ("Home", "home", "pages/1_Vendas.py"),
            ("Vendas", "vendas", "pages/1_Vendas.py"),
            ("Leads", "leads", "pages/2_Leads.py"),
            ("Reservas", "reservas", "pages/3_Reservas.py"),
            ("Motivo Fora do Prazo", "motivo_fora_prazo", "pages/4_Motivo_fora_do_prazo.py")
        ]
        
        # Calculate number of accessible items
        accessible_items = [item for item in nav_items if can_access_page(item[1])]
        num_cols = len(accessible_items) + 1  # +1 for logo
        
        if num_cols > 1:
            cols = st.columns([1] * (num_cols - 1) + [0.5])  # Navigation items + logo space
            
            col_idx = 0
            for item_name, page_key, page_path in nav_items:
                if can_access_page(page_key):
                    with cols[col_idx]:
                        if st.button(item_name, use_container_width=True):
                            st.switch_page(page_path)
                    col_idx += 1
            
            # Logo in the last column
            with cols[-1]:
                display_logo()
        
        st.markdown('</div>', unsafe_allow_html=True)

def display_logo():
    """Display the logo in the top right corner"""
    # Obter caminho da logo
    current_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(current_dir, "logo.png")
    # Exibir logo
    st.image(logo_path, width=80)
