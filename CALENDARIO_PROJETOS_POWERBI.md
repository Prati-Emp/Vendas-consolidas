# 📅 Calendário de Projetos - Documentação para Power BI

## 🗄️ Banco de Dados e Tabelas

### Fonte Principal
- **Banco**: `informacoes_consolidadas`
- **View/Tabela**: `Jira_status_tarefas`

### Campos Necessários da View `Jira_status_tarefas`

```sql
SELECT
    tipo_item,
    chave,
    resumo,
    responsavel,
    prioridade,
    status,
    resolucao,
    atualizado,
    data_limite,
    projeto_name,
    data_inicio_corrigida,
    data_fim_corrigida,
    data_original_inicio,
    data_original_fim,
    start_date,
    dias_para_conclusao,
    status_tarefas,
    "chamada_Para" as chamada_para,
    indice
FROM informacoes_consolidadas.Jira_status_tarefas
```

---

## 📊 Estrutura do Calendário

### 1. Tabela de Mapeamento de Subtarefas

**Query para criar a tabela de mapeamento:**

```sql
SELECT 
    COALESCE(TRIM("chamada_Para"), '') AS chamada_para,
    MIN(indice) AS indice
FROM informacoes_consolidadas.Jira_status_tarefas
WHERE "chamada_Para" IS NOT NULL 
  AND TRIM("chamada_Para") <> ''
  AND indice IS NOT NULL
GROUP BY "chamada_Para"
ORDER BY indice
```

**Campos resultantes:**
- `chamada_para`: Nome da subtarefa (ex: "02 - Alvará", "03 - Inicio do CEF")
- `indice`: Ordem de exibição das subtarefas
- `subtarefa`: Cópia de `chamada_para` (para exibição)

---

### 2. Lógica de Cálculo das Datas

#### **Data Original** (primeira previsão)
```
SE data_original_fim NÃO é NULL:
    Data Original = data_original_fim
SENÃO SE data_original_inicio NÃO é NULL:
    Data Original = data_original_inicio
SENÃO:
    Data Original = data_limite
```

#### **Data Corrigida** (data replanejada)
```
SE data_fim_corrigida NÃO é NULL:
    Data Corrigida = data_fim_corrigida
SENÃO:
    Data Corrigida = data_limite
```

---

### 3. Cálculo do Status (Cores)

```
SE Data Corrigida NÃO é NULL E Data Original NÃO é NULL:
    SE Data Corrigida <= Data Original:
        Status = "adiantado" (Verde: #065f46)
    SENÃO:
        Status = "atrasado" (Vermelho: #7f1d1d)
SENÃO:
    Status = "sem_dado" (sem cor especial)
```

---

## 🔄 Processo de Construção do Calendário

### Passo 1: Filtrar por Projeto
- Filtrar `Jira_status_tarefas` onde `projeto_name = [Projeto Selecionado]`

### Passo 2: Normalização de Texto (para matching)
- Normalizar `chamada_para` removendo acentos, convertendo para minúsculas e removendo espaços extras
- Esta normalização é usada para fazer o match entre a tabela de mapeamento e as tarefas do projeto

### Passo 3: Match entre Mapeamento e Tarefas
Para cada linha da tabela de mapeamento (ordenada por `indice`):

1. **Match Exato**: Buscar tarefa onde `chamada_para_normalizada = match_norm`
2. **Match Flexível** (fallback): Se não encontrar match exato, buscar onde `chamada_para_normalizada CONTAINS match_norm`
3. Se encontrar múltiplas tarefas, selecionar a primeira ordenada por `data_limite` (mais antiga)

### Passo 4: Construir Linha do Calendário
Para cada subtarefa encontrada:
- **Subtarefa**: Nome da subtarefa do mapeamento
- **Data Original**: Calculada conforme lógica acima
- **Data Corrigida**: Calculada conforme lógica acima
- **Status**: Calculado conforme lógica acima

---

## 📋 Estrutura da Tabela Final

| Subtarefa | Data Original | Data Corrigida | Status |
|-----------|--------------|----------------|--------|
| 02 - Alvará | 26/03/2026 | 29/03/2026 | atrasado |
| 03 - Inicio do CEF | 09/01/2026 | 04/03/2026 | atrasado |
| ... | ... | ... | ... |

---

## 🎨 Formatação Visual (Power BI)

### Cores de Fundo das Colunas de Data

**Quando Status = "adiantado":**
- Cor de fundo: `#065f46` (Verde escuro)
- Cor do texto: `white`
- Estilo: `bold`

**Quando Status = "atrasado":**
- Cor de fundo: `#7f1d1d` (Vermelho escuro)
- Cor do texto: `white`
- Estilo: `bold`

**Quando Status = "sem_dado":**
- Sem formatação especial

### Legenda
```
"Data Original = primeira previsão | Verde = dentro do prazo | Vermelho = replanejado após a data original"
```

---

## 📐 Medidas DAX Sugeridas (Power BI)

### Medida: Data Original Calculada
```dax
Data Original = 
VAR DataOriginalFim = SELECTEDVALUE('Jira_status_tarefas'[data_original_fim])
VAR DataOriginalInicio = SELECTEDVALUE('Jira_status_tarefas'[data_original_inicio])
VAR DataLimite = SELECTEDVALUE('Jira_status_tarefas'[data_limite])
RETURN
    IF(
        NOT ISBLANK(DataOriginalFim),
        DataOriginalFim,
        IF(
            NOT ISBLANK(DataOriginalInicio),
            DataOriginalInicio,
            DataLimite
        )
    )
```

