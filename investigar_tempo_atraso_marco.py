"""Script para investigar o cálculo de Tempo de Atraso Ponderado em março de 2025."""

import pandas as pd
import os
from dotenv import load_dotenv
import duckdb
from datetime import datetime, timedelta

# Carregar variáveis de ambiente
load_dotenv()
MOTHERDUCK_TOKEN = os.getenv("MOTHERDUCK_TOKEN")

# Conectar diretamente ao MotherDuck sem cache
connection_string = f"motherduck:{MOTHERDUCK_TOKEN}@my_db"
conn = duckdb.connect(connection_string)

# Carregar dados de março de 2025
query = """
    SELECT 
        n_do_pedido,
        data_pedido,
        data_prevista,
        data_entregue,
        total_l_quido_insumo,
        obra,
        comprador
    FROM planilhas.main.relacao_de_pedidos_de_compras
    WHERE data_entregue IS NOT NULL
      AND TRIM(data_entregue) != ''
"""

df = conn.execute(query).df()

if df.empty:
    print("Nenhum dado encontrado para março de 2025")
    exit()

# Converter datas
date_cols = ['data_pedido', 'data_prevista', 'data_entregue']
for col in date_cols:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)

# Filtrar apenas março de 2025
if 'data_entregue' in df.columns:
    df = df[
        (df['data_entregue'].dt.year == 2025) & 
        (df['data_entregue'].dt.month == 3)
    ].copy()

# Identificar coluna de valor
col_valor = 'total_l_quido_insumo' if 'total_l_quido_insumo' in df.columns else \
           ('total_liquido_insumo' if 'total_liquido_insumo' in df.columns else None)

print("=" * 80)
print("INVESTIGAÇÃO - TEMPO DE ATRASO PONDERADO - MARÇO 2025")
print("=" * 80)

# Calcular entregue_no_prazo
df['entregue_no_prazo'] = df['data_entregue'] <= df['data_prevista']
df['tempo_atraso'] = (df['data_entregue'] - df['data_prevista']).dt.days

# Filtrar apenas atrasados
df_atrasados = df[~df['entregue_no_prazo']].copy()

print(f"\nTotal de itens entregues em março 2025: {len(df)}")
print(f"Itens no prazo: {df['entregue_no_prazo'].sum()}")
print(f"Itens atrasados: {len(df_atrasados)}")

if not df_atrasados.empty:
    print(f"\n{'='*80}")
    print("ANÁLISE DOS ITENS ATRASADOS:")
    print(f"{'='*80}")
    
    # Média simples
    tempo_atraso_medio_simples = df_atrasados['tempo_atraso'].mean()
    print(f"\nTempo de Atraso Médio (simples): {tempo_atraso_medio_simples:.2f} dias")
    
    # Estatísticas básicas
    print(f"\nEstatísticas do tempo de atraso:")
    print(f"  Mínimo: {df_atrasados['tempo_atraso'].min()} dias")
    print(f"  Máximo: {df_atrasados['tempo_atraso'].max()} dias")
    print(f"  Mediana: {df_atrasados['tempo_atraso'].median():.2f} dias")
    print(f"  Desvio padrão: {df_atrasados['tempo_atraso'].std():.2f} dias")
    
    if col_valor and col_valor in df_atrasados.columns:
        # Verificar valores
        print(f"\n{'='*80}")
        print("ANÁLISE DOS VALORES:")
        print(f"{'='*80}")
        print(f"  Soma total de valores: R$ {df_atrasados[col_valor].sum():,.2f}")
        print(f"  Valor médio: R$ {df_atrasados[col_valor].mean():,.2f}")
        print(f"  Valor mínimo: R$ {df_atrasados[col_valor].min():,.2f}")
        print(f"  Valor máximo: R$ {df_atrasados[col_valor].max():,.2f}")
        
        # Calcular ponderado
        df_atrasados['tempo_atraso_ponderado_calc'] = df_atrasados[col_valor] * df_atrasados['tempo_atraso']
        soma_numerador = df_atrasados['tempo_atraso_ponderado_calc'].sum()
        soma_denominador = df_atrasados[col_valor].sum()
        tempo_atraso_medio_ponderado = (soma_numerador / soma_denominador) if soma_denominador > 0 else 0.0
        
        print(f"\n{'='*80}")
        print("CÁLCULO PONDERADO:")
        print(f"{'='*80}")
        print(f"  Numerador (SUMX): {soma_numerador:,.2f}")
        print(f"  Denominador (SUM valores): {soma_denominador:,.2f}")
        print(f"  Tempo de Atraso Médio Ponderado: {tempo_atraso_medio_ponderado:.2f} dias")
        
        # Top 10 itens com maior impacto (valor * atraso)
        print(f"\n{'='*80}")
        print("TOP 10 ITENS COM MAIOR IMPACTO (Valor * Atraso):")
        print(f"{'='*80}")
        df_atrasados_sorted = df_atrasados.nlargest(10, 'tempo_atraso_ponderado_calc')
        for idx, row in df_atrasados_sorted.iterrows():
            print(f"  Pedido: {row.get('n_do_pedido', 'N/A')} | "
                  f"Valor: R$ {row[col_valor]:,.2f} | "
                  f"Atraso: {row['tempo_atraso']} dias | "
                  f"Impacto: R$ {row['tempo_atraso_ponderado_calc']:,.2f}")
        
        # Verificar se há valores negativos ou muito altos
        print(f"\n{'='*80}")
        print("VERIFICAÇÕES:")
        print(f"{'='*80}")
        valores_negativos = df_atrasados[df_atrasados[col_valor] < 0]
        if not valores_negativos.empty:
            print(f"  ⚠️ ATENÇÃO: {len(valores_negativos)} itens com valores NEGATIVOS!")
        
        atrasos_muito_altos = df_atrasados[df_atrasados['tempo_atraso'] > 100]
        if not atrasos_muito_altos.empty:
            print(f"  ⚠️ ATENÇÃO: {len(atrasos_muito_altos)} itens com atraso > 100 dias")
            print(f"     Maior atraso: {df_atrasados['tempo_atraso'].max()} dias")
        
        valores_muito_altos = df_atrasados[df_atrasados[col_valor] > df_atrasados[col_valor].quantile(0.95)]
        if not valores_muito_altos.empty:
            print(f"  ℹ️ {len(valores_muito_altos)} itens no percentil 95% de valores")
            print(f"     Valor máximo: R$ {df_atrasados[col_valor].max():,.2f}")
    else:
        print("\n⚠️ Coluna de valor não encontrada!")
else:
    print("\nNenhum item atrasado em março de 2025")

print("\n" + "=" * 80)

