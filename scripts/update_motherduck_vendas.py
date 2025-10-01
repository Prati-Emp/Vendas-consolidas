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

# Importar controle de concorrência
from scripts.concurrency_control import check_concurrency, release_concurrency

def main():
    """Função principal para execução via GitHub Actions"""
    print("🌙 INICIANDO ATUALIZAÇÃO DO MOTHERDUCK (MADRUGADA)")
    print("=" * 60)
    print(f"⏰ Timestamp: {datetime.now()}")
    print(f"🐍 Python: {sys.version}")
    print(f"📁 Working directory: {os.getcwd()}")
    
    # CORREÇÃO: Verificar concorrência antes de executar
    print("\n🔒 Verificando controle de concorrência...")
    if not check_concurrency():
        print("❌ Outro workflow está executando. Abortando para evitar conflitos.")
        sys.exit(1)
    print("✅ Controle de concorrência OK - Prosseguindo com execução")
    
    # Carregar variáveis de ambiente (útil para desenvolvimento local)
    load_dotenv()
    
    # Verificar variáveis críticas
    required_vars = ['MOTHERDUCK_TOKEN', 'CVCRM_EMAIL', 'CVCRM_TOKEN', 'SIENGE_TOKEN']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"❌ Variáveis de ambiente faltando: {', '.join(missing_vars)}")
        release_concurrency()  # Liberar lock em caso de erro
        sys.exit(1)
    
    print("✅ Todas as variáveis de ambiente estão configuradas")
    
    try:
        # Importar o sistema completo
        from sistema_completo import sistema_completo
        
        print("\n🚀 Executando pipeline completo de atualização...")
        # Permitir pausar canceladas via env (para economizar requisições)
        # Quando SIENGE_SKIP_CANCELADAS=true, vamos forçar retorno vazio para canceladas
        if os.environ.get('SIENGE_SKIP_CANCELADAS', 'false').lower() == 'true':
            os.environ['SIENGE_APENAS_REALIZADAS'] = 'true'
        
        # Executar com timeout de 15 minutos
        sucesso = asyncio.run(asyncio.wait_for(sistema_completo(), timeout=900.0))
        
        if sucesso:
            print("\n✅ ATUALIZAÇÃO CONCLUÍDA COM SUCESSO!")
            print("🌐 Dados atualizados no MotherDuck")
            print("📊 Dashboard pode ser consultado para validação")
            release_concurrency()  # Liberar lock em caso de sucesso
            sys.exit(0)
        else:
            print("\n❌ FALHA NA ATUALIZAÇÃO")
            print("🔍 Verifique os logs acima para detalhes")
            release_concurrency()  # Liberar lock em caso de falha
            sys.exit(1)
            
    except asyncio.TimeoutError:
        print("\n⏰ TIMEOUT - Operação demorou mais de 15 minutos")
        print("🔍 Considere otimizar o pipeline ou aumentar o timeout")
        release_concurrency()  # Liberar lock em caso de timeout
        sys.exit(1)
        
    except ImportError as e:
        print(f"\n❌ ERRO DE IMPORTAÇÃO: {e}")
        print("🔍 Verifique se todos os módulos estão disponíveis")
        release_concurrency()  # Liberar lock em caso de erro de importação
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ ERRO INESPERADO: {e}")
        print("🔍 Verifique a configuração e conectividade")
        import traceback
        traceback.print_exc()
        release_concurrency()  # Liberar lock em caso de erro inesperado
        sys.exit(1)

if __name__ == "__main__":
    main()
