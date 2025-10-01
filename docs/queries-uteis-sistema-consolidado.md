# Queries Úteis - Sistema Consolidado de Vendas

## 📋 Consultas Básicas

### 1. Verificar Estrutura do Banco
```sql
-- Listar bancos disponíveis
SHOW DATABASES;

-- Listar tabelas/views no banco consolidado
SHOW TABLES FROM informacoes_consolidadas;

-- Descrever estrutura da view principal
DESCRIBE informacoes_consolidadas.sienge_vendas_consolidadas;
```

### 2. Contagem de Registros
```sql
-- Total de registros na view consolidada
SELECT COUNT(*) as total_registros 
FROM informacoes_consolidadas.sienge_vendas_consolidadas;

-- Registros por origem
SELECT 
    origem,
    COUNT(*) as total_registros
FROM informacoes_consolidadas.sienge_vendas_consolidadas
GROUP BY origem
ORDER BY total_registros DESC;
```

## 📊 Análises Temporais

### 3. Vendas por Ano
```sql
-- Vendas totais por ano
SELECT 
    EXTRACT(YEAR FROM contractDate) as ano,
    COUNT(*) as total_vendas,
    SUM(value) as valor_total,
    AVG(value) as valor_medio
FROM informacoes_consolidadas.sienge_vendas_consolidadas
GROUP BY EXTRACT(YEAR FROM contractDate)
ORDER BY ano DESC;
```

### 4. Vendas por Mês (Ano Específico)
```sql
-- Vendas mensais para 2025
SELECT 
    EXTRACT(MONTH FROM contractDate) as mes,
    COUNT(*) as total_vendas,
    SUM(value) as valor_total,
    AVG(value) as valor_medio
FROM informacoes_consolidadas.sienge_vendas_consolidadas
WHERE EXTRACT(YEAR FROM contractDate) = 2025
GROUP BY EXTRACT(MONTH FROM contractDate)
ORDER BY mes;
```

### 5. Vendas por Período Específico
```sql
-- Vendas de setembro 2025
SELECT 
    COUNT(*) as total_vendas,
    SUM(value) as valor_total,
    AVG(value) as valor_medio,
    MIN(contractDate) as primeira_venda,
    MAX(contractDate) as ultima_venda
FROM informacoes_consolidadas.sienge_vendas_consolidadas
WHERE EXTRACT(YEAR FROM contractDate) = 2025
  AND EXTRACT(MONTH FROM contractDate) = 9;
```

## 🏢 Análises por Empreendimento

### 6. Ranking de Empreendimentos
```sql
-- Top 10 empreendimentos por valor total
SELECT 
    enterpriseId,
    nome_empreendimento,
    COUNT(*) as total_vendas,
    SUM(value) as valor_total,
    AVG(value) as valor_medio,
    MIN(contractDate) as primeira_venda,
    MAX(contractDate) as ultima_venda
FROM informacoes_consolidadas.sienge_vendas_consolidadas
GROUP BY enterpriseId, nome_empreendimento
ORDER BY valor_total DESC
LIMIT 10;
```

### 7. Performance de Empreendimento Específico
```sql
-- Análise detalhada do Loteamento Vera Cruz (ID 5)
SELECT 
    enterpriseId,
    nome_empreendimento,
    origem,
    COUNT(*) as total_vendas,
    SUM(value) as valor_total,
    AVG(value) as valor_medio
FROM informacoes_consolidadas.sienge_vendas_consolidadas
WHERE enterpriseId = 5
GROUP BY enterpriseId, nome_empreendimento, origem
ORDER BY valor_total DESC;
```

### 8. Comparação entre Empreendimentos
```sql
-- Comparação de performance entre empreendimentos
SELECT 
    nome_empreendimento,
    COUNT(*) as total_vendas,
    SUM(value) as valor_total,
    AVG(value) as valor_medio,
    ROUND(SUM(value) * 100.0 / (SELECT SUM(value) FROM informacoes_consolidadas.sienge_vendas_consolidadas), 2) as percentual_total
FROM informacoes_consolidadas.sienge_vendas_consolidadas
GROUP BY nome_empreendimento
ORDER BY valor_total DESC;
```

## 👥 Análises Comerciais

### 9. Top Corretores
```sql
-- Top 20 corretores por performance
SELECT 
    corretor,
    COUNT(*) as total_vendas,
    SUM(value) as valor_total,
    AVG(value) as valor_medio
FROM informacoes_consolidadas.sienge_vendas_consolidadas
WHERE corretor != 'N/A'
GROUP BY corretor
ORDER BY valor_total DESC
LIMIT 20;
```

