#!/usr/bin/env python3
"""
Script para corrigir a coluna corretor para buscar da tabela reservas_abril
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

def testar_relacionamento_corretor(conn):
    """Testa o relacionamento corretor entre Sienge e Reservas"""
    print("\n" + "="*60)
    print("TESTANDO RELACIONAMENTO CORRETOR")
    print("="*60)
    
    try:
        # 1. Verificar alguns registros do Sienge
        print("1. Verificando registros do Sienge...")
        result = conn.execute("""
            SELECT 
                s.id,
                s.brokers[1].name as corretor_sienge,
                s.brokers[1].id as idcorretor_sienge,
                (SELECT corretor FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as corretor_reservas
            FROM reservas.sienge_vendas_realizadas s
            WHERE s.brokers[1].name IS NOT NULL
            LIMIT 10
        """).fetchall()
        
        print("   Exemplos de relacionamento:")
        for row in result:
            print(f"   ID: {row[0]}")
            print(f"      Corretor Sienge: {row[1]}")
            print(f"      Corretor Reservas: {row[2]}")
            print()
        
        # 2. Verificar quantos registros têm correspondência
        print("2. Verificando correspondências...")
        result = conn.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT((SELECT corretor FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1)) as com_corretor_reservas
            FROM reservas.sienge_vendas_realizadas s
            WHERE s.brokers[1].name IS NOT NULL
        """).fetchone()
        
        taxa_correspondencia = (result[1] / result[0]) * 100 if result[0] > 0 else 0
        print(f"   Total de registros Sienge: {result[0]:,}")
        print(f"   Com corretor na tabela reservas: {result[1]:,} ({taxa_correspondencia:.1f}%)")
        
        # 3. Verificar corretores únicos na tabela reservas
        print("\n3. Verificando corretores únicos na tabela reservas...")
        result = conn.execute("""
            SELECT 
                corretor,
                COUNT(*) as total
            FROM reservas.reservas_abril
            WHERE corretor IS NOT NULL AND corretor != ''
            GROUP BY corretor
            ORDER BY total DESC
            LIMIT 10
        """).fetchall()
        
        print("   Top 10 corretores na tabela reservas:")
        for row in result:
            print(f"   - {row[0]}: {row[1]:,} registros")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao testar relacionamento: {e}")
        return False

def corrigir_corretor_reservas(conn):
    """Corrige a coluna corretor para buscar da tabela reservas_abril"""
    print("\n" + "="*60)
    print("CORRIGINDO CORRETOR PARA BUSCAR DA TABELA RESERVAS")
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
        
        # 3. Criar view corrigida com corretor da tabela reservas
        print("\n3. Criando view com corretor da tabela reservas...")
        
        sql_view = """
        CREATE VIEW sienge_vendas_consolidadas AS
        -- Seção 1: Vendas Realizadas Sienge (CORRETOR DA TABELA RESERVAS)
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
            -- CORRETOR DA TABELA RESERVAS (usando s.id ↔ codigointerno)
            (SELECT corretor FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as corretor,
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

        -- Seção 2: Vendas Canceladas Sienge (CORRETOR DA TABELA RESERVAS)
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
            -- CORRETOR DA TABELA RESERVAS (usando s.id ↔ codigointerno)
            (SELECT corretor FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as corretor,
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
        print("   View com corretor da tabela reservas criada com sucesso!")
        
        # 4. Verificar resultado
        print(f"\n4. Verificando resultado...")
        result = conn.execute("SELECT COUNT(*) FROM sienge_vendas_consolidadas").fetchone()
        print(f"   Total de registros: {result[0]:,}")
        
        # 5. Verificar corretor por origem
        print(f"\n5. Verificando corretor por origem...")
        result = conn.execute("""
            SELECT 
                origem,
                COUNT(*) as total,
                COUNT(corretor) as com_corretor
            FROM sienge_vendas_consolidadas
            GROUP BY origem
            ORDER BY origem
        """).fetchall()
        
        for row in result:
            taxa = (row[2] / row[1]) * 100 if row[1] > 0 else 0
            print(f"   {row[0]}: {row[2]:,}/{row[1]:,} ({taxa:.1f}%) com corretor")
        
        # 6. Verificar top corretores
        print(f"\n6. Verificando top corretores...")
        result = conn.execute("""
            SELECT 
                corretor,
                COUNT(*) as total
            FROM sienge_vendas_consolidadas
            WHERE corretor IS NOT NULL AND corretor != ''
            GROUP BY corretor
            ORDER BY total DESC
            LIMIT 10
        """).fetchall()
        
        print("   Top 10 corretores:")
        for row in result:
            print(f"   - {row[0]}: {row[1]:,} registros")
        
        # 7. Verificar corretor específico mencionado
        print(f"\n7. Verificando corretor 'Alana C. Konzen'...")
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
        
        print("   Alana C. Konzen:")
        for row in result:
            print(f"   - {row[0]} ({row[1]}): {row[2]:,} registros")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao corrigir corretor: {e}")
        return False

def main():
    """Funcao principal"""
    print("CORRIGINDO CORRETOR PARA BUSCAR DA TABELA RESERVAS")
    print("="*60)
    print("Usando s.id <-> codigointerno para buscar corretor da tabela reservas_abril")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        # Primeiro testar o relacionamento
        if not testar_relacionamento_corretor(conn):
            return False
        
        # Depois corrigir a view
        if not corrigir_corretor_reservas(conn):
            return False
        
        print("\n" + "="*60)
        print("CORRETOR CORRIGIDO COM SUCESSO!")
        print("="*60)
        print("A view agora busca corretor da tabela reservas_abril usando s.id ↔ codigointerno!")
        
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
