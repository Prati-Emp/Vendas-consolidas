# 02 — Regras de negócio (Vendas / Comercial)

Regras aplicadas pelo Streamlit. A IA deve seguir estas definições para reproduzir os números do dashboard.

## 1. Fonte oficial de vendas realizadas

- Tabela: `informacoes_consolidadas.sienge_vendas_consolidadas`
- Valor monetário: coluna `value`
- Data de referência: `contractDate` (não usar `issueDate` como padrão do dashboard Vendas)
- Sempre filtrar `value IS NOT NULL`

Filtro de período (igual ao Streamlit):

```sql
contractDate BETWEEN 'YYYY-MM-DD' AND 'YYYY-MM-DD'
```

## 2. Permuta de unidade

Na definição da view `sienge_vendas_consolidadas`, registros com

```sql
Tipo_venda_consolidada = 'Permuta de Unidade'
```

já são **excluídos**. Não há filtro adicional necessário no dashboard; se consultar a view, a permuta já não entra.

## 3. House (interna) vs externa

Classificação pela coluna `imobiliaria`:

```text
Se UPPER(imobiliaria) contém 'PRATI' → Venda Interna (House / Prati)
Senão → Venda Externa (Imobiliárias)
```

Taxa House no dashboard é calculada por **valor** (`SUM(value)`), não por quantidade.

Metas House vs externas usam tabelas separadas:

- Interna → `metas_vendas_internas`
- Externa → `metas_vendas_externas`
- Meta geral → `meta_vendas`

## 4. Metas

- Layout wide: uma linha por empreendimento; meses em colunas `jan/25`, `fev/25`, … / `jan/26`, …
- Nome da coluna de empreendimento na view: `"Empreendiemento"` (grafia histórica com typo)
- Código: `"Codigo empreendimento"`
- Para atingir o % de meta: `realizado / meta`, com realizado vindo de `sienge_vendas_consolidadas`
- `metas_vendas_internas` e `metas_vendas_externas` atualmente têm apenas colunas de **2026**

## 5. Dimensões de análise em vendas

Filtros comuns do dashboard (todos opcionais):

- `nome_empreendimento`
- `midia`
- `tipovenda`
- `corretor`
- `imobiliaria`

Nulos/vazios de imobiliária/corretor são tratados como `'—'` no Streamlit.

## 6. VPL

Na análise de corretor/imobiliária:

- Considerar linhas com `vpl_reserva` e `vpl_tabela` não nulos e ≠ 0
- `% VPL ≈ (vpl_reserva / vpl_tabela) - 1`
- Na view `sienge_vendas_consolidadas`, se `vpl_tabela` vier NULL ou 0, a própria view já substitui por `vpl_reserva` (`COALESCE(NULLIF(vpl_tabela, 0), vpl_reserva)`)

## 7. Times e grupos de imobiliária

Colunas enriquecidas em `sienge_vendas_consolidadas`:

| Coluna | Significado |
|---|---|
| `idtime` / `time` | Time da imobiliária (API CV Times) |
| `id_imobiliaria_grupo` / `imobiliaria_grupo` | Grupo da planilha de metas externas |

Join de negócio:

```text
idimobiliaria → cv_times → idtime = id_imobiliaria_grupo (planilha metas externas)
```

Nem toda venda tem time/grupo preenchido (LEFT JOIN).

## 8. Leads (página Leads)

- Fonte: `cv_leads_workflow_consolidado`
- Período: `CAST(Data_cad AS DATE)`
- Tempo: coluna `tempo` em **minutos** (exibir em dias/horas/minutos)
- Exige `tempo IS NOT NULL` e `Data_cad IS NOT NULL`
- Corretor consolidado: `corretor_consolidado`
- Imobiliária: `Imobiliaria` (atenção à capitalização)
- Empreendimento: `empreendimento_consolidado` + `enterprise_id`/`codigointerno_empreendimento` (join em `dim_empreendimentos_dinamica.enterpriseId`; não usar `idempreendimento` do CV)

## 9. VGV e estoque

- Fonte de unidades/valores: `cv_vgv_empreendimentos_consolidado`
- Situação da unidade: `"unidades.situacao"` (ex.: Vendida)
- Valor unidade: `"unidades.valor_total"` (quando Vendida, a view pode usar valor do CV)
- Totalizador “Geral Prati” no dashboard exclui loteamentos da agregação de incorporações (ver página Vendas_VGV)

## 10. Prosoluto antes / pós chaves

- Visão pronta: `administracao.prosoluto_antes_e_pos_chaves`
  - `periodo` ∈ (`antes_chaves`, `pos_chaves`)
  - `valor_prosoluto`, `valor_venda_financiamento`, `pct_prosoluto`
- Análise por período de vendas: usa `contas_recebidas_receber` + data fim de obra em `planilhas.data_entrega_empreendimentos_prosoluto_antes_pos_chaves` + join com `cv_vendas`

## 11. Reservas

- Fonte operacional: `reservas.reservas_abril`
- Data de cadastro típica: `data_cad`
- Valor de contrato: `valor_contrato` / `valor_contrato_com_juros`
- Não confundir “reserva” com “venda realizada Sienge”: são etapas diferentes do funil

## 12. Anti-padrões (não fazer)

- Não somar metas somando colunas de meses errados / misturando internas+externas sem pedido explícito
- Não usar `reservas_abril.valor_contrato` como substituto de `sienge_vendas_consolidadas.value` para o KPI de vendas do dashboard
- Não filtrar CR/prosoluto com a mesma regra de “venda House” sem revisar o caso
- Não assumir que `metas_vendas_externas` é só meta mensal sem grupo: a view já traz `id_imobiliaria_grupo` e `imobiliaria_grupo` da planilha. Para analisar vendas por grupo, use também as colunas em `sienge_vendas_consolidadas`.
