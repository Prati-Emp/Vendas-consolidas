# 03 — Funil de Leads: nova fonte (substituir `cv_leads`)

Guia para o projeto Claude / dashboard Prati (`prati-dashboard`).

Use este arquivo quando for montar ou corrigir o **funil de leads**, KPIs de volume por período, ou filtros por empreendimento no visual que hoje lê `reservas.main.cv_leads` filtrando `data_consolidada`.

---

## 1. O que mudar (resumo)

| Antes (visual atual) | Depois (correto) |
|---|---|
| Fonte: `reservas.main.cv_leads` | Fonte: `informacoes_consolidadas.cv_leads_workflow_historico_situacao` |
| Filtro de período: `data_consolidada` | Fluxo: ciclo aberto; venda/descarte: `data_evento` no mês |
| 1 linha = 1 lead | 1 linha = 1 passagem de situação (+ checkpoints) |
| Empreendimento frágil / pouco preenchido | Usar `empreendimento_consolidado` + `enterprise_id` |
| Escopo | Só Prati ou imobiliária vazia (já no ETL de `cv_leads`) |

**Não delete** `cv_leads`: ela continua sendo a base bruta e alimenta a view.  
**Para o funil do visual**, pare de contar leads só com `WHERE data_consolidada BETWEEN ...`.

---

## 2. Por que o modelo antigo falha

### `data_consolidada` / `ultima_data_conversao` não medem “mudou de situação”

Na API do CV, `ultima_data_conversao` muitas vezes copia a **última alteração cadastral** (nome, e-mail, valor, tags, data de vencimento), não a data em que o lead mudou de etapa do funil.

Exemplos validados:

- Lead **6153**: mudança real `Com Reserva → Venda Realizada` em **12/05/2026**; `ultima_data_conversao` veio **22/07/2026** (edição de cadastro).
- Lead **3781**: venda em **17/09/2024**; `ultima_data_conversao` veio **06/06/2026** (edição de valor/tags).

Consequência no dashboard antigo: o lead “aparece” no mês errado (ou some do mês em que deveria contar).

### Regra de negócio desejada (acordada)

Um lead que:

1. cadastra em janeiro,
2. fica ativo em fevereiro,
3. vende em março,

deve entrar no funil de **jan, fev e mar**.  
Depois do desfecho (**venda** ou **descarte**), **para** de contar nos meses seguintes.  
O mesmo vale para ciclos pós-reativação.

Isso **não** se resolve com um único `data_consolidada` por lead.

---

## 3. Nova tabela/view a usar

| Campo | Valor |
|---|---|
| Nome | `cv_leads_workflow_historico_situacao` |
| Nome completo | `informacoes_consolidadas.cv_leads_workflow_historico_situacao` |
| Tipo | VIEW |
| Script | `scripts/criar_view_cv_leads_workflow_historico_situacao.py` |
| Fontes | `reservas.cv_leads_workflow_tempo` + `reservas.cv_leads` |

### O que a view faz

1. Monta a **trilha de situações** a partir do workflow de tempo do CV.
2. Se o lead **não tem workflow**, cria 1 linha sintética com a situação atual (`origem_etapa = 'cv_leads'`).
3. Se o desfecho (`Venda Realizada` / `Descartado`) **não veio** no workflow, completa com linha sintética a partir de `cv_leads.Situacao`.
4. Calcula **ciclo** (`data_inicio_ciclo` → `data_desfecho`) e atributos atuais (corretor, mídia, empreendimento…).

Granularidade: **1 linha ≈ 1 etapa** (`idlead` + `n_etapa`).  
Sempre agregue com `COUNT(DISTINCT idlead)` quando quiser “quantos leads”.

Ficha detalhada: [`tabelas/cv_leads_workflow_historico_situacao.md`](tabelas/cv_leads_workflow_historico_situacao.md).

---

## 4. Como chegar no resultado do funil

A view agora separa **fluxo** (etapas intermediárias) de **checkpoint** (venda / descarte).

### 4.0 Escopo Prati (já no ETL)

`cv_leads` só traz imobiliária contendo **Prati** ou **vazia** (`scripts/cv_leads_api.py`). Validado nos dados: 0 leads de outras imobiliárias. A view herda esse filtro.

### 4.1 Venda / descarte = evento no mês (checkpoint)

```sql
-- Vendas do mês (CRM) — data_evento ja corrigida (entrada na venda)
WHERE tipo_evento = 'venda'
  AND CAST(data_evento AS DATE) BETWEEN :inicio AND :fim
```

No CV, o `data_cad` da linha “Venda Realizada” costuma ser a **saída** da venda. A view corrige: `data_evento` = data da etapa anterior (entrada). Se o lead volta ao fluxo, `data_saida_venda` marca o reset e sobe `n_ciclo_lead`.