### 10. Top Imobiliárias
```sql
-- Top 20 imobiliárias por performance
SELECT 
    imobiliaria,
    COUNT(*) as total_vendas,
    SUM(value) as valor_total,
    AVG(value) as valor_medio
FROM informacoes_consolidadas.sienge_vendas_consolidadas
WHERE imobiliaria != 'N/A'
GROUP BY imobiliaria
ORDER BY valor_total DESC
LIMIT 20;
```

### 11. Performance por Corretor e Imobiliária
```sql
-- Performance combinada corretor + imobiliária
SELECT 
    corretor,
    imobiliaria,
    COUNT(*) as total_vendas,
    SUM(value) as valor_total,
    AVG(value) as valor_medio
FROM informacoes_consolidadas.sienge_vendas_consolidadas
WHERE corretor != 'N/A' AND imobiliaria != 'N/A'
GROUP BY corretor, imobiliaria
ORDER BY valor_total DESC
LIMIT 20;
```

## 👤 Análises de Clientes

### 12. Perfil Demográfico
```sql
-- Análise por perfil demográfico
SELECT 
    sexo,
    estado_civil,
    COUNT(*) as total_clientes,
    AVG(idade) as idade_media,
    AVG(renda) as renda_media,
    SUM(value) as valor_total
FROM informacoes_consolidadas.sienge_vendas_consolidadas
WHERE sexo != 'N/A'
GROUP BY sexo, estado_civil
ORDER BY valor_total DESC;
```

### 13. Análise por Cidade
```sql
-- Top 20 cidades por valor total
SELECT 
    cidade,
    COUNT(*) as total_vendas,
    SUM(value) as valor_total,
    AVG(value) as valor_medio
FROM informacoes_consolidadas.sienge_vendas_consolidadas
WHERE cidade != 'N/A'
GROUP BY cidade
ORDER BY valor_total DESC
LIMIT 20;
```

### 14. Análise por Faixa Etária
```sql
-- Vendas por faixa etária
SELECT 
    CASE 
        WHEN idade < 30 THEN 'Menos de 30'
        WHEN idade BETWEEN 30 AND 40 THEN '30-40'
        WHEN idade BETWEEN 41 AND 50 THEN '41-50'
        WHEN idade BETWEEN 51 AND 60 THEN '51-60'
        WHEN idade > 60 THEN 'Mais de 60'
        ELSE 'Não informado'
    END as faixa_etaria,
    COUNT(*) as total_vendas,
    SUM(value) as valor_total,
    AVG(value) as valor_medio
FROM informacoes_consolidadas.sienge_vendas_consolidadas
WHERE idade IS NOT NULL
GROUP BY faixa_etaria
ORDER BY valor_total DESC;
```

## 📈 Análises de Performance

### 15. Crescimento Mensal
```sql
-- Crescimento mensal em 2025
SELECT 
    EXTRACT(MONTH FROM contractDate) as mes,
    COUNT(*) as total_vendas,
    SUM(value) as valor_total,
    LAG(SUM(value)) OVER (ORDER BY EXTRACT(MONTH FROM contractDate)) as valor_mes_anterior,
    ROUND(
        (SUM(value) - LAG(SUM(value)) OVER (ORDER BY EXTRACT(MONTH FROM contractDate))) * 100.0 / 
        LAG(SUM(value)) OVER (ORDER BY EXTRACT(MONTH FROM contractDate)), 2
    ) as crescimento_percentual
FROM informacoes_consolidadas.sienge_vendas_consolidadas
WHERE EXTRACT(YEAR FROM contractDate) = 2025
GROUP BY EXTRACT(MONTH FROM contractDate)
ORDER BY mes;
```

### 16. Análise de Sazonalidade
```sql
-- Análise de sazonalidade por trimestre
SELECT 
    CASE 
        WHEN EXTRACT(MONTH FROM contractDate) IN (1,2,3) THEN 'Q1'
        WHEN EXTRACT(MONTH FROM contractDate) IN (4,5,6) THEN 'Q2'
        WHEN EXTRACT(MONTH FROM contractDate) IN (7,8,9) THEN 'Q3'
        WHEN EXTRACT(MONTH FROM contractDate) IN (10,11,12) THEN 'Q4'
    END as trimestre,
    COUNT(*) as total_vendas,
    SUM(value) as valor_total,
    AVG(value) as valor_medio
FROM informacoes_consolidadas.sienge_vendas_consolidadas
WHERE EXTRACT(YEAR FROM contractDate) = 2025
GROUP BY trimestre
ORDER BY trimestre;
```

## 🔍 Consultas de Diagnóstico

