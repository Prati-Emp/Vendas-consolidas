#!/usr/bin/env python3
"""
Processador de CSV do Sienge baixado via webscraping
- Lê arquivo CSV baixado pelo sienge_mcp_persistente.py
- Processa e normaliza dados
- Faz upload para MotherDuck na tabela sienge_relatorio_pedidos_compras
"""

import os
import pandas as pd
import duckdb
from datetime import datetime
from dotenv import load_dotenv
import glob
import pathlib

def processar_csv_sienge(caminho_csv: str) -> pd.DataFrame:
    """
    Processa arquivo CSV do Sienge baixado via webscraping
    
    Args:
        caminho_csv: Caminho para o arquivo CSV baixado
        
    Returns:
        DataFrame processado
    """
    print(f"📄 Processando CSV do Sienge: {pathlib.Path(caminho_csv).name}")
    
    try:
        # Ler CSV com encoding correto
        df = pd.read_csv(caminho_csv, encoding='utf-8', sep=';')
        print(f"✅ CSV lido: {len(df)} registros, {len(df.columns)} colunas")
        
        # Adicionar colunas de controle
        df['fonte'] = 'sienge_webscraping'
        df['processado_em'] = datetime.now()
        df['arquivo_origem'] = pathlib.Path(caminho_csv).name
        
        # Normalizar colunas de data se existirem
        colunas_data = [col for col in df.columns if 'data' in col.lower() or 'date' in col.lower()]
        for col in colunas_data:
            try:
                df[col] = pd.to_datetime(df[col], errors='coerce')
            except:
                pass
        
        # Normalizar colunas de valor se existirem
        colunas_valor = [col for col in df.columns if 'valor' in col.lower() or 'value' in col.lower()]
        for col in colunas_valor:
            try:
                # Remover formatação brasileira (R$ 1.000,00 -> 1000.00)
                df[col] = df[col].astype(str).str.replace('R$', '').str.replace('.', '').str.replace(',', '.').str.replace(' ', '')
                df[col] = pd.to_numeric(df[col], errors='coerce')
            except:
                pass
        
        print(f"✅ CSV processado: {len(df)} registros")
        return df
        
    except Exception as e:
        print(f"❌ Erro ao processar CSV: {e}")
        return pd.DataFrame()

def upload_csv_sienge_motherduck(df: pd.DataFrame) -> bool:
    """
    Faz upload do DataFrame processado para MotherDuck
    
    Args:
        df: DataFrame processado
        
    Returns:
        bool: True se sucesso, False se erro
    """
    if df.empty:
        print("⚠️ DataFrame vazio - nada para upload")
        return False
    
    try:
        print("📤 Fazendo upload para MotherDuck...")
        
        # Configurar DuckDB
        duckdb.sql("INSTALL motherduck")
        duckdb.sql("LOAD motherduck")
        
        token = os.environ.get('MOTHERDUCK_TOKEN', '').strip()
        if not token:
            print("❌ MOTHERDUCK_TOKEN não encontrado")
            return False
        
        # Configurar token
        duckdb.sql(f"SET motherduck_token='{token}'")
        conn = duckdb.connect('md:reservas')
        
        # Upload para tabela específica do webscraping
        conn.register("df_sienge_csv", df)
        conn.execute("CREATE OR REPLACE TABLE main.sienge_relatorio_pedidos_compras AS SELECT * FROM df_sienge_csv")
        
        count = conn.sql("SELECT COUNT(*) FROM main.sienge_relatorio_pedidos_compras").fetchone()[0]
        print(f"✅ Upload concluído: {count:,} registros na tabela sienge_relatorio_pedidos_compras")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erro no upload: {e}")
        return False

def encontrar_ultimo_csv_sienge(diretorio_downloads: str = "downloads_tmp") -> str:
    """
    Encontra o arquivo CSV mais recente baixado pelo webscraping
    
    Args:
        diretorio_downloads: Diretório onde os CSVs são salvos
        
    Returns:
        str: Caminho para o arquivo mais recente
    """
    if not os.path.exists(diretorio_downloads):
        print(f"❌ Diretório não encontrado: {diretorio_downloads}")
        return None
    
    # Buscar arquivos CSV recentes (últimas 24 horas)
    csv_files = glob.glob(os.path.join(diretorio_downloads, "*.csv"))
    recent_files = []
    
    for file_path in csv_files:
        # Verificar se foi criado nas últimas 24 horas
        if os.path.getmtime(file_path) > datetime.now().timestamp() - 86400:
            recent_files.append(file_path)
    
    if not recent_files:
        print("❌ Nenhum CSV recente encontrado")
        return None
    
    # Pegar o mais recente
    latest_file = max(recent_files, key=os.path.getmtime)
    print(f"📁 Arquivo mais recente: {pathlib.Path(latest_file).name}")
    return latest_file

def main():
    """Função principal"""
    print("🚀 PROCESSADOR CSV SIENGE - WEBSCRAPING")
    print("=" * 60)
    
    # Carregar variáveis de ambiente
    load_dotenv()
    
    # Verificar token
    if not os.environ.get('MOTHERDUCK_TOKEN'):
        print("❌ MOTHERDUCK_TOKEN não encontrado")
        return False
    
    # Encontrar último CSV
    csv_path = encontrar_ultimo_csv_sienge()
    if not csv_path:
        print("❌ Nenhum CSV encontrado para processar")
        return False
    
    # Processar CSV
    df = processar_csv_sienge(csv_path)
    if df.empty:
        print("❌ Falha ao processar CSV")
        return False
    
    # Upload para MotherDuck
    sucesso = upload_csv_sienge_motherduck(df)
    if sucesso:
        print("✅ PROCESSAMENTO CONCLUÍDO COM SUCESSO!")
        return True
    else:
        print("❌ FALHA NO UPLOAD")
        return False

if __name__ == "__main__":
    main()
