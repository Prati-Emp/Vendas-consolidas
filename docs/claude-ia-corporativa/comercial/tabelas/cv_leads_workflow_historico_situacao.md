# Tabela/View: cv_leads_workflow_historico_situacao

| Campo | Valor |
|---|---|
| Banco | `informacoes_consolidadas` |
| Nome completo | `informacoes_consolidadas.cv_leads_workflow_historico_situacao` |
| Tipo | VIEW |
| Script | `scripts/criar_view_cv_leads_workflow_historico_situacao.py` |
| Status | Disponível (vida do lead / funil por mês até desfecho) |

## Fontes

- `reservas.cv_leads_workflow_tempo` — trilha de situações (tempo)
- `reservas.cv_leads` — atributos atuais + complemento de desfecho / leads sem workflow

O nome deixa explícito que a view une **leads + workflow**.

## Para que serve

Trilha completa da vida do lead: 1 linha por passagem de situação, com intervalo de permanência e ciclo até o desfecho (venda ou descarte).

Quando o workflow **não traz** a etapa final (ex.: `Venda Realizada`), a view **completa** com uma linha sintética a partir de `cv_leads.Situacao` (`origem_etapa = 'cv_leads'`).

Quando o lead **não tem nenhuma linha no workflow**, também gera uma linha sintética com a situação atual e `data_inicio_ciclo`, para não perder leads no caminho.

## Granularidade

1 linha ≈ 1 etapa do ciclo (`idlead` + `n_etapa`).

## Colunas-chave de ciclo / tempo

| Coluna | Uso |
|---|---|
| `n_etapa` | Ordem da trilha |
| `situacao_etapa` | Situação daquela passagem |
| `origem_etapa` | `workflow` ou `cv_leads` (desfecho complementar) |
| `data_entrada_etapa` | Início da etapa |
| `data_saida_etapa` | Fim da etapa (`LEAD` ou desfecho) |
| `flag_etapa_final` | Última linha da trilha |
| `data_inicio_ciclo` | `data_reativacao` → senão `Data_cad` |
| `data_desfecho` | Quando encerrou (venda/descarte); NULL se em aberto |
| `tipo_desfecho` | `venda` / `descartado` / `em_aberto` |
| `flag_no_ciclo_atual` | Etapa >= início do ciclo (útil pós-reativação) |
| `data_consolidada` | Desfecho se houver; senão data da etapa |
| `empreendimento_consolidado` / `enterprise_id` | Nome consolidado + chave de join (`codigointerno` → `dim.enterpriseId`) |
| `empreendimento` / `empreendimento_primeiro` / `empreendimento_ultimo` | Nomes brutos da API |
| `idempreendimento*` | IDs internos do CV (não confundir com `enterprise_id`) |
| `codigointerno_empreendimento` | Mesmo valor de `enterprise_id` |
| `corretor_consolidado` / `Imobiliaria` / status… | Atributos atuais do lead |

## Regra de “vivo no mês”

Lead conta no mês M se o ciclo cruza o mês:

```sql
data_inicio_ciclo <= fim_do_mes
AND (data_desfecho IS NULL OR data_desfecho >= inicio_do_mes)
```

Para etapa do funil: já tinha alcançado a etapa até o fim do mês (`data_entrada_etapa <= fim_do_mes`).

## Exemplo — histórico

```sql
SELECT n_etapa, situacao_etapa, origem_etapa,
       data_entrada_etapa, data_saida_etapa, tipo_desfecho
FROM informacoes_consolidadas.cv_leads_workflow_historico_situacao
WHERE idlead = 3781
ORDER BY n_etapa;
```
