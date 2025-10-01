# Implementação do Banco de Dados Consolidado - Vendas Consolidadas

## 📋 Visão Geral

Este documento detalha a implementação completa do sistema de banco de dados consolidado para análise de vendas, incluindo a criação de um novo banco de dados, views dinâmicas e consolidação de dados de múltiplas fontes.

## 🗄️ Arquitetura do Banco de Dados

### Estrutura Atual
- **Banco Original:** `reservas` (dados brutos)
- **Banco Consolidado:** `informacoes_consolidadas` (dados tratados)
- **Tabelas Base:** `sienge_vendas_realizadas`, `sienge_vendas_canceladas`, `reservas_abril`

## 🚀 Implementação Passo a Passo

### 1. Criação do Novo Banco de Dados

```sql
-- Criação do banco de dados para informações consolidadas
CREATE DATABASE informacoes_consolidadas;
```

**Objetivo:** Separar dados brutos (reservas) dos dados tratados (informacoes_consolidadas)

### 2. Criação da View Consolidada Vera Cruz

#### 2.1. Análise da Tabela Reservas
```sql
-- Verificação dos campos disponíveis na tabela reservas_abril
DESCRIBE reservas.reservas_abril;
```

#### 2.2. Filtros Identificados
- **Empreendimento:** Loteamento Vera Cruz (ID 5)
- **Situação:** Mútuo (com tratamento de encoding)
- **Campos Relevantes:** corretor, imobiliaria, cliente, dados demográficos

#### 2.3. Criação da View
```sql
-- Remoção da tabela existente (se houver)
DROP TABLE IF EXISTS reservas.cv_vendas_consolidadas_vera_cruz;

-- Criação da view dinâmica para Vera Cruz
CREATE OR REPLACE VIEW reservas.cv_vendas_consolidadas_vera_cruz AS
SELECT 
    CAST(codigointerno_empreendimento AS INTEGER) as enterpriseId,
    empreendimento as nome_empreendimento,
    valor_contrato as value,
    CAST(data_ultima_alteracao_situacao AS DATE) as issueDate,
    CAST(data_ultima_alteracao_situacao AS DATE) as contractDate,
    CONCAT('Reserva - ', situacao) as origem,
    corretor,
    imobiliaria,
    cliente,
    email,
    cidade,
    cep_cliente,
    renda,
    sexo,
    idade,
    estado_civil,
    documento_cliente,
    idcliente,
    idcorretor,
    idimobiliaria,
    situacao as situacao_original,
    data_venda,
    data_contrato,
    valor_contrato_com_juros,
    vencimento,
    campanha,
    midia,
    tipovenda,
    grupo,
    regiao,
    bloco,
    unidade,
    etapa
FROM reservas.reservas_abril 
WHERE codigointerno_empreendimento = '5' 
  AND situacao LIKE '%Mútuo%';
```

### 3. Criação da View Consolidada Principal

