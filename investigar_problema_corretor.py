#!/usr/bin/env python3
"""
Script para investigar o problema da coluna corretor
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

def investigar_problema_corretor(conn):
    """Investiga o problema da coluna corretor"""
    print("\n" + "="*60)
    print("INVESTIGANDO PROBLEMA COLUNA CORRETOR")
    print("="*60)
    
    try:
        # 1. Verificar corretor específico mencionado
        print("1. Verificando corretor 'Alana C. Konzen'...")
        
        # Buscar na view atual
        result = conn.execute("""
            SELECT 
                corretor,
                origem,
                COUNT(*) as total
            FROM informacoes_consolidadas.sienge_vendas_consolidadas
            WHERE corretor LIKE '%Alana%' OR corretor LIKE '%Konzen%'
            GROUP BY corretor, origem
            ORDER BY total DESC
        """).fetchall()
        
        print("   Na view atual:")
        for row in result:
            print(f"   - {row[0]} ({row[1]}): {row[2]:,} registros")
        
        # 2. Verificar nas tabelas Sienge diretamente
        print("\n2. Verificando nas tabelas Sienge diretamente...")
        
        # Sienge Vendas Realizadas
        result = conn.execute("""
            SELECT 
                s.brokers[1].name as corretor,
                COUNT(*) as total
            FROM reservas.sienge_vendas_realizadas s
            WHERE s.brokers[1].name LIKE '%Alana%' OR s.brokers[1].name LIKE '%Konzen%'
            GROUP BY s.brokers[1].name
            ORDER BY total DESC
        """).fetchall()
        
        print("   Sienge Vendas Realizadas:")
        for row in result:
            print(f"   - {row[0]}: {row[1]:,} registros")
        
        # Sienge Vendas Canceladas
        result = conn.execute("""
            SELECT 
                s.brokers[1].name as corretor,
                COUNT(*) as total
            FROM reservas.sienge_vendas_canceladas s
            WHERE s.brokers[1].name LIKE '%Alana%' OR s.brokers[1].name LIKE '%Konzen%'
            GROUP BY s.brokers[1].name
            ORDER BY total DESC
        """).fetchall()
        
        print("   Sienge Vendas Canceladas:")
        for row in result:
            print(f"   - {row[0]}: {row[1]:,} registros")
        
        # 3. Verificar na tabela reservas_abril
        print("\n3. Verificando na tabela reservas_abril...")
        result = conn.execute("""
            SELECT 
                corretor,
                COUNT(*) as total
            FROM reservas.reservas_abril
            WHERE corretor LIKE '%Alana%' OR corretor LIKE '%Konzen%'
            GROUP BY corretor
            ORDER BY total DESC
        """).fetchall()
        
        print("   Reservas Abril:")
        for row in result:
            print(f"   - {row[0]}: {row[1]:,} registros")
        
        # 4. Verificar relacionamentos
        print("\n4. Verificando relacionamentos...")
        
        # Verificar se há correspondência por ID
        result = conn.execute("""
            SELECT 
                s.id,
                s.brokers[1].name as corretor_sienge,
                s.brokers[1].id as idcorretor_sienge,
                (SELECT corretor FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as corretor_reservas,
                (SELECT corretor FROM reservas.reservas_abril WHERE idcorretor = s.brokers[1].id LIMIT 1) as corretor_por_idcorretor
            FROM reservas.sienge_vendas_realizadas s
            WHERE s.brokers[1].name LIKE '%Alana%' OR s.brokers[1].name LIKE '%Konzen%'
            LIMIT 10
        """).fetchall()
        
        print("   Relacionamentos encontrados:")
        for row in result:
            print(f"   ID: {row[0]}")
            print(f"      Corretor Sienge: {row[1]} (ID: {row[2]})")
            print(f"      Corretor por codigointerno: {row[3]}")
            print(f"      Corretor por idcorretor: {row[4]}")
            print()
        
        # 5. Verificar quantos registros estão sendo perdidos
        print("\n5. Verificando quantos registros estão sendo perdidos...")
        
        # Total de registros do corretor nas tabelas Sienge
        result = conn.execute("""
            SELECT 
                'Sienge Realizadas' as origem,
                COUNT(*) as total
            FROM reservas.sienge_vendas_realizadas s
            WHERE s.brokers[1].name LIKE '%Alana%' OR s.brokers[1].name LIKE '%Konzen%'
            
            UNION ALL
            
            SELECT 
                'Sienge Canceladas' as origem,
                COUNT(*) as total
            FROM reservas.sienge_vendas_canceladas s
            WHERE s.brokers[1].name LIKE '%Alana%' OR s.brokers[1].name LIKE '%Konzen%'
        """).fetchall()
        
        print("   Total nas tabelas Sienge:")
        total_sienge = 0
        for row in result:
            print(f"   - {row[0]}: {row[1]:,} registros")
            total_sienge += row[1]
        
        print(f"   Total Sienge: {total_sienge:,} registros")
        
        # Total na view atual
        result = conn.execute("""
            SELECT COUNT(*) as total
            FROM informacoes_consolidadas.sienge_vendas_consolidadas
            WHERE corretor LIKE '%Alana%' OR corretor LIKE '%Konzen%'
        """).fetchone()
        
        print(f"   Total na view atual: {result[0]:,} registros")
        print(f"   Registros perdidos: {total_sienge - result[0]:,} registros")
        
        # 6. Verificar outros corretores para comparar
        print("\n6. Verificando outros corretores para comparar...")
        result = conn.execute("""
            SELECT 
                corretor,
                COUNT(*) as total
            FROM informacoes_consolidadas.sienge_vendas_consolidadas
            WHERE origem IN ('Sienge Realizada', 'Sienge Cancelada')
            GROUP BY corretor
            ORDER BY total DESC
            LIMIT 10
        """).fetchall()
        
        print("   Top 10 corretores na view atual:")
        for row in result:
            print(f"   - {row[0]}: {row[1]:,} registros")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao investigar corretor: {e}")
        return False

def corrigir_coluna_corretor(conn):
    """Corrige a coluna corretor na view"""
    print("\n" + "="*60)
    print("CORRIGINDO COLUNA CORRETOR")
    print("="*60)
    
    try:
        # 1. Usar o banco informacoes_consolidadas
        print("1. Usando banco informacoes_consolidadas...")
        conn.execute("USE informacoes_consolidadas")
        print("   Banco informacoes_consolidadas selecionado!")
        
        # 2. Remover view existente
        print("\n2. Removendo view existente...")
        conn.execute("DROP VIEW IF EXISTS sienge_vendas_consolidadas")
        print("   View existente removida!")
        
        # 3. Criar view corrigida com corretor correto
        print("\n3. Criando view com corretor corrigido...")
        
        sql_view = """
        CREATE VIEW sienge_vendas_consolidadas AS
        -- Seção 1: Vendas Realizadas Sienge (COM CORRETOR CORRIGIDO)
        SELECT
            CAST(s.enterpriseId AS INTEGER) as enterpriseId,
            COALESCE(
                (SELECT empreendimento FROM reservas.reservas_abril 
                 WHERE codigointerno_empreendimento = CAST(s.enterpriseId AS INTEGER) 
                 LIMIT 1),
                CASE WHEN s.enterpriseId = '19' THEN 'Ondina II' ELSE 'Sienge Realizada' END
            ) as nome_empreendimento,
            s.value,
            CAST(s.issueDate AS DATE) as issueDate,
            CAST(s.contractDate AS DATE) as contractDate,
            'Sienge Realizada' as origem,
            -- CORRETOR CORRIGIDO: Usar dados do Sienge como principal, reservas como complemento
            COALESCE(
                s.brokers[1].name,
                (SELECT corretor FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1),
                (SELECT corretor FROM reservas.reservas_abril WHERE idcorretor = s.brokers[1].id LIMIT 1)
            ) as corretor,
            COALESCE(
                (SELECT imobiliaria FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1),
                (SELECT imobiliaria FROM reservas.reservas_abril WHERE idcorretor = s.brokers[1].id LIMIT 1),
                (SELECT imobiliaria FROM reservas.reservas_abril WHERE idimobiliaria = s.brokers[1].id LIMIT 1)
            ) as imobiliaria,
            s.customers[1].name as cliente,
            s.customers[1].email as email,
            s.customers[1].addresses[1].city as cidade,
            s.customers[1].addresses[1].zipCode as cep_cliente,
            s.customers[1].profession as profissao,
            s.customers[1].cpf as documento_cliente,
            s.customers[1].id as idcliente,
            s.brokers[1].id as idcorretor,
            (SELECT idimobiliaria FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as idimobiliaria,
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
            -- COLUNAS EXISTENTES
            (SELECT vpl_reserva FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as vpl_reserva,
            (SELECT vpl_tabela FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as vpl_tabela,
            (SELECT idreserva FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as idreserva
        FROM reservas.sienge_vendas_realizadas s

        UNION ALL

        -- Seção 2: Vendas Canceladas Sienge (COM CORRETOR CORRIGIDO)
        SELECT
            CAST(s.enterpriseId AS INTEGER) as enterpriseId,
            COALESCE(
                (SELECT empreendimento FROM reservas.reservas_abril 
                 WHERE codigointerno_empreendimento = CAST(s.enterpriseId AS INTEGER) 
                 LIMIT 1),
                CASE WHEN s.enterpriseId = '19' THEN 'Ondina II' ELSE 'Sienge Cancelada' END
            ) as nome_empreendimento,
            s.value,
            CAST(s.issueDate AS DATE) as issueDate,
            CAST(s.contractDate AS DATE) as contractDate,
            'Sienge Cancelada' as origem,
            -- CORRETOR CORRIGIDO: Usar dados do Sienge como principal, reservas como complemento
            COALESCE(
                s.brokers[1].name,
                (SELECT corretor FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1),
                (SELECT corretor FROM reservas.reservas_abril WHERE idcorretor = s.brokers[1].id LIMIT 1)
            ) as corretor,
            COALESCE(
                (SELECT imobiliaria FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1),
                (SELECT imobiliaria FROM reservas.reservas_abril WHERE idcorretor = s.brokers[1].id LIMIT 1),
                (SELECT imobiliaria FROM reservas.reservas_abril WHERE idimobiliaria = s.brokers[1].id LIMIT 1)
            ) as imobiliaria,
            s.customers[1].name as cliente,
            s.customers[1].email as email,
            s.customers[1].addresses[1].city as cidade,
            s.customers[1].addresses[1].zipCode as cep_cliente,
            s.customers[1].profession as profissao,
            s.customers[1].cpf as documento_cliente,
            s.customers[1].id as idcliente,
            s.brokers[1].id as idcorretor,
            (SELECT idimobiliaria FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as idimobiliaria,
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
            -- COLUNAS EXISTENTES
            (SELECT vpl_reserva FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as vpl_reserva,
            (SELECT vpl_tabela FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as vpl_tabela,
            (SELECT idreserva FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as idreserva
        FROM reservas.sienge_vendas_canceladas s

        UNION ALL

        -- Seção 3: Reservas Vera Cruz (MANTÉM COMO ESTAVA)
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
            -- COLUNAS EXISTENTES
            r.vpl_reserva,
            r.vpl_tabela,
            r.idreserva
        FROM reservas.cv_vendas_consolidadas_vera_cruz r
        """
        
        conn.execute(sql_view)
        print("   View com corretor corrigido criada com sucesso!")
        
        # 4. Verificar resultado
        print(f"\n4. Verificando resultado...")
        result = conn.execute("SELECT COUNT(*) FROM sienge_vendas_consolidadas").fetchone()
        print(f"   Total de registros: {result[0]:,}")
        
        # 5. Verificar corretor específico
        print(f"\n5. Verificando corretor 'Alana C. Konzen' após correção...")
        result = conn.execute("""
            SELECT 
                corretor,
                origem,
                COUNT(*) as total
            FROM sienge_vendas_consolidadas
            WHERE corretor LIKE '%Alana%' OR corretor LIKE '%Konzen%'
            GROUP BY corretor, origem
            ORDER BY total DESC
        """).fetchall()
        
        print("   Após correção:")
        for row in result:
            print(f"   - {row[0]} ({row[1]}): {row[2]:,} registros")
        
        # 6. Verificar top corretores
        print(f"\n6. Verificando top corretores após correção...")
        result = conn.execute("""
            SELECT 
                corretor,
                COUNT(*) as total
            FROM sienge_vendas_consolidadas
            WHERE origem IN ('Sienge Realizada', 'Sienge Cancelada')
            GROUP BY corretor
            ORDER BY total DESC
            LIMIT 10
        """).fetchall()
        
        print("   Top 10 corretores após correção:")
        for row in result:
            print(f"   - {row[0]}: {row[1]:,} registros")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao corrigir corretor: {e}")
        return False

def main():
    """Funcao principal"""
    print("INVESTIGANDO E CORRIGINDO PROBLEMA COLUNA CORRETOR")
    print("="*60)
    print("Verificando por que estamos perdendo dados de corretores")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        # Primeiro investigar o problema
        if not investigar_problema_corretor(conn):
            return False
        
        # Depois corrigir a view
        if not corrigir_coluna_corretor(conn):
            return False
        
        print("\n" + "="*60)
        print("COLUNA CORRETOR CORRIGIDA COM SUCESSO!")
        print("="*60)
        print("A view agora usa os dados do Sienge como principal!")
        
        return True
        
    except Exception as e:
        print(f"ERRO na execucao: {e}")
        return False
    
    finally:
        if conn:
            conn.close()
            print("\nConexao com MotherDuck encerrada.")

if __name__ == "__main__":
    main()
