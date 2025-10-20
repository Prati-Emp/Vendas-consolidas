#!/usr/bin/env python3
"""
Teste do Sistema Completo com API de Leads
Script para testar a integração completa incluindo a nova API de Leads
"""

import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

def main():
    """Função principal para testar o sistema completo com Leads"""
    print("🧪 TESTE DO SISTEMA COMPLETO COM API DE LEADS")
    print("=" * 60)
    print(f"⏰ Timestamp: {datetime.now()}")
    
    # Carregar variáveis de ambiente
    load_dotenv()
    
    # Verificar variáveis críticas
    required_vars = ['MOTHERDUCK_TOKEN', 'CVCRM_EMAIL', 'CVCRM_TOKEN', 'SIENGE_TOKEN']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"❌ Variáveis de ambiente faltando: {', '.join(missing_vars)}")
        print("💡 Configure todas as variáveis necessárias no arquivo .env")
        return False
    
    print("✅ Todas as variáveis de ambiente estão configuradas")
    
    try:
        # Importar o sistema completo
        from sistema_completo import sistema_completo
        
        print("\n🚀 Executando sistema completo com API de Leads...")
        print("⚠️ ATENÇÃO: Este teste irá fazer upload para o MotherDuck")
        print("Pressione Ctrl+C para cancelar se necessário")
        print()
        
        # Executar com timeout de 15 minutos
        sucesso = asyncio.run(asyncio.wait_for(sistema_completo(), timeout=900.0))
        
        if sucesso:
            print(f"\n✅ SISTEMA COMPLETO COM LEADS EXECUTADO COM SUCESSO!")
            print(f"📊 A tabela 'main.cv_leads' foi criada no MotherDuck")
            print(f"🌐 Você pode agora validar visualmente no dashboard")
            return True
        else:
            print(f"\n❌ FALHA NA EXECUÇÃO DO SISTEMA COMPLETO")
            print(f"🔍 Verifique os logs acima para detalhes")
            return False
            
    except asyncio.TimeoutError:
        print(f"\n⏰ TIMEOUT - Sistema demorou mais de 15 minutos")
        print(f"🔍 Considere otimizar o pipeline ou aumentar o timeout")
        return False
        
    except ImportError as e:
        print(f"\n❌ ERRO DE IMPORTAÇÃO: {e}")
        print(f"🔍 Verifique se todos os módulos estão disponíveis")
        return False
        
    except Exception as e:
        print(f"\n❌ ERRO INESPERADO: {e}")
        print(f"🔍 Verifique a configuração e conectividade")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    sucesso = main()
    if sucesso:
        print(f"\n🎉 Teste do sistema completo com Leads executado com sucesso!")
        sys.exit(0)
    else:
        print(f"\n❌ Falha no teste do sistema completo com Leads")
        sys.exit(1)