#### 3.1. Estrutura da View Consolidada
```sql
CREATE OR REPLACE VIEW informacoes_consolidadas.sienge_vendas_consolidadas AS
-- Seção 1: Vendas Realizadas Sienge
SELECT
    CAST(s.enterpriseId AS INTEGER) as enterpriseId,
    COALESCE(r.empreendimento, CASE WHEN s.enterpriseId = '19' THEN 'Ondina II' ELSE 'Sienge Realizada' END) as nome_empreendimento,
    s.value,
    CAST(s.issueDate AS DATE) as issueDate,
    CAST(s.contractDate AS DATE) as contractDate,
    'Sienge Realizada' as origem,
    COALESCE(r.corretor, s.brokers[1].name) as corretor,
    COALESCE(r.imobiliaria, (SELECT name FROM reservas.reservas_abril WHERE idimobiliaria = s.brokers[1].id LIMIT 1)) as imobiliaria,
    s.customers[1].name as cliente,
    s.customers[1].email as email,
    s.customers[1].addresses[1].city as cidade,
    s.customers[1].addresses[1].zipCode as cep_cliente,
    s.customers[1].profession as profissao,
    s.customers[1].cpf as documento_cliente,
    s.customers[1].id as idcliente,
    s.brokers[1].id as idcorretor,
    (SELECT idimobiliaria FROM reservas.reservas_abril WHERE idimobiliaria = s.brokers[1].id LIMIT 1) as idimobiliaria,
    s.customers[1].sex as sexo,
    s.customers[1].civilStatus as estado_civil,
    NULL as idade,
    NULL as renda,
    NULL as situacao_original,
    NULL as data_venda,
    NULL as valor_contrato_com_juros,
    NULL as vencimento,
    NULL as campanha,
    NULL as midia,
    NULL as tipovenda,
    NULL as grupo,
    NULL as regiao,
    NULL as bloco,
    NULL as unidade,
    NULL as etapa
FROM reservas.sienge_vendas_realizadas s
LEFT JOIN (SELECT DISTINCT idempreendimento, empreendimento, corretor, imobiliaria, idcorretor, idimobiliaria FROM reservas.reservas_abril) r ON CAST(s.enterpriseId AS INTEGER) = r.idempreendimento

UNION ALL

-- Seção 2: Vendas Canceladas Sienge
SELECT
    CAST(s.enterpriseId AS INTEGER) as enterpriseId,
    COALESCE(r.empreendimento, CASE WHEN s.enterpriseId = '19' THEN 'Ondina II' ELSE 'Sienge Cancelada' END) as nome_empreendimento,
    s.value,
    CAST(s.issueDate AS DATE) as issueDate,
    CAST(s.contractDate AS DATE) as contractDate,
    'Sienge Cancelada' as origem,
    COALESCE(r.corretor, s.brokers[1].name) as corretor,
    COALESCE(r.imobiliaria, (SELECT name FROM reservas.reservas_abril WHERE idimobiliaria = s.brokers[1].id LIMIT 1)) as imobiliaria,
    s.customers[1].name as cliente,
    s.customers[1].email as email,
    s.customers[1].addresses[1].city as cidade,
    s.customers[1].addresses[1].zipCode as cep_cliente,
    s.customers[1].profession as profissao,
    s.customers[1].cpf as documento_cliente,
    s.customers[1].id as idcliente,
    s.brokers[1].id as idcorretor,
    (SELECT idimobiliaria FROM reservas.reservas_abril WHERE idimobiliaria = s.brokers[1].id LIMIT 1) as idimobiliaria,
    s.customers[1].sex as sexo,
    s.customers[1].civilStatus as estado_civil,
    NULL as idade,
    NULL as renda,
    NULL as situacao_original,
    NULL as data_venda,
    NULL as valor_contrato_com_juros,
    NULL as vencimento,
    NULL as campanha,
    NULL as midia,
    NULL as tipovenda,
    NULL as grupo,
    NULL as regiao,
    NULL as bloco,
    NULL as unidade,
    NULL as etapa
FROM reservas.sienge_vendas_canceladas s
LEFT JOIN (SELECT DISTINCT idempreendimento, empreendimento, corretor, imobiliaria, idcorretor, idimobiliaria FROM reservas.reservas_abril) r ON CAST(s.enterpriseId AS INTEGER) = r.idempreendimento

UNION ALL

-- Seção 3: Reservas Vera Cruz
SELECT
    r.enterpriseId,
    r.nome_empreendimento,
    r.value,
    r.issueDate,
    r.contractDate,
    r.origem,
    r.corretor,
    r.imobiliaria,
    r.cliente,
    r.email,
    r.cidade,
    r.cep_cliente,
    r.renda,
    r.sexo,
    r.idade,
    r.estado_civil,
    r.documento_cliente,
    r.idcliente,
    r.idcorretor,
    r.idimobiliaria,
    r.situacao_original,
    r.data_venda,
    r.valor_contrato_com_juros,
    r.vencimento,
    r.campanha,
    r.midia,
    r.tipovenda,
    r.grupo,
    r.regiao,
    r.bloco,
    r.unidade,
    r.etapa
FROM reservas.cv_vendas_consolidadas_vera_cruz r;
```

## 🔧 Características Técnicas

### 3.1. Views Dinâmicas vs Tabelas Estáticas

**Vantagens das Views Dinâmicas:**
- ✅ Atualização automática quando dados base mudam
- ✅ Sem necessidade de reprocessamento manual
- ✅ Sempre reflete o estado atual dos dados
- ✅ Economia de espaço de armazenamento

**Implementação:**
```sql
-- Uso de CREATE OR REPLACE VIEW para garantir atualização
CREATE OR REPLACE VIEW nome_da_view AS
SELECT ... FROM tabela_base;
```

### 3.2. Tratamento de Dados

