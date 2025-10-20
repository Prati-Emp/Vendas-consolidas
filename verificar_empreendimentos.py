#!/usr/bin/env python3
"""
Script para verificar quais empreendimentos estão sendo carregados
"""

import os
import sys
from dotenv import load_dotenv

# Adiciona o diretório raiz do projeto ao sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from scripts.sienge_apis import obter_lista_empreendimentos_motherduck

def verificar_empreendimentos():
    """Verifica quais empreendimentos estão sendo carregados"""
    print("🔍 VERIFICANDO EMPREENDIMENTOS CARREGADOS")
    print("=" * 50)
    
    # Carregar variáveis de ambiente
    load_dotenv()
    
    try:
        # Buscar lista de empreendimentos
        empreendimentos = obter_lista_empreendimentos_motherduck()
        
        print(f"📊 Total de empreendimentos: {len(empreendimentos)}")
        print("\n📋 Lista de empreendimentos:")
        
        for i, emp in enumerate(empreendimentos, 1):
            print(f"   {i}. ID: {emp['id']} | Nome: {emp['nome']}")
        
        print(f"\n🔍 Detalhes:")
        print(f"   - Empreendimento fixo: ID 19 (Ondina II)")
        print(f"   - Empreendimentos do MotherDuck: {len(empreendimentos) - 1}")
        
        # Verificar se há IDs duplicados
        ids = [emp['id'] for emp in empreendimentos]
        duplicados = [id for id in ids if ids.count(id) > 1]
        if duplicados:
            print(f"⚠️ IDs duplicados encontrados: {duplicados}")
        else:
            print("✅ Nenhum ID duplicado")
        
        return empreendimentos
        
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    empreendimentos = verificar_empreendimentos()
    if empreendimentos:
        print(f"\n✅ {len(empreendimentos)} empreendimentos carregados com sucesso!")
    else:
        print("\n❌ Falha ao carregar empreendimentos!")
        sys.exit(1)
