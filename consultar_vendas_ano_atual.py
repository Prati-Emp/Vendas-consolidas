#!/usr/bin/env python3
"""Consulta valores acumulados das vendas do ano corrente por imobiliária."""

import datetime as dt
import os

import duckdb
import pandas as pd
from dotenv import load_dotenv


def main() -> None:
    load_dotenv("motherduck_config.env")
    token = os.getenv("MOTHERDUCK_TOKEN")
    if not token:
        raise SystemExit("Token MotherDuck ausente. Verifique o arquivo motherduck_config.env")

    inicio_ano = dt.date.today().replace(month=1, day=1)

    conn = duckdb.connect(f"md:?motherduck_token={token}")
    conn.execute("USE informacoes_consolidadas")

    query = """
    WITH dados AS (
        SELECT
            TRY_CAST(data_contrato AS DATE) AS data_util,
            TRIM(imobiliaria) AS imobiliaria,
            value
        FROM sienge_vendas_consolidadas
    )
    SELECT
        SUM(value) FILTER (WHERE data_util >= $1) AS total_value,
        SUM(value) FILTER (WHERE data_util >= $1 AND imobiliaria = 'DANIEL HECK CORRETORES ASSOCIADOS') AS heck,
        SUM(value) FILTER (WHERE data_util >= $1 AND imobiliaria = 'INVESTINDO TOLEDO') AS investindo,
        SUM(value) FILTER (WHERE data_util >= $1 AND imobiliaria = 'Imobiliaria Ativa') AS ativa,
        SUM(value) FILTER (WHERE data_util >= $1 AND imobiliaria = 'CONEXÃO IMÓVEIS') AS conexao,
        SUM(value) FILTER (WHERE data_util >= $1 AND imobiliaria = 'Prati Empreendimentos') AS prati,
        SUM(value) FILTER (
            WHERE data_util >= $1
              AND imobiliaria IS NOT NULL
              AND imobiliaria NOT IN ('DANIEL HECK CORRETORES ASSOCIADOS', 'INVESTINDO TOLEDO', 'Imobiliaria Ativa', 'CONEXÃO IMÓVEIS', 'Prati Empreendimentos')
        ) AS outras,
        SUM(value) FILTER (
            WHERE data_util >= $1
              AND imobiliaria IS NULL
        ) AS imobiliaria_nao_informada
    FROM dados
    WHERE data_util IS NOT NULL
    """

    resultado = conn.execute(query, [inicio_ano]).fetchdf()
    
    # Formatar números para apresentação ao diretor
    print("\n" + "="*80)
    print(" " * 20 + "RELATORIO EXECUTIVO DE VENDAS")
    print(" " * 15 + "VALORES ACUMULADOS - ANO ATUAL")
    print("="*80)
    
    hoje = dt.date.today()
    print(f"\nPeríodo: {inicio_ano.strftime('%d/%m/%Y')} até {hoje.strftime('%d/%m/%Y')}")
    print(f"Total de dias: {(hoje - inicio_ano).days + 1} dias")
    print()
    
    row = resultado.iloc[0]
    
    def formatar_valor(valor):
        if pd.isna(valor) or valor is None:
            return "R$ 0,00"
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    def calcular_percentual(valor, total):
        if pd.isna(valor) or valor is None or total == 0:
            return "0,0%"
        return f"{(valor/total)*100:.1f}%"
    
    total_geral = row['total_value'] if not pd.isna(row['total_value']) else 0
    
    print("="*80)
    print(" " * 25 + "RESUMO GERAL")
    print("="*80)
    print(f"{'TOTAL GERAL:':<25} {formatar_valor(total_geral):>25}")
    print("="*80)
    
    print("\n" + "="*80)
    print(" " * 20 + "DISTRIBUICAO POR IMOBILIARIA")
    print("="*80)
    
    imobiliarias = [
        ("DANIEL HECK CORRETORES ASSOCIADOS", row['heck']),
        ("INVESTINDO TOLEDO", row['investindo']),
        ("Imobiliaria Ativa", row['ativa']),
        ("CONEXÃO IMÓVEIS", row['conexao']),
        ("Prati Empreendimentos", row['prati']),
        ("Outras", row['outras']),
        ("Nao informada", row['imobiliaria_nao_informada'])
    ]
    
    for nome, valor in imobiliarias:
        valor_formatado = formatar_valor(valor)
        percentual = calcular_percentual(valor, total_geral)
        print(f"{nome:<40} {valor_formatado:>20} ({percentual:>6})")
    
    print("="*80)
    
    # Análise adicional
    print(f"\nINSIGHTS:")
    print(f"   - Maior participacao: {max(imobiliarias, key=lambda x: x[1] if not pd.isna(x[1]) else 0)[0]}")
    print(f"   - Valor medio por contrato: {formatar_valor(total_geral / max(1, len(imobiliarias)))}")
    print(f"   - Data de geracao: {hoje.strftime('%d/%m/%Y as %H:%M')}")
    print("\n" + "="*80)

    conn.close()


if __name__ == "__main__":
    main()

