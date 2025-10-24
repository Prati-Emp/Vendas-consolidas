#!/usr/bin/env python3
"""
Script para verificar colunas detalhadamente
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

def verificar_colunas_detalhado(conn):
    """Verifica colunas detalhadamente"""
    print("\n" + "="*60)
    print("VERIFICANDO COLUNAS DETALHADAMENTE")
    print("="*60)
    
    try:
        # 1. Verificar view cv_vendas_consolidadas_vera_cruz
        print("1. Verificando view cv_vendas_consolidadas_vera_cruz...")
        try:
            columns_vera_cruz = conn.execute("DESCRIBE reservas.cv_vendas_consolidadas_vera_cruz").fetchall()
            print(f"   Total de colunas: {len(columns_vera_cruz)}")
            print("   Colunas:")
            for i, col in enumerate(columns_vera_cruz, 1):
                print(f"   {i:2d}. {col[0]} ({col[1]})")
        except Exception as e:
            print(f"   ERRO: {e}")
        
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
        
        # 3. Testar seção Sienge Canceladas
        print("\n3. Testando seção Sienge Canceladas...")
        try:
            sql_sienge_canceladas = """
            SELECT
                CAST(s.enterpriseId AS INTEGER) as enterpriseId,
                COALESCE(r.empreendimento, CASE WHEN s.enterpriseId = '19' THEN 'Ondina II' ELSE 'Sienge Cancelada' END) as nome_empreendimento,
                s.value,
                CAST(s.issueDate AS DATE) as issueDate,
                CAST(s.contractDate AS DATE) as contractDate,
                'Sienge Cancelada' as origem,
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
            FROM reservas.sienge_vendas_canceladas s
            LEFT JOIN (SELECT DISTINCT idempreendimento, empreendimento, corretor, imobiliaria, idcorretor, idimobiliaria FROM reservas.reservas_abril) r ON CAST(s.enterpriseId AS INTEGER) = r.idempreendimento
            LIMIT 1
            """
            
            result = conn.execute(sql_sienge_canceladas).fetchone()
            print(f"   Sienge Canceladas: {len(result)} colunas")
            
        except Exception as e:
            print(f"   ERRO Sienge Canceladas: {e}")
        
        # 4. Testar seção Reservas Vera Cruz
        print("\n4. Testando seção Reservas Vera Cruz...")
        try:
            sql_reservas = """
            SELECT
                r.enterpriseId,
                r.nome_empreendimento,
                r.value,
                r.issueDate,
                r.contractDate,
                r.origem,
                r.corretor,
                r.imobiliaria,
                r.cliente,
                r.email,
                r.cidade,
                r.cep_cliente,
                r.renda,
                r.sexo,
                r.idade,
                r.estado_civil,
                r.documento_cliente,
                r.idcliente,
                r.idcorretor,
                r.idimobiliaria,
                r.situacao_original,
                r.data_venda,
                r.valor_contrato_com_juros,
                r.vencimento,
                r.campanha,
                r.midia,
                r.tipovenda,
                r.grupo,
                r.regiao,
                r.bloco,
                r.unidade,
                r.etapa,
                r.vpl_reserva,
                r.vpl_tabela,
                r.idreserva
            FROM reservas.cv_vendas_consolidadas_vera_cruz r
            LIMIT 1
            """
            
            result = conn.execute(sql_reservas).fetchone()
            print(f"   Reservas Vera Cruz: {len(result)} colunas")
            
        except Exception as e:
            print(f"   ERRO Reservas Vera Cruz: {e}")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao verificar colunas: {e}")
        return False

def main():
    """Funcao principal"""
    print("VERIFICANDO COLUNAS DETALHADAMENTE")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        verificar_colunas_detalhado(conn)
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