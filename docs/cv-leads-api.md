# 🔗 CV Leads API - Documentação

## Visão Geral

A API de Leads do CVCRM foi integrada ao sistema de vendas consolidadas para capturar dados de leads com filtros específicos para imobiliárias "Prati" ou registros com imobiliária vazia.

## 📊 Endpoint e Configuração

### Endpoint
- **URL**: `https://prati.cvcrm.com.br/api/v1/cvdw/leads`
- **Método**: GET
- **Autenticação**: Email + Token (mesmas credenciais do CV Vendas)

### Headers
```python
headers = {
    'accept': 'application/json',
    'email': os.environ.get('CVCRM_EMAIL'),
    'token': os.environ.get('CVCRM_TOKEN')
}
```

### Parâmetros de Paginação
```python
params = {
    'pagina': 1,                    # Página atual (inicia em 1)
    'registros_por_pagina': 500     # Registros por página (padrão: 500)
}
```

## 🔍 Filtros Aplicados

### Filtro de Imobiliária
- **Mantém**: Registros com imobiliária contendo "Prati" (case insensitive)
- **Mantém**: Registros com imobiliária vazia ou nula
- **Remove**: Todos os outros registros

### Sem Filtro de Data
- A API busca sempre os dados mais atualizados
- Não aplica filtros de data de início ou fim

## 📋 Estrutura de Dados

### Campos Retornados
```json
{
  "Idlead": "string",
  "Data_cad": "YYYY-MM-DD",
  "Situacao": "string",
  "Imobiliaria": "string",
  "nome_situacao_anterior_lead": "string",
  "gestor": "string",
  "empreendimento_primeiro": "string",
  "empreendimento_ultimo": "string",
  "referencia_data": "YYYY-MM-DD",
  "data_reativacao": "YYYY-MM-DD",
  "corretor": "string",
  "corretor_ultimo": "string",
  "corretor_consolidado": "string (corretor + fallback corretor_ultimo)",
  "tags": "string (valores separados por vírgula)",
  "midia_original": "string",
  "midia_ultimo": "string",
  "midia_consolidada": "string (midia_ultimo + fallback midia_original)",
  "status_venda_realizada": "string (Sim/Não baseado em tags)",
  "status_reserva": "string (Sim/Não baseado em tags)",
  "status_visita_realizada": "string (Sim/Não baseado em tags)",
  "status_em_atendimento": "string (Sim/Não baseado em tags)",
  "status_descoberta": "string (Sim/Não baseado em tags)",
  "status_qualificacao": "string (Sim/Não baseado em tags)",
  "data_consolidada": "YYYY-MM-DD (mais recente entre ultima_data_conversao, data_reativacao e Data_cad)",
  "motivo_cancelamento": "string",
  "motivo_cancelamento_consolidada": "string (tratamento de texto - remove 'Descartar Lead -')",
  "data_cancelamento": "YYYY-MM-DD",
  "ultima_data_conversao": "YYYY-MM-DD",
  "descricao_motivo_cancelamento": "string",
  "possibilidade_venda": "string",
  "score": "string",
  "novo": "string",
  "retorno": "string",
  "data_ultima_alteracao": "YYYY-MM-DD",
  "campo_[nome_dinamico]": "string (valor do campo)"
}
```

### Campos Adicionais Dinâmicos

A coluna `campos_adicionais` é expansível e contém uma lista de objetos com:
- **nome**: Nome do campo adicional (vira nome da coluna)
- **valor**: Valor do campo adicional

**Processamento Dinâmico:**
- Cada item único da coluna `nome` vira uma coluna separada
- Nome da coluna: `campo_[nome_normalizado]`
- Valor da coluna: conteúdo da coluna `valor` correspondente
- Normalização: espaços viram `_`, caracteres especiais são removidos, tudo em minúsculas

**Exemplo:**
- Se `nome` = "Situação Especial" → coluna `campo_situacao_especial`
- Se `nome` = "Tipo-Cliente" → coluna `campo_tipo_cliente`

### Campos Adicionais (Processamento)
- **fonte**: `'cv_leads'` (identificador da fonte)
- **processado_em**: Timestamp de processamento

## 🏗️ Implementação

### Arquivo Principal
- **Localização**: `scripts/cv_leads_api.py`
- **Classe**: `CVLeadsAPIClient`
- **Função Principal**: `obter_dados_cv_leads()`

### Configuração
- **Arquivo**: `scripts/config.py`
- **Nome da API**: `'cv_leads'`
- **Rate Limit**: 60 requisições/minuto

### Integração
- **Sistema Completo**: `sistema_completo.py`
- **Upload**: Tabela `main.cv_leads` no MotherDuck
- **GitHub Actions**: Flag `CV_LEADS_ENABLED: 'true'`

## 🚀 Uso

### Teste Individual
```bash
python scripts/cv_leads_api.py
```

### Teste Completo
```bash
python teste_leads.py
```

### Sistema Completo
```bash
python sistema_completo.py
```

## 📊 Estatísticas e Monitoramento

### Logs de Debug
- Contagem de registros processados vs filtrados
- Exemplos de imobiliárias encontradas
- Tempo de processamento por página

### Métricas
- Total de registros processados
- Total de registros filtrados (Prati + vazias)
- Registros finais salvos
- Páginas processadas