Ex. 4632: vendeu em **jan/2025**; em **02/07/2026** resetou o ciclo; em **07/07/2026** descartou — não conta venda em jul/2026.
### 4.2 Lead “vivo” no período (ciclo aberto atual)

```sql
data_inicio_ciclo::DATE <= :fim
AND (data_desfecho IS NULL OR data_desfecho::DATE >= :inicio)
```

- `data_inicio_ciclo` = início do **ciclo aberto** (após último checkpoint, ou cadastro/reativação).
- `data_desfecho` só preenche se `situacao_atual` ainda é venda/descartado; se voltou ao fluxo, fica `em_aberto`.

### 4.3 Etapas intermediárias (Leads → Com reserva)

```sql
flag_etapa_fluxo = TRUE          -- ignora linhas de venda/descarte
AND flag_no_ciclo_atual = TRUE   -- só o ciclo depois do último checkpoint
AND data_entrada_etapa::DATE <= :fim
```

Mapeie `situacao_etapa` para as etapas 1–5. **Não** use max-stage incluindo `venda realizada` — venda entra só via §4.1.

### 4.4 Mapa de situação → etapa do funil

| Situação (lower/trim) | Etapa do funil |
|---|---|
| aguardando atendimento, qualificação, descoberta, novo… | Leads |
| em atendimento, atendimento futuro | Em atendimento |
| visita agendada | Visita agendada |
| visita realizada, atendimento pos/pós visita | Visita realizada |
| pre cadastro*, em pré-cadastro, com reserva | Com reserva |
| *(checkpoint)* venda realizada | **não** mapear aqui — usar `tipo_evento = 'venda'` |
| *(checkpoint)* descartado | **não** mapear como etapa de fluxo |

Ordem cumulativa das etapas de fluxo: Leads → … → Com reserva.  
**Venda realizada** é contagem à parte (evento).

### 4.5 Descartados

Contar no mês do evento (`tipo_evento = 'descarte'`). No fluxo intermediário, descartado **não** vira “Venda realizada” e não classifica etapa de funil (`flag_etapa_fluxo = false`).

### 4.6 Esboço SQL

```sql
-- 1) Vendas-evento no mês
SELECT COUNT(DISTINCT idlead) AS venda_realizada
FROM informacoes_consolidadas.cv_leads_workflow_historico_situacao
WHERE tipo_evento = 'venda'
  AND CAST(data_evento AS DATE) BETWEEN :inicio AND :fim
  AND COALESCE(NULLIF(TRIM(corretor_consolidado), ''), '—')
      NOT IN (/* CORRETORES_REMOVIDOS */);

-- 2) Etapas de fluxo (ciclo atual), cumulativo sem checkpoint
WITH vivos AS (
  SELECT DISTINCT idlead
  FROM informacoes_consolidadas.cv_leads_workflow_historico_situacao
  WHERE CAST(data_inicio_ciclo AS DATE) <= :fim
    AND (data_desfecho IS NULL OR CAST(data_desfecho AS DATE) >= :inicio)
),
por_lead AS (
  SELECT h.idlead, MAX(/* idx 1..5 via mapa, só flag_etapa_fluxo */) AS idx
  FROM informacoes_consolidadas.cv_leads_workflow_historico_situacao h
  JOIN vivos v USING (idlead)
  WHERE h.flag_etapa_fluxo AND h.flag_no_ciclo_atual
    AND CAST(h.data_entrada_etapa AS DATE) <= :fim
  GROUP BY h.idlead
)
SELECT ...;
```

No `prati-dashboard` (`funnel.py`):

- etapas 1–5: `flag_etapa_fluxo` + `flag_no_ciclo_atual`
- etapa 6: `tipo_evento = 'venda'` + `data_evento` no período (ou Sienge HOUSE)
---

## 5. Colunas: o que usar para quê

### Ciclo / tempo (obrigatórias no funil)

| Coluna | O que faz |
|---|---|
| `idlead` | ID do lead |
| `n_etapa` | Ordem da passagem na trilha |
| `situacao_etapa` | Situação daquela passagem |
| `origem_etapa` | `workflow` ou `cv_leads` (linha sintética) |
| `data_entrada_etapa` | Quando entrou na etapa |
| `data_saida_etapa` | Quando saiu (próxima etapa ou desfecho) |
| `flag_etapa_final` | Última linha da trilha |
| `data_inicio_ciclo` | Início do ciclo atual (reativação ou cadastro) |
| `data_desfecho` | Fim do ciclo (venda/descarte); NULL se aberto |
| `tipo_desfecho` | `venda` / `descartado` / `em_aberto` |
| `flag_no_ciclo_atual` | Etapa pertence ao ciclo pós-reativação |
| `data_consolidada` | Na view = desfecho se houver, senão data da etapa — **não** é o legado de `cv_leads` |
| `data_consolidada_legado` | Cópia do `data_consolidada` antigo de `cv_leads` (só auditoria) |

