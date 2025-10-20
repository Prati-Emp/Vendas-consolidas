#!/usr/bin/env python3
"""
Teste da API de Leads
Script para testar a integração da nova API de Leads
"""

import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Adicionar o diretório scripts ao path
sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))

def main():
    """Função principal para testar a API de Leads"""
    print("🧪 TESTE DA API DE LEADS")
    print("=" * 50)
    print(f"⏰ Timestamp: {datetime.now()}")
    
    # Carregar variáveis de ambiente
    load_dotenv()
    
    # Verificar variáveis críticas
    required_vars = ['CVCRM_EMAIL', 'CVCRM_TOKEN']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"❌ Variáveis de ambiente faltando: {', '.join(missing_vars)}")
        print("💡 Configure as variáveis CVCRM_EMAIL e CVCRM_TOKEN no arquivo .env")
        return False
    
    print("✅ Variáveis de ambiente configuradas")
    
    try:
        # Importar e testar a API de Leads
        from scripts.cv_leads_api import obter_dados_cv_leads
        
        print("\n🚀 Testando coleta de dados CV Leads...")
        
        # Executar com timeout de 5 minutos
        df_leads = asyncio.run(asyncio.wait_for(obter_dados_cv_leads(), timeout=300.0))
        
        print(f"\n📊 RESULTADO DO TESTE:")
        print(f"   - Registros coletados: {len(df_leads):,}")
        
        if not df_leads.empty:
            print(f"   - Colunas: {list(df_leads.columns)}")
            print(f"   - Primeiros registros:")
            print(df_leads.head())
            
            # Verificar filtros
            prati_count = len(df_leads[df_leads['Imobiliaria'].str.contains('Prati', case=False, na=False)])
            vazias_count = len(df_leads[df_leads['Imobiliaria'].isna() | (df_leads['Imobiliaria'] == '')])
            
            print(f"\n🔍 ANÁLISE DOS FILTROS:")
            print(f"   - Registros com 'Prati': {prati_count:,}")
            print(f"   - Registros com imobiliária vazia: {vazias_count:,}")
            print(f"   - Total filtrado: {prati_count + vazias_count:,}")
            
            print(f"\n✅ TESTE CONCLUÍDO COM SUCESSO!")
            print(f"📈 A API de Leads está funcionando corretamente")
            return True
        else:
            print(f"\n⚠️ NENHUM REGISTRO ENCONTRADO")
            print(f"🔍 Verifique se há dados na API ou se os filtros estão corretos")
            return False
            
    except asyncio.TimeoutError:
        print(f"\n⏰ TIMEOUT - Teste demorou mais de 5 minutos")
        print(f"🔍 Considere otimizar a API ou aumentar o timeout")
        return False
        
    except ImportError as e:
        print(f"\n❌ ERRO DE IMPORTAÇÃO: {e}")
        print(f"🔍 Verifique se o arquivo scripts/cv_leads_api.py existe")
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
        print(f"\n🎉 Teste da API de Leads executado com sucesso!")
        sys.exit(0)
    else:
        print(f"\n❌ Falha no teste da API de Leads")
        sys.exit(1)





