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
        cols = st.columns([1, 1, 1, 0.5])  # 3 navigation items + logo space
        
        # Get current page name
        current_page = os.path.basename(st.session_state.get('current_page', 'Home.py'))
        # Navigation buttons
        with cols[0]:
            if st.button("Home", use_container_width=True):
                st.switch_page("Home.py")
        with cols[1]:
            if st.button("Leads", use_container_width=True):
                st.switch_page("pages/Leads.py")
        with cols[2]:
            if st.button("Vendas Sienge", use_container_width=True):
                st.switch_page("pages/Vendas_Sienge.py")
        
        # Logo in the last column
        with cols[3]:
            display_logo()
        
        st.markdown('</div>', unsafe_allow_html=True)

def display_logo():
    """Display the logo in the top right corner"""
    # Obter caminho da logo
    current_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(current_dir, "..", "logo.png")
    # Exibir logo
    st.image(logo_path, width=80)
