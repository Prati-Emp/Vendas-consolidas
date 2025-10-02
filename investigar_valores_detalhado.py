#!/usr/bin/env python3
"""
Script para investigar detalhadamente os valores na tabela cv_repasses
"""

import os
import duckdb
import pandas as pd
from dotenv import load_dotenv

def conectar_motherduck():
    """Conecta ao banco MotherDuck"""
    load_dotenv('motherduck_config.env')
    
    token = os.environ.get('MOTHERDUCK_TOKEN', '').strip()
    if not token:
        raise ValueError("MOTHERDUCK_TOKEN nao encontrado")
    
    # Configurar DuckDB
    duckdb.sql("INSTALL motherduck")
    duckdb.sql("LOAD motherduck")
    duckdb.sql(f"SET motherduck_token='{token}'")
    
    # Conectar
    conn = duckdb.connect('md:reservas')
    return conn

def investigar_valores_detalhado():
    """Investiga os valores em detalhes"""
    print("INVESTIGACAO DETALHADA DOS VALORES - CV_REPASSES")
    print("="*60)
    
    conn = conectar_motherduck()
    
    try:
        # Verificar se existe backup para comparar
        backup_exists = conn.execute("""
            SELECT COUNT(*) as count 
            FROM information_schema.tables 
            WHERE table_name = 'cv_repasses_backup'
        """).fetchone()[0]
        
        if backup_exists > 0:
            print("Backup encontrado. Comparando valores...")
            
            # Comparar alguns registros específicos
            print("\nComparando registros específicos:")
            print("-" * 60)
            
            # Pegar alguns registros para comparar
            comparacao = conn.execute("""
                SELECT 
                    a.idrepasse,
                    a.valor_contrato as valor_atual,
                    b.valor_contrato as valor_backup,
                    a.Para,
                    a.empreendimento
                FROM main.cv_repasses a
                JOIN main.cv_repasses_backup b ON a.idrepasse = b.idrepasse
                WHERE a.valor_contrato IS NOT NULL
                ORDER BY a.valor_contrato DESC
                LIMIT 10
            """).fetchall()
            
            print("ID | Valor Atual | Valor Backup | Status | Empreendimento")
            print("-" * 80)
            for idrepasse, atual, backup, status, empreendimento in comparacao:
                print(f"{idrepasse} | R$ {atual:,.2f} | R$ {backup:,.2f} | {status} | {empreendimento}")
                
                # Verificar se o valor mudou
                if atual != backup:
                    print(f"  -> VALOR MUDOU: {backup:,.2f} -> {atual:,.2f}")
                else:
                    print(f"  -> VALOR NAO MUDOU")
            
            # Verificar se os valores estão em centavos
            print("\nVerificando se valores estão em centavos:")
            print("-" * 60)
            
            # Se dividirmos por 100, os valores fazem mais sentido?
            teste_centavos = conn.execute("""
                SELECT 
                    ROUND(AVG(valor_contrato / 100), 2) as media_centavos,
                    ROUND(SUM(valor_contrato / 100), 2) as total_centavos,
                    ROUND(MIN(valor_contrato / 100), 2) as min_centavos,
                    ROUND(MAX(valor_contrato / 100), 2) as max_centavos
                FROM main.cv_repasses
                WHERE valor_contrato IS NOT NULL
            """).fetchone()
            
            print("Se dividirmos por 100 (convertendo centavos para reais):")
            print(f"  Valor médio: R$ {teste_centavos[0]:,.2f}")
            print(f"  Valor total: R$ {teste_centavos[1]:,.2f}")
            print(f"  Valor mínimo: R$ {teste_centavos[2]:,.2f}")
            print(f"  Valor máximo: R$ {teste_centavos[3]:,.2f}")
            
            # Verificar se faz mais sentido
            if teste_centavos[0] < 1000000:  # Se valor médio < 1 milhão
                print("\nESTE FAZ MAIS SENTIDO! Os valores provavelmente estão em centavos.")
                print("Precisamos dividir por 100 para obter os valores corretos.")
                return True
            else:
                print("\nAinda não faz sentido. Investigando mais...")
                
                # Verificar se há valores em formato de string no backup
                print("\nVerificando formato dos valores no backup:")
                backup_format = conn.execute("""
                    SELECT 
                        typeof(valor_contrato) as tipo,
                        COUNT(*) as count
                    FROM main.cv_repasses_backup
                    GROUP BY typeof(valor_contrato)
                """).fetchall()
                
                for tipo, count in backup_format:
                    print(f"  {tipo}: {count} registros")
                
                # Mostrar alguns exemplos de valores do backup
                print("\nExemplos de valores do backup:")
                exemplos_backup = conn.execute("""
                    SELECT valor_contrato, Para, empreendimento
                    FROM main.cv_repasses_backup
                    ORDER BY valor_contrato DESC
                    LIMIT 5
                """).fetchall()
                
                for valor, status, empreendimento in exemplos_backup:
                    print(f"  R$ {valor:,.2f} - {status} - {empreendimento}")
                
                return False
        else:
            print("Backup não encontrado!")
            return False
            
    except Exception as e:
        print(f"Erro: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()

def corrigir_valores_centavos():
    """Corrige os valores dividindo por 100 (centavos para reais)"""
    print("\n" + "="*60)
    print("CORRIGINDO VALORES (CENTAVOS -> REAIS)")
    print("="*60)
    
    conn = conectar_motherduck()
    
    try:
        # Criar backup antes da correção
        print("1. Criando backup antes da correção...")
        conn.execute("CREATE TABLE IF NOT EXISTS main.cv_repasses_backup_centavos AS SELECT * FROM main.cv_repasses")
        print("   Backup criado: cv_repasses_backup_centavos")
        
        # Aplicar correção dividindo por 100
        print("2. Aplicando correção (dividindo por 100)...")
        
        # Colunas de valor para corrigir
        colunas_valor = [
            'valor_previsto', 'valor_divida', 'valor_subsidio', 
            'valor_fgts', 'valor_registro', 'valor_financiado', 'valor_contrato'
        ]
        
        for col in colunas_valor:
            print(f"   Corrigindo {col}...")
            conn.execute(f"""
                UPDATE main.cv_repasses 
                SET {col} = {col} / 100.0
                WHERE {col} IS NOT NULL
            """)
        
        # Verificar resultado
        print("3. Verificando resultado...")
        resultado = conn.execute("""
            SELECT 
                COUNT(*) as total_registros,
                ROUND(AVG(valor_contrato), 2) as valor_medio,
                ROUND(SUM(valor_contrato), 2) as valor_total,
                ROUND(MIN(valor_contrato), 2) as valor_min,
                ROUND(MAX(valor_contrato), 2) as valor_max
            FROM main.cv_repasses
            WHERE valor_contrato IS NOT NULL
        """).fetchone()
        
        print(f"   Total registros: {resultado[0]:,}")
        print(f"   Valor médio: R$ {resultado[1]:,.2f}")
        print(f"   Valor total: R$ {resultado[2]:,.2f}")
        print(f"   Valor mínimo: R$ {resultado[3]:,.2f}")
        print(f"   Valor máximo: R$ {resultado[4]:,.2f}")
        
        if resultado[1] < 1000000:  # Se valor médio < 1 milhão
            print("\nCORRECAO APLICADA COM SUCESSO!")
            print("Os valores agora fazem sentido.")
            return True
        else:
            print("\nOs valores ainda estão muito altos.")
            return False
            
    except Exception as e:
        print(f"Erro na correção: {e}")
        return False
    finally:
        conn.close()

def main():
    """Função principal"""
    print("INVESTIGACAO E CORRECAO DE VALORES - CV_REPASSES")
    print("="*60)
    
    try:
        # Investigar valores
        valores_ok = investigar_valores_detalhado()
        
        if not valores_ok:
            print("\nOs valores não fazem sentido. Tentando correção...")
            corrigir_valores_centavos()
        
    except Exception as e:
        print(f"Erro durante a investigação: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