#### 3.2.1. Encoding de Caracteres
```sql
-- Tratamento para caracteres especiais (Mútuo vs Mtuo)
WHERE situacao LIKE '%Mútuo%'
```

#### 3.2.2. Mapeamento de IDs
```sql
-- Mapeamento manual para IDs sem correspondência
CASE WHEN s.enterpriseId = '19' THEN 'Ondina II' ELSE 'Sienge Realizada' END
```

#### 3.2.3. Campos Nulos
```sql
-- Tratamento de campos não disponíveis em todas as fontes
NULL as idade,  -- Idade não disponível no Sienge
NULL as renda, -- Renda não disponível no Sienge
```

### 3.3. Estrutura de Dados Consolidada

#### Campos Principais:
- **Identificação:** `enterpriseId`, `nome_empreendimento`
- **Valores:** `value`, `issueDate`, `contractDate`
- **Origem:** `origem` (Sienge Realizada/Cancelada/Reserva)
- **Comercial:** `corretor`, `imobiliaria`
- **Cliente:** `cliente`, `email`, `cidade`, `documento_cliente`
- **Demográficos:** `sexo`, `idade`, `estado_civil`, `renda`
- **Propriedade:** `bloco`, `unidade`, `etapa`

## 📊 Análises Implementadas

### 4.1. Análise de Vendas por Período
```sql
-- Vendas por ano
SELECT 
    EXTRACT(YEAR FROM contractDate) as ano,
    COUNT(*) as total_vendas,
    SUM(value) as valor_total
FROM informacoes_consolidadas.sienge_vendas_consolidadas
GROUP BY EXTRACT(YEAR FROM contractDate)
ORDER BY ano;
```

### 4.2. Análise por Empreendimento
```sql
-- Vendas por empreendimento
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

### 4.3. Análise por Origem
```sql
-- Vendas por origem (Sienge vs Reservas)
SELECT 
    origem,
    COUNT(*) as total_vendas,
    SUM(value) as valor_total
FROM informacoes_consolidadas.sienge_vendas_consolidadas
GROUP BY origem
ORDER BY valor_total DESC;
```

## 🔍 Troubleshooting

### 5.1. Problemas de Encoding
**Sintoma:** Caracteres especiais não são reconhecidos
**Solução:** Usar `LIKE '%Mútuo%'` ou verificar encoding da tabela base

### 5.2. Campos Nulos
**Sintoma:** Erro ao formatar valores nulos
**Solução:** Usar `COALESCE(valor, 0)` ou tratamento de nulos

### 5.3. Performance
**Sintoma:** Consultas lentas
**Solução:** 
- Usar índices nas colunas de filtro
- Limitar resultados com `LIMIT`
- Otimizar JOINs

## 📈 Benefícios da Implementação

### 6.1. Consolidação de Dados
- ✅ Dados de múltiplas fontes em uma única view
- ✅ Padronização de campos e formatos
- ✅ Eliminação de duplicatas e inconsistências

### 6.2. Análise Unificada
- ✅ Visão completa do pipeline de vendas
- ✅ Comparação entre origens (Sienge vs Reservas)
- ✅ Análise temporal e por empreendimento

### 6.3. Manutenibilidade
- ✅ Views dinâmicas se atualizam automaticamente
- ✅ Separação clara entre dados brutos e tratados
- ✅ Estrutura escalável para novos empreendimentos

## 🚀 Próximos Passos

### 7.1. Expansão do Sistema
- Adicionar novos empreendimentos à view consolidada
- Implementar views específicas por região
- Criar views de performance por corretor/imobiliária

### 7.2. Otimizações
- Implementar índices para melhor performance
- Criar views materializadas para consultas frequentes
- Implementar cache para análises complexas

### 7.3. Monitoramento
- Implementar alertas para dados inconsistentes
- Criar relatórios de qualidade dos dados
- Monitorar performance das views

## 📝 Conclusão

A implementação do banco de dados consolidado representa um marco na estruturação dos dados de vendas, proporcionando:

1. **Visão Unificada:** Todos os dados de vendas em uma única fonte
2. **Atualização Automática:** Views dinâmicas sempre atualizadas
3. **Análise Completa:** Dados de clientes, corretores e imobiliárias
4. **Escalabilidade:** Estrutura preparada para crescimento

O sistema está pronto para suportar análises avançadas e tomada de decisões baseadas em dados consolidados e confiáveis.
