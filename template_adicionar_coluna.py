#!/usr/bin/env python3
"""
TEMPLATE: Script para adicionar nova coluna à view consolidada de vendas
Copie este arquivo e substitua 'NOME_DA_COLUNA' pela coluna desejada
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

def investigar_coluna(conn, nome_coluna):
    """Investiga a nova coluna antes de adicionar"""
    print(f"\n" + "="*60)
    print(f"INVESTIGANDO COLUNA: {nome_coluna}")
    print("="*60)
    
    try:
        # 1. Verificar se a coluna existe
        print("1. Verificando se a coluna existe na tabela reservas_abril...")
        columns = conn.execute("DESCRIBE reservas.reservas_abril").fetchall()
        coluna_existe = False
        
        for col in columns:
            if nome_coluna.lower() in col[0].lower():
                print(f"   ✓ Encontrada: {col[0]} ({col[1]})")
                coluna_existe = True
        
        if not coluna_existe:
            print(f"   ✗ Coluna '{nome_coluna}' não encontrada!")
            return False
        
        # 2. Verificar dados da coluna
        print(f"\n2. Verificando dados da coluna {nome_coluna}...")
        result = conn.execute(f"""
            SELECT 
                {nome_coluna},
                COUNT(*) as total
            FROM reservas.reservas_abril
            WHERE {nome_coluna} IS NOT NULL AND {nome_coluna} != ''
            GROUP BY {nome_coluna}
            ORDER BY total DESC
            LIMIT 10
        """).fetchall()
        
        print(f"   Top 10 valores de {nome_coluna}:")
        for row in result:
            print(f"   - {row[0]}: {row[1]:,} registros")
        
        # 3. Testar relacionamentos
        print(f"\n3. Testando relacionamentos para {nome_coluna}...")
        
        # Teste por codigointerno
        result = conn.execute(f"""
            SELECT 
                s.id,
                (SELECT {nome_coluna} FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as valor_por_codigointerno
            FROM reservas.sienge_vendas_realizadas s
            WHERE s.brokers[1].id IS NOT NULL
            LIMIT 5
        """).fetchall()
        
        print(f"   Exemplos por codigointerno:")
        for row in result:
            print(f"   ID: {row[0]} -> {nome_coluna}: {row[1]}")
        
        # Teste por idcorretor
        result = conn.execute(f"""
            SELECT 
                s.brokers[1].id as idcorretor,
                (SELECT {nome_coluna} FROM reservas.reservas_abril WHERE idcorretor = s.brokers[1].id LIMIT 1) as valor_por_idcorretor
            FROM reservas.sienge_vendas_realizadas s
            WHERE s.brokers[1].id IS NOT NULL
            LIMIT 5
        """).fetchall()
        
        print(f"   Exemplos por idcorretor:")
        for row in result:
            print(f"   Corretor: {row[0]} -> {nome_coluna}: {row[1]}")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao investigar coluna: {e}")
        return False

def adicionar_coluna_view(conn, nome_coluna):
    """Adiciona nova coluna à view consolidada"""
    print(f"\n" + "="*60)
    print(f"ADICIONANDO COLUNA: {nome_coluna}")
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
        
        # 3. Criar view com nova coluna
        print(f"\n3. Criando view com coluna {nome_coluna}...")
        
        sql_view = f"""
        CREATE VIEW sienge_vendas_consolidadas AS
        -- Seção 1: Vendas Realizadas Sienge
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
            -- COLUNAS EXISTENTES
            (SELECT vpl_reserva FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as vpl_reserva,
            (SELECT vpl_tabela FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as vpl_tabela,
            (SELECT idreserva FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as idreserva,
            -- NOVA COLUNA ADICIONADA
            COALESCE(
                (SELECT {nome_coluna} FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1),
                (SELECT {nome_coluna} FROM reservas.reservas_abril WHERE idcorretor = s.brokers[1].id LIMIT 1),
                (SELECT {nome_coluna} FROM reservas.reservas_abril WHERE idimobiliaria = s.brokers[1].id LIMIT 1)
            ) as {nome_coluna}
        FROM reservas.sienge_vendas_realizadas s

        UNION ALL

        -- Seção 2: Vendas Canceladas Sienge
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
            -- COLUNAS EXISTENTES
            (SELECT vpl_reserva FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as vpl_reserva,
            (SELECT vpl_tabela FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as vpl_tabela,
            (SELECT idreserva FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as idreserva,
            -- NOVA COLUNA ADICIONADA
            COALESCE(
                (SELECT {nome_coluna} FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1),
                (SELECT {nome_coluna} FROM reservas.reservas_abril WHERE idcorretor = s.brokers[1].id LIMIT 1),
                (SELECT {nome_coluna} FROM reservas.reservas_abril WHERE idimobiliaria = s.brokers[1].id LIMIT 1)
            ) as {nome_coluna}
        FROM reservas.sienge_vendas_canceladas s

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
            r.idreserva,
            -- NOVA COLUNA (se existir na view cv_vendas_consolidadas_vera_cruz)
            r.{nome_coluna}
        FROM reservas.cv_vendas_consolidadas_vera_cruz r
        """
        
        conn.execute(sql_view)
        print(f"   View atualizada com coluna {nome_coluna}!")
        
        # 4. Verificar resultado
        print(f"\n4. Verificando resultado...")
        result = conn.execute("SELECT COUNT(*) FROM sienge_vendas_consolidadas").fetchone()
        print(f"   Total de registros: {result[0]:,}")
        
        # 5. Verificar nova coluna
        result = conn.execute(f"""
            SELECT 
                COUNT(*) as total,
                COUNT({nome_coluna}) as com_dados
            FROM sienge_vendas_consolidadas
        """).fetchone()
        
        taxa_preenchimento = (result[1] / result[0]) * 100 if result[0] > 0 else 0
        print(f"   Registros com {nome_coluna}: {result[1]:,} de {result[0]:,} ({taxa_preenchimento:.1f}%)")
        
        # 6. Verificar por origem
        print(f"\n6. Verificando por origem:")
        result = conn.execute(f"""
            SELECT 
                origem,
                COUNT(*) as total,
                COUNT({nome_coluna}) as com_dados
            FROM sienge_vendas_consolidadas
            GROUP BY origem
            ORDER BY origem
        """).fetchall()
        
        for row in result:
            taxa = (row[2] / row[1]) * 100 if row[1] > 0 else 0
            print(f"   {row[0]}: {row[2]:,}/{row[1]:,} ({taxa:.1f}%)")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao adicionar coluna: {e}")
        return False

def main():
    """Funcao principal"""
    print("TEMPLATE: ADICIONAR NOVA COLUNA À VIEW CONSOLIDADA DE VENDAS")
    print("="*60)
    print("INSTRUÇÕES:")
    print("1. Substitua 'NOME_DA_COLUNA' pelo nome da coluna desejada")
    print("2. Execute o script")
    print("="*60)
    
    # ⚠️ SUBSTITUIR PELO NOME DA COLUNA DESEJADA ⚠️
    nome_coluna = "NOME_DA_COLUNA"  # ← ALTERAR AQUI
    
    if nome_coluna == "NOME_DA_COLUNA":
        print("ERRO: Você precisa substituir 'NOME_DA_COLUNA' pelo nome da coluna desejada!")
        return False
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        # Primeiro investigar a coluna
        if not investigar_coluna(conn, nome_coluna):
            return False
        
        # Depois adicionar à view
        if not adicionar_coluna_view(conn, nome_coluna):
            return False
        
        print("\n" + "="*60)
        print("COLUNA ADICIONADA COM SUCESSO!")
        print("="*60)
        print(f"A coluna '{nome_coluna}' foi adicionada à view consolidada!")
        
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
