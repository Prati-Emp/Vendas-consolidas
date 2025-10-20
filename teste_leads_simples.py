#!/usr/bin/env python3
"""
Teste simples da API de Leads
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Adicionar o diretório scripts ao path
sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))

async def main():
    print("🎯 TESTE SIMPLES DA API DE LEADS")
    print("=" * 40)
    
    # Carregar variáveis de ambiente
    load_dotenv()
    
    # Verificar variáveis
    email = os.environ.get('CVCRM_EMAIL')
    token = os.environ.get('CVCRM_TOKEN')
    motherduck = os.environ.get('MOTHERDUCK_TOKEN')
    
    print(f"CVCRM_EMAIL: {'✅' if email else '❌'}")
    print(f"CVCRM_TOKEN: {'✅' if token else '❌'}")
    print(f"MOTHERDUCK_TOKEN: {'✅' if motherduck else '❌'}")
    
    if not all([email, token, motherduck]):
        print("❌ Variáveis de ambiente faltando")
        return
    
    try:
        from scripts.cv_leads_api import obter_dados_cv_leads
        
        print("\n🚀 Coletando dados...")
        df = await obter_dados_cv_leads()
        
        print(f"\n📊 RESULTADO:")
        print(f"   - Registros: {len(df)}")
        if not df.empty:
            print(f"   - Colunas: {list(df.columns)}")
            print(f"   - Primeiros 3 registros:")
            print(df.head(3))
        
        return df
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    df = asyncio.run(main())
    if df is not None:
        print(f"\n✅ Teste concluído com sucesso!")
    else:
        print(f"\n❌ Teste falhou!")





