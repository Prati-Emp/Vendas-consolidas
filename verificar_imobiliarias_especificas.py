#!/usr/bin/env python3
"""Verificar valores específicos por imobiliária para 2025"""

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

    # Verificar valores específicos para cada imobiliária mencionada
    imobiliarias_especificas = [
        "DANIEL HECK CORRETORES ASSOCIADOS",
        "INVESTINDO TOLEDO", 
        "Imobiliaria Ativa",
        "CONEXÃO IMÓVEIS",
        "Prati Empreendimentos"
    ]

    print("="*80)
    print(" " * 20 + "VERIFICACAO POR IMOBILIARIA ESPECIFICA")
    print("="*80)
    print(f"Periodo: {inicio_ano.strftime('%d/%m/%Y')} até hoje")
    print()

    def formatar_valor(valor):
        if pd.isna(valor) or valor is None:
            return "R$ 0,00"
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    total_geral = 0
    
    for imobiliaria in imobiliarias_especificas:
        query = """
        SELECT 
            imobiliaria,
            COUNT(*) as contratos,
            SUM(value) as total_value
        FROM sienge_vendas_consolidadas 
        WHERE TRY_CAST(data_contrato AS DATE) >= $1 
        AND imobiliaria = $2
        GROUP BY imobiliaria
        """
        
        resultado = conn.execute(query, [inicio_ano, imobiliaria]).fetchdf()
        
        if len(resultado) > 0:
            row = resultado.iloc[0]
            total = row['total_value'] if not pd.isna(row['total_value']) else 0
            contratos = row['contratos']
            total_geral += total
            print(f"{imobiliaria:<40} {formatar_valor(total):>20} ({contratos} contratos)")
        else:
            print(f"{imobiliaria:<40} {'R$ 0,00':>20} (0 contratos)")

    print("="*80)
    print(f"{'TOTAL DAS IMOBILIARIAS ESPECIFICAS:':<40} {formatar_valor(total_geral):>20}")
    print("="*80)

    # Verificar total geral de 2025
    query_total = """
    SELECT 
        COUNT(*) as total_contratos,
        SUM(value) as total_value
    FROM sienge_vendas_consolidadas 
    WHERE TRY_CAST(data_contrato AS DATE) >= $1
    """
    
    resultado_total = conn.execute(query_total, [inicio_ano]).fetchdf()
    row_total = resultado_total.iloc[0]
    total_geral_2025 = row_total['total_value'] if not pd.isna(row_total['total_value']) else 0
    total_contratos_2025 = row_total['total_contratos']
    
    print(f"\nTOTAL GERAL 2025: {formatar_valor(total_geral_2025)} ({total_contratos_2025} contratos)")
    print(f"Participacao das imobiliarias especificas: {(total_geral/total_geral_2025)*100:.1f}%")

    conn.close()


if __name__ == "__main__":
    main()
