#!/usr/bin/env python3
"""
Script para corrigir a coluna nome_empreendimento na view
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

def verificar_relacao_empreendimento(conn):
    """Verifica a relação entre enterpriseId e codigointerno_empreendimento"""
    print("\n" + "="*60)
    print("VERIFICANDO RELACAO EMPREENDIMENTO")
    print("="*60)
    
    try:
        # 1. Verificar estrutura da tabela reservas_abril
        print("1. Verificando estrutura da tabela reservas_abril...")
        columns = conn.execute("DESCRIBE reservas.reservas_abril").fetchall()
        print("   Colunas disponíveis:")
        for col in columns:
            if 'empreendimento' in col[0].lower() or 'codigo' in col[0].lower():
                print(f"   - {col[0]} ({col[1]})")
        
        # 2. Verificar valores únicos de enterpriseId nas tabelas Sienge
        print("\n2. Verificando enterpriseId únicos nas tabelas Sienge...")
        result = conn.execute("""
            SELECT enterpriseId, COUNT(*) as total
            FROM reservas.sienge_vendas_realizadas
            GROUP BY enterpriseId
            ORDER BY enterpriseId
        """).fetchall()
        
        print("   Sienge Vendas Realizadas:")
        for row in result:
            print(f"   - enterpriseId {row[0]}: {row[1]} registros")
        
        result = conn.execute("""
            SELECT enterpriseId, COUNT(*) as total
            FROM reservas.sienge_vendas_canceladas
            GROUP BY enterpriseId
            ORDER BY enterpriseId
        """).fetchall()
        
        print("   Sienge Vendas Canceladas:")
        for row in result:
            print(f"   - enterpriseId {row[0]}: {row[1]} registros")
        
        # 3. Verificar valores únicos de codigointerno_empreendimento
        print("\n3. Verificando codigointerno_empreendimento únicos...")
        result = conn.execute("""
            SELECT codigointerno_empreendimento, COUNT(*) as total
            FROM reservas.reservas_abril
            GROUP BY codigointerno_empreendimento
            ORDER BY codigointerno_empreendimento
        """).fetchall()
        
        print("   Reservas Abril:")
        for row in result:
            print(f"   - codigointerno_empreendimento {row[0]}: {row[1]} registros")
        
        # 4. Verificar se há correspondência
        print("\n4. Verificando correspondência entre enterpriseId e codigointerno_empreendimento...")
        result = conn.execute("""
            SELECT DISTINCT 
                r.codigointerno_empreendimento,
                r.empreendimento,
                COUNT(*) as total_registros
            FROM reservas.reservas_abril r
            GROUP BY r.codigointerno_empreendimento, r.empreendimento
            ORDER BY r.codigointerno_empreendimento
        """).fetchall()
        
        print("   Mapeamento disponivel:")
        for row in result:
            print(f"   - {row[0]} -> {row[1]} ({row[2]} registros)")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao verificar relação: {e}")
        return False

def corrigir_nome_empreendimento(conn):
    """Corrige a coluna nome_empreendimento na view"""
    print("\n" + "="*60)
    print("CORRIGINDO NOME EMPREENDIMENTO")
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
        
        # 3. Criar a view corrigida com nome_empreendimento correto
        print("\n3. Criando view com nome_empreendimento corrigido...")
        
        sql_view = """
        CREATE VIEW sienge_vendas_consolidadas AS
        -- Seção 1: Vendas Realizadas Sienge (COM NOME EMPREENDIMENTO CORRETO)
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
            (SELECT imobiliaria FROM reservas.reservas_abril WHERE idimobiliaria = s.brokers[1].id LIMIT 1) as imobiliaria,
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
            -- NOVAS COLUNAS ADICIONADAS
            (SELECT vpl_reserva FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as vpl_reserva,
            (SELECT vpl_tabela FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as vpl_tabela,
            (SELECT idreserva FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as idreserva
        FROM reservas.sienge_vendas_realizadas s

        UNION ALL

        -- Seção 2: Vendas Canceladas Sienge (COM NOME EMPREENDIMENTO CORRETO)
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
            (SELECT imobiliaria FROM reservas.reservas_abril WHERE idimobiliaria = s.brokers[1].id LIMIT 1) as imobiliaria,
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
        print("   View com nome_empreendimento corrigido criada com sucesso!")
        
        # 4. Verificar a nova estrutura
        print("\n4. Verificando estrutura da view corrigida...")
        columns_nova = conn.execute("DESCRIBE sienge_vendas_consolidadas").fetchall()
        print(f"   Total de colunas: {len(columns_nova)}")
        
        # 5. Testar contagem
        print(f"\n5. Testando contagem de registros...")
        result = conn.execute("SELECT COUNT(*) FROM sienge_vendas_consolidadas").fetchone()
        print(f"   Total de registros: {result[0]:,}")
        
        # 6. Verificar nomes de empreendimentos
        print(f"\n6. Verificando nomes de empreendimentos:")
        result = conn.execute("""
            SELECT nome_empreendimento, COUNT(*) as total
            FROM sienge_vendas_consolidadas
            GROUP BY nome_empreendimento
            ORDER BY nome_empreendimento
        """).fetchall()
        
        for row in result:
            print(f"   - {row[0]}: {row[1]:,} registros")
        
        # 7. Verificar por origem
        print(f"\n7. Verificando por origem:")
        result = conn.execute("""
            SELECT origem, COUNT(*) as total
            FROM sienge_vendas_consolidadas
            GROUP BY origem
            ORDER BY origem
        """).fetchall()
        
        for row in result:
            print(f"   - {row[0]}: {row[1]:,} registros")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao corrigir nome_empreendimento: {e}")
        return False

def main():
    """Funcao principal"""
    print("CORRIGINDO NOME EMPREENDIMENTO NA VIEW")
    print("="*60)
    print("Buscando nomes reais dos empreendimentos na tabela reservas_abril")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        # Primeiro verificar a relação
        if not verificar_relacao_empreendimento(conn):
            return False
        
        # Depois corrigir a view
        if not corrigir_nome_empreendimento(conn):
            return False
        
        print("\n" + "="*60)
        print("NOME EMPREENDIMENTO CORRIGIDO COM SUCESSO!")
        print("="*60)
        print("A view agora mostra os nomes reais dos empreendimentos!")
        
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
