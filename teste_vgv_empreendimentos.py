#!/usr/bin/env python3
"""
Script de teste para a API VGV Empreendimentos
Testa a coleta de dados e processamento
"""

import asyncio
import sys
from datetime import datetime
from dotenv import load_dotenv
from scripts.cv_vgv_empreendimentos_api import obter_dados_vgv_empreendimentos

async def test_vgv_empreendimentos():
    """Teste completo da API VGV Empreendimentos"""
    print("🧪 TESTE VGV EMPREENDIMENTOS")
    print("=" * 40)
    
    try:
        # Carregar configurações
        print("1. Carregando configurações...")
        load_dotenv()
        
        # Verificar variáveis de ambiente
        env_vars = ['CVCRM_EMAIL', 'CVCRM_TOKEN']
        for var in env_vars:
            if not os.environ.get(var):
                print(f"❌ {var} não encontrado")
                return False
        
        print("✅ Configurações carregadas")
        
        # Testar coleta de dados (apenas IDs 1-5 para teste)
        print("\n2. Testando coleta de dados (IDs 1-5)...")
        df = await obter_dados_vgv_empreendimentos(1, 5)
        
        print(f"✅ Dados coletados: {len(df)} registros")
        
        if not df.empty:
            print("\n📊 Informações dos dados:")
            print(f"   - Total de registros: {len(df)}")
            print(f"   - Total de colunas: {len(df.columns)}")
            print(f"   - Colunas: {list(df.columns)}")
            
            print("\n📋 Primeiros registros:")
            print(df.head())
            
            # Verificar empreendimentos únicos
            if 'id_empreendimento' in df.columns:
                empreendimentos = df['id_empreendimento'].unique()
                print(f"\n🏢 Empreendimentos encontrados: {len(empreendimentos)}")
                print(f"   IDs: {sorted(empreendimentos)}")
            
            # Verificar unidades por empreendimento
            if 'id_empreendimento' in df.columns:
                print(f"\n📈 Unidades por empreendimento:")
                unidades_por_emp = df.groupby('id_empreendimento').size()
                for emp_id, count in unidades_por_emp.items():
                    print(f"   - Empreendimento {emp_id}: {count} unidades")
            
            print("\n✅ Teste concluído com sucesso!")
            return True
        else:
            print("⚠️ Nenhum dado coletado")
            return False
            
    except Exception as e:
        print(f"❌ Erro no teste: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Função principal"""
    print("🧪 TESTE DA API VGV EMPREENDIMENTOS")
    print("Este script testa a coleta de dados da nova API")
    print()
    
    try:
        sucesso = asyncio.run(test_vgv_empreendimentos())
        
        if sucesso:
            print("\n✅ Teste executado com sucesso!")
        else:
            print("\n❌ Falha no teste")
            
    except KeyboardInterrupt:
        print("\n⚠️ Teste cancelado pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
    finally:
        print("\n🏁 Teste finalizado")

if __name__ == "__main__":
    main()

