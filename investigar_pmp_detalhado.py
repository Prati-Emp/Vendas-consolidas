import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import duckdb
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

def get_md_connection_planilhas():
    """Conecta ao banco 'planilhas' do MotherDuck"""
    token = os.getenv('MOTHERDUCK_TOKEN') or os.getenv('Token_MD')
    
    if not token:
        raise ValueError("MOTHERDUCK_TOKEN não encontrado")
    
    duckdb.sql("INSTALL motherduck")
    duckdb.sql("LOAD motherduck")
    duckdb.sql(f"SET motherduck_token='{token}'")
    return duckdb.connect("md:planilhas")

def investigar_pmp_janeiro():
    """Investiga especificamente o PMP de janeiro 2025"""
    try:
        conn = get_md_connection_planilhas()
        
        # Carregar dados com filtros aplicados
        # Verificar se há outras colunas que possam estar sendo usadas como filtro
        sql = """
        SELECT 
            data_do_pagamento,
            data_emiss_o,
            valor_l_quido,
            tipo_de_baixa,
            parcela_autorizada,
            saldo_em_aberto,
            valor_da_baixa
        FROM planilhas.main.contas_pagas
        WHERE UPPER(tipo_de_baixa) IN ('ADIANTAMENTO', 'PAGAMENTO')
          AND UPPER(parcela_autorizada) = 'SIM'
          AND data_do_pagamento IS NOT NULL
          AND data_emiss_o IS NOT NULL
          AND valor_l_quido IS NOT NULL
        """
        
        df = conn.execute(sql).df()
        conn.close()
        
        if df.empty:
            print("Nenhum dado encontrado!")
            return
        
        # Converter datas
        df['data_pag'] = pd.to_datetime(df['data_do_pagamento'], dayfirst=True, errors='coerce')
        df['data_emiss'] = pd.to_datetime(df['data_emiss_o'], dayfirst=True, errors='coerce')
        
        # Remover linhas com datas inválidas
        df = df[df['data_pag'].notna() & df['data_emiss'].notna()].copy()
        
        # Filtrar apenas janeiro 2025 (baseado em data_do_pagamento)
        # Testar diferentes formas de agrupar
        print("\n" + "=" * 60)
        print("TESTE: Diferentes formas de agrupar por mês")
        print("=" * 60)
        
        # Forma 1: usando to_period (como estamos fazendo)
        df_jan1 = df[df['data_pag'].dt.to_period('M') == '2025-01'].copy()
        print(f"Forma 1 (to_period): {len(df_jan1)} registros")
        
        # Forma 2: usando year e month separadamente
        df_jan2 = df[(df['data_pag'].dt.year == 2025) & (df['data_pag'].dt.month == 1)].copy()
        print(f"Forma 2 (year + month): {len(df_jan2)} registros")
        
        # Forma 3: usando strftime
        df_jan3 = df[df['data_pag'].dt.strftime('%Y-%m') == '2025-01'].copy()
        print(f"Forma 3 (strftime): {len(df_jan3)} registros")
        
        # Usar a primeira forma (que é a que estamos usando)
        df_jan = df_jan1.copy()
        
        print("=" * 60)
        print(f"TOTAL DE REGISTROS PARA JANEIRO 2025: {len(df_jan)}")
        print("=" * 60)
        
        if df_jan.empty:
            print("Nenhum registro encontrado para janeiro 2025!")
            return
        
        # Calcular PMP simples
        df_jan['pmp_simples'] = (df_jan['data_pag'] - df_jan['data_emiss']).dt.days
        
        # Remover valores inválidos
        df_jan = df_jan[(df_jan['pmp_simples'] >= 0) & (df_jan['pmp_simples'] <= 365)].copy()
        
        print(f"\nRegistros após filtrar PMP válido (0-365 dias): {len(df_jan)}")
        
        # Testar sem filtrar valores zero
        print("\n" + "=" * 60)
        print("TESTE: Incluindo valores zero no cálculo")
        print("=" * 60)
        df_jan_com_zero = df[df['data_pag'].dt.to_period('M') == '2025-01'].copy()
        df_jan_com_zero['pmp_simples'] = (df_jan_com_zero['data_pag'] - df_jan_com_zero['data_emiss']).dt.days
        df_jan_com_zero = df_jan_com_zero[(df_jan_com_zero['pmp_simples'] >= 0) & (df_jan_com_zero['pmp_simples'] <= 365)].copy()
        df_jan_com_zero['pmp_ponderado_calc'] = df_jan_com_zero['pmp_simples'] * df_jan_com_zero['valor_l_quido']
        soma_numerador_zero = df_jan_com_zero['pmp_ponderado_calc'].sum()
        soma_denominador_zero = df_jan_com_zero['valor_l_quido'].sum()
        pmp_ponderado_zero = (soma_numerador_zero / soma_denominador_zero) if soma_denominador_zero > 0 else 0.0
        print(f"PMP Ponderado (com todos os valores): {pmp_ponderado_zero:.2f} dias")
        
        # Testar excluindo valores zero
        print("\n" + "=" * 60)
        print("TESTE: Excluindo valores zero do cálculo")
        print("=" * 60)
        df_jan_sem_zero = df_jan[df_jan['valor_l_quido'] > 0].copy()
        print(f"Registros com valor > 0: {len(df_jan_sem_zero)}")
        if not df_jan_sem_zero.empty:
            df_jan_sem_zero['pmp_ponderado_calc'] = df_jan_sem_zero['pmp_simples'] * df_jan_sem_zero['valor_l_quido']
            soma_numerador_sem_zero = df_jan_sem_zero['pmp_ponderado_calc'].sum()
            soma_denominador_sem_zero = df_jan_sem_zero['valor_l_quido'].sum()
            pmp_ponderado_sem_zero = (soma_numerador_sem_zero / soma_denominador_sem_zero) if soma_denominador_sem_zero > 0 else 0.0
            print(f"PMP Ponderado (sem valores zero): {pmp_ponderado_sem_zero:.2f} dias")
        
        # Verificar se saldo_em_aberto ou valor_da_baixa podem estar sendo usados como filtro
        print("\n" + "=" * 60)
        print("VERIFICAÇÃO DE OUTROS FILTROS POSSÍVEIS")
        print("=" * 60)
        print(f"Registros com saldo_em_aberto = 0: {(df_jan['saldo_em_aberto'] == 0).sum()}")
        print(f"Registros com saldo_em_aberto != 0: {(df_jan['saldo_em_aberto'] != 0).sum()}")
        print(f"Registros com valor_da_baixa > 0: {(df_jan['valor_da_baixa'] > 0).sum()}")
        print(f"Registros com valor_da_baixa = 0: {(df_jan['valor_da_baixa'] == 0).sum()}")
        
        # Testar filtrando apenas registros com saldo_em_aberto = 0 (pagamentos completos)
        print("\n" + "=" * 60)
        print("TESTE: Filtrando apenas saldo_em_aberto = 0")
        print("=" * 60)
        df_jan_saldo_zero = df_jan[df_jan['saldo_em_aberto'] == 0].copy()
        print(f"Registros com saldo_em_aberto = 0: {len(df_jan_saldo_zero)}")
        if not df_jan_saldo_zero.empty:
            df_jan_saldo_zero['pmp_ponderado_calc'] = df_jan_saldo_zero['pmp_simples'] * df_jan_saldo_zero['valor_l_quido']
            soma_numerador_saldo = df_jan_saldo_zero['pmp_ponderado_calc'].sum()
            soma_denominador_saldo = df_jan_saldo_zero['valor_l_quido'].sum()
            pmp_ponderado_saldo = (soma_numerador_saldo / soma_denominador_saldo) if soma_denominador_saldo > 0 else 0.0
            print(f"PMP Ponderado (saldo_em_aberto = 0): {pmp_ponderado_saldo:.2f} dias")
        
        # Estatísticas
        print("\n" + "=" * 60)
        print("ESTATÍSTICAS DO PMP SIMPLES PARA JANEIRO 2025")
        print("=" * 60)
        print(f"Mínimo: {df_jan['pmp_simples'].min()} dias")
        print(f"Máximo: {df_jan['pmp_simples'].max()} dias")
        print(f"Média: {df_jan['pmp_simples'].mean():.2f} dias")
        print(f"Mediana: {df_jan['pmp_simples'].median():.2f} dias")
        
        # Calcular PMP Ponderado
        df_jan['pmp_ponderado_calc'] = df_jan['pmp_simples'] * df_jan['valor_l_quido']
        soma_numerador = df_jan['pmp_ponderado_calc'].sum()
        soma_denominador = df_jan['valor_l_quido'].sum()
        pmp_ponderado = (soma_numerador / soma_denominador) if soma_denominador > 0 else 0.0
        
        print("\n" + "=" * 60)
        print("CÁLCULO PMP PONDERADO PARA JANEIRO 2025")
        print("=" * 60)
        print(f"Soma numerador (PMP simples * Valor líquido): {soma_numerador:,.2f}")
        print(f"Soma denominador (Valor líquido): {soma_denominador:,.2f}")
        print(f"PMP Ponderado: {pmp_ponderado:.2f} dias")
        print(f"PMP Ponderado (arredondado): {round(pmp_ponderado)} dias")
        
        # Verificar distribuição de valores
        print("\n" + "=" * 60)
        print("DISTRIBUIÇÃO DE VALORES LÍQUIDOS")
        print("=" * 60)
        print(f"Total valor líquido: {df_jan['valor_l_quido'].sum():,.2f}")
        print(f"Média valor líquido: {df_jan['valor_l_quido'].mean():,.2f}")
        print(f"Mediana valor líquido: {df_jan['valor_l_quido'].median():,.2f}")
        
        # Verificar se há valores zero ou negativos
        print("\n" + "=" * 60)
        print("VERIFICAÇÃO DE VALORES ZERO OU NEGATIVOS")
        print("=" * 60)
        print(f"Valores líquidos zero: {(df_jan['valor_l_quido'] == 0).sum()}")
        print(f"Valores líquidos negativos: {(df_jan['valor_l_quido'] < 0).sum()}")
        print(f"PMP simples negativo: {(df_jan['pmp_simples'] < 0).sum()}")
        
        # Amostra de dados
        print("\n" + "=" * 60)
        print("AMOSTRA DE DADOS (primeiras 10 linhas)")
        print("=" * 60)
        df_amostra = df_jan[['data_pag', 'data_emiss', 'pmp_simples', 'valor_l_quido', 'pmp_ponderado_calc']].head(10)
        print(df_amostra.to_string())
        
        # Verificar range de datas
        print("\n" + "=" * 60)
        print("RANGE DE DATAS")
        print("=" * 60)
        print(f"Data pagamento mínima: {df_jan['data_pag'].min()}")
        print(f"Data pagamento máxima: {df_jan['data_pag'].max()}")
        print(f"Data emissão mínima: {df_jan['data_emiss'].min()}")
        print(f"Data emissão máxima: {df_jan['data_emiss'].max()}")
        
    except Exception as e:
        print(f"Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    investigar_pmp_janeiro()

