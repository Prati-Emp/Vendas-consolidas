#!/usr/bin/env python3
"""
Cria a view administracao.prosoluto_antes_e_pos_chaves.

Dinâmica: mesma lógica do ProSoluto (snapshot_prosoluto_mensal):
- Parcelas: Tipo_Baixa IS NULL, Tipo_Condicao IN ('12','PM','AT','PB','PA','PI','PQ','PS')
- Join id2 = id1: Cod_Centro_Custo & Unidade = codigointerno_empreendimento & unidade
- Denominador: valor_contrato de cv_vendas (tipovenda = 'Venda Financiamento')

Divisão antes/pós chaves:
- Tabela de corte: planilhas.data_entrega_empreendimentos_prosoluto_antes_pos_chaves
- Colunas: id_empreendimento, data_fim_obra
- Antes chaves: Data_Vencimento <= data_fim_obra
- Pós chaves: Data_Vencimento > data_fim_obra

Nomes dos empreendimentos: informacoes_consolidadas.dim_empreendimentos_dinamica (enterpriseId, nome_empreendimento).
"""

import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TIPOS_PROSOLUTO = "'12', 'PM', 'AT', 'PB', 'PA', 'PI', 'PQ', 'PS'"


def main():
    load_dotenv()
    token = os.environ.get("MOTHERDUCK_TOKEN", "").strip()
    if not token:
        print("ERRO: MOTHERDUCK_TOKEN nao encontrado")
        sys.exit(1)

    import duckdb
    duckdb.sql("INSTALL motherduck")
    duckdb.sql("LOAD motherduck")
    duckdb.sql(f"SET motherduck_token='{token}'")

    conn = duckdb.connect("md:administracao")
    for db, alias in [("planilhas", "planilhas"), ("informacoes_consolidadas", "informacoes_consolidadas")]:
        try:
            conn.execute(f"ATTACH 'md:{db}' AS {alias}")
        except Exception as e:
            if "already attached" not in str(e).lower():
                print(f"AVISO ATTACH {db}: {e}")

    print("=" * 60)
    print("CRIANDO VIEW prosoluto_antes_e_pos_chaves")
    print("=" * 60)

    conn.execute("DROP VIEW IF EXISTS prosoluto_antes_e_pos_chaves")

    sql = f"""
    CREATE VIEW prosoluto_antes_e_pos_chaves AS
    WITH
    data_corte AS (
        SELECT
            dc.id_empreendimento,
            COALESCE(dim.nome_empreendimento, dc.nome_empreendimento) AS nome_empreendimento,
            CAST(dc.data_fim_obra AS DATE) AS data_fim_obra
        FROM planilhas.data_entrega_empreendimentos_prosoluto_antes_pos_chaves dc
        LEFT JOIN (
            SELECT TRY_CAST(enterpriseId AS BIGINT) AS id_empreendimento,
                   MAX(nome_empreendimento) AS nome_empreendimento
            FROM informacoes_consolidadas.dim_empreendimentos_dinamica
            WHERE enterpriseId IS NOT NULL
            GROUP BY 1
        ) dim ON dim.id_empreendimento = dc.id_empreendimento
        WHERE dc.id_empreendimento IS NOT NULL AND dc.data_fim_obra IS NOT NULL
    ),
    parcelas_classificadas AS (
        SELECT
            v.codigointerno_empreendimento,
            v.empreendimento,
            d.id_empreendimento,
            d.nome_empreendimento,
            d.data_fim_obra,
            cr.Valor_Devido,
            CASE
                WHEN TRY_CAST(cr.Data_Vencimento AS DATE) <= d.data_fim_obra THEN 'antes_chaves'
                ELSE 'pos_chaves'
            END AS periodo
        FROM contas_recebidas_receber cr
        INNER JOIN reservas.cv_vendas v
            ON v.tipovenda = 'Venda Financiamento'
           AND (COALESCE(CAST(cr.Cod_Centro_Custo AS VARCHAR), '') || COALESCE(TRIM(CAST(cr.Unidade AS VARCHAR)), ''))
             = (COALESCE(CAST(v.codigointerno_empreendimento AS VARCHAR), '') || COALESCE(TRIM(CAST(v.unidade AS VARCHAR)), ''))
        INNER JOIN data_corte d
            ON TRY_CAST(v.codigointerno_empreendimento AS BIGINT) = d.id_empreendimento
        WHERE cr.Tipo_Baixa IS NULL
          AND cr.Tipo_Condicao IN ({TIPOS_PROSOLUTO})
    ),
    valor_por_periodo AS (
        SELECT
            codigointerno_empreendimento,
            empreendimento,
            id_empreendimento,
            nome_empreendimento,
            data_fim_obra,
            periodo,
            SUM(Valor_Devido) AS valor_prosoluto
        FROM parcelas_classificadas
        GROUP BY codigointerno_empreendimento, empreendimento, id_empreendimento, nome_empreendimento, data_fim_obra, periodo
    ),
    denom_emp AS (
        SELECT
            TRY_CAST(codigointerno_empreendimento AS BIGINT) AS id_empreendimento,
            codigointerno_empreendimento,
            empreendimento,
            SUM(valor_contrato) AS valor_venda_financiamento
        FROM reservas.cv_vendas
        WHERE tipovenda = 'Venda Financiamento'
          AND codigointerno_empreendimento IS NOT NULL
        GROUP BY codigointerno_empreendimento, empreendimento
    ),
    base AS (
        SELECT
            dc.id_empreendimento,
            dc.nome_empreendimento,
            dc.data_fim_obra,
            p.periodo,
            COALESCE(v.valor_prosoluto, 0) AS valor_prosoluto,
            COALESCE(d.valor_venda_financiamento, 0) AS valor_venda_financiamento
        FROM data_corte dc
        CROSS JOIN (SELECT 'antes_chaves' AS periodo UNION ALL SELECT 'pos_chaves') p
        LEFT JOIN valor_por_periodo v
            ON dc.id_empreendimento = v.id_empreendimento AND dc.data_fim_obra = v.data_fim_obra AND p.periodo = v.periodo
        INNER JOIN denom_emp d
            ON dc.id_empreendimento = d.id_empreendimento
    ),
    geral_prati AS (
        SELECT
            periodo,
            SUM(valor_prosoluto) AS valor_prosoluto,
            SUM(valor_venda_financiamento) AS valor_venda_financiamento
        FROM base
        GROUP BY periodo
    )
    SELECT
        id_empreendimento,
        nome_empreendimento,
        data_fim_obra,
        periodo,
        valor_prosoluto,
        valor_venda_financiamento,
        CASE WHEN valor_venda_financiamento IS NULL OR valor_venda_financiamento = 0 THEN 0
             ELSE valor_prosoluto / valor_venda_financiamento
        END AS pct_prosoluto
    FROM base
    UNION ALL
    SELECT
        NULL::BIGINT AS id_empreendimento,
        'Geral Prati' AS nome_empreendimento,
        NULL::DATE AS data_fim_obra,
        periodo,
        valor_prosoluto,
        valor_venda_financiamento,
        CASE WHEN valor_venda_financiamento IS NULL OR valor_venda_financiamento = 0 THEN 0
             ELSE valor_prosoluto / valor_venda_financiamento
        END AS pct_prosoluto
    FROM geral_prati
    """

    conn.execute(sql)
    print("OK: View prosoluto_antes_e_pos_chaves criada")

    # Amostra
    print("\n" + "-" * 60)
    print("Amostra (Geral Prati + primeiros empreendimentos):")
    rows = conn.execute("""
        SELECT id_empreendimento, nome_empreendimento, periodo,
               valor_prosoluto, valor_venda_financiamento,
               ROUND(pct_prosoluto * 100, 2) AS pct_prosoluto_pct
        FROM prosoluto_antes_e_pos_chaves
        ORDER BY id_empreendimento NULLS FIRST, periodo
        LIMIT 12
    """).fetchall()
    for r in rows:
        print(f"  {r}")

    conn.close()
    print("\nView: administracao.prosoluto_antes_e_pos_chaves")
    print("Fonte: contas_recebidas_receber + reservas.cv_vendas + planilhas.data_entrega + informacoes_consolidadas.dim_empreendimentos_dinamica")


if __name__ == "__main__":
    main()
