# Dashboard de Vendas Consolidadas

Dashboard Streamlit para análise de vendas consolidadas utilizando dados do Sienge e metas de vendas.

## 📋 Visão Geral

Este dashboard replica as funcionalidades do dashboard original (`dashboard/pages/Vendas.py`) mas utiliza:
- **Fonte de Vendas**: `informacoes_consolidadas.sienge_vendas_consolidadas`
- **Fonte de Metas**: `informacoes_consolidadas.meta_vendas_2025`
- **Relacionamento**: `enterpriseId` ↔ `codigo_empreendimento`

## 🚀 Instalação e Configuração

### 1. Pré-requisitos

- Python 3.8+
- Token do MotherDuck

### 2. Instalação

```bash
# Navegar para o diretório do dashboard
cd vendas_consolidadas

# Instalar dependências
pip install -r requirements.txt
```

### 3. Configuração do Token

```bash
# Copiar arquivo de exemplo
copy .env.example .env

# Editar .env e adicionar seu token do MotherDuck
# Use o token do arquivo motherduck_config.env do projeto principal
MOTHERDUCK_TOKEN=seu_token_motherduck_aqui
```

### 4. Executar o Dashboard

```bash
streamlit run app.py
```

O dashboard será aberto automaticamente em: http://localhost:8501

## 📊 Fontes de Dados

### Banco de Dados
- **MotherDuck** via DuckDB
- **Banco**: `informacoes_consolidadas`

### Tabelas Utilizadas

#### 1. Vendas Consolidadas (`sienge_vendas_consolidadas`)
- `enterpriseId` (INTEGER) - ID do empreendimento
- `nome_empreendimento` (VARCHAR) - Nome do empreendimento
- `contractDate` (DATE) - Data do contrato (usado para filtros de período)
- `value` (DOUBLE) - Valor da venda
- `imobiliaria` (VARCHAR) - Nome da imobiliária
- `corretor` (VARCHAR) - Nome do corretor
- `midia` (VARCHAR) - Mídia de origem
- `tipovenda` (VARCHAR) - Tipo de venda
- `bloco` (VARCHAR) - Bloco da unidade
- `unidade` (VARCHAR) - Unidade
- `origem` (VARCHAR) - Origem dos dados (Sienge Realizada/Cancelada/Reserva)

#### 2. Metas de Vendas (`meta_vendas_2025`)
- `Empreendiemento` (VARCHAR) - Nome do empreendimento
- `Codigo empreendimento` (BIGINT) - Código do empreendimento
- `jan/25` até `dez/25` (BIGINT) - Metas mensais para 2025

## 🔍 Funcionalidades

### Filtros Globais
- **Período**: Intervalo de datas (padrão: 2025-01-01 até última data disponível)
- **Empreendimento**: Dropdown com todos os empreendimentos
- **Mídia**: Multi-seleção de mídias
- **Tipo de Venda**: Multi-seleção de tipos de venda

### Métricas Principais (KPIs)
- **Total de Vendas**: Quantidade de vendas no período
- **Valor Total**: Soma dos valores de vendas
- **Ticket Médio**: Valor médio por venda
- **Maior Venda**: Maior valor individual
- **Menor Venda**: Menor valor individual

### Análise de Metas
- **Meta do Período**: Soma das metas mensais no período
- **Atingimento**: Percentual de atingimento da meta
- **Diferença para Meta**: Diferença entre vendas e meta

### Análises Detalhadas
- **Evolução Mensal**: Gráfico de linha com timeline de vendas
- **Top Empreendimentos**: Ranking por valor total
- **Vendas House x Imobiliárias**: Análise de origem das vendas
- **Estratificação por Empreendimento**: Tabela detalhada por origem

### Exportação
- **KPIs**: Download em CSV
- **Timeline**: Download dos dados mensais

## 🏗️ Estrutura do Projeto

```
vendas_consolidadas/
├── app.py                 # Dashboard principal
├── utils/
│   ├── md_conn.py        # Conexão MotherDuck e queries SQL
│   └── formatters.py     # Formatação de valores
├── requirements.txt      # Dependências Python
├── .env.example         # Exemplo de configuração
└── README.md            # Esta documentação
```

## 🔧 Tratamento de Dados

### Empreendimentos sem Informações Completas
- Prioriza o campo `value` mesmo quando outros campos estão vazios
- Exemplo: Ondina tem vendas mas pode não ter todos os detalhes
- Usa `COALESCE` para campos opcionais: `COALESCE(corretor, 'Não informado')`

### Normalização de Nomes
- Remove prefixos: "Residencial ", "Loteamento ", "Condomínio "
- Função `normalizar_nome_empreendimento()` para matching com metas

### Classificação de Vendas
- **Venda Interna (Prati)**: Imobiliária contém "PRATI"
- **Venda Externa (Imobiliárias)**: Demais imobiliárias

## 📈 Cálculos de Metas

### Estrutura da Tabela de Metas
A tabela `meta_vendas_2025` possui colunas para cada mês:
- `jan/25`, `fev/25`, `mar/25`, etc.

### Cálculo de Meta do Período
1. Identifica meses no período selecionado
2. Soma metas dos meses correspondentes
3. Considera apenas valores > 0
4. Trata empreendimentos sem meta (ex: Ondina)

### Relacionamento
- `sienge_vendas_consolidadas.enterpriseId` ↔ `meta_vendas_2025.Codigo empreendimento`

## 🚨 Tratamento de Erros

- **Conexão**: Mensagens de erro amigáveis para problemas de conexão
- **Dados**: Fallbacks para períodos sem dados
- **Metas**: Tratamento de empreendimentos sem metas definidas
- **Cache**: TTL de 5 minutos para otimização de performance

## 🔄 Cache e Performance

- **Conexão**: Cache singleton com `@st.cache_resource`
- **Dados**: Cache de 5 minutos com `@st.cache_data`
- **Queries**: Otimizadas com filtros SQL eficientes

## 📝 Logs e Debug

- Mensagens de sucesso/erro no Streamlit
- Logs de queries SQL em caso de erro
- Informações de debug no console

## 🤝 Contribuição

Para contribuir com melhorias:
1. Mantenha a estrutura de pastas
2. Documente novas funcionalidades
3. Teste com dados reais
4. Siga os padrões de formatação existentes

## 📞 Suporte

Em caso de problemas:
1. Verifique a configuração do token
2. Confirme conectividade com MotherDuck
3. Valide estrutura das tabelas
4. Consulte logs de erro no console

