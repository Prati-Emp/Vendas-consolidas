"""
Configurações centralizadas e seguras para o dashboard
"""
import os
import streamlit as st
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

class SecureConfig:
    """Classe para gerenciar configurações de forma segura"""
    
    @staticmethod
    def get_motherduck_token():
        """Obtém token do MotherDuck de forma segura"""
        token = st.secrets.get("MOTHERDUCK_TOKEN", os.getenv("MOTHERDUCK_TOKEN", ""))
        if not token:
            st.error("Token do MotherDuck não configurado. Verifique as configurações de secrets.")
            st.stop()
        return token.strip()
    
    @staticmethod
    def get_cvcrm_credentials():
        """Obtém credenciais do CVCRM de forma segura"""
        email = st.secrets.get("CVCRM_EMAIL", os.getenv("CVCRM_EMAIL", ""))
        token = st.secrets.get("CVCRM_TOKEN", os.getenv("CVCRM_TOKEN", ""))
        
        if not email or not token:
            st.error("Credenciais CVCRM não configuradas. Verifique as configurações de secrets.")
            return None, None
            
        return email.strip(), token.strip()
    
    @staticmethod
    def get_motherduck_connection_string():
        """Retorna string de conexão segura para MotherDuck"""
        token = SecureConfig.get_motherduck_token()
        return f"md:reservas?token={token}"
    
    @staticmethod
    def get_cvcrm_headers():
        """Retorna headers seguros para API CVCRM"""
        email, token = SecureConfig.get_cvcrm_credentials()
        if not email or not token:
            return None
            
        return {
            "accept": "application/json",
            "email": email,
            "token": token,
        }
