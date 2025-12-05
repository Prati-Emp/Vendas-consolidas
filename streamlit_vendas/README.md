# 📊 Dashboard de Vendas Consolidadas - Streamlit

Sistema de analytics de vendas conectado ao MotherDuck com interface multipage em Streamlit.

## 🎯 Funcionalidades

- **Dashboard Principal**: KPIs, timeline mensal e tabelas resumidas
- **Tabela Hierárquica**: Drill-down com expand/collapse por níveis
- **Análises por Dimensões**: Visualizações por mídia, tipo de venda, imobiliária e corretores
- **Filtros Globais**: Período, mídia e tipo de venda aplicados a todas as páginas
- **Exportação**: Download de dados em CSV
- **Formatação pt-BR**: Números, moeda e datas em formato brasileiro

## 🏗️ Estrutura do Projeto

```
streamlit_vendas/
├── app.py                          # Página principal + filtros + KPIs + timeline
├── pages/
│   ├── 01_Tabela_Drilldown.py     # Tabela hierárquica com drill-down
│   └── 02_Analises.py             # Análises por dimensões
├── utils/
│   ├── md_conn.py                 # Conexão MotherDuck + funções de consulta
│   └── formatters.py              # Formatadores pt-BR (moeda, percent, etc.)
├── .streamlit/
│   └── config.toml                # Configuração do tema Streamlit
├── requirements.txt               # Dependências Python
├── env_example.txt                # Exemplo de configuração .env
└── README.md                      # Esta documentação
```

## 🚀 Instalação e Configuração

### 1. Pré-requisitos

- Python 3.10+
- Token do MotherDuck (do projeto principal)

### 2. Instalação

```bash
# Navegar para o diretório do projeto
cd streamlit_vendas

# Criar ambiente virtual (recomendado)
python -m venv .venv

# Ativar ambiente virtual
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

### 3. Configuração do Token

```bash
# Copiar arquivo de exemplo
copy env_example.txt .env

