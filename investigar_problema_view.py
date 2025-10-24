#!/usr/bin/env python3
"""
Script para investigar o problema na view
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

def investigar_problema_view(conn):
    """Investiga o problema na view"""
    print("\n" + "="*60)
    print("INVESTIGANDO PROBLEMA NA VIEW")
    print("="*60)
    
    try:
        # 1. Verificar contagem das tabelas base
        print("1. Verificando contagem das tabelas base...")
        try:
            result = conn.execute("SELECT COUNT(*) FROM reservas.sienge_vendas_realizadas").fetchone()
            print(f"   reservas.sienge_vendas_realizadas: {result[0]:,}")
            
            result = conn.execute("SELECT COUNT(*) FROM reservas.sienge_vendas_canceladas").fetchone()
            print(f"   reservas.sienge_vendas_canceladas: {result[0]:,}")
            
            result = conn.execute("SELECT COUNT(*) FROM reservas.cv_vendas_consolidadas_vera_cruz").fetchone()
            print(f"   reservas.cv_vendas_consolidadas_vera_cruz: {result[0]:,}")
            
            total_esperado = 1058 + 39 + 53
            print(f"   Total esperado: {total_esperado:,}")
            
        except Exception as e:
            print(f"   ERRO: {e}")
        
        # 2. Testar cada seção da view individualmente
        print("\n2. Testando cada seção da view individualmente...")
        
        # Testar seção Sienge Realizadas
        try:
            print("   Testando seção Sienge Realizadas...")
            sql_sienge_realizadas = """
            SELECT COUNT(*) as total
            FROM (
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
            ) as sienge_realizadas
            """
            
            result = conn.execute(sql_sienge_realizadas).fetchone()
            print(f"   Sienge Realizadas: {result[0]:,} registros")
            
        except Exception as e:
            print(f"   ERRO Sienge Realizadas: {e}")
        
        # Testar seção Sienge Canceladas
        try:
            print("   Testando seção Sienge Canceladas...")
            sql_sienge_canceladas = """
            SELECT COUNT(*) as total
            FROM (
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
            ) as sienge_canceladas
            """
            
            result = conn.execute(sql_sienge_canceladas).fetchone()
            print(f"   Sienge Canceladas: {result[0]:,} registros")
            
        except Exception as e:
            print(f"   ERRO Sienge Canceladas: {e}")
        
        # Testar seção Reservas Vera Cruz
        try:
            print("   Testando seção Reservas Vera Cruz...")
            sql_reservas = """
            SELECT COUNT(*) as total
            FROM (
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
                    r.renda as profissao,
                    r.documento_cliente,
                    r.idcliente,
                    r.idcorretor,
                    r.idimobiliaria,
                    r.sexo,
                    r.estado_civil,
                    r.idade,
                    r.renda,
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
            ) as reservas
            """
            
            result = conn.execute(sql_reservas).fetchone()
            print(f"   Reservas Vera Cruz: {result[0]:,} registros")
            
        except Exception as e:
            print(f"   ERRO Reservas Vera Cruz: {e}")
        
        # 3. Verificar se há problema no LEFT JOIN
        print("\n3. Verificando se há problema no LEFT JOIN...")
        try:
            # Verificar quantos registros tem a tabela reservas_abril
            result = conn.execute("SELECT COUNT(*) FROM reservas.reservas_abril").fetchone()
            print(f"   reservas.reservas_abril: {result[0]:,} registros")
            
            # Verificar se há duplicatas na tabela reservas_abril
            result = conn.execute("""
                SELECT COUNT(*) as total, COUNT(DISTINCT idempreendimento) as unicos
                FROM reservas.reservas_abril
            """).fetchone()
            
            print(f"   Total: {result[0]:,}, Únicos por empreendimento: {result[1]:,}")
            if result[0] != result[1]:
                print(f"   ⚠️  DUPLICATAS ENCONTRADAS: {result[0] - result[1]:,}")
                
        except Exception as e:
            print(f"   ERRO: {e}")
        
        # 4. Verificar se há problema na view atual
        print("\n4. Verificando view atual...")
        try:
            conn.execute("USE informacoes_consolidadas")
            result = conn.execute("SELECT COUNT(*) FROM sienge_vendas_consolidadas").fetchone()
            print(f"   informacoes_consolidadas.sienge_vendas_consolidadas: {result[0]:,}")
        except Exception as e:
            print(f"   ERRO: {e}")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao investigar: {e}")
        return False

def main():
    """Funcao principal"""
    print("INVESTIGANDO PROBLEMA NA VIEW")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        investigar_problema_view(conn)
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

