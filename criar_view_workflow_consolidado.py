#!/usr/bin/env python3
"""
Script para criar a view cv_workflow_consolidado
Une workflow_abril com reservas_abril usando idreserva como chave
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

def criar_view_workflow_consolidado(conn):
    """Cria a view cv_workflow_consolidado"""
    print("\n" + "="*60)
    print("CRIANDO VIEW CV_WORKFLOW_CONSOLIDADO")
    print("="*60)
    
    try:
        # 1. Usar o banco informacoes_consolidadas
        print("1. Usando banco informacoes_consolidadas...")
        conn.execute("USE informacoes_consolidadas")
        print("   Banco informacoes_consolidadas selecionado!")
        
        # 2. Remover view existente se houver
        print("\n2. Removendo view existente se houver...")
        conn.execute("DROP VIEW IF EXISTS cv_workflow_consolidado")
        print("   View existente removida!")
        
        # 3. Criar view consolidada
        print("\n3. Criando view cv_workflow_consolidado...")
        
        sql_view = """
        CREATE VIEW cv_workflow_consolidado AS
        SELECT
            -- COLUNAS DA TABELA WORKFLOW_ABRIL
            w.referencia,
            w.referencia_data,
            w.ativo,
            w.idtempo,
            w.idreserva,
            w.idsituacao,
            w.situacao,
            w.sigla,
            w.tempo,
            w.data_cad,
            
            -- COLUNAS DA TABELA RESERVAS_ABRIL (usando idreserva como chave)
            r.empreendimento,
            r.corretor,
            r.imobiliaria,
            
            -- COLUNAS ADICIONAIS ÚTEIS DA RESERVAS_ABRIL
            r.codigointerno,
            r.numero_venda,
            r.aprovada,
            r.data_venda,
            r.situacao as situacao_reserva,
            r.situacao_comercial,
            r.idempreendimento,
            r.codigointerno_empreendimento,
            r.etapa,
            r.bloco,
            r.unidade,
            r.regiao,
            r.venda,
            r.idcliente,
            r.documento_cliente,
            r.cliente,
            r.email,
            r.cidade,
            r.cep_cliente,
            r.renda,
            r.sexo,
            r.idade,
            r.estado_civil,
            r.idcorretor,
            r.idimobiliaria,
            r.valor_contrato,
            r.valor_contrato_com_juros,
            r.vencimento,
            r.campanha,
            r.cessao,
            r.motivo_cancelamento,
            r.data_cancelamento,
            r.espacos_complementares,
            r.idlead,
            r.data_ultima_alteracao_situacao,
            r.idempresa_correspondente,
            r.empresa_correspondente,
            r.valor_fgts,
            r.valor_financiamento,
            r.valor_subsidio,
            r.nome_usuario,
            r.idunidade,
            r.idprecadastro,
            r.idmidia,
            r.midia,
            r.descricao_motivo_cancelamento,
            r.idsituacao_anterior,
            r.situacao_anterior,
            r.idtabela,
            r.nometabela,
            r.codigointernotabela,
            r.idtipo_tabela,
            r.tipo_tabela,
            r.data_contrato,
            r.valor_proposta,
            r.vpl_reserva,
            r.valor_liquido_com_juros,
            r.valor_liquido_sem_juros,
            r.vgv_tabela,
            r.vpl_tabela,
            r.usuario_aprovacao,
            r.data_aprovacao,
            r.juros_condicao_aprovada,
            r.juros_apos_entrega_condicao_aprovada,
            r.idtabela_condicao_aprovada,
            r.data_primeira_aprovacao,
            r.aprovacao_absoluto,
            r.aprovacao_vpl_valor,
            r.idtipovenda,
            r.tipovenda,
            r.idgrupo,
            r.grupo,
            r.data_modificacao,
            r.idgestor_time,
            r.nome_time,
            r.juros_apos_entrega_cadastro,
            r.juros_cadastro_fixa_adicional,
            r.juros_cadastro,
            r.data_entrega,
            r.vgv_tabela_minima,
            r.vpl_tabela_minima,
            r.idtime,
            r.campos_adicionais,
            r.campos_adicionais_contrato
            
        FROM reservas.workflow_abril w
        LEFT JOIN reservas.reservas_abril r ON w.idreserva = r.idreserva
        """
        
        conn.execute(sql_view)
        print("   View cv_workflow_consolidado criada com sucesso!")
        
        # 4. Verificar resultado
        print(f"\n4. Verificando resultado...")
        result = conn.execute("SELECT COUNT(*) FROM cv_workflow_consolidado").fetchone()
        print(f"   Total de registros: {result[0]:,}")
        
        # 5. Verificar registros com e sem relacionamento
        print(f"\n5. Verificando relacionamentos...")
        result = conn.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(empreendimento) as com_empreendimento,
                COUNT(corretor) as com_corretor,
                COUNT(imobiliaria) as com_imobiliaria
            FROM cv_workflow_consolidado
        """).fetchone()
        
        print(f"   Total de registros: {result[0]:,}")
        print(f"   Com empreendimento: {result[1]:,} ({result[1]/result[0]*100:.1f}%)")
        print(f"   Com corretor: {result[2]:,} ({result[2]/result[0]*100:.1f}%)")
        print(f"   Com imobiliaria: {result[3]:,} ({result[3]/result[0]*100:.1f}%)")
        
        # 6. Verificar alguns exemplos
        print(f"\n6. Exemplos de dados consolidados:")
        print("-" * 50)
        result = conn.execute("""
            SELECT 
                idreserva,
                situacao,
                empreendimento,
                corretor,
                imobiliaria,
                COUNT(*) as total_registros
            FROM cv_workflow_consolidado
            WHERE empreendimento IS NOT NULL
            GROUP BY idreserva, situacao, empreendimento, corretor, imobiliaria
            ORDER BY total_registros DESC
            LIMIT 5
        """).fetchall()
        
        print("   Top 5 exemplos:")
        for row in result:
            print(f"   ID {row[0]}: {row[1]} | {row[2]} | {row[3]} | {row[4]} ({row[5]} registros)")
        
        # 7. Verificar situações únicas
        print(f"\n7. Verificando situações únicas:")
        print("-" * 50)
        result = conn.execute("""
            SELECT 
                situacao,
                COUNT(*) as total
            FROM cv_workflow_consolidado
            GROUP BY situacao
            ORDER BY total DESC
            LIMIT 10
        """).fetchall()
        
        print("   Top 10 situações:")
        for row in result:
            print(f"   - {row[0]}: {row[1]:,} registros")
        
        # 8. Verificar empreendimentos únicos
        print(f"\n8. Verificando empreendimentos únicos:")
        print("-" * 50)
        result = conn.execute("""
            SELECT 
                empreendimento,
                COUNT(*) as total
            FROM cv_workflow_consolidado
            WHERE empreendimento IS NOT NULL
            GROUP BY empreendimento
            ORDER BY total DESC
            LIMIT 10
        """).fetchall()
        
        print("   Top 10 empreendimentos:")
        for row in result:
            print(f"   - {row[0]}: {row[1]:,} registros")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao criar view: {e}")
        return False

def main():
    """Funcao principal"""
    print("CRIANDO VIEW CV_WORKFLOW_CONSOLIDADO")
    print("="*60)
    print("Relacionamento: workflow_abril.idreserva = reservas_abril.idreserva")
    print("Colunas adicionadas: empreendimento, corretor, imobiliaria")
    print("="*60)
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        if not criar_view_workflow_consolidado(conn):
            return False
        
        print("\n" + "="*60)
        print("VIEW CV_WORKFLOW_CONSOLIDADO CRIADA COM SUCESSO!")
        print("="*60)
        print("A view une workflow_abril com reservas_abril usando idreserva!")
        print("Colunas principais: empreendimento, corretor, imobiliaria")
        
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


