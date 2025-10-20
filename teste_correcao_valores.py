#!/usr/bin/env python3
"""
Script de Teste - Validação da Correção de Valores Monetários
Testa a função de normalização com exemplos reais
"""

import pandas as pd
from datetime import datetime

def normalizar_valor_monetario_otimizado(valor):
    """
    Normalização otimizada de valores monetários
    - Se tem vírgula: já está no formato brasileiro correto
    - Se tem pontos: substitui apenas o ÚLTIMO ponto por vírgula
    - Se não tem nem pontos nem vírgulas: número simples
    """
    if pd.isna(valor) or valor is None:
        return 0.0
    
    valor_str = str(valor).replace('R$', '').replace('$', '').strip()
    
    # Se já tem vírgula, está no formato brasileiro correto
    if ',' in valor_str:
        return float(valor_str.replace(',', '.'))
    
    # Se tem pontos, substituir apenas o ÚLTIMO ponto por vírgula
    if '.' in valor_str:
        ultimo_ponto = valor_str.rfind('.')
        valor_corrigido = valor_str[:ultimo_ponto] + ',' + valor_str[ultimo_ponto+1:]
        return float(valor_corrigido.replace(',', '.'))
    
    # Número simples sem formatação
    try:
        return float(valor_str)
    except ValueError:
        return 0.0

def testar_normalizacao():
    """Testa a normalização com exemplos reais"""
    print("🧪 TESTE DE VALIDAÇÃO - CORREÇÃO DE VALORES MONETÁRIOS")
    print("=" * 70)
    
    # Exemplos baseados em valores reais de empreendimentos
    exemplos_teste = [
        # Formato brasileiro correto
        ("210.000,50", 210000.50, "Formato brasileiro com centavos"),
        ("450.000,00", 450000.00, "Formato brasileiro sem centavos"),
        ("2.100.000,50", 2100000.50, "Formato brasileiro milhões"),
        
        # Formato problemático (valores que estavam sendo interpretados incorretamente)
        ("210.000", 210000.00, "Valor sem centavos (problema anterior)"),
        ("2.100", 2100.00, "Valor pequeno (problema anterior)"),
        ("450.000", 450000.00, "Valor médio (problema anterior)"),
        
        # Valores já corretos
        ("210000.50", 210000.50, "Valor já em formato decimal"),
        ("450000", 450000.00, "Valor inteiro simples"),
        ("2100000", 2100000.00, "Valor milhões simples"),
        
        # Casos edge
        ("R$ 210.000,50", 210000.50, "Com símbolo R$"),
        ("$ 450.000,00", 450000.00, "Com símbolo $"),
        ("", 0.0, "String vazia"),
        (None, 0.0, "Valor None"),
        (0, 0.0, "Zero"),
    ]
    
    print("📊 TESTANDO EXEMPLOS:")
    print("-" * 70)
    
    sucessos = 0
    falhas = 0
    
    for entrada, esperado, descricao in exemplos_teste:
        try:
            resultado = normalizar_valor_monetario_otimizado(entrada)
            diferenca = abs(resultado - esperado)
            
            if diferenca < 0.01:  # Tolerância de 1 centavo
                status = "✅"
                sucessos += 1
            else:
                status = "❌"
                falhas += 1
            
            print(f"{status} {descricao}")
            print(f"    Entrada: '{entrada}'")
            print(f"    Esperado: {esperado:,.2f}")
            print(f"    Resultado: {resultado:,.2f}")
            if diferenca >= 0.01:
                print(f"    DIFERENÇA: {diferenca:,.2f}")
            print()
            
        except Exception as e:
            print(f"❌ ERRO: {descricao}")
            print(f"    Entrada: '{entrada}'")
            print(f"    Erro: {str(e)}")
            print()
            falhas += 1
    
    # Resumo
    print("=" * 70)
    print(f"📈 RESUMO DO TESTE:")
    print(f"   ✅ Sucessos: {sucessos}")
    print(f"   ❌ Falhas: {falhas}")
    print(f"   📊 Taxa de sucesso: {(sucessos/(sucessos+falhas)*100):.1f}%")
    
    if falhas == 0:
        print("\n🎉 TODOS OS TESTES PASSARAM! A correção está funcionando perfeitamente.")
        return True
    else:
        print(f"\n⚠️ {falhas} TESTES FALHARAM. Verifique a implementação.")
        return False

def testar_com_dataframe():
    """Testa a normalização com DataFrame simulado"""
    print("\n" + "=" * 70)
    print("📊 TESTE COM DATAFRAME SIMULADO")
    print("=" * 70)
    
    # Criar DataFrame com valores problemáticos
    dados_teste = {
        'valor_venda': [
            '210.000,50',    # Formato brasileiro correto
            '450.000,00',    # Formato brasileiro sem centavos
            '2.100.000,50',  # Formato brasileiro milhões
            '210.000',       # Problema: sem centavos
            '2.100',         # Problema: valor pequeno
            '450.000',       # Problema: valor médio
            '210000.50',     # Já correto
            '450000',        # Já correto
            'R$ 210.000,50', # Com símbolo
            None,            # Valor nulo
        ],
        'valor_contrato': [
            '200.000,00',
            '400.000,00',
            '2.000.000,00',
            '200.000',
            '2.000',
            '400.000',
            '200000.00',
            '400000',
            'R$ 200.000,00',
            None,
        ]
    }
    
    df = pd.DataFrame(dados_teste)
    
    print("📋 DADOS ORIGINAIS:")
    print(df.to_string())
    print()
    
    # Aplicar normalização
    print("🔧 APLICANDO NORMALIZAÇÃO...")
    for col in ['valor_venda', 'valor_contrato']:
        df[col] = df[col].apply(normalizar_valor_monetario_otimizado)
    
    print("📊 DADOS NORMALIZADOS:")
    print(df.to_string())
    print()
    
    # Estatísticas
    print("📈 ESTATÍSTICAS:")
    for col in ['valor_venda', 'valor_contrato']:
        stats = df[col].describe()
        print(f"   {col}:")
        print(f"     Min: {stats['min']:,.2f}")
        print(f"     Max: {stats['max']:,.2f}")
        print(f"     Mean: {stats['mean']:,.2f}")
        print(f"     Count: {stats['count']:.0f}")
        print()
    
    return df

def main():
    """Função principal"""
    print("🔧 VALIDAÇÃO DA CORREÇÃO DE VALORES MONETÁRIOS")
    print("Este script testa se a correção está funcionando corretamente")
    print()
    
    try:
        # 1. Teste com exemplos
        sucesso_exemplos = testar_normalizacao()
        
        # 2. Teste com DataFrame
        df_resultado = testar_com_dataframe()
        
        # 3. Resumo final
        print("=" * 70)
        print("🎯 CONCLUSÃO:")
        
        if sucesso_exemplos:
            print("✅ A correção está funcionando perfeitamente!")
            print("✅ Pode ser implementada na próxima atualização.")
            print("✅ Os valores monetários serão normalizados corretamente.")
        else:
            print("❌ A correção precisa de ajustes antes da implementação.")
        
        print("\n📝 PRÓXIMOS PASSOS:")
        print("1. Se todos os testes passaram, a correção está pronta")
        print("2. Execute a próxima atualização do sistema")
        print("3. Monitore os logs para verificar se a normalização está funcionando")
        print("4. Verifique os valores no dashboard após a atualização")
        
    except Exception as e:
        print(f"❌ Erro durante o teste: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