### 17. Verificar Dados Faltantes
```sql
-- Verificar campos com valores nulos
SELECT 
    'corretor' as campo,
    COUNT(*) as total_registros,
    COUNT(corretor) as registros_preenchidos,
    COUNT(*) - COUNT(corretor) as registros_nulos
FROM informacoes_consolidadas.sienge_vendas_consolidadas
UNION ALL
SELECT 
    'imobiliaria' as campo,
    COUNT(*) as total_registros,
    COUNT(imobiliaria) as registros_preenchidos,
    COUNT(*) - COUNT(imobiliaria) as registros_nulos
FROM informacoes_consolidadas.sienge_vendas_consolidadas
UNION ALL
SELECT 
    'cliente' as campo,
    COUNT(*) as total_registros,
    COUNT(cliente) as registros_preenchidos,
    COUNT(*) - COUNT(cliente) as registros_nulos
FROM informacoes_consolidadas.sienge_vendas_consolidadas;
```

### 18. Verificar Consistência de Dados
```sql
-- Verificar registros com valores inconsistentes
SELECT 
    'Valores negativos' as tipo_inconsistencia,
    COUNT(*) as total_registros
FROM informacoes_consolidadas.sienge_vendas_consolidadas
WHERE value < 0
UNION ALL
SELECT 
    'Valores zero' as tipo_inconsistencia,
    COUNT(*) as total_registros
FROM informacoes_consolidadas.sienge_vendas_consolidadas
WHERE value = 0
UNION ALL
SELECT 
    'Datas futuras' as tipo_inconsistencia,
    COUNT(*) as total_registros
FROM informacoes_consolidadas.sienge_vendas_consolidadas
WHERE contractDate > CURRENT_DATE;
```

## 📊 Relatórios Executivos

### 19. Dashboard Executivo
```sql
-- Resumo executivo completo
SELECT 
    'Total de Vendas' as metrica,
    COUNT(*) as valor
FROM informacoes_consolidadas.sienge_vendas_consolidadas
UNION ALL
SELECT 
    'Valor Total' as metrica,
    SUM(value) as valor
FROM informacoes_consolidadas.sienge_vendas_consolidadas
UNION ALL
SELECT 
    'Valor Médio' as metrica,
    AVG(value) as valor
FROM informacoes_consolidadas.sienge_vendas_consolidadas
UNION ALL
SELECT 
    'Maior Venda' as metrica,
    MAX(value) as valor
FROM informacoes_consolidadas.sienge_vendas_consolidadas
UNION ALL
SELECT 
    'Menor Venda' as metrica,
    MIN(value) as valor
FROM informacoes_consolidadas.sienge_vendas_consolidadas;
```

### 20. Análise de Tendências
```sql
-- Análise de tendências por semana
SELECT 
    EXTRACT(WEEK FROM contractDate) as semana,
    COUNT(*) as total_vendas,
    SUM(value) as valor_total,
    AVG(value) as valor_medio
FROM informacoes_consolidadas.sienge_vendas_consolidadas
WHERE EXTRACT(YEAR FROM contractDate) = 2025
  AND EXTRACT(MONTH FROM contractDate) = 9
GROUP BY EXTRACT(WEEK FROM contractDate)
ORDER BY semana;
```

## 🚀 Dicas de Performance

### 21. Consultas Otimizadas
```sql
-- Usar LIMIT para consultas grandes
SELECT * FROM informacoes_consolidadas.sienge_vendas_consolidadas
WHERE EXTRACT(YEAR FROM contractDate) = 2025
ORDER BY contractDate DESC
LIMIT 100;

-- Usar índices implícitos em filtros
SELECT * FROM informacoes_consolidadas.sienge_vendas_consolidadas
WHERE enterpriseId = 5
  AND contractDate >= '2025-01-01'
  AND contractDate <= '2025-12-31';
```

### 22. Consultas de Agregação Eficientes
```sql
-- Agregação eficiente com filtros
SELECT 
    enterpriseId,
    COUNT(*) as total_vendas,
    SUM(value) as valor_total
FROM informacoes_consolidadas.sienge_vendas_consolidadas
WHERE contractDate >= '2025-01-01'
  AND contractDate <= '2025-12-31'
GROUP BY enterpriseId
HAVING COUNT(*) > 10  -- Apenas empreendimentos com mais de 10 vendas
ORDER BY valor_total DESC;
```

## 📝 Notas Importantes

1. **Performance:** Use `LIMIT` em consultas grandes para melhor performance
2. **Filtros:** Sempre use filtros de data para consultas temporais
3. **Índices:** O MotherDuck otimiza automaticamente, mas filtros específicos ajudam
4. **Agregações:** Use `GROUP BY` com `HAVING` para filtrar resultados agregados
5. **Datas:** Use `EXTRACT()` para análises temporais precisas

## 🔧 Troubleshooting

### Problemas Comuns:
- **Erro de encoding:** Use `LIKE '%texto%'` para caracteres especiais
- **Valores nulos:** Use `COALESCE()` ou `IS NOT NULL` para filtrar
- **Performance lenta:** Adicione filtros de data e use `LIMIT`
- **Dados inconsistentes:** Verifique a origem dos dados com `GROUP BY origem`
