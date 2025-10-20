#!/usr/bin/env python3
"""
Teste da API de Repasses Workflow
Script para testar a nova API de workflow de repasses
"""

import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Adicionar o diretório scripts ao path
sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))

def main():
    """Função principal para testar a API de Repasses Workflow"""
    print("🧪 TESTE DA API DE REPASSES WORKFLOW")
    print("=" * 50)
    print(f"⏰ Timestamp: {datetime.now()}")
    
    # Carregar variáveis de ambiente
    load_dotenv()
    
    # Verificar variáveis críticas
    required_vars = ['CVCRM_EMAIL', 'CVCRM_TOKEN', 'MOTHERDUCK_TOKEN']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"❌ Variáveis de ambiente faltando: {', '.join(missing_vars)}")
        print("💡 Configure as variáveis CVCRM_EMAIL e CVCRM_TOKEN no arquivo .env")
        return False
    
    print("✅ Variáveis de ambiente configuradas")
    
    try:
        # Importar e testar a API de Repasses Workflow
        from scripts.cv_repasses_workflow_api import obter_dados_cv_repasses_workflow
        
        print("\n🚀 Testando coleta de dados CV Repasses Workflow...")
        
        # Executar com timeout de 5 minutos
        df_workflow = asyncio.run(asyncio.wait_for(obter_dados_cv_repasses_workflow(), timeout=300.0))
        
        print(f"\n📊 RESULTADO DO TESTE:")
        print(f"   - Registros coletados: {len(df_workflow):,}")
        
        if not df_workflow.empty:
            print(f"   - Colunas: {list(df_workflow.columns)}")
            print(f"   - Primeiros registros:")
            print(df_workflow.head())
            
            print(f"\n✅ TESTE CONCLUÍDO COM SUCESSO!")
            print(f"📈 A API de Repasses Workflow está funcionando corretamente")
            return True
        else:
            print(f"\n⚠️ NENHUM REGISTRO ENCONTRADO")
            print(f"🔍 Verifique se há dados na API")
            return False
            
    except asyncio.TimeoutError:
        print(f"\n⏰ TIMEOUT - Teste demorou mais de 5 minutos")
        print(f"🔍 Considere otimizar a API ou aumentar o timeout")
        return False
        
    except ImportError as e:
        print(f"\n❌ ERRO DE IMPORTAÇÃO: {e}")
        print(f"🔍 Verifique se o arquivo scripts/cv_repasses_workflow_api.py existe")
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
        print(f"\n🎉 Teste da API de Repasses Workflow executado com sucesso!")
        sys.exit(0)
    else:
        print(f"\n❌ Falha no teste da API de Repasses Workflow")
        sys.exit(1)





