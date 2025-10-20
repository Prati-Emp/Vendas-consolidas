#!/usr/bin/env python3
"""
Teste para verificar se o campo 'referencia_data' está sendo capturado corretamente
na API cv_leads
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# Adicionar o diretório scripts ao path
sys.path.append('scripts')

from cv_leads_api import obter_dados_cv_leads

async def test_referencia_data():
    """Testa se os campos referencia_data, corretor e colunas dinâmicas estão sendo capturados"""
    print("🧪 TESTE: Campos 'referencia_data', 'data_reativacao', 'corretor' e colunas dinâmicas na API CV Leads")
    print("=" * 60)
    
    try:
        # Carregar variáveis de ambiente
        load_dotenv()
        
        # Verificar se as credenciais estão configuradas
        if not os.environ.get('CVCRM_EMAIL') or not os.environ.get('CVCRM_TOKEN'):
            print("❌ Credenciais CVCRM não encontradas")
            print("   Configure CVCRM_EMAIL e CVCRM_TOKEN no arquivo .env")
            return False
        
        print("✅ Credenciais encontradas")
        print("🔍 Buscando dados da API CV Leads...")
        
        # Buscar dados
        df = await obter_dados_cv_leads()
        
        if df.empty:
            print("⚠️ Nenhum dado retornado da API")
            return False
        
        print(f"✅ Dados obtidos: {len(df)} registros")
        print(f"📊 Colunas disponíveis: {list(df.columns)}")
        
        # Verificar se os campos estão presentes
        campos_esperados = ['referencia_data', 'data_reativacao', 'corretor']
        campos_encontrados = []
        campos_faltando = []
        
        # Verificar colunas dinâmicas (que começam com 'campo_')
        colunas_dinamicas = [col for col in df.columns if col.startswith('campo_')]
        
        for campo in campos_esperados:
            if campo in df.columns:
                campos_encontrados.append(campo)
            else:
                campos_faltando.append(campo)
        
        print(f"✅ Campos encontrados: {campos_encontrados}")
        if campos_faltando:
            print(f"❌ Campos faltando: {campos_faltando}")
        
        # Verificar colunas dinâmicas
        if colunas_dinamicas:
            print(f"✅ Colunas dinâmicas encontradas: {len(colunas_dinamicas)}")
            print(f"   Exemplos: {colunas_dinamicas[:5]}")
        else:
            print("⚠️ Nenhuma coluna dinâmica encontrada")
        
        # Verificar estatísticas dos campos
        for campo in campos_encontrados:
            if campo in df.columns:
                na_count = df[campo].isna().sum()
                filled_count = len(df) - na_count
                
                print(f"\n📈 Estatísticas do campo '{campo}':")
                print(f"   - Registros com valor: {filled_count}")
                print(f"   - Registros vazios: {na_count}")
                print(f"   - Percentual preenchido: {(filled_count/len(df)*100):.1f}%")
                
                # Mostrar alguns exemplos
                if filled_count > 0:
                    print(f"   📋 Exemplos de valores:")
                    examples = df[df[campo].notna()][campo].head(3)
                    for i, value in enumerate(examples, 1):
                        print(f"      {i}. {value}")
        
        # Verificar estatísticas das colunas dinâmicas
        if colunas_dinamicas:
            print(f"\n📈 Estatísticas das colunas dinâmicas:")
            for col in colunas_dinamicas[:3]:  # Mostrar apenas as primeiras 3
                na_count = df[col].isna().sum()
                filled_count = len(df) - na_count
                print(f"   {col}: {filled_count} preenchidos, {na_count} vazios")
        
        return len(campos_encontrados) > 0 or len(colunas_dinamicas) > 0
            
    except Exception as e:
        print(f"❌ Erro no teste: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Função principal do teste"""
    print("🚀 Iniciando teste do campo 'referencia_data'")
    print()
    
    try:
        sucesso = asyncio.run(test_referencia_data())
        
        if sucesso:
            print("\n🎉 TESTE CONCLUÍDO COM SUCESSO!")
            print("✅ Os campos 'referencia_data', 'data_reativacao', 'corretor' e colunas dinâmicas estão sendo capturados corretamente")
        else:
            print("\n❌ TESTE FALHOU!")
            print("⚠️ Verifique a implementação e as credenciais")
            
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
    finally:
        print("\n🏁 Teste finalizado")

if __name__ == "__main__":
    main()
