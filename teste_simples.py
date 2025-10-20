#!/usr/bin/env python3
"""
Teste simples para verificar se as alterações funcionam
"""

import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Adiciona o diretório raiz do projeto ao sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

async def teste_simples():
    print("🧪 TESTE SIMPLES SIENGE")
    print("=" * 30)
    
    # Carregar variáveis de ambiente
    load_dotenv()
    
    # Verificar variáveis
    print(f"SIENGE_TOKEN: {'✅' if os.environ.get('SIENGE_TOKEN') else '❌'}")
    print(f"MOTHERDUCK_TOKEN: {'✅' if os.environ.get('MOTHERDUCK_TOKEN') else '❌'}")
    
    try:
        from scripts.sienge_apis import SiengeAPIClient
        
        # Criar cliente
        client = SiengeAPIClient()
        
        # Data atual
        data_fim = datetime.now().strftime('%Y-%m-%d')
        
        print(f"\n📅 Período: 2020-01-01 a {data_fim}")
        print(f"🏢 Empreendimentos: {len(client.empreendimentos)}")
        
        # Testar vendas realizadas
        print("\n🔍 Testando vendas realizadas...")
        resultado = await client.get_vendas_realizadas('2020-01-01', data_fim)
        
        if resultado.get('success'):
            print("✅ Sucesso!")
            dados = resultado.get('data', {})
            print(f"📊 Dados: {dados}")
        else:
            print(f"❌ Erro: {resultado.get('error', 'Erro desconhecido')}")
        
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(teste_simples())