# Editar .env e adicionar seu token do MotherDuck
# Use o token do arquivo motherduck_config.env do projeto principal
MOTHERDUCK_TOKEN=seu_token_motherduck_aqui
```

### 4. Executar o App

```bash
streamlit run app.py
```

O app será aberto automaticamente em: http://localhost:8501

## 📊 Fontes de Dados

### Banco de Dados
- **MotherDuck** via DuckDB
- **Tabela Principal**: `informacoes_consolidadas.sienge_vendas_consolidadas`

### Colunas Utilizadas
- `nome_empreendimento` (string)
- `value` (numérico - valor do contrato em BRL)
- `contractDate` (data - usado como filtro de período)
- `corretor` (string)
- `imobiliaria` (string)
- `midia` (string)
- `tipovenda` (string)
- `bloco` (string)
- `unidade` (string)

## 🔍 Filtros Globais

### Período (Obrigatório)
- Intervalo por `contractDate`
- Default: min → max disponíveis na base
- Formato: YYYY-MM-DD

### Mídia (Opcional)
- Multi-seleção
- Filtro aplicado a todas as páginas
- Valores únicos carregados da base

### Tipo de Venda (Opcional)
- Multi-seleção
- Filtro aplicado a todas as páginas
- Valores únicos carregados da base

## 📈 Páginas do Dashboard

### 1. Dashboard Principal (`app.py`)

**KPIs Principais:**
- Total de Vendas (quantidade)
- Valor Total (R$)
- Ticket Médio (R$)
- Maior Venda (R$)

**Timeline Mensal:**
- Gráfico de linha com evolução do valor total por mês
- Marcadores com informações detalhadas
- Tabela resumo mensal

**Tabelas Resumidas:**
- Top N empreendimentos por valor total
- Top N empreendimentos por quantidade de vendas

### 2. Tabela Drill-Down (`pages/01_Tabela_Drilldown.py`)

**Hierarquia:**
1. **Empreendimento** (nível principal)
2. **Imobiliária** (agrupamento por imobiliária)
3. **Corretor** (agrupamento por corretor)
4. **Bloco** (agrupamento por bloco)
5. **Unidade** (vendas individuais)

**Funcionalidades:**
- Expand/Collapse por níveis (default: colapsado)
- Coluna "Valor (R$)" fixada à direita
- Formatação numérica pt-BR
- Totais por grupo via agregação
- Altura configurável (~600px)
- Exportação CSV
- Seleção múltipla de linhas

### 3. Análises por Dimensões (`pages/02_Analises.py`)

**Visualizações:**
- **Mídia**: Barras horizontais por valor total
- **Tipo de Venda**: Barras horizontais por valor total
- **Imobiliária**: Barras verticais (Top 15)
- **Corretores**: Tabela Top 20 + gráfico Top 10

**Características:**
- Gráficos interativos com Plotly
- Tooltips informativos
- Tabelas detalhadas expansíveis
- Cores dinâmicas baseadas em valores

## 🎨 Formatação e Locale

### Formatação pt-BR
- **Moeda**: R$ 1.234,56
- **Números**: 1.234 (separador de milhares)
- **Percentuais**: 15,5%
- **Datas**: 15/03/2025

### Tratamento de Nulos
- Strings vazias/nulas exibidas como "—" (travessão)
- Valores nulos em `value` descartados da análise
- Campos de hierarquia nulos substituídos por "—" apenas para exibição

## ⚡ Performance e Cache

### Cache de Dados
- `@st.cache_data(ttl=300)` nas consultas principais
- Cache de 5 minutos para otimizar performance
- Agregações realizadas no SQL antes de trazer para Python

### Otimizações
- Consultas SQL otimizadas com filtros
- Limite configurável para tabelas auxiliares
- Paginação automática no AG Grid

## 📥 Exportação de Dados

### Formatos Disponíveis
- **CSV**: Dados completos e limpos
- **KPIs**: Resumo dos indicadores
- **Timeline**: Dados mensais agregados
- **Drill-down**: Dados hierárquicos

### Localização
- Botões de download em cada seção
- Nomes de arquivo com timestamp
- Dados filtrados conforme seleção atual

## 🔧 Configurações Avançadas

### Tema Streamlit
- Tema claro corporativo
- Cores personalizadas
- Fontes padrão corporativas
- Configuração em `.streamlit/config.toml`

### Dependências
```
streamlit>=1.37.0
pandas>=2.2.0
duckdb>=1.0.0
python-dotenv>=1.0.1
plotly>=5.22.0
streamlit-aggrid>=0.3.4
```

## 🐛 Troubleshooting

### Problemas Comuns

**1. Erro de Conexão com MotherDuck**
```
❌ Token do MotherDuck não encontrado
```
- Verificar se o arquivo `.env` existe
- Confirmar se `MOTHERDUCK_TOKEN` está configurado
- Usar token do arquivo `motherduck_config.env` do projeto principal

**2. Erro de Dependências**
```
ModuleNotFoundError: No module named 'streamlit'
```
- Ativar ambiente virtual
- Executar `pip install -r requirements.txt`

**3. Dados Não Carregam**
```
⚠️ Nenhum dado encontrado para os filtros aplicados
```
- Verificar se o período selecionado tem dados
- Confirmar se a tabela `informacoes_consolidadas.sienge_vendas_consolidadas` existe
- Testar conexão com MotherDuck

**4. Erro de Formatação**
```
ValueError: Invalid format specifier
```
- Verificar se locale pt-BR está disponível
- Fallback automático para formatação manual

### Logs e Debug

**Habilitar Logs Detalhados:**
```bash
streamlit run app.py --logger.level=debug
```

**Verificar Conexão:**
```python
# Teste rápido no Python
from utils.md_conn import get_md_connection
conn = get_md_connection()
conn.connect()
print("✅ Conexão OK")
```

## 🚀 Comandos Úteis

### Desenvolvimento
```bash
# Executar em modo de desenvolvimento
streamlit run app.py --server.runOnSave true

# Executar em porta específica
streamlit run app.py --server.port 8502

# Executar sem abrir navegador
streamlit run app.py --server.headless true
```

### Manutenção
```bash
# Limpar cache do Streamlit
streamlit cache clear

# Verificar dependências
pip list | grep streamlit

# Atualizar dependências
pip install -r requirements.txt --upgrade
```

## 📝 Notas de Desenvolvimento

### Estrutura de Dados
- Dados sempre filtrados por `value IS NOT NULL`
- Agregações realizadas no SQL para performance
- Cache de 5 minutos para consultas frequentes

### Navegação
- Filtros mantidos em `st.session_state`
- Estado persistente entre páginas
- Aplicação automática de filtros

### Responsividade
- Layout wide para melhor visualização
- Gráficos responsivos com Plotly
- Tabelas com scroll horizontal quando necessário

## 🤝 Contribuição

Para contribuir com o projeto:

1. Fork o repositório
2. Crie uma branch para sua feature
3. Implemente as mudanças
4. Teste localmente
5. Submeta um pull request

## 📄 Licença

Este projeto faz parte do sistema Vendas_Consolidadas e segue as mesmas diretrizes de licenciamento.

---

**Desenvolvido para análise de vendas consolidadas com integração MotherDuck e interface Streamlit moderna.**






























