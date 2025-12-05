#!/usr/bin/env python3
"""
Script para investigar e corrigir as colunas midia e tipovenda na view de vendas
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

def investigar_midia_tipovenda(conn):
    """Investiga as colunas midia e tipovenda na view atual"""
    print("\n" + "="*60)
    print("INVESTIGANDO COLUNAS MIDIA E TIPOVENDA")
    print("="*60)
    
    try:
        # 1. Usar o banco informacoes_consolidadas
        print("1. Usando banco informacoes_consolidadas...")
        conn.execute("USE informacoes_consolidadas")
        print("   Banco informacoes_consolidadas selecionado!")
        
        # 2. Verificar midia e tipovenda por origem
        print("\n2. Verificando midia e tipovenda por origem:")
        print("-" * 50)
        result = conn.execute("""
            SELECT 
                origem,
                COUNT(*) as total,
                COUNT(midia) as com_midia,
                COUNT(tipovenda) as com_tipovenda
            FROM sienge_vendas_consolidadas
            GROUP BY origem
            ORDER BY origem
        """).fetchall()
        
        for row in result:
            taxa_midia = (row[2] / row[1]) * 100 if row[1] > 0 else 0
            taxa_tipovenda = (row[3] / row[1]) * 100 if row[1] > 0 else 0
            print(f"   {row[0]}:")
            print(f"      Total: {row[1]:,}")
            print(f"      Com midia: {row[2]:,} ({taxa_midia:.1f}%)")
            print(f"      Com tipovenda: {row[3]:,} ({taxa_tipovenda:.1f}%)")
            print()
        
        # 3. Verificar valores únicos de midia
        print("3. Verificando valores únicos de midia:")
        print("-" * 50)
        result = conn.execute("""
            SELECT 
                midia,
                COUNT(*) as total
            FROM sienge_vendas_consolidadas
            WHERE midia IS NOT NULL AND midia != ''
            GROUP BY midia
            ORDER BY total DESC
            LIMIT 10
        """).fetchall()
        
        print("   Top 10 midias:")
        for row in result:
            print(f"   - {row[0]}: {row[1]:,} registros")
        
        # 4. Verificar valores únicos de tipovenda
        print(f"\n4. Verificando valores únicos de tipovenda:")
        print("-" * 50)
        result = conn.execute("""
            SELECT 
                tipovenda,
                COUNT(*) as total
            FROM sienge_vendas_consolidadas
            WHERE tipovenda IS NOT NULL AND tipovenda != ''
            GROUP BY tipovenda
            ORDER BY total DESC
            LIMIT 10
        """).fetchall()
        
        print("   Top 10 tipovendas:")
        for row in result:
            print(f"   - {row[0]}: {row[1]:,} registros")
        
        # 5. Verificar relacionamento s.id ↔ codigointerno
        print(f"\n5. Verificando relacionamento s.id ↔ codigointerno:")
        print("-" * 50)
        
        # Verificar quantos registros Sienge têm correspondência na reservas_abril
        result = conn.execute("""
            SELECT 
                COUNT(*) as total_sienge,
                COUNT((SELECT codigointerno FROM reservas.reservas_abril WHERE codigointerno = CAST(s.id AS VARCHAR) LIMIT 1)) as com_correspondencia
            FROM reservas.sienge_vendas_realizadas s
        """).fetchone()
        
        taxa_correspondencia = (result[1] / result[0]) * 100 if result[0] > 0 else 0
        print(f"   Sienge Realizadas:")
        print(f"      Total: {result[0]:,}")
        print(f"      Com correspondência: {result[1]:,} ({taxa_correspondencia:.1f}%)")
        
        # Verificar alguns exemplos de relacionamento
        print(f"\n6. Exemplos de relacionamento:")
        print("-" * 50)
        result = conn.execute("""
            SELECT 
                s.id,
                s.brokers[1].name as corretor_sienge,
                (SELECT midia FROM reservas.reservas_abril WHERE codigointerno = CAST(s.id AS VARCHAR) LIMIT 1) as midia_reservas,
                (SELECT tipovenda FROM reservas.reservas_abril WHERE codigointerno = CAST(s.id AS VARCHAR) LIMIT 1) as tipovenda_reservas
            FROM reservas.sienge_vendas_realizadas s
            WHERE s.brokers[1].name IS NOT NULL
            LIMIT 10
        """).fetchall()
        
        print("   Exemplos de relacionamento:")
        for row in result:
            print(f"   ID {row[0]}: {row[1]}")
            print(f"      Midia: {row[2]}")
            print(f"      Tipovenda: {row[3]}")
            print()
        
        return True
        
    except Exception as e:
        print(f"ERRO ao investigar: {e}")
        return False

def corrigir_midia_tipovenda(conn):
    """Corrige as colunas midia e tipovenda na view de vendas"""
    print("\n" + "="*60)
    print("CORRIGINDO MIDIA E TIPOVENDA NA VIEW DE VENDAS")
    print("="*60)
    
    try:
        # 1. Remover view existente
        print("1. Removendo view existente...")
        conn.execute("DROP VIEW IF EXISTS sienge_vendas_consolidadas")
        print("   View existente removida!")
        
        # 2. Criar view corrigida
        print("\n2. Criando view com midia e tipovenda da tabela reservas...")
        
        sql_view = """
        CREATE VIEW sienge_vendas_consolidadas AS
        -- Seção 1: Vendas Realizadas Sienge (MIDIA E TIPOVENDA DA TABELA RESERVAS)
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
            -- CORRETOR DA TABELA RESERVAS
            (SELECT corretor FROM reservas.reservas_abril WHERE codigointerno = CAST(s.id AS VARCHAR) LIMIT 1) as corretor,
            COALESCE(
                (SELECT imobiliaria FROM reservas.reservas_abril WHERE codigointerno = CAST(s.id AS VARCHAR) LIMIT 1),
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
            (SELECT idimobiliaria FROM reservas.reservas_abril WHERE codigointerno = CAST(s.id AS VARCHAR) LIMIT 1) as idimobiliaria,
            s.customers[1].sex as sexo,
            s.customers[1].civilStatus as estado_civil,
            NULL as idade,
            NULL as renda,
            NULL as situacao_original,
            NULL as data_venda,
            NULL as valor_contrato_com_juros,
            NULL as vencimento,
            NULL as campanha,
            -- MIDIA E TIPOVENDA DA TABELA RESERVAS (usando s.id ↔ codigointerno)
            (SELECT midia FROM reservas.reservas_abril WHERE codigointerno = CAST(s.id AS VARCHAR) LIMIT 1) as midia,
            (SELECT tipovenda FROM reservas.reservas_abril WHERE codigointerno = CAST(s.id AS VARCHAR) LIMIT 1) as tipovenda,
            NULL as grupo,
            NULL as regiao,
            NULL as bloco,
            NULL as unidade,
            NULL as etapa,
            -- COLUNAS EXISTENTES
            (SELECT vpl_reserva FROM reservas.reservas_abril WHERE codigointerno = CAST(s.id AS VARCHAR) LIMIT 1) as vpl_reserva,
            (SELECT vpl_tabela FROM reservas.reservas_abril WHERE codigointerno = CAST(s.id AS VARCHAR) LIMIT 1) as vpl_tabela,
            (SELECT idreserva FROM reservas.reservas_abril WHERE codigointerno = CAST(s.id AS VARCHAR) LIMIT 1) as idreserva
        FROM reservas.sienge_vendas_realizadas s

        UNION ALL

        -- Seção 2: Vendas Canceladas Sienge (MIDIA E TIPOVENDA DA TABELA RESERVAS)
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
            -- CORRETOR DA TABELA RESERVAS
            (SELECT corretor FROM reservas.reservas_abril WHERE codigointerno = CAST(s.id AS VARCHAR) LIMIT 1) as corretor,
            COALESCE(
                (SELECT imobiliaria FROM reservas.reservas_abril WHERE codigointerno = CAST(s.id AS VARCHAR) LIMIT 1),
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
            (SELECT idimobiliaria FROM reservas.reservas_abril WHERE codigointerno = CAST(s.id AS VARCHAR) LIMIT 1) as idimobiliaria,
            s.customers[1].sex as sexo,
            s.customers[1].civilStatus as estado_civil,
            NULL as idade,
            NULL as renda,
            NULL as situacao_original,
            NULL as data_venda,
            NULL as valor_contrato_com_juros,
            NULL as vencimento,
            NULL as campanha,
            -- MIDIA E TIPOVENDA DA TABELA RESERVAS (usando s.id ↔ codigointerno)
            (SELECT midia FROM reservas.reservas_abril WHERE codigointerno = CAST(s.id AS VARCHAR) LIMIT 1) as midia,
            (SELECT tipovenda FROM reservas.reservas_abril WHERE codigointerno = CAST(s.id AS VARCHAR) LIMIT 1) as tipovenda,
            NULL as grupo,
            NULL as regiao,
            NULL as bloco,
            NULL as unidade,
            NULL as etapa,
            -- COLUNAS EXISTENTES
            (SELECT vpl_reserva FROM reservas.reservas_abril WHERE codigointerno = CAST(s.id AS VARCHAR) LIMIT 1) as vpl_reserva,
            (SELECT vpl_tabela FROM reservas.reservas_abril WHERE codigointerno = CAST(s.id AS VARCHAR) LIMIT 1) as vpl_tabela,
            (SELECT idreserva FROM reservas.reservas_abril WHERE codigointerno = CAST(s.id AS VARCHAR) LIMIT 1) as idreserva
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
        print("   View com midia e tipovenda da tabela reservas criada com sucesso!")
        
        # 3. Verificar resultado
        print(f"\n3. Verificando resultado...")
        result = conn.execute("SELECT COUNT(*) FROM sienge_vendas_consolidadas").fetchone()
        print(f"   Total de registros: {result[0]:,}")
        
        # 4. Verificar midia e tipovenda por origem
        print(f"\n4. Verificando midia e tipovenda por origem:")
        print("-" * 50)
        result = conn.execute("""
            SELECT 
                origem,
                COUNT(*) as total,
                COUNT(midia) as com_midia,
                COUNT(tipovenda) as com_tipovenda
            FROM sienge_vendas_consolidadas
            GROUP BY origem
            ORDER BY origem
        """).fetchall()
        
        for row in result:
            taxa_midia = (row[2] / row[1]) * 100 if row[1] > 0 else 0
            taxa_tipovenda = (row[3] / row[1]) * 100 if row[1] > 0 else 0
            print(f"   {row[0]}:")
            print(f"      Total: {row[1]:,}")
            print(f"      Com midia: {row[2]:,} ({taxa_midia:.1f}%)")
            print(f"      Com tipovenda: {row[3]:,} ({taxa_tipovenda:.1f}%)")
        
        # 5. Verificar valores únicos de midia
        print(f"\n5. Verificando valores únicos de midia:")
        print("-" * 50)
        result = conn.execute("""
            SELECT 
                midia,
                COUNT(*) as total
            FROM sienge_vendas_consolidadas
            WHERE midia IS NOT NULL AND midia != ''
            GROUP BY midia
            ORDER BY total DESC
            LIMIT 10
        """).fetchall()
        
        print("   Top 10 midias:")
        for row in result:
            print(f"   - {row[0]}: {row[1]:,} registros")
        
        # 6. Verificar valores únicos de tipovenda
        print(f"\n6. Verificando valores únicos de tipovenda:")
        print("-" * 50)
        result = conn.execute("""
            SELECT 
                tipovenda,
                COUNT(*) as total
            FROM sienge_vendas_consolidadas
            WHERE tipovenda IS NOT NULL AND tipovenda != ''
            GROUP BY tipovenda
            ORDER BY total DESC
            LIMIT 10
        """).fetchall()
        
        print("   Top 10 tipovendas:")
        for row in result:
            print(f"   - {row[0]}: {row[1]:,} registros")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao corrigir view: {e}")
        return False

def main():
    """Funcao principal"""
    print("CORRIGINDO MIDIA E TIPOVENDA NA VIEW DE VENDAS")
    print("="*60)
    print("Usando s.id ↔ codigointerno para buscar midia e tipovenda da tabela reservas_abril")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        # Primeiro investigar a situação atual
        if not investigar_midia_tipovenda(conn):
            return False
        
        # Depois corrigir a view
        if not corrigir_midia_tipovenda(conn):
            return False
        
        print("\n" + "="*60)
        print("MIDIA E TIPOVENDA CORRIGIDAS COM SUCESSO!")
        print("="*60)
        print("A view agora busca midia e tipovenda da tabela reservas_abril usando s.id ↔ codigointerno!")
        
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

