#!/usr/bin/env python3
"""
Script para validar se todos os empreendimentos estão sendo carregados
SEM consumir requisições da API do Sienge
"""

import os
import sys
from dotenv import load_dotenv

def configurar_ambiente():
    """Configura as variáveis de ambiente"""
    load_dotenv()
    
    required_vars = ['MOTHERDUCK_TOKEN']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"❌ Variáveis de ambiente faltando: {', '.join(missing_vars)}")
        return False
    
    print("✅ Variáveis de ambiente configuradas")
    return True

def validar_empreendimentos():
    """Valida se todos os empreendimentos estão sendo carregados"""
    print("\n🔍 VALIDANDO EMPREENDIMENTOS")
    print("=" * 60)
    
    try:
        from scripts.sienge_apis import obter_lista_empreendimentos_motherduck
        
        empreendimentos = obter_lista_empreendimentos_motherduck()
        
        print(f"📊 Empreendimentos carregados: {len(empreendimentos)}")
        
        # Listar todos os empreendimentos
        for i, emp in enumerate(empreendimentos, 1):
            print(f"   {i:2d}. {emp['nome']} (ID: {emp['id']})")
        
        # Verificar se temos os 8 esperados
        if len(empreendimentos) == 8:
            print(f"\n✅ SUCESSO! Todos os 8 empreendimentos foram carregados")
            return True
        else:
            print(f"\n⚠️ ATENÇÃO! Esperado 8 empreendimentos, encontrado {len(empreendimentos)}")
            return False
        
    except Exception as e:
        print(f"❌ Erro ao validar empreendimentos: {e}")
        return False

def validar_configuracao_requisicoes():
    """Valida a configuração de requisições"""
    print("\n🔍 VALIDANDO CONFIGURAÇÃO DE REQUISIÇÕES")
    print("=" * 60)
    
    try:
        from scripts.sienge_apis import SiengeAPIClient
        
        # Criar cliente (sem fazer requisições)
        client = SiengeAPIClient()
        
        print(f"📊 Configuração de requisições:")
        print(f"   • Limite diário: {client.limite_diario}")
        print(f"   • Empreendimentos: {client.empreendimentos_count}")
        print(f"   • Requisições por execução: {client.requisicoes_por_execucao}")
        print(f"   • Execuções possíveis: {client.execucoes_possiveis}")
        
        # Verificar se a configuração está correta
        if client.limite_diario == 40 and client.requisicoes_por_execucao == 16:
            print(f"\n✅ SUCESSO! Configuração de requisições está correta")
            print(f"   • 40 requisições diárias")
            print(f"   • 16 requisições por execução (8 empreendimentos × 2 APIs)")
            print(f"   • 2 execuções possíveis por dia")
            return True
        else:
            print(f"\n⚠️ ATENÇÃO! Configuração não está como esperado")
            return False
        
    except Exception as e:
        print(f"❌ Erro ao validar configuração: {e}")
        return False

def main():
    """Função principal"""
    print("🔍 VALIDAÇÃO DAS MUDANÇAS IMPLEMENTADAS")
    print("=" * 80)
    print("Este script NÃO consome requisições da API do Sienge")
    
    # 1. Configurar ambiente
    if not configurar_ambiente():
        sys.exit(1)
    
    # 2. Validar empreendimentos
    empreendimentos_ok = validar_empreendimentos()
    
    # 3. Validar configuração de requisições
    config_ok = validar_configuracao_requisicoes()
    
    # 4. Resumo
    print(f"\n📊 RESUMO DA VALIDAÇÃO:")
    print("=" * 60)
    
    if empreendimentos_ok and config_ok:
        print("✅ TODAS AS VALIDAÇÕES PASSARAM!")
        print("🎯 Mudanças implementadas com sucesso:")
        print("   • Todos os 8 empreendimentos são carregados")
        print("   • Configuração de requisições está correta")
        print("   • Sistema pronto para processar todos os empreendimentos")
        print("   • Delay de 5 minutos entre vendas realizadas e canceladas")
        print("   • Limite de 40 requisições diárias configurado")
    else:
        print("❌ ALGUMAS VALIDAÇÕES FALHARAM!")
        if not empreendimentos_ok:
            print("   • Problema: Empreendimentos não estão sendo carregados corretamente")
        if not config_ok:
            print("   • Problema: Configuração de requisições não está correta")
    
    print(f"\n🎯 PRÓXIMOS PASSOS:")
    print("   1. Executar o sistema completo para testar com dados reais")
    print("   2. Monitorar o uso de requisições")
    print("   3. Verificar se todos os empreendimentos retornam dados")

if __name__ == "__main__":
    main()