### Medida: Data Corrigida Calculada
```dax
Data Corrigida = 
VAR DataFimCorrigida = SELECTEDVALUE('Jira_status_tarefas'[data_fim_corrigida])
VAR DataLimite = SELECTEDVALUE('Jira_status_tarefas'[data_limite])
RETURN
    IF(
        NOT ISBLANK(DataFimCorrigida),
        DataFimCorrigida,
        DataLimite
    )
```

### Medida: Status do Calendário
```dax
Status Calendário = 
VAR DataOriginal = [Data Original]
VAR DataCorrigida = [Data Corrigida]
RETURN
    IF(
        NOT ISBLANK(DataOriginal) && NOT ISBLANK(DataCorrigida),
        IF(
            DataCorrigida <= DataOriginal,
            "adiantado",
            "atrasado"
        ),
        "sem_dado"
    )
```

### Coluna Calculada: Chamada Para Normalizada
```dax
chamada_para_norm = 
LOWER(
    TRIM(
        SUBSTITUTE(
            SUBSTITUTE(
                SUBSTITUTE(
                    SUBSTITUTE(
                        SUBSTITUTE(
                            SUBSTITUTE(
                                SUBSTITUTE(
                                    SUBSTITUTE(
                                        SUBSTITUTE(
                                            'Jira_status_tarefas'[chamada_Para],
                                            "á", "a"
                                        ),
                                        "é", "e"
                                    ),
                                    "í", "i"
                                ),
                                "ó", "o"
                            ),
                            "ú", "u"
                        ),
                        "ã", "a"
                    ),
                    "õ", "o"
                ),
                "ç", "c"
            )
        )
    )
)
```

---

## 🔗 Relacionamentos Necessários

1. **Tabela de Mapeamento** ↔ **Jira_status_tarefas**
   - Relacionamento: Many-to-One
   - Campo de match: `chamada_para` (normalizado) ↔ `chamada_Para` (normalizado)
   - Tipo: Não ativo (usar em cálculos específicos)

---

## 📝 Observações Importantes

1. **Normalização de Texto**: O matching é feito com texto normalizado (sem acentos, minúsculas). No Power BI, você pode usar funções DAX para remover acentos ou criar uma tabela de mapeamento auxiliar.

2. **Ordenação**: As subtarefas devem ser ordenadas pelo campo `indice` da tabela de mapeamento.

3. **Filtros Aplicados**: O calendário pode ser filtrado pelos mesmos filtros do dashboard (Status, Projetos, Tipo de Item, Responsáveis, Prioridade).

4. **Múltiplas Tarefas**: Se uma subtarefa aparecer múltiplas vezes no projeto, selecionar a primeira ordenada por `data_limite` (mais antiga).

5. **Campos de Data**: Todos os campos de data devem ser do tipo `Date` ou `DateTime` no Power BI.

---

## 🚀 Passos para Implementação no Power BI

1. **Conectar ao MotherDuck** e importar a view `Jira_status_tarefas`
2. **Criar tabela de mapeamento** usando a query SQL fornecida acima
3. **Criar colunas calculadas** para normalização de texto
4. **Criar medidas DAX** para Data Original, Data Corrigida e Status
5. **Criar tabela visual** com as colunas: Subtarefa, Data Original, Data Corrigida
6. **Aplicar formatação condicional** nas colunas de data baseado no Status
7. **Adicionar filtro de projeto** (slicer ou filtro de página)
8. **Ordenar por índice** da tabela de mapeamento

---

## 📌 Exemplo de Query Completa (para validação)

```sql
-- Exemplo de como obter os dados do calendário para um projeto específico
WITH Mapeamento AS (
    SELECT 
        COALESCE(TRIM("chamada_Para"), '') AS chamada_para,
        MIN(indice) AS indice
    FROM informacoes_consolidadas.Jira_status_tarefas
    WHERE "chamada_Para" IS NOT NULL 
      AND TRIM("chamada_Para") <> ''
      AND indice IS NOT NULL
    GROUP BY "chamada_Para"
),
TarefasProjeto AS (
    SELECT *
    FROM informacoes_consolidadas.Jira_status_tarefas
    WHERE projeto_name = 'Arcangelo'  -- Substituir pelo projeto desejado
)
SELECT 
    m.chamada_para AS Subtarefa,
    m.indice,
    COALESCE(
        tp.data_original_fim,
        tp.data_original_inicio,
        tp.data_limite
    ) AS Data_Original,
    COALESCE(
        tp.data_fim_corrigida,
        tp.data_limite
    ) AS Data_Corrigida,
    CASE 
        WHEN COALESCE(tp.data_fim_corrigida, tp.data_limite) IS NOT NULL 
         AND COALESCE(tp.data_original_fim, tp.data_original_inicio, tp.data_limite) IS NOT NULL
        THEN 
            CASE 
                WHEN COALESCE(tp.data_fim_corrigida, tp.data_limite) <= 
                     COALESCE(tp.data_original_fim, tp.data_original_inicio, tp.data_limite)
                THEN 'adiantado'
                ELSE 'atrasado'
            END
        ELSE 'sem_dado'
    END AS Status
FROM Mapeamento m
LEFT JOIN TarefasProjeto tp 
    ON LOWER(TRIM(tp."chamada_Para")) = LOWER(TRIM(m.chamada_para))
ORDER BY m.indice
```

---

**Última atualização**: 2026-01-29
