#!/usr/bin/env python3
"""
Script para criar a view com caminho completo
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

def criar_view_caminho_completo(conn):
    """Cria a view com caminho completo"""
    print("\n" + "="*60)
    print("CRIANDO VIEW COM CAMINHO COMPLETO")
    print("="*60)
    
    try:
        # 1. Verificar qual banco estamos usando
        print("1. Verificando banco atual...")
        try:
            result = conn.execute("SELECT current_database()").fetchone()
            print(f"   Banco atual: {result[0]}")
        except Exception as e:
            print(f"   ERRO ao verificar banco: {e}")
        
        # 2. Listar bancos disponíveis
        print("\n2. Listando bancos disponíveis...")
        try:
            result = conn.execute("SHOW DATABASES").fetchall()
            print("   Bancos disponíveis:")
            for db in result:
                print(f"   - {db[0]}")
        except Exception as e:
            print(f"   ERRO ao listar bancos: {e}")
        
        # 3. Tentar criar a view com diferentes caminhos
        print("\n3. Tentando criar view com diferentes caminhos...")
        
        # Tentar com main.informacoes_consolidadas
        try:
            print("   Tentando com main.informacoes_consolidadas...")
            conn.execute("CREATE SCHEMA IF NOT EXISTS main.informacoes_consolidadas")
            print("   Schema main.informacoes_consolidadas criado!")
        except Exception as e:
            print(f"   ERRO com main.informacoes_consolidadas: {e}")
        
        # 4. Criar a view
        print("\n4. Criando view...")
        
        sql_view = """
        CREATE VIEW main.informacoes_consolidadas.sienge_vendas_consolidadas AS
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

        -- Seção 3: Reservas Vera Cruz (ORDEM CORRIGIDA PARA MATCHAR)
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
            r.renda as profissao,  -- CORRIGIDO: profissao vem de renda
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
        print("   View criada com sucesso!")
        
        # 5. Verificar a nova estrutura
        print("\n5. Verificando estrutura da view...")
        columns_nova = conn.execute("DESCRIBE main.informacoes_consolidadas.sienge_vendas_consolidadas").fetchall()
        print(f"   Total de colunas: {len(columns_nova)}")
        
        # Verificar se as novas colunas existem
        colunas_existentes = [col[0] for col in columns_nova]
        novas_colunas = ['vpl_reserva', 'vpl_tabela', 'idreserva']
        
        print(f"\n6. Verificando novas colunas:")
        for coluna in novas_colunas:
            if coluna in colunas_existentes:
                print(f"   OK {coluna} - EXISTE")
            else:
                print(f"   X {coluna} - NAO EXISTE")
        
        # 7. Testar contagem
        print(f"\n7. Testando contagem de registros...")
        result = conn.execute("SELECT COUNT(*) FROM main.informacoes_consolidadas.sienge_vendas_consolidadas").fetchone()
        print(f"   Total de registros: {result[0]:,}")
        
        # 8. Verificar contagem por origem
        print(f"\n8. Verificando contagem por origem:")
        result = conn.execute("""
            SELECT origem, COUNT(*) as total
            FROM main.informacoes_consolidadas.sienge_vendas_consolidadas
            GROUP BY origem
            ORDER BY origem
        """).fetchall()
        
        for row in result:
            print(f"   {row[0]}: {row[1]:,} registros")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao criar view: {e}")
        return False

def main():
    """Funcao principal"""
    print("CRIANDO VIEW COM CAMINHO COMPLETO")
    print("="*60)
    print("Adicionando colunas: vpl_reserva, vpl_tabela, idreserva")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        if not criar_view_caminho_completo(conn):
            return False
        
        print("\n" + "="*60)
        print("VIEW CRIADA COM SUCESSO!")
        print("="*60)
        print("A view main.informacoes_consolidadas.sienge_vendas_consolidadas foi criada com as 3 novas colunas.")
        print("Agora você pode usar vpl_reserva, vpl_tabela e idreserva nas suas consultas!")
        
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