## 🔧 Configuração Avançada

### Parâmetros Configuráveis
```python
await client.get_all_leads(
    registros_por_pagina=500,           # Registros por página
    imobiliaria_match="Prati",          # Filtro de imobiliária
    include_empty_imobiliaria=True,     # Incluir vazias
    max_paginas=5000,                   # Limite de páginas
    sleep_between_calls=0.0             # Delay entre chamadas
)
```

### Rate Limiting
- **Limite**: 60 requisições/minuto
- **Delay**: 0.0s (configurável)
- **Timeout**: 30 segundos por requisição

## 🗄️ Armazenamento

### Tabela no MotherDuck
- **Nome**: `main.cv_leads`
- **Schema**: Substituição completa a cada execução
- **Indexação**: Por `Idlead` e `Data_cad`

### Estrutura da Tabela
```sql
CREATE TABLE main.cv_leads (
    Idlead VARCHAR,
    Data_cad TIMESTAMP,
    Situacao VARCHAR,
    Imobiliaria VARCHAR,
    nome_situacao_anterior_lead VARCHAR,
    gestor VARCHAR,
    empreendimento_primeiro VARCHAR,
    empreendimento_ultimo VARCHAR,
    referencia_data TIMESTAMP,
    data_reativacao TIMESTAMP,
    corretor VARCHAR,
    corretor_ultimo VARCHAR,
    corretor_consolidado VARCHAR, -- corretor + fallback corretor_ultimo
    tags VARCHAR, -- coluna original
    tag1 VARCHAR, -- colunas derivadas dinamicamente
    tag2 VARCHAR,
    tagN VARCHAR,
    midia_original VARCHAR,
    midia_ultimo VARCHAR,
    midia_consolidada VARCHAR, -- midia_ultimo + fallback midia_original
    status_venda_realizada VARCHAR, -- Sim/Não baseado em tags
    status_reserva VARCHAR, -- Sim/Não baseado em tags
    status_visita_realizada VARCHAR, -- Sim/Não baseado em tags
    status_em_atendimento VARCHAR, -- Sim/Não baseado em tags
    status_descoberta VARCHAR, -- Sim/Não baseado em tags
    status_qualificacao VARCHAR, -- Sim/Não baseado em tags
    data_consolidada TIMESTAMP, -- max(ultima_data_conversao, data_reativacao, Data_cad)
    motivo_cancelamento VARCHAR,
    motivo_cancelamento_consolidada VARCHAR, -- tratamento de texto
    data_cancelamento TIMESTAMP,
    ultima_data_conversao TIMESTAMP,
    descricao_motivo_cancelamento VARCHAR,
    possibilidade_venda VARCHAR,
    score VARCHAR,
    novo VARCHAR,
    retorno VARCHAR,
    data_ultima_alteracao TIMESTAMP,
    campo_[nome_dinamico] VARCHAR,  -- Colunas dinâmicas baseadas nos nomes únicos
    fonte VARCHAR DEFAULT 'cv_leads',
    processado_em TIMESTAMP
);
```

**Nota:** As colunas `campo_[nome_dinamico]` são criadas dinamicamente baseadas nos valores únicos encontrados na coluna `nome` dos campos adicionais. O número e nomes dessas colunas podem variar conforme os dados.

## 🔄 Fluxo de Execução

### 1. Inicialização
```python
client = CVLeadsAPIClient()
```

### 2. Paginação
```python
pagina = 1
while pagina <= max_paginas:
    result = await client.get_pagina(pagina, registros_por_pagina)
    # Processar dados...
    pagina += 1
```

### 3. Filtros
```python
for item in dados:
    imob = (item.get("imobiliaria") or "").strip()
    is_prati = "prati" in imob.lower()
    is_empty = (imob == "")
    
    if is_prati or is_empty:
        # Incluir no resultado
```

### 4. Processamento
```python
df = processar_dados_cv_leads(dados)
```

### 5. Upload
```python
conn.execute("CREATE OR REPLACE TABLE main.cv_leads AS SELECT * FROM df_cv_leads")
```

## 🛡️ Tratamento de Erros

### Erros Comuns
- **404**: Fim dos dados (normal)
- **429**: Rate limit excedido (retry automático)
- **500**: Erro do servidor (log e continuar)

### Estratégias de Recuperação
- Retry automático para 429
- Log detalhado de erros
- Continuação em caso de falha parcial

## 📈 Performance

### Otimizações
- Paginação eficiente (500 registros/página)
- Filtros aplicados em memória
- Rate limiting inteligente
- Processamento assíncrono

### Métricas Típicas
- **Registros/página**: 500
- **Páginas processadas**: 10-50
- **Tempo total**: 2-5 minutos
- **Taxa de sucesso**: >95%

## 🔮 Melhorias Futuras

### Funcionalidades Planejadas
- Cache de dados intermediários
- Filtros de data configuráveis
- Análise de tendências
- Alertas automáticos

### Otimizações
- Processamento paralelo
- Compressão de dados
- Indexação avançada
- Métricas em tempo real

## 📚 Referências

- [CVCRM API Documentation](https://prati.cvcrm.com.br/api/v1/)
- [Sistema de Vendas Consolidadas](./README.md)
- [GitHub Actions](./github-actions.md)
- [Troubleshooting](./troubleshooting.md)



