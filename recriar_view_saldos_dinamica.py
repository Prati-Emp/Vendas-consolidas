#!/usr/bin/env python3
"""
Script para recriar a view saldos_bancarios_consolidado com lógica dinâmica de blocos
Versão corrigida para incluir o primeiro bloco de dados (semana de 25/09/2023)
"""

import os
import duckdb
from dotenv import load_dotenv

def conectar_motherduck():
    """Conecta ao MotherDuck"""
    try:
        load_dotenv('.env')
        token = os.getenv('MOTHERDUCK_TOKEN')
        if not token:
            print("ERRO: Token do MotherDuck nao encontrado!")
            return None
        
        print("Conectando ao MotherDuck...")
        conn = duckdb.connect(f'md:?motherduck_token={token}')
        print("Conexao estabelecida com sucesso!")
        return conn
        
    except Exception as e:
        print(f"ERRO na conexao: {e}")
        return None

def criar_view_dinamica(conn):
    """Recria a view usando window functions com grupos para simular forward fill"""
    print("\n" + "="*60)
    print("RECRIANDO VIEW COM LOGICA DINAMICA DE BLOCOS (V4 - CORRECAO SEMANA 25/09)")
    print("="*60)
    
    try:
        # CTEs
        cte_base = """
        WITH raw_data AS (
            SELECT 
                *,
                ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) as row_num
            FROM planilhas.saldos_banc_rios
        ),
        marked_headers AS (
            SELECT 
                *,
                CASE 
                    WHEN TRIM(LOWER(saldos_bancarios)) = 'saldos bancarios' THEN 1 
                    ELSE 0 
                END as is_header
            FROM raw_data
        ),
        grouped_blocks AS (
            SELECT
                *,
                -- Cria um ID de grupo que incrementa a cada header encontrado
                -- O primeiro bloco (antes do primeiro header) tera block_id = 0
                SUM(is_header) OVER (ORDER BY row_num) as block_id
            FROM marked_headers
        ),
        filled_dates AS (
            SELECT 
                row_num,
                saldos_bancarios as categoria,
                is_header,
                block_id,
                
                -- Para cada par, propagar o valor do header para todo o bloco
                -- CORRECAO: Se block_id = 0, usar o nome da coluna como data (primeira semana)
                
                -- Par 1 (Sicredi)
                CASE 
                    WHEN block_id = 0 THEN '2023_09_25_00_00_00'
                    ELSE MAX(CASE WHEN is_header = 1 THEN "2023_09_25_00_00_00" ELSE NULL END) OVER (PARTITION BY block_id) 
                END as date_1,
                "2023_09_25_00_00_00" as val_sicredi_1,
                "unnamed_2" as val_cef_1,
                
                -- Par 2 (Sicredi)
                CASE 
                    WHEN block_id = 0 THEN '2023_09_26_00_00_00'
                    ELSE 
                        CASE
                            -- CORRECAO DE ERRO DE DIGITACAO: 2025-02-11 digitado como 2025-12-11
                            -- Se a data 1 do bloco for 2025-02-10 e a data 2 for 2025-12-11, corrige para 2025-02-11
                            WHEN MAX(CASE WHEN is_header = 1 THEN "2023_09_26_00_00_00" ELSE NULL END) OVER (PARTITION BY block_id) LIKE '%2025-12-11%'
                             AND MAX(CASE WHEN is_header = 1 THEN "2023_09_25_00_00_00" ELSE NULL END) OVER (PARTITION BY block_id) LIKE '%2025-02-10%'
                            THEN '2025-02-11 00:00:00'
                            
                            ELSE MAX(CASE WHEN is_header = 1 THEN "2023_09_26_00_00_00" ELSE NULL END) OVER (PARTITION BY block_id)
                        END
                END as date_2,
                "2023_09_26_00_00_00" as val_sicredi_2,
                "unnamed_4" as val_cef_2,
                
                -- Par 3 (Sicredi)
                CASE 
                    WHEN block_id = 0 THEN '2023_09_27_00_00_00'
                    ELSE MAX(CASE WHEN is_header = 1 THEN "2023_09_27_00_00_00" ELSE NULL END) OVER (PARTITION BY block_id)
                END as date_3,
                "2023_09_27_00_00_00" as val_sicredi_3,
                "unnamed_6" as val_cef_3,
                
                -- Par 4 (Sicredi)
                CASE 
                    WHEN block_id = 0 THEN '2023_09_28_00_00_00'
                    ELSE MAX(CASE WHEN is_header = 1 THEN "2023_09_28_00_00_00" ELSE NULL END) OVER (PARTITION BY block_id)
                END as date_4,
                "2023_09_28_00_00_00" as val_sicredi_4,
                "unnamed_8" as val_cef_4,
                
                -- Par 5 (Sicredi)
                CASE 
                    WHEN block_id = 0 THEN '2023_09_29_00_00_00'
                    ELSE MAX(CASE WHEN is_header = 1 THEN "2023_09_29_00_00_00" ELSE NULL END) OVER (PARTITION BY block_id)
                END as date_5,
                "2023_09_29_00_00_00" as val_sicredi_5,
                "unnamed_10" as val_cef_5
                
            FROM grouped_blocks
        ),
        clean_rows AS (
            SELECT *
            FROM filled_dates
            WHERE is_header = 0
              AND categoria IS NOT NULL 
              AND TRIM(categoria) != ''
              AND categoria NOT IN ('Sicredi', 'CEF', 'total_semana', 'Total Semana')
        )
        """
        
        union_parts = []
        for i in range(1, 6):
            # Sicredi
            union_parts.append(f"""
            SELECT 
                date_{i} as raw_date,
                'Sicredi' as Banco,
                categoria,
                val_sicredi_{i} as valor_str
            FROM clean_rows
            WHERE val_sicredi_{i} IS NOT NULL AND TRIM(val_sicredi_{i}) != ''
            """)
            
            # CEF
            union_parts.append(f"""
            SELECT 
                date_{i} as raw_date,
                'CEF' as Banco,
                categoria,
                val_cef_{i} as valor_str
            FROM clean_rows
            WHERE val_cef_{i} IS NOT NULL AND TRIM(val_cef_{i}) != ''
            """)
            
        full_union = " UNION ALL ".join(union_parts)
        
        sql = f"""
        CREATE OR REPLACE VIEW administracao.saldos_bancarios_consolidado AS
        {cte_base},
        unpivoted_data AS (
            {full_union}
        ),
        processed_data AS (
            SELECT
                -- Tratamento de Data usando REGEX para identificar formato YYYY_MM_DD
                CASE 
                    WHEN regexp_matches(raw_date, '\d{{4}}_\d{{2}}_\d{{2}}.*') THEN 
                        TRY_CAST(strptime(SUBSTRING(raw_date, 1, 10), '%Y_%m_%d') AS DATE)
                    ELSE 
                        TRY_CAST(raw_date AS DATE)
                END as Data_Transacao,
                
                Banco,
                
                -- Tratamento de Categoria
                CASE 
                    -- Normalizacao de grafia para manter consistencia, mas respeitando separacao
                    WHEN categoria = 'Pagamentos/ Aplic.' THEN 'Pagamentos/ Aplicações'
                    WHEN categoria = 'Aplicação' THEN 'Aplicação' -- Mantem separado
                    WHEN categoria = 'Pagamentos' THEN 'Pagamentos' -- Mantem separado
                    
                    WHEN categoria = 'Recebimentos' THEN 'Recebimentos' -- Mantem separado
                    WHEN categoria = 'Resgate' THEN 'Resgate' -- Mantem separado
                    -- 'Recebimentos/ Resgate' ja esta correto
                    
                    ELSE categoria
                END as Categoria,
                
                -- Tratamento de Valor
                TRY_CAST(REPLACE(REPLACE(valor_str, '.', ''), ',', '.') AS DOUBLE) as Valor_Clean,
                TRY_CAST(valor_str AS DOUBLE) as Valor_Direct
            FROM unpivoted_data
            WHERE raw_date IS NOT NULL
        )
        SELECT 
            Data_Transacao,
            Banco,
            Categoria,
            COALESCE(Valor_Direct, Valor_Clean) as Valor
        FROM processed_data
        WHERE COALESCE(Valor_Direct, Valor_Clean) IS NOT NULL
        ORDER BY Data_Transacao, Banco, Categoria
        """
        
        conn.execute(sql)
        print("View criada com sucesso!")
        
        # Validar
        print("\nVerificando totais:")
        result = conn.execute("SELECT COUNT(*), COUNT(DISTINCT Data_Transacao) FROM administracao.saldos_bancarios_consolidado").fetchone()
        print(f"Total Registros: {result[0]}")
        print(f"Dias Únicos: {result[1]}")
        
        print("\nAmostra de Categorias:")
        cats = conn.execute("SELECT DISTINCT Categoria FROM administracao.saldos_bancarios_consolidado ORDER BY 1").fetchall()
        for c in cats:
            print(f"- {c[0]}")

        print("\nAmostra de Datas (Primeiras 10):")
        dates = conn.execute("SELECT DISTINCT Data_Transacao FROM administracao.saldos_bancarios_consolidado ORDER BY 1 LIMIT 10").fetchall()
        for d in dates:
            print(f"- {d[0]}")
        
        # Verificar especificamente 25/09/2023
        print("\nVerificando 25/09/2023:")
        count_25 = conn.execute("SELECT COUNT(*) FROM administracao.saldos_bancarios_consolidado WHERE Data_Transacao = '2023-09-25'").fetchone()[0]
        print(f"Registros em 2023-09-25: {count_25}")
            
        return True
        
    except Exception as e:
        print(f"ERRO ao criar view: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    conn = conectar_motherduck()
    if conn:
        criar_view_dinamica(conn)
        conn.close()

if __name__ == "__main__":
    main()