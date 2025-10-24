#!/usr/bin/env python3
"""
Script para investigar e corrigir a coluna imobiliaria
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

def investigar_imobiliaria(conn):
    """Investiga o problema da coluna imobiliaria"""
    print("\n" + "="*60)
    print("INVESTIGANDO PROBLEMA COLUNA IMOBILIARIA")
    print("="*60)
    
    try:
        # 1. Verificar como está sendo buscada atualmente
        print("1. Verificando como está sendo buscada a imobiliaria atualmente...")
        result = conn.execute("""
            SELECT 
                origem,
                COUNT(*) as total,
                COUNT(imobiliaria) as com_imobiliaria,
                COUNT(*) - COUNT(imobiliaria) as sem_imobiliaria
            FROM informacoes_consolidadas.sienge_vendas_consolidadas
            GROUP BY origem
            ORDER BY origem
        """).fetchall()
        
        for row in result:
            print(f"   {row[0]}: {row[1]:,} total, {row[2]:,} com imobiliaria, {row[3]:,} sem imobiliaria")
        
        # 2. Verificar estrutura da tabela reservas_abril para imobiliaria
        print("\n2. Verificando estrutura da tabela reservas_abril...")
        columns = conn.execute("DESCRIBE reservas.reservas_abril").fetchall()
        print("   Colunas relacionadas a imobiliaria:")
        for col in columns:
            if 'imobiliaria' in col[0].lower() or 'idimobiliaria' in col[0].lower():
                print(f"   - {col[0]} ({col[1]})")
        
        # 3. Verificar dados de imobiliaria na tabela reservas_abril
        print("\n3. Verificando dados de imobiliaria na tabela reservas_abril...")
        result = conn.execute("""
            SELECT 
                imobiliaria,
                COUNT(*) as total
            FROM reservas.reservas_abril
            WHERE imobiliaria IS NOT NULL AND imobiliaria != ''
            GROUP BY imobiliaria
            ORDER BY total DESC
            LIMIT 10
        """).fetchall()
        
        print("   Top 10 imobiliarias na tabela reservas_abril:")
        for row in result:
            print(f"   - {row[0]}: {row[1]:,} registros")
        
        # 4. Verificar relação entre idcorretor e imobiliaria
        print("\n4. Verificando relação entre idcorretor e imobiliaria...")
        result = conn.execute("""
            SELECT 
                idcorretor,
                imobiliaria,
                COUNT(*) as total
            FROM reservas.reservas_abril
            WHERE idcorretor IS NOT NULL AND imobiliaria IS NOT NULL AND imobiliaria != ''
            GROUP BY idcorretor, imobiliaria
            ORDER BY total DESC
            LIMIT 10
        """).fetchall()
        
        print("   Top 10 relações idcorretor -> imobiliaria:")
        for row in result:
            print(f"   - {row[0]} -> {row[1]}: {row[2]:,} registros")
        
        # 5. Verificar se há problema na busca atual
        print("\n5. Verificando problema na busca atual...")
        result = conn.execute("""
            SELECT 
                s.id,
                s.brokers[1].id as idcorretor,
                s.brokers[1].name as nome_corretor,
                (SELECT imobiliaria FROM reservas.reservas_abril WHERE idimobiliaria = s.brokers[1].id LIMIT 1) as imobiliaria_atual,
                (SELECT imobiliaria FROM reservas.reservas_abril WHERE idcorretor = s.brokers[1].id LIMIT 1) as imobiliaria_por_idcorretor
            FROM reservas.sienge_vendas_realizadas s
            WHERE s.brokers[1].id IS NOT NULL
            LIMIT 5
        """).fetchall()
        
        print("   Exemplos de busca atual:")
        for row in result:
            print(f"   ID: {row[0]}, Corretor: {row[1]} ({row[2]})")
            print(f"      Imobiliaria por idimobiliaria: {row[3]}")
            print(f"      Imobiliaria por idcorretor: {row[4]}")
            print()
        
        # 6. Verificar se devemos usar codigointerno para buscar
        print("\n6. Verificando se devemos usar codigointerno para buscar...")
        result = conn.execute("""
            SELECT 
                s.id,
                s.brokers[1].id as idcorretor,
                s.brokers[1].name as nome_corretor,
                (SELECT imobiliaria FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as imobiliaria_por_codigointerno
            FROM reservas.sienge_vendas_realizadas s
            WHERE s.brokers[1].id IS NOT NULL
            LIMIT 5
        """).fetchall()
        
        print("   Exemplos usando codigointerno:")
        for row in result:
            print(f"   ID: {row[0]}, Corretor: {row[1]} ({row[2]})")
            print(f"      Imobiliaria por codigointerno: {row[3]}")
            print()
        
        return True
        
    except Exception as e:
        print(f"ERRO ao investigar imobiliaria: {e}")
        return False

def corrigir_imobiliaria(conn):
    """Corrige a coluna imobiliaria na view"""
    print("\n" + "="*60)
    print("CORRIGINDO COLUNA IMOBILIARIA")
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
        
        # 3. Criar a view corrigida com imobiliaria correta
        print("\n3. Criando view com imobiliaria corrigida...")
        
        sql_view = """
        CREATE VIEW sienge_vendas_consolidadas AS
        -- Seção 1: Vendas Realizadas Sienge (COM IMOBILIARIA CORRIGIDA)
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
            s.brokers[1].name as corretor,
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
            -- NOVAS COLUNAS ADICIONADAS
            (SELECT vpl_reserva FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as vpl_reserva,
            (SELECT vpl_tabela FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as vpl_tabela,
            (SELECT idreserva FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as idreserva
        FROM reservas.sienge_vendas_realizadas s

        UNION ALL

        -- Seção 2: Vendas Canceladas Sienge (COM IMOBILIARIA CORRIGIDA)
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
            s.brokers[1].name as corretor,
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
            -- NOVAS COLUNAS ADICIONADAS
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
            -- NOVAS COLUNAS ADICIONADAS (vêm direto da tabela reservas)
            r.vpl_reserva,
            r.vpl_tabela,
            r.idreserva
        FROM reservas.cv_vendas_consolidadas_vera_cruz r
        """
        
        conn.execute(sql_view)
        print("   View com imobiliaria corrigida criada com sucesso!")
        
        # 4. Verificar a nova estrutura
        print("\n4. Verificando estrutura da view corrigida...")
        columns_nova = conn.execute("DESCRIBE sienge_vendas_consolidadas").fetchall()
        print(f"   Total de colunas: {len(columns_nova)}")
        
        # 5. Testar contagem
        print(f"\n5. Testando contagem de registros...")
        result = conn.execute("SELECT COUNT(*) FROM sienge_vendas_consolidadas").fetchone()
        print(f"   Total de registros: {result[0]:,}")
        
        # 6. Verificar imobiliaria por origem
        print(f"\n6. Verificando imobiliaria por origem:")
        result = conn.execute("""
            SELECT 
                origem,
                COUNT(*) as total,
                COUNT(imobiliaria) as com_imobiliaria,
                COUNT(*) - COUNT(imobiliaria) as sem_imobiliaria
            FROM sienge_vendas_consolidadas
            GROUP BY origem
            ORDER BY origem
        """).fetchall()
        
        for row in result:
            print(f"   {row[0]}: {row[1]:,} total, {row[2]:,} com imobiliaria, {row[3]:,} sem imobiliaria")
        
        # 7. Verificar top imobiliarias
        print(f"\n7. Verificando top imobiliarias:")
        result = conn.execute("""
            SELECT 
                imobiliaria,
                COUNT(*) as total
            FROM sienge_vendas_consolidadas
            WHERE imobiliaria IS NOT NULL AND imobiliaria != ''
            GROUP BY imobiliaria
            ORDER BY total DESC
            LIMIT 10
        """).fetchall()
        
        for row in result:
            print(f"   - {row[0]}: {row[1]:,} registros")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao corrigir imobiliaria: {e}")
        return False

def main():
    """Funcao principal"""
    print("INVESTIGANDO E CORRIGINDO COLUNA IMOBILIARIA")
    print("="*60)
    print("Verificando campos em branco e corrigindo busca")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        # Primeiro investigar o problema
        if not investigar_imobiliaria(conn):
            return False
        
        # Depois corrigir a view
        if not corrigir_imobiliaria(conn):
            return False
        
        print("\n" + "="*60)
        print("COLUNA IMOBILIARIA CORRIGIDA COM SUCESSO!")
        print("="*60)
        print("A view agora busca imobiliaria usando múltiplas estratégias!")
        
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
