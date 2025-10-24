#!/usr/bin/env python3
"""
Script para corrigir a view sem o JOIN problemático
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

def corrigir_view_sem_join(conn):
    """Corrige a view sem o JOIN problemático"""
    print("\n" + "="*60)
    print("CORRIGINDO VIEW SEM JOIN PROBLEMATICO")
    print("="*60)
    
    try:
        # 1. Usar o banco informacoes_consolidadas
        print("1. Usando banco informacoes_consolidadas...")
        try:
            conn.execute("USE informacoes_consolidadas")
            print("   Banco informacoes_consolidadas selecionado!")
        except Exception as e:
            print(f"   ERRO ao usar banco: {e}")
            return False
        
        # 2. Remover view existente
        print("\n2. Removendo view existente...")
        try:
            conn.execute("DROP VIEW IF EXISTS sienge_vendas_consolidadas")
            print("   View existente removida!")
        except Exception as e:
            print(f"   Aviso: {e}")
        
        # 3. Criar a view corrigida sem o JOIN problemático
        print("\n3. Criando view corrigida...")
        
        sql_view = """
        CREATE VIEW sienge_vendas_consolidadas AS
        -- Seção 1: Vendas Realizadas Sienge (SEM JOIN PROBLEMÁTICO)
        SELECT
            CAST(s.enterpriseId AS INTEGER) as enterpriseId,
            CASE WHEN s.enterpriseId = '19' THEN 'Ondina II' ELSE 'Sienge Realizada' END as nome_empreendimento,
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

        -- Seção 2: Vendas Canceladas Sienge (SEM JOIN PROBLEMÁTICO)
        SELECT
            CAST(s.enterpriseId AS INTEGER) as enterpriseId,
            CASE WHEN s.enterpriseId = '19' THEN 'Ondina II' ELSE 'Sienge Cancelada' END as nome_empreendimento,
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
        print("   View corrigida criada com sucesso!")
        
        # 4. Verificar a nova estrutura
        print("\n4. Verificando estrutura da view corrigida...")
        columns_nova = conn.execute("DESCRIBE sienge_vendas_consolidadas").fetchall()
        print(f"   Total de colunas: {len(columns_nova)}")
        
        # Verificar se as novas colunas existem
        colunas_existentes = [col[0] for col in columns_nova]
        novas_colunas = ['vpl_reserva', 'vpl_tabela', 'idreserva']
        
        print(f"\n5. Verificando novas colunas:")
        for coluna in novas_colunas:
            if coluna in colunas_existentes:
                print(f"   OK {coluna} - EXISTE")
            else:
                print(f"   X {coluna} - NAO EXISTE")
        
        # 6. Testar contagem
        print(f"\n6. Testando contagem de registros...")
        result = conn.execute("SELECT COUNT(*) FROM sienge_vendas_consolidadas").fetchone()
        print(f"   Total de registros: {result[0]:,}")
        
        # 7. Verificar contagem por origem
        print(f"\n7. Verificando contagem por origem:")
        result = conn.execute("""
            SELECT origem, COUNT(*) as total
            FROM sienge_vendas_consolidadas
            GROUP BY origem
            ORDER BY origem
        """).fetchall()
        
        for row in result:
            print(f"   {row[0]}: {row[1]:,} registros")
        
        # 8. Testar as novas colunas
        print(f"\n8. Testando novas colunas:")
        result = conn.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(vpl_reserva) as com_vpl_reserva,
                COUNT(vpl_tabela) as com_vpl_tabela,
                COUNT(idreserva) as com_idreserva
            FROM sienge_vendas_consolidadas
        """).fetchone()
        
        print(f"   Total de registros: {result[0]:,}")
        print(f"   Registros com vpl_reserva: {result[1]:,}")
        print(f"   Registros com vpl_tabela: {result[2]:,}")
        print(f"   Registros com idreserva: {result[3]:,}")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao corrigir view: {e}")
        return False

def main():
    """Funcao principal"""
    print("CORRIGINDO VIEW SEM JOIN PROBLEMATICO")
    print("="*60)
    print("Removendo JOIN problemático que estava multiplicando os dados")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        if not corrigir_view_sem_join(conn):
            return False
        
        print("\n" + "="*60)
        print("VIEW CORRIGIDA COM SUCESSO!")
        print("="*60)
        print("A view foi corrigida removendo o JOIN problemático.")
        print("Agora a contagem deve estar correta!")
        
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

