# Arquivo __init__.py para tornar utils um pacote Python
import streamlit as st
import os

def display_navigation():
    """Display a horizontal navigation bar at the top of the page"""
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
        
        .nav-container {
            margin-bottom: 2rem;
            padding: 1rem;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Create navigation container
    with st.container():
        st.markdown('<div class="nav-container">', unsafe_allow_html=True)
        cols = st.columns([1, 1, 1, 1, 0.5])  # 4 navigation items + logo space
        
        # Get current page name
        current_page = os.path.basename(st.session_state.get('current_page', 'Home.py'))
        # Navigation buttons - Nova ordem: Vendas (1º), Reservas (2º), Leads (3º), Motivos fora do prazo (4º)
        with cols[0]:
            if st.button("Vendas", use_container_width=True):
                st.switch_page("pages/Vendas_Sienge.py")
        with cols[1]:
            if st.button("Reservas", use_container_width=True):
                st.switch_page("Reservas.py")
        with cols[2]:
            if st.button("Leads", use_container_width=True):
                st.switch_page("pages/Leads.py")
        with cols[3]:
            if st.button("Motivos fora do prazo", use_container_width=True):
                st.switch_page("pages/Motivo_fora_do_prazo.py")
        
        # Logo in the last column
        with cols[4]:
            display_logo()
        
        st.markdown('</div>', unsafe_allow_html=True)

def display_logo():
    """Display the logo in the top right corner"""
    # Obter caminho da logo
    current_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(current_dir, "..", "logo.png")
    # Exibir logo
    st.image(logo_path, width=80)
