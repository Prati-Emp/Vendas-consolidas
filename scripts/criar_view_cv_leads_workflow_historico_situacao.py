#!/usr/bin/env python3
"""Cria/atualiza a view cv_leads_workflow_historico_situacao em informacoes_consolidadas.

1 linha por passagem de situacao (vida do lead):
- etapas do workflow
- etapa sintetica para leads SEM workflow (situacao atual do cv_leads)
- etapa final sintetica quando Situacao atual e desfecho
  (Venda realizada / Descartado) e nao existe no workflow
- data_entrada/saida, ciclo, desfecho, ordem

Tambem remove views antigas/nao utilizadas, se existirem:
- cv_leads_consolidado
- cv_leads_historico_situacao (nome anterior)
"""

import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DESFECHOS_SQL = "('venda realizada', 'descartado')"

SQL_CV_LEADS_HISTORICO = f"""
CREATE OR REPLACE VIEW cv_leads_workflow_historico_situacao AS
WITH leads AS (
    SELECT
        Idlead AS idlead,
        Situacao AS situacao_atual,
        nome_situacao_anterior_lead,
        TRY_CAST(Data_cad AS TIMESTAMP) AS data_cadastro_lead,
        TRY_CAST(data_reativacao AS TIMESTAMP) AS data_reativacao,
        TRY_CAST(data_cancelamento AS TIMESTAMP) AS data_cancelamento,
        Imobiliaria,
        gestor,
        corretor,
        corretor_ultimo,
        corretor_consolidado,
        empreendimento,
        empreendimento_primeiro,
        empreendimento_ultimo,
        empreendimento_consolidado,
        TRY_CAST(idempreendimento AS BIGINT) AS idempreendimento,
        TRY_CAST(idempreendimento_primeiro AS BIGINT) AS idempreendimento_primeiro,
        TRY_CAST(idempreendimento_ultimo AS BIGINT) AS idempreendimento_ultimo,
        TRY_CAST(idempreendimento_consolidado AS BIGINT) AS idempreendimento_consolidado,
        TRY_CAST(codigointerno_empreendimento AS BIGINT) AS codigointerno_empreendimento,
        TRY_CAST(enterprise_id AS BIGINT) AS enterprise_id,
        midia_original,
        midia_ultimo,
        midia_consolidada,
        tags,
        status_venda_realizada,
        status_reserva,
        status_visita_realizada,
        status_em_atendimento,
        status_descoberta,
        status_qualificacao,
        TRY_CAST(ultima_data_conversao AS TIMESTAMP) AS ultima_data_conversao,
        TRY_CAST(data_ultima_alteracao AS TIMESTAMP) AS data_ultima_alteracao,
        TRY_CAST(data_consolidada AS TIMESTAMP) AS data_consolidada_legado,
        lower(trim(COALESCE(Situacao, ''))) AS situacao_atual_norm,
        COALESCE(
            TRY_CAST(data_reativacao AS TIMESTAMP),
            TRY_CAST(Data_cad AS TIMESTAMP)
        ) AS data_inicio_ciclo
    FROM reservas.main.cv_leads
),
wf_raw AS (
    SELECT
        w.idlead,
        w.idtempo,
        w.idsituacao,
        w.situacao AS situacao_etapa,
        w.sigla,
        w.tempo AS tempo_minutos,
        w.ativo AS ativo_wf,
        TRY_CAST(w.data_cad AS TIMESTAMP) AS data_entrada_etapa,
        TRY_CAST(w.referencia_data AS TIMESTAMP) AS referencia_data_wf,
        w.referencia AS referencia_wf,
        'workflow' AS origem_etapa
    FROM reservas.main.cv_leads_workflow_tempo AS w
    WHERE w.idlead IS NOT NULL
),
ultima_wf AS (
    SELECT
        idlead,
        situacao_etapa AS situacao_ultima_wf,
        data_entrada_etapa AS data_ultima_wf,
        ROW_NUMBER() OVER (
            PARTITION BY idlead
            ORDER BY data_entrada_etapa DESC NULLS LAST, idtempo DESC
        ) AS rn
    FROM wf_raw
),
ultima_wf_1 AS (
    SELECT * FROM ultima_wf WHERE rn = 1
),
sem_workflow_sintetico AS (
    SELECT
        l.idlead,
        CAST(NULL AS BIGINT) AS idtempo,
        CAST(NULL AS BIGINT) AS idsituacao,
        l.situacao_atual AS situacao_etapa,
        CAST(NULL AS VARCHAR) AS sigla,
        CAST(NULL AS BIGINT) AS tempo_minutos,
        CAST(NULL AS VARCHAR) AS ativo_wf,
        l.data_inicio_ciclo AS data_entrada_etapa,
        l.data_inicio_ciclo AS referencia_data_wf,
        CAST(NULL AS VARCHAR) AS referencia_wf,
        'cv_leads' AS origem_etapa
    FROM leads AS l
    LEFT JOIN ultima_wf_1 AS u ON l.idlead = u.idlead
    WHERE u.idlead IS NULL
),
desfecho_sintetico AS (
    SELECT
        l.idlead,
        CAST(NULL AS BIGINT) AS idtempo,
        CAST(NULL AS BIGINT) AS idsituacao,
        l.situacao_atual AS situacao_etapa,
        CAST(NULL AS VARCHAR) AS sigla,
        CAST(NULL AS BIGINT) AS tempo_minutos,
        CAST(NULL AS VARCHAR) AS ativo_wf,
        u.data_ultima_wf AS data_entrada_etapa,
        u.data_ultima_wf AS referencia_data_wf,
        CAST(NULL AS VARCHAR) AS referencia_wf,
        'cv_leads' AS origem_etapa
    FROM leads AS l
    INNER JOIN ultima_wf_1 AS u ON l.idlead = u.idlead
    WHERE l.situacao_atual_norm IN {DESFECHOS_SQL}
      AND lower(trim(COALESCE(u.situacao_ultima_wf, ''))) <> l.situacao_atual_norm
),
etapas AS (
    SELECT * FROM wf_raw
    UNION ALL
    SELECT * FROM sem_workflow_sintetico
    UNION ALL
    SELECT * FROM desfecho_sintetico
),
etapas_ord AS (
    SELECT
        e.*,
        CASE WHEN e.origem_etapa = 'cv_leads' THEN 1 ELSE 0 END AS ord_origem,
        ROW_NUMBER() OVER (
            PARTITION BY e.idlead
            ORDER BY e.data_entrada_etapa ASC NULLS LAST,
                     CASE WHEN e.origem_etapa = 'cv_leads' THEN 1 ELSE 0 END ASC,
                     COALESCE(e.idtempo, 999999999999) ASC
        ) AS n_etapa,
        LEAD(e.data_entrada_etapa) OVER (
            PARTITION BY e.idlead
            ORDER BY e.data_entrada_etapa ASC NULLS LAST,
                     CASE WHEN e.origem_etapa = 'cv_leads' THEN 1 ELSE 0 END ASC,
                     COALESCE(e.idtempo, 999999999999) ASC
        ) AS data_proxima_etapa,
        ROW_NUMBER() OVER (
            PARTITION BY e.idlead
            ORDER BY e.data_entrada_etapa DESC NULLS LAST,
                     CASE WHEN e.origem_etapa = 'cv_leads' THEN 1 ELSE 0 END DESC,
                     COALESCE(e.idtempo, 0) DESC
        ) AS rn_desc
    FROM etapas AS e
),
ciclo AS (
    SELECT
        l.idlead,
        l.data_inicio_ciclo,
        CASE
            WHEN l.situacao_atual_norm = 'venda realizada' THEN 'venda'
            WHEN l.situacao_atual_norm = 'descartado' THEN 'descartado'
            ELSE 'em_aberto'
        END AS tipo_desfecho,
        CASE
            WHEN l.situacao_atual_norm = 'descartado'
                 AND l.data_cancelamento IS NOT NULL
                THEN l.data_cancelamento
            WHEN l.situacao_atual_norm IN {DESFECHOS_SQL}
                THEN (
                    SELECT MAX(o.data_entrada_etapa)
                    FROM etapas_ord AS o
                    WHERE o.idlead = l.idlead
                      AND lower(trim(o.situacao_etapa)) = l.situacao_atual_norm
                )
            ELSE NULL
        END AS data_desfecho
    FROM leads AS l
)
SELECT
    o.idlead,
    o.n_etapa,
    o.idtempo,
    o.idsituacao,
    o.situacao_etapa,
    o.sigla,
    o.tempo_minutos,
    o.ativo_wf,
    o.origem_etapa,
    o.data_entrada_etapa,
    CASE
        WHEN o.data_proxima_etapa IS NOT NULL THEN o.data_proxima_etapa
        WHEN c.tipo_desfecho <> 'em_aberto'
             AND lower(trim(o.situacao_etapa)) = lower(trim(l.situacao_atual))
            THEN c.data_desfecho
        WHEN c.tipo_desfecho <> 'em_aberto' AND o.rn_desc = 1
            THEN c.data_desfecho
        ELSE NULL
    END AS data_saida_etapa,
    (o.rn_desc = 1) AS flag_etapa_final,
    c.data_inicio_ciclo,
    c.data_desfecho,
    c.tipo_desfecho,
    (o.data_entrada_etapa IS NULL OR o.data_entrada_etapa >= c.data_inicio_ciclo) AS flag_no_ciclo_atual,
    COALESCE(c.data_desfecho, o.data_entrada_etapa) AS data_consolidada,
    l.situacao_atual,
    l.nome_situacao_anterior_lead,
    l.data_cadastro_lead,
    l.data_reativacao,
    l.data_cancelamento,
    l.Imobiliaria,
    l.gestor,
    l.corretor,
    l.corretor_ultimo,
    l.corretor_consolidado,
    l.empreendimento,
    l.empreendimento_primeiro,
    l.empreendimento_ultimo,
    l.empreendimento_consolidado,
    l.idempreendimento,
    l.idempreendimento_primeiro,
    l.idempreendimento_ultimo,
    l.idempreendimento_consolidado,
    l.codigointerno_empreendimento,
    l.enterprise_id,
    l.midia_original,
    l.midia_ultimo,
    l.midia_consolidada,
    l.tags,
    l.status_venda_realizada,
    l.status_reserva,
    l.status_visita_realizada,
    l.status_em_atendimento,
    l.status_descoberta,
    l.status_qualificacao,
    l.ultima_data_conversao,
    l.data_ultima_alteracao,
    l.data_consolidada_legado,
    o.referencia_data_wf,
    o.referencia_wf
FROM etapas_ord AS o
INNER JOIN leads AS l ON o.idlead = l.idlead
LEFT JOIN ciclo AS c ON o.idlead = c.idlead
"""


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

    conn = duckdb.connect("md:informacoes_consolidadas")
    try:
        conn.execute("ATTACH 'md:reservas' AS reservas")
    except Exception as e:
        if "already attached" not in str(e).lower():
            print(f"AVISO ATTACH reservas: {e}")

    print("=" * 60)
    print("VIEW cv_leads_workflow_historico_situacao")
    print("=" * 60)

    print("\n1) Removendo views antigas/nao utilizadas...")
    conn.execute("DROP VIEW IF EXISTS cv_leads_consolidado")
    conn.execute("DROP VIEW IF EXISTS cv_leads_historico_situacao")
    print("   OK")

    print("\n2) Criando/atualizando cv_leads_workflow_historico_situacao...")
    conn.execute(SQL_CV_LEADS_HISTORICO)
    n = conn.sql("SELECT COUNT(*) FROM cv_leads_workflow_historico_situacao").fetchone()[0]
    leads = conn.sql(
        "SELECT COUNT(DISTINCT idlead) FROM cv_leads_workflow_historico_situacao"
    ).fetchone()[0]
    print(f"   OK — {n:,} etapas / {leads:,} leads")

    print("\n3) Paridade vs cv_leads...")
    print(
        conn.sql(
            """
            WITH o AS (SELECT DISTINCT Idlead AS idlead FROM reservas.main.cv_leads),
                 h AS (SELECT DISTINCT idlead FROM cv_leads_workflow_historico_situacao)
            SELECT
              (SELECT COUNT(*) FROM o) AS original,
              (SELECT COUNT(*) FROM h) AS historico,
              (SELECT COUNT(*) FROM o ANTI JOIN h USING (idlead)) AS original_sem_historico
            """
        )
        .fetchdf()
        .to_string(index=False)
    )

    print("\n4) Nomes antigos ainda existem?")
    still = conn.sql(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'main'
          AND table_name IN (
            'cv_leads_consolidado',
            'cv_leads_historico_situacao'
          )
        ORDER BY 1
        """
    ).fetchdf()
    print(still.to_string(index=False) if len(still) else "   nenhum")

    conn.close()
    print("\nCONCLUIDO — view ativa: informacoes_consolidadas.cv_leads_workflow_historico_situacao")


if __name__ == "__main__":
    main()
