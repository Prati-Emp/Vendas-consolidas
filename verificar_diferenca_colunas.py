#!/usr/bin/env python3
"""
Script para verificar a diferença exata entre as colunas
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

def verificar_diferenca_colunas(conn):
    """Verifica a diferença exata entre as colunas"""
    print("\n" + "="*60)
    print("VERIFICANDO DIFERENCA EXATA ENTRE COLUNAS")
    print("="*60)
    
    try:
        # 1. Verificar view cv_vendas_consolidadas_vera_cruz
        print("1. Verificando view cv_vendas_consolidadas_vera_cruz...")
        columns_vera_cruz = conn.execute("DESCRIBE reservas.cv_vendas_consolidadas_vera_cruz").fetchall()
        print(f"   Total de colunas: {len(columns_vera_cruz)}")
        
        # 2. Testar seção Sienge Realizadas
        print("\n2. Testando seção Sienge Realizadas...")
        try:
            sql_sienge_realizadas = """
            SELECT
                CAST(s.enterpriseId AS INTEGER) as enterpriseId,
                COALESCE(r.empreendimento, CASE WHEN s.enterpriseId = '19' THEN 'Ondina II' ELSE 'Sienge Realizada' END) as nome_empreendimento,
                s.value,
                CAST(s.issueDate AS DATE) as issueDate,
                CAST(s.contractDate AS DATE) as contractDate,
                'Sienge Realizada' as origem,
                COALESCE(r.corretor, s.brokers[1].name) as corretor,
                COALESCE(r.imobiliaria, (SELECT imobiliaria FROM reservas.reservas_abril WHERE idimobiliaria = s.brokers[1].id LIMIT 1)) as imobiliaria,
                s.customers[1].name as cliente,
                s.customers[1].email as email,
                s.customers[1].addresses[1].city as cidade,
                s.customers[1].addresses[1].zipCode as cep_cliente,
                s.customers[1].profession as profissao,
                s.customers[1].cpf as documento_cliente,
                s.customers[1].id as idcliente,
                s.brokers[1].id as idcorretor,
                (SELECT idimobiliaria FROM reservas.reservas_abril WHERE idimobiliaria = s.brokers[1].id LIMIT 1) as idimobiliaria,
                s.customers[1].sex as sexo,
                s.customers[1].civilStatus as estado_civil,
                NULL as idade,
                NULL as renda,
                NULL as situacao_original,
                NULL as data_venda,
                NULL as valor_contrato_com_juros,
                NULL as vencimento,
                NULL as campanha,
                NULL as midia,
                NULL as tipovenda,
                NULL as grupo,
                NULL as regiao,
                NULL as bloco,
                NULL as unidade,
                NULL as etapa,
                (SELECT vpl_reserva FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as vpl_reserva,
                (SELECT vpl_tabela FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as vpl_tabela,
                (SELECT idreserva FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as idreserva
            FROM reservas.sienge_vendas_realizadas s
            LEFT JOIN (SELECT DISTINCT idempreendimento, empreendimento, corretor, imobiliaria, idcorretor, idimobiliaria FROM reservas.reservas_abril) r ON CAST(s.enterpriseId AS INTEGER) = r.idempreendimento
            LIMIT 1
            """
            
            result = conn.execute(sql_sienge_realizadas).fetchone()
            print(f"   Sienge Realizadas: {len(result)} colunas")
            
        except Exception as e:
            print(f"   ERRO Sienge Realizadas: {e}")
        
        # 3. Comparar as colunas
        print("\n3. Comparando colunas...")
        
        # Colunas esperadas na ordem correta
        colunas_esperadas = [
            'enterpriseId', 'nome_empreendimento', 'value', 'issueDate', 'contractDate', 'origem',
            'corretor', 'imobiliaria', 'cliente', 'email', 'cidade', 'cep_cliente', 'profissao',
            'documento_cliente', 'idcliente', 'idcorretor', 'idimobiliaria', 'sexo', 'estado_civil',
            'idade', 'renda', 'situacao_original', 'data_venda', 'valor_contrato_com_juros', 'vencimento',
            'campanha', 'midia', 'tipovenda', 'grupo', 'regiao', 'bloco', 'unidade', 'etapa',
            'vpl_reserva', 'vpl_tabela', 'idreserva'
        ]
        
        print(f"   Colunas esperadas: {len(colunas_esperadas)}")
        print("   Lista de colunas esperadas:")
        for i, col in enumerate(colunas_esperadas, 1):
            print(f"   {i:2d}. {col}")
        
        # Verificar se a view Vera Cruz tem todas as colunas esperadas
        colunas_vera_cruz = [col[0] for col in columns_vera_cruz]
        print(f"\n   Colunas da view Vera Cruz: {len(colunas_vera_cruz)}")
        
        print("\n   Comparando colunas:")
        for i, col_esperada in enumerate(colunas_esperadas, 1):
            if i <= len(colunas_vera_cruz):
                col_vera_cruz = colunas_vera_cruz[i-1]
                if col_esperada == col_vera_cruz:
                    print(f"   {i:2d}. OK {col_esperada}")
                else:
                    print(f"   {i:2d}. DIFERENTE: esperada '{col_esperada}', encontrada '{col_vera_cruz}'")
            else:
                print(f"   {i:2d}. FALTANDO: {col_esperada}")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao verificar diferença: {e}")
        return False

def main():
    """Funcao principal"""
    print("VERIFICANDO DIFERENCA EXATA ENTRE COLUNAS")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        verificar_diferenca_colunas(conn)
        return True
        
    except Exception as e:
        print(f"ERRO: {e}")
        return False
    
    finally:
        if conn:
            conn.close()
            print("\nConexao com MotherDuck encerrada.")

if __name__ == "__main__":
    main()