### Atributos para filtro / RLS / cards

| Coluna | O que faz |
|---|---|
| `corretor_consolidado` | RLS e filtro de corretor (mesmo campo do visual) |
| `Imobiliaria` | Filtro imobiliária |
| `situacao_atual` | Situação atual do lead (snapshot) |
| `nome_situacao_anterior_lead` | Situação anterior (útil em descarte) |
| `midia_consolidada` | Mídia |
| `tags` / `status_*` | Flags auxiliares (venda/reserva/visita…) |

### Empreendimento (ajuste recente no ETL)

| Coluna | Usar? | Motivo |
|---|---|---|
| `empreendimento_consolidado` | **Sim** (rótulo) | `ultimo` → `empreendimento` → `primeiro` |
| `enterprise_id` | **Sim** (join/filtro) | = `codigointerno_empreendimento`; casa com `dim_empreendimentos_dinamica.enterpriseId` |
| `codigointerno_empreendimento` | Sim (igual `enterprise_id`) | Chave canônica no ecossistema Prati |
| `idempreendimento*` / `idempreendimento_consolidado` | Não para join com dim | São IDs **internos do CV** (ex.: Villa Bella I = CV `6`, dim `29`) |

Cobertura aproximada (após carga):

- nome consolidado ~30% geral / ~88% fora de Descartado;
- `enterprise_id` com match ~100% na dim quando preenchido.

Join recomendado:

```sql
LEFT JOIN informacoes_consolidadas.dim_empreendimentos_dinamica d
  ON h.enterprise_id = d.enterpriseId
```

---

## 6. O que ainda pode usar `cv_leads`

Use `reservas.cv_leads` quando precisar apenas do **snapshot atual** do lead (1 linha), sem trilha temporal — por exemplo:

- listagem cadastral;
- campos dinâmicos `campo_*`;
- auditoria de `ultima_data_conversao` / `data_ultima_alteracao`.

Para funil, ranking por período, “quantos leads ativos no mês”, “quem chegou em reserva em março”: use a **view de histórico**.

---

## 7. Checklist de migração no visual (Claude / prati-dashboard)

1. Trocar fonte `reservas.main.cv_leads` → `informacoes_consolidadas.cv_leads_workflow_historico_situacao`.
2. Remover filtro exclusivo em `data_consolidada` (legado).
3. Implementar “vivo no período” com `data_inicio_ciclo` / `data_desfecho` do **ciclo aberto**.
4. Etapas 1–5: `flag_etapa_fluxo` + `flag_no_ciclo_atual` + mapa §4.4 + cumulativo.
5. Etapa **Venda realizada**: `tipo_evento = 'venda'` e `data_evento` no período — **ou** Sienge HOUSE no card/ponta (escolha explícita).
6. Descarte: `tipo_evento = 'descarte'` + `data_evento` no período (se a tela mostrar).
7. Manter exclusão de `CORRETORES_REMOVIDOS` e RLS em `corretor_consolidado`.
8. Filtrar empreendimento por `enterprise_id` quando houver.
9. Agregar com `COUNT(DISTINCT idlead)`.
10. Validar: venda de junho **não** aparece em julho; lead que voltou após venda conta só nas etapas do ciclo novo.
---

## 8. Ajustes já feitos na esteira (referência)

- ETL `scripts/cv_leads_api.py`: novos campos de empreendimento + `enterprise_id`.
- View `cv_leads_workflow_historico_situacao` no MotherDuck, com ciclo/desfecho/etapas sintéticas.
- Commit em `main`: `c8df3af` (`feat(cv-leads): mapear empreendimento com IDs e enterprise_id`), além do ajuste anterior de `data_consolidada` em `cv_leads` (`cd862c0`) — este último **não** resolve o funil; a view sim.

---

## 9. Anti-padrões (não fazer)

- Contar funil com `WHERE data_consolidada BETWEEN ...` em `cv_leads`.
- Usar `ultima_data_conversao` como data de mudança de situação.
- Join de empreendimento com `idempreendimento` do CV contra `dim.enterpriseId`.
- Somar linhas da view sem `DISTINCT idlead` (infla o número: várias etapas por lead).
- Tratar `data_consolidada` da view como se fosse o campo legado de `cv_leads`.
- Esperar que “Venda realizada” do CRM bata sozinha com o card Sienge — alinhar a ponta ao ERP se a meta for o número oficial.
- Contar venda via max-stage de ciclo antigo — use `tipo_evento` + `data_evento` no mês.