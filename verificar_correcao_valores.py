#!/usr/bin/env python3
"""
Script para verificar se a correção de valores foi aplicada corretamente
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

def verificar_valores_atuais():
    """Verifica os valores atuais na tabela cv_repasses"""
    print("VERIFICANDO VALORES ATUAIS - CV_REPASSES")
    print("="*60)
    
    conn = conectar_motherduck()
    
    try:
        # Verificar se existe backup
        backup_exists = conn.execute("""
            SELECT COUNT(*) as count 
            FROM information_schema.tables 
            WHERE table_name = 'cv_repasses_backup'
        """).fetchone()[0]
        
        if backup_exists > 0:
            print("✅ Backup encontrado: cv_repasses_backup")
            
            # Comparar valores entre tabela atual e backup
            print("\nComparando valores entre tabela atual e backup:")
            print("-" * 60)
            
            # Valores da tabela atual
            atual = conn.execute("""
                SELECT 
                    COUNT(*) as total_registros,
                    ROUND(AVG(valor_contrato), 2) as valor_medio_atual,
                    ROUND(SUM(valor_contrato), 2) as valor_total_atual,
                    ROUND(MIN(valor_contrato), 2) as valor_min_atual,
                    ROUND(MAX(valor_contrato), 2) as valor_max_atual
                FROM main.cv_repasses
                WHERE valor_contrato IS NOT NULL
            """).fetchone()
            
            # Valores do backup
            backup = conn.execute("""
                SELECT 
                    COUNT(*) as total_registros,
                    ROUND(AVG(valor_contrato), 2) as valor_medio_backup,
                    ROUND(SUM(valor_contrato), 2) as valor_total_backup,
                    ROUND(MIN(valor_contrato), 2) as valor_min_backup,
                    ROUND(MAX(valor_contrato), 2) as valor_max_backup
                FROM main.cv_repasses_backup
                WHERE valor_contrato IS NOT NULL
            """).fetchone()
            
            print("TABELA ATUAL:")
            print(f"  Total registros: {atual[0]:,}")
            print(f"  Valor médio: R$ {atual[1]:,.2f}")
            print(f"  Valor total: R$ {atual[2]:,.2f}")
            print(f"  Valor mínimo: R$ {atual[3]:,.2f}")
            print(f"  Valor máximo: R$ {atual[4]:,.2f}")
            
            print("\nBACKUP (ANTES DA CORREÇÃO):")
            print(f"  Total registros: {backup[0]:,}")
            print(f"  Valor médio: R$ {backup[1]:,.2f}")
            print(f"  Valor total: R$ {backup[2]:,.2f}")
            print(f"  Valor mínimo: R$ {backup[3]:,.2f}")
            print(f"  Valor máximo: R$ {backup[4]:,.2f}")
            
            # Calcular diferenças
            print("\nDIFERENÇAS:")
            print(f"  Diferença no valor médio: R$ {atual[1] - backup[1]:,.2f}")
            print(f"  Diferença no valor total: R$ {atual[2] - backup[2]:,.2f}")
            
            # Verificar se os valores ainda estão muito altos
            if atual[1] > 1000000:  # Se valor médio > 1 milhão
                print("\n⚠️  ATENÇÃO: Os valores ainda estão muito altos!")
                print("   Isso indica que a correção pode não ter sido aplicada corretamente.")
                
                # Mostrar alguns exemplos de valores
                print("\nExemplos de valores atuais:")
                exemplos = conn.execute("""
                    SELECT valor_contrato, Para
                    FROM main.cv_repasses 
                    ORDER BY valor_contrato DESC 
                    LIMIT 5
                """).fetchall()
                
                for valor, status in exemplos:
                    print(f"  R$ {valor:,.2f} - {status}")
                
                return False
            else:
                print("\n✅ Valores parecem estar corretos!")
                return True
        else:
            print("❌ Backup não encontrado!")
            return False
            
    except Exception as e:
        print(f"Erro: {e}")
        return False
    finally:
        conn.close()

def verificar_exemplos_especificos():
    """Verifica exemplos específicos de valores"""
    print("\n" + "="*60)
    print("VERIFICANDO EXEMPLOS ESPECÍFICOS")
    print("="*60)
    
    conn = conectar_motherduck()
    
    try:
        # Buscar registros com valores suspeitos (muito altos)
        print("Registros com valores suspeitos (> 1 milhão):")
        suspeitos = conn.execute("""
            SELECT 
                valor_contrato,
                Para,
                empreendimento,
                cliente
            FROM main.cv_repasses 
            WHERE valor_contrato > 1000000
            ORDER BY valor_contrato DESC
            LIMIT 10
        """).fetchall()
        
        if suspeitos:
            print(f"Encontrados {len(suspeitos)} registros com valores > R$ 1 milhão:")
            for valor, status, empreendimento, cliente in suspeitos:
                print(f"  R$ {valor:,.2f} - {status} - {empreendimento} - {cliente}")
        else:
            print("Nenhum registro com valores suspeitos encontrado.")
            
        # Verificar se há valores em formato de string
        print("\nVerificando se há valores em formato de string:")
        string_values = conn.execute("""
            SELECT valor_contrato, COUNT(*) as count
            FROM main.cv_repasses 
            WHERE typeof(valor_contrato) = 'VARCHAR'
            GROUP BY valor_contrato
            LIMIT 5
        """).fetchall()
        
        if string_values:
            print("Valores em formato string encontrados:")
            for valor, count in string_values:
                print(f"  '{valor}' - {count} registros")
        else:
            print("Todos os valores estão em formato numérico.")
            
    except Exception as e:
        print(f"Erro: {e}")
    finally:
        conn.close()

def main():
    """Função principal"""
    print("VERIFICAÇÃO DA CORREÇÃO DE VALORES - CV_REPASSES")
    print("="*60)
    
    try:
        # Verificar valores atuais
        valores_ok = verificar_valores_atuais()
        
        # Verificar exemplos específicos
        verificar_exemplos_especificos()
        
        print("\n" + "="*60)
        if valores_ok:
            print("✅ CORREÇÃO APLICADA COM SUCESSO!")
        else:
            print("❌ CORREÇÃO PODE NÃO TER SIDO APLICADA CORRETAMENTE!")
            print("   Recomenda-se executar novamente o script de correção.")
        print("="*60)
        
    except Exception as e:
        print(f"Erro durante a verificação: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

