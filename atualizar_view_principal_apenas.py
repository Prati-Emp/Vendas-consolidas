#!/usr/bin/env python3
"""
Script para atualizar apenas a view principal sienge_vendas_consolidadas
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

def verificar_estrutura_views(conn):
    """Verifica a estrutura das views"""
    print("\n" + "="*60)
    print("VERIFICANDO ESTRUTURA DAS VIEWS")
    print("="*60)
    
    try:
        # Verificar view Vera Cruz
        print("1. View Vera Cruz:")
        columns_vera_cruz = conn.execute("DESCRIBE reservas.cv_vendas_consolidadas_vera_cruz").fetchall()
        print(f"   Total de colunas: {len(columns_vera_cruz)}")
        for col in columns_vera_cruz:
            print(f"   - {col[0]} ({col[1]})")
        
        # Verificar view principal atual
        print("\n2. View Principal (atual):")
        try:
            columns_principal = conn.execute("DESCRIBE informacoes_consolidadas.sienge_vendas_consolidadas").fetchall()
            print(f"   Total de colunas: {len(columns_principal)}")
            for col in columns_principal:
                print(f"   - {col[0]} ({col[1]})")
        except Exception as e:
            print(f"   ERRO ao verificar view principal: {e}")
        
        return len(columns_vera_cruz)
        
    except Exception as e:
        print(f"ERRO ao verificar estrutura: {e}")
        return 0

def atualizar_view_principal(conn):
    """Atualiza apenas a view principal"""
    print("\n" + "="*60)
    print("ATUALIZANDO VIEW PRINCIPAL")
    print("="*60)
    
    try:
        sql_principal = """
        CREATE OR REPLACE VIEW informacoes_consolidadas.sienge_vendas_consolidadas AS
        -- Seção 1: Vendas Realizadas Sienge
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
            -- NOVAS COLUNAS ADICIONADAS
            (SELECT vpl_reserva FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as vpl_reserva,
            (SELECT vpl_tabela FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as vpl_tabela,
            (SELECT idreserva FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as idreserva
        FROM reservas.sienge_vendas_realizadas s
        LEFT JOIN (SELECT DISTINCT idempreendimento, empreendimento, corretor, imobiliaria, idcorretor, idimobiliaria FROM reservas.reservas_abril) r ON CAST(s.enterpriseId AS INTEGER) = r.idempreendimento

        UNION ALL

        -- Seção 2: Vendas Canceladas Sienge
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
            -- NOVAS COLUNAS ADICIONADAS
            (SELECT vpl_reserva FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as vpl_reserva,
            (SELECT vpl_tabela FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as vpl_tabela,
            (SELECT idreserva FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as idreserva
        FROM reservas.sienge_vendas_canceladas s
        LEFT JOIN (SELECT DISTINCT idempreendimento, empreendimento, corretor, imobiliaria, idcorretor, idimobiliaria FROM reservas.reservas_abril) r ON CAST(s.enterpriseId AS INTEGER) = r.idempreendimento

        UNION ALL

        -- Seção 3: Reservas Vera Cruz
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
            -- NOVAS COLUNAS ADICIONADAS (vêm direto da tabela reservas)
            r.vpl_reserva,
            r.vpl_tabela,
            r.idreserva
        FROM reservas.cv_vendas_consolidadas_vera_cruz r
        """
        
        print("Executando atualizacao da view principal...")
        conn.execute(sql_principal)
        print("View principal atualizada com sucesso!")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao atualizar view principal: {e}")
        return False

def testar_view_atualizada(conn):
    """Testa se a view atualizada funciona corretamente"""
    print("\n" + "="*60)
    print("TESTANDO VIEW ATUALIZADA")
    print("="*60)
    
    try:
        # Testar contagem total
        print("1. Testando contagem total...")
        result = conn.execute("SELECT COUNT(*) FROM informacoes_consolidadas.sienge_vendas_consolidadas").fetchone()
        print(f"   Total de registros: {result[0]:,}")
        
        # Testar as novas colunas
        print("\n2. Testando novas colunas...")
        result = conn.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(vpl_reserva) as com_vpl_reserva,
                COUNT(vpl_tabela) as com_vpl_tabela,
                COUNT(idreserva) as com_idreserva
            FROM informacoes_consolidadas.sienge_vendas_consolidadas
        """).fetchone()
        
        print(f"   Total de registros: {result[0]:,}")
        print(f"   Registros com vpl_reserva: {result[1]:,}")
        print(f"   Registros com vpl_tabela: {result[2]:,}")
        print(f"   Registros com idreserva: {result[3]:,}")
        
        # Testar amostra de dados
        print("\n3. Amostra de dados com novas colunas:")
        result = conn.execute("""
            SELECT 
                origem,
                vpl_reserva,
                vpl_tabela,
                idreserva,
                COUNT(*) as quantidade
            FROM informacoes_consolidadas.sienge_vendas_consolidadas
            WHERE vpl_reserva IS NOT NULL OR vpl_tabela IS NOT NULL OR idreserva IS NOT NULL
            GROUP BY origem, vpl_reserva, vpl_tabela, idreserva
            ORDER BY quantidade DESC
            LIMIT 10
        """).fetchall()
        
        for row in result:
            print(f"   {row[0]} | vpl_reserva: {row[1]} | vpl_tabela: {row[2]} | idreserva: {row[3]} | qtd: {row[4]}")
        
        print("\nTeste da view concluido com sucesso!")
        return True
        
    except Exception as e:
        print(f"ERRO ao testar view: {e}")
        return False

def main():
    """Funcao principal"""
    print("ATUALIZACAO DA VIEW PRINCIPAL SIENGE_VENDAS_CONSOLIDADAS")
    print("="*60)
    print("Adicionando colunas: vpl_reserva, vpl_tabela, idreserva")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        # 1. Verificar estrutura atual
        num_colunas = verificar_estrutura_views(conn)
        if num_colunas == 0:
            return False
        
        # 2. Atualizar view principal
        if not atualizar_view_principal(conn):
            return False
        
        # 3. Testar view atualizada
        if not testar_view_atualizada(conn):
            return False
        
        print("\n" + "="*60)
        print("ATUALIZACAO CONCLUIDA COM SUCESSO!")
        print("="*60)
        print("As colunas vpl_reserva, vpl_tabela e idreserva foram adicionadas a view consolidada.")
        
        return True
        
    except Exception as e:
        print(f"ERRO na atualizacao: {e}")
        return False
    
    finally:
        if conn:
            conn.close()
            print("\nConexao com MotherDuck encerrada.")

if __name__ == "__main__":
    main()

