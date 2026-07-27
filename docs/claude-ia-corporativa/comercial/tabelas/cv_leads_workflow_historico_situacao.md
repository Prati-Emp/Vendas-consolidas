# Tabela/View: cv_leads_workflow_historico_situacao

| Campo | Valor |
|---|---|
| Banco | `informacoes_consolidadas` |
| Nome completo | `informacoes_consolidadas.cv_leads_workflow_historico_situacao` |
| Tipo | VIEW |
| Script | `scripts/criar_view_cv_leads_workflow_historico_situacao.py` |
| Status | Disponível (vida do lead / funil por mês + checkpoints de venda/descarte) |

## Fontes

- `reservas.cv_leads_workflow_tempo` — trilha de situações (tempo)
- `reservas.cv_leads` — atributos atuais + complemento de desfecho / leads sem workflow

**Escopo de leads:** a tabela `cv_leads` já vem filtrada na API (imobiliária **Prati** ou **vazia**). A view herda esse recorte — só leads internos/HOUSE.

## Para que serve

Trilha completa da vida do lead: 1 linha por passagem de situação, com intervalo de permanência, **ciclos** e **checkpoints** (venda / descarte como evento na data em que ocorreram).

Regra de negócio:

1. **Venda** conta só no mês em que o checkpoint `venda` aconteceu (`data_evento`).
2. **Descarte** idem (`tipo_evento = 'descarte'`).
3. Depois do checkpoint o lead pode **voltar** ao fluxo: abre-se um novo `n_ciclo_lead`; etapas seguintes não “carregam” a venda antiga no funil intermediário.

## Granularidade

1 linha ≈ 1 etapa do ciclo (`idlead` + `n_etapa`).

## Colunas-chave de ciclo / checkpoint

| Coluna | Uso |
|---|---|
| `n_etapa` | Ordem da trilha |
| `n_ciclo_lead` | Ciclo após cada checkpoint (1, 2, 3…) |
| `n_ciclo_atual` | Último ciclo do lead |
| `situacao_etapa` | Situação daquela passagem |
| `tipo_evento` | `venda` / `descarte` / NULL |
| `flag_checkpoint` | TRUE se a linha é venda ou descarte |
| `data_evento` | Data do checkpoint (**entrada** na venda = data da etapa anterior no CV; descarte = data do registro) |
| `data_registro_etapa` | Timestamp bruto da API (`data_cad` do workflow) |
| `data_saida_venda` | Quando saiu de “Venda Realizada” (volta ao fluxo); NULL se ainda vendido |
| `flag_etapa_fluxo` | TRUE se **não** é checkpoint (etapas 1–5 do funil) |
| `origem_etapa` | `workflow` ou `cv_leads` |
| `data_entrada_etapa` / `data_saida_etapa` | Permanência na etapa |
| `flag_etapa_final` | Última linha da trilha |
| `data_inicio_ciclo` | Início do ciclo **aberto** atual |
| `data_desfecho` / `tipo_desfecho` | Fecha só se `situacao_atual` ainda é venda/descartado |
| `flag_no_ciclo_atual` | `n_ciclo_lead = n_ciclo_atual` |
| `data_ultima_venda` / `data_ultimo_descarte` | Último checkpoint de cada tipo |
| `qtd_vendas_historico` / `qtd_descartes_historico` | Quantos checkpoints o lead já teve |
| `empreendimento_consolidado` / `enterprise_id` | Empreendimento (join dim) |
| `corretor_consolidado` / `Imobiliaria` | Atributos atuais |

## Peculiaridade CV (importante)

No endpoint de workflow/tempo, a linha `Venda Realizada` muitas vezes traz em `data_cad` a data em que o lead **saiu** da venda (ex.: voltou a Aguardando), não a data em que vendeu.

Exemplo lead **4632**:

| Evento real (histórico CV) | Como a view grava |
|---|---|
| 31/01/2025 Com Reserva → Venda Realizada | `tipo_evento=venda`, `data_evento=2025-01-31` |
| 02/07/2026 Venda Realizada → Aguardando | `data_saida_venda=2026-07-02`, abre `n_ciclo_lead=2` |
| 07/07/2026 → Descartado | `tipo_evento=descarte`, `data_evento=2026-07-07` |

Regra: para venda, `data_evento` / `data_entrada_etapa` = data da **etapa anterior**; `data_registro_etapa` = timestamp bruto da API.

## Como montar o funil do mês

### Venda realizada (evento)

```sql
SELECT COUNT(DISTINCT idlead)
FROM informacoes_consolidadas.cv_leads_workflow_historico_situacao
WHERE tipo_evento = 'venda'
  AND CAST(data_evento AS DATE) BETWEEN :inicio AND :fim;
```

Para alinhar ao card oficial HOUSE, use `sienge_vendas_consolidadas` (`contractDate` + filtro Prati/vazio) — CRM e Sienge não fecham 1:1.

### Descarte no mês

```sql
WHERE tipo_evento = 'descarte'
  AND CAST(data_evento AS DATE) BETWEEN :inicio AND :fim
```

### Etapas intermediárias (Leads → Com reserva)

- Lead vivo no ciclo aberto: `data_inicio_ciclo <= fim` e (`data_desfecho` nulo ou `>= inicio`)
- Só linhas com `flag_etapa_fluxo` e `flag_no_ciclo_atual`
- `data_entrada_etapa <= fim`
- Cumulativo pelo mapa de situações (sem incluir checkpoints)

## Exemplo — histórico com ciclos

```sql
SELECT n_etapa, n_ciclo_lead, situacao_etapa, tipo_evento,
       flag_checkpoint, flag_no_ciclo_atual, data_entrada_etapa
FROM informacoes_consolidadas.cv_leads_workflow_historico_situacao
WHERE idlead = 2688
ORDER BY n_etapa;
```
