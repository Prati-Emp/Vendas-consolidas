# Tabela: cv_leads

| Campo | Valor |
|---|---|
| Banco | `reservas` |
| Nome completo | `reservas.cv_leads` |
| Tipo | TABELA |
| Uso no Streamlit | TV Comercial (contagem / indicadores de leads) |
| Status | Usada |

## Para que serve

Base bruta de leads do CV CRM, com status consolidados (venda, reserva, visita, atendimento etc.).

## Granularidade

1 linha ≈ 1 lead.

## Colunas-chave

| Coluna | Tipo | Uso |
|---|---|---|
| `Idlead` | BIGINT | ID |
| `Data_cad` | TIMESTAMP_NS | Cadastro |
| `Situacao` | VARCHAR | Situação |
| `Imobiliaria` | VARCHAR | Imobiliária |
| `corretor` / `corretor_consolidado` | VARCHAR | Corretor |
| `empreendimento` | VARCHAR | Nome atual (API) |
| `empreendimento_primeiro` / `empreendimento_ultimo` | VARCHAR | Interesse |
| `empreendimento_consolidado` | VARCHAR | `ultimo` → `empreendimento` → `primeiro` |
| `idempreendimento` / `idempreendimento_primeiro` / `idempreendimento_ultimo` | BIGINT | IDs internos do CV (não usar no join com dim) |
| `idempreendimento_consolidado` | BIGINT | ID CV consolidado (`ultimo` → `id` → `primeiro`; `0` vira nulo) |
| `codigointerno_empreendimento` / `enterprise_id` | BIGINT | Chave de join com `dim_empreendimentos_dinamica.enterpriseId` |
| `midia_original` / `midia_consolidada` | VARCHAR | Mídia |
| `status_venda_realizada` | VARCHAR | Funil |
| `status_reserva` | VARCHAR | Funil |
| `status_visita_realizada` | VARCHAR | Funil |
| `status_em_atendimento` | VARCHAR | Funil |
| `data_consolidada` | TIMESTAMP_NS | Mais recente entre `ultima_data_conversao`, `data_reativacao` e `Data_cad` |

## Perguntas que responde

- Volume de leads no período (TV)
- Status do funil (venda/reserva/visita)

## Não usar para

- Tempo de permanência em cada etapa do workflow → use `cv_leads_workflow_consolidado`

## Exemplo SQL

```sql
SELECT
  CAST(Data_cad AS DATE) AS dia,
  COUNT(*) AS qtd_leads
FROM reservas.cv_leads
WHERE Data_cad IS NOT NULL
  AND CAST(Data_cad AS DATE) BETWEEN '2026-06-01' AND '2026-06-30'
GROUP BY 1
ORDER BY 1;
```
