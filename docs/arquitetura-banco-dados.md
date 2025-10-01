# Arquitetura do Banco de Dados Consolidado

## 🏗️ Estrutura do Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                    MOTHERDUCK DATABASE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────────────────────────┐  │
│  │   BANCO:        │    │        BANCO:                      │  │
│  │   reservas      │    │   informacoes_consolidadas         │  │
│  │   (Dados Brutos)│    │   (Dados Tratados)                 │  │
│  └─────────────────┘    └─────────────────────────────────────┘  │
│           │                              │                     │
│           │                              │                     │
│  ┌────────▼────────┐              ┌─────▼─────────────┐      │
│  │ TABELAS BASE:   │              │ VIEWS DINÂMICAS:  │      │
│  │                 │              │                   │      │
│  │ • reservas_abril│              │ • sienge_vendas_  │      │
│  │ • sienge_vendas_│              │   consolidadas    │      │
│  │   realizadas    │              │                   │      │
│  │ • sienge_vendas_│              │                   │      │
│  │   canceladas    │              │                   │      │
│  └─────────────────┘              └───────────────────┘      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🔄 Fluxo de Dados

### 1. Fontes de Dados Originais
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   RESERVAS      │    │   SIENGE       │    │   SIENGE       │
│   (Vera Cruz)   │    │   REALIZADAS   │    │   CANCELADAS   │
│                 │    │                │    │                │
│ • Mútuo         │    │ • Vendas       │    │ • Canceladas   │
│ • Corretor      │    │ • Clientes     │    │ • Clientes     │
│ • Imobiliária   │    │ • Brokers      │    │ • Brokers      │
│ • Demográficos  │    │ • Valores      │    │ • Valores      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   VIEW CONSOLIDADA      │
                    │   sienge_vendas_        │
                    │   consolidadas          │
                    │                         │
                    │ • UNION ALL das 3       │
                    │   fontes                │
                    │ • Padronização de       │
                    │   campos                │
                    │ • Mapeamento de IDs     │
                    │ • Tratamento de nulos   │
                    └─────────────────────────┘
```

## 📊 Estrutura da View Consolidada

### Campos Padronizados:
```
┌─────────────────────────────────────────────────────────────────┐
│                    CAMPOS PRINCIPAIS                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  IDENTIFICAÇÃO:                                                 │
│  • enterpriseId (INTEGER)                                      │
│  • nome_empreendimento (TEXT)                                  │
│                                                                 │
│  VALORES:                                                      │
│  • value (DECIMAL)                                             │
│  • issueDate (DATE)                                            │
│  • contractDate (DATE)                                         │
│                                                                 │
│  ORIGEM:                                                       │
│  • origem (TEXT) - 'Sienge Realizada'/'Sienge Cancelada'/'Reserva' │
│                                                                 │
│  COMERCIAL:                                                    │
│  • corretor (TEXT)                                             │
│  • imobiliaria (TEXT)                                          │
│                                                                 │
│  CLIENTE:                                                      │
│  • cliente (TEXT)                                              │
│  • email (TEXT)                                                │
│  • cidade (TEXT)                                               │
│  • documento_cliente (TEXT)                                     │
│                                                                 │
│  DEMOGRÁFICOS:                                                 │
│  • sexo (TEXT)                                                 │
│  • idade (INTEGER)                                             │
│  • estado_civil (TEXT)                                         │
│  • renda (DECIMAL)                                             │
│                                                                 │
│  PROPRIEDADE:                                                  │
│  • bloco (TEXT)                                                │
│  • unidade (TEXT)                                              │
│  • etapa (TEXT)                                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🔧 Lógica de Consolidação

### 1. Seção Sienge Realizadas
```sql
-- Mapeamento de campos Sienge → Consolidado
s.enterpriseId → enterpriseId
s.value → value
s.issueDate → issueDate
s.contractDate → contractDate
'Sienge Realizada' → origem
s.brokers[1].name → corretor
s.customers[1].name → cliente
```

### 2. Seção Sienge Canceladas
```sql
-- Mesma estrutura da seção anterior
-- Diferença: origem = 'Sienge Cancelada'
```

### 3. Seção Reservas Vera Cruz
```sql
-- Mapeamento de campos Reservas → Consolidado
r.enterpriseId → enterpriseId
r.value → value
r.issueDate → issueDate
r.contractDate → contractDate
r.origem → origem
r.corretor → corretor
r.imobiliaria → imobiliaria
```

## 🎯 Benefícios da Arquitetura

### 1. Separação de Responsabilidades
- **reservas:** Dados brutos e originais
- **informacoes_consolidadas:** Dados tratados e analíticos

### 2. Views Dinâmicas
- ✅ Atualização automática
- ✅ Sem necessidade de reprocessamento
- ✅ Sempre reflete dados atuais

### 3. Consolidação Inteligente
- ✅ UNION ALL de múltiplas fontes
- ✅ Padronização de campos
- ✅ Tratamento de inconsistências

### 4. Escalabilidade
- ✅ Fácil adição de novos empreendimentos
- ✅ Estrutura preparada para crescimento
- ✅ Manutenção simplificada

## 📈 Análises Suportadas

### 1. Análise Temporal
```sql
-- Vendas por período
SELECT 
    EXTRACT(YEAR FROM contractDate) as ano,
    EXTRACT(MONTH FROM contractDate) as mes,
    COUNT(*) as total_vendas,
    SUM(value) as valor_total
FROM informacoes_consolidadas.sienge_vendas_consolidadas
GROUP BY ano, mes
ORDER BY ano, mes;
```

### 2. Análise por Empreendimento
```sql
-- Performance por empreendimento
SELECT 
    enterpriseId,
    nome_empreendimento,
    COUNT(*) as total_vendas,
    SUM(value) as valor_total,
    AVG(value) as valor_medio
FROM informacoes_consolidadas.sienge_vendas_consolidadas
GROUP BY enterpriseId, nome_empreendimento
ORDER BY valor_total DESC;
```

### 3. Análise por Origem
```sql
-- Comparação Sienge vs Reservas
SELECT 
    origem,
    COUNT(*) as total_vendas,
    SUM(value) as valor_total,
    AVG(value) as valor_medio
FROM informacoes_consolidadas.sienge_vendas_consolidadas
GROUP BY origem
ORDER BY valor_total DESC;
```

### 4. Análise Comercial
```sql
-- Performance por corretor/imobiliária
SELECT 
    corretor,
    imobiliaria,
    COUNT(*) as total_vendas,
    SUM(value) as valor_total
FROM informacoes_consolidadas.sienge_vendas_consolidadas
GROUP BY corretor, imobiliaria
ORDER BY valor_total DESC;
```

## 🚀 Próximos Passos

### 1. Expansão
- Adicionar novos empreendimentos
- Implementar views específicas por região
- Criar views de performance detalhada

### 2. Otimização
- Implementar índices para performance
- Criar views materializadas
- Implementar cache inteligente

### 3. Monitoramento
- Alertas para inconsistências
- Relatórios de qualidade
- Dashboard de performance

## 📝 Conclusão

A arquitetura implementada proporciona:

1. **Consolidação Completa:** Todos os dados de vendas em uma única fonte
2. **Atualização Automática:** Views dinâmicas sempre atualizadas
3. **Análise Unificada:** Dados de múltiplas fontes padronizados
4. **Escalabilidade:** Estrutura preparada para crescimento
5. **Manutenibilidade:** Separação clara de responsabilidades

O sistema está pronto para suportar análises avançadas e tomada de decisões baseadas em dados consolidados e confiáveis.
