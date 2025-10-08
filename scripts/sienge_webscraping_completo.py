#!/usr/bin/env python3
"""
Sistema completo: Webscraping Sienge + Processamento CSV + Upload MotherDuck
- Executa webscraping via sienge_mcp_persistente.py
- Processa CSV baixado
- Faz upload para MotherDuck na tabela sienge_relatorio_pedidos_compras
"""

import os
import sys
import subprocess
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# Importar processador
from scripts.processar_csv_sienge import processar_csv_sienge, upload_csv_sienge_motherduck, encontrar_ultimo_csv_sienge

async def executar_webscraping_sienge():
    """
    Executa webscraping do Sienge usando o script existente
    """
    print("🌐 Executando webscraping do Sienge...")
    
    try:
        # Executar script de webscraping
        result = subprocess.run(
            ['python', 'sienge_mcp_persistente.py'],
            capture_output=True, 
            text=True, 
            encoding='utf-8', 
            errors='ignore', 
            timeout=1200  # 20 minutos
        )
        
        print("📋 Saída do webscraping:")
        print(result.stdout)
        
        if result.stderr:
            print("⚠️ Avisos:")
            print(result.stderr)
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("⏱️ Timeout no webscraping (20 minutos)")
        return False
    except Exception as e:
        print(f"❌ Erro no webscraping: {e}")
        return False

async def sistema_completo_sienge():
    """
    Sistema completo: Webscraping + Processamento + Upload
    """
    print("🚀 SISTEMA COMPLETO SIENGE WEBSCRAPING")
    print("=" * 60)
    print(f"Timestamp: {datetime.now()}")
    
    start_time = datetime.now()
    
    try:
        # 1. Executar webscraping
        print("\n1. Executando webscraping...")
        sucesso_webscraping = await executar_webscraping_sienge()
        
        if not sucesso_webscraping:
            print("❌ Falha no webscraping")
            return False
        
        print("✅ Webscraping concluído")
        
        # 2. Aguardar um pouco para garantir que o arquivo foi salvo
        print("\n2. Aguardando processamento do arquivo...")
        await asyncio.sleep(5)
        
        # 3. Encontrar e processar CSV
        print("\n3. Processando CSV baixado...")
        csv_path = encontrar_ultimo_csv_sienge()
        
        if not csv_path:
            print("❌ Nenhum CSV encontrado")
            return False
        
        # 4. Processar CSV
        df = processar_csv_sienge(csv_path)
        if df.empty:
            print("❌ Falha ao processar CSV")
            return False
        
        # 5. Upload para MotherDuck
        print("\n4. Fazendo upload para MotherDuck...")
        sucesso_upload = upload_csv_sienge_motherduck(df)
        
        if not sucesso_upload:
            print("❌ Falha no upload")
            return False
        
        # 6. Estatísticas finais
        end_time = datetime.now()
        duration = end_time - start_time
        
        print(f"\n✅ SISTEMA COMPLETO CONCLUÍDO!")
        print(f"Duração: {duration}")
        print(f"Registros processados: {len(df):,}")
        print(f"Arquivo: {os.path.basename(csv_path)}")
        print(f"Tabela: sienge_relatorio_pedidos_compras")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERRO NO SISTEMA COMPLETO: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Função principal para execução via GitHub Actions"""
    print("INICIANDO SISTEMA COMPLETO SIENGE WEBSCRAPING")
    print("=" * 60)
    print(f"Timestamp: {datetime.now()}")
    print(f"Python: {sys.version}")
    print(f"Working directory: {os.getcwd()}")
    
    # Carregar variáveis de ambiente
    load_dotenv()
    
    # Verificar variáveis críticas
    required_vars = ['MOTHERDUCK_TOKEN']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"❌ Variáveis de ambiente faltando: {', '.join(missing_vars)}")
        sys.exit(1)
    
    print("✅ Variáveis de ambiente configuradas")
    
    try:
        # Executar com timeout de 25 minutos
        sucesso = asyncio.run(asyncio.wait_for(sistema_completo_sienge(), timeout=1500.0))
        
        if sucesso:
            print("\n✅ SISTEMA COMPLETO CONCLUÍDO COM SUCESSO!")
            print("Dados do Sienge atualizados no MotherDuck")
            print("Tabela: sienge_relatorio_pedidos_compras")
            sys.exit(0)
        else:
            print("\n❌ FALHA NO SISTEMA COMPLETO")
            print("Verifique os logs acima para detalhes")
            sys.exit(1)
            
    except asyncio.TimeoutError:
        print("\n⏱️ TIMEOUT - Operação demorou mais de 25 minutos")
        print("Considere otimizar o pipeline ou aumentar o timeout")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ ERRO INESPERADO: {e}")
        print("Verifique a configuração e conectividade")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
