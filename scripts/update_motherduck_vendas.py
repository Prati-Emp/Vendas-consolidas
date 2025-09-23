#!/usr/bin/env python3
"""
Atualização completa do MotherDuck (agendada pelo GitHub Actions)
Reutiliza o pipeline de sistema_completo.py para garantir consistência.
"""

import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Garante import do projeto quando rodar via Actions
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

def main():
    """Função principal para execução via GitHub Actions"""
    print("🌙 INICIANDO ATUALIZAÇÃO DO MOTHERDUCK (MADRUGADA)")
    print("=" * 60)
    print(f"⏰ Timestamp: {datetime.now()}")
    print(f"🐍 Python: {sys.version}")
    print(f"📁 Working directory: {os.getcwd()}")
    
    # Carregar variáveis de ambiente (útil para desenvolvimento local)
    load_dotenv()
    
    # Verificar variáveis críticas
    required_vars = ['MOTHERDUCK_TOKEN', 'CVCRM_EMAIL', 'CVCRM_TOKEN', 'SIENGE_TOKEN']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"❌ Variáveis de ambiente faltando: {', '.join(missing_vars)}")
        sys.exit(1)
    
    print("✅ Todas as variáveis de ambiente estão configuradas")
    
    try:
        # Importar o sistema completo
        from sistema_completo import sistema_completo
        
        print("\n🚀 Executando pipeline completo de atualização...")
        
        # Executar com timeout de 15 minutos
        sucesso = asyncio.run(
            asyncio.wait_for(sistema_completo(), timeout=900.0)
        )
        
        if sucesso:
            print("\n✅ ATUALIZAÇÃO CONCLUÍDA COM SUCESSO!")
            print("🌐 Dados atualizados no MotherDuck")
            print("📊 Dashboard pode ser consultado para validação")
            sys.exit(0)
        else:
            print("\n❌ FALHA NA ATUALIZAÇÃO")
            print("🔍 Verifique os logs acima para detalhes")
            sys.exit(1)
            
    except asyncio.TimeoutError:
        print("\n⏰ TIMEOUT - Operação demorou mais de 15 minutos")
        print("🔍 Considere otimizar o pipeline ou aumentar o timeout")
        sys.exit(1)
        
    except ImportError as e:
        print(f"\n❌ ERRO DE IMPORTAÇÃO: {e}")
        print("🔍 Verifique se todos os módulos estão disponíveis")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ ERRO INESPERADO: {e}")
        print("🔍 Verifique a configuração e conectividade")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
