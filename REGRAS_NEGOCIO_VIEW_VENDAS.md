# Regras de Negócio: View Consolidada de Vendas

Este documento descreve as regras de negócio específicas aplicadas à view `informacoes_consolidadas.sienge_vendas_consolidadas`, em especial a lógica de consolidação de **Tipo de Venda** e **Filtros**.

## 1. Consolidação do Tipo de Venda

Para garantir a melhor qualidade de dados para o campo "Tipo de Venda", a view utiliza uma estratégia de consolidação que combina dados de duas fontes diferentes.

### Fontes de Dados
1.  **`reservas.cv_vendas` (Prioritária):**
    *   **Coluna:** `tipovenda`
    *   **Chave de Ligação:** `sienge_vendas_realizadas.externalId` = `cv_vendas.referencia`
    *   Esta tabela contém os dados mais precisos do CRM (CV).

2.  **`reservas.reservas_abril` (Secundária/Fallback):**
    *   **Coluna:** `tipovenda`
    *   **Chave de Ligação:** `sienge_vendas_realizadas.id` = `reservas_abril.codigointerno`
    *   Usada como backup caso a informação não seja encontrada na primeira fonte.

### Lógica de Consolidação
A coluna final `Tipo_venda_consolidada` é calculada usando a seguinte lógica de prioridade (COALESCE):

1.  Tenta buscar `tipovenda` na tabela `cv_vendas` (via `externalId`).
2.  Se não encontrar (NULL), busca `tipovenda` na tabela `reservas_abril` (via `id`).

**Snippet SQL:**
```sql
COALESCE(
    -- Prioridade 1: CV Vendas (via externalId)
    (SELECT tipovenda FROM reservas.cv_vendas WHERE referencia = CAST(s.externalId AS VARCHAR) LIMIT 1),
    -- Prioridade 2: Reservas Abril (via id)
    (SELECT tipovenda FROM reservas.reservas_abril WHERE codigointerno = CAST(s.id AS VARCHAR) LIMIT 1)
) as Tipo_venda_consolidada
```

---

## 2. Regra de Exclusão (Filtro)

Para limpar a base de dados de registros que não devem ser contabilizados como vendas efetivas para fins de análise, foi aplicada uma regra de exclusão.

### Regra
Excluir automaticamente qualquer registro onde o **Tipo de Venda Consolidado** seja identificado como **"Permuta de Unidade"**.

*   **Critério:** `Tipo_venda_consolidada != 'Permuta de Unidade'`
*   **Comportamento:** Registros com `Tipo_venda_consolidada` NULO (NULL) são **mantidos**. Apenas a string exata "Permuta de Unidade" é removida.

**Snippet SQL (Filtro Final):**
```sql
SELECT * 
FROM dados_unificados
WHERE Tipo_venda_consolidada IS NULL 
   OR Tipo_venda_consolidada != 'Permuta de Unidade'
```

---

## 3. Resumo da Estrutura das Colunas de Venda

A view disponibiliza três colunas relacionadas ao tipo de venda para permitir rastreabilidade e validação:

| Nome da Coluna | Descrição | Fonte |
| :--- | :--- | :--- |
| `tipovenda` | Dado original de legado/backup | `reservas.reservas_abril` |
| `tipovenda_cv` | Dado direto do CRM (CV) | `reservas.cv_vendas` |
| **`Tipo_venda_consolidada`** | **Coluna Oficial para Análises** | **Consolidada (CV > Abril)** |

> **Nota:** Para relatórios e dashboards, utilize sempre a coluna **`Tipo_venda_consolidada`**.

---

**Última atualização:** 31/12/2025
**Responsável:** Equipe de Dados


