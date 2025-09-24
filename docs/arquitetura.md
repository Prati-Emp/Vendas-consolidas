# 🏗️ Arquitetura do Sistema de Vendas Consolidadas

## Visão Geral

O sistema é uma solução de integração e consolidação de dados de vendas de múltiplas fontes, com dashboard interativo para análise e visualização em tempo real.

## 🎯 Objetivos do Sistema

- **Consolidação**: Integrar dados de CVCRM, Sienge e CV Vendas
- **Automação**: Atualização automática via GitHub Actions
- **Visualização**: Dashboard interativo com Streamlit
- **Escalabilidade**: Rate limiting e processamento assíncrono
- **Confiabilidade**: Tratamento de erros e timeouts

## 🏛️ Arquitetura de Alto Nível

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   CVCRM APIs    │    │   Sienge APIs   │    │   CV Vendas     │
│                 │    │                 │    │                 │
│ • Reservas      │    │ • Vendas        │    │ • Relatório     │
│ • Workflow      │    │   Realizadas    │    │   de Vendas     │
│                 │    │ • Vendas        │    │                 │
│                 │    │   Canceladas    │    │                 │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │     Orquestrador          │
                    │                           │
                    │ • Rate Limiting           │
                    │ • Retry Logic             │
                    │ • Error Handling          │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │    Processador de         │
                    │    Dados                  │
                    │                           │
                    │ • Normalização            │
                    │ • Validação               │
                    │ • Consolidação            │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │     MotherDuck            │
                    │     Database              │
                    │                           │
                    │ • cv_vendas               │
                    │ • sienge_vendas_*         │
                    │ • Dados Consolidados      │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │     Dashboard             │
                    │     Streamlit             │
                    │                           │
                    │ • Visualizações           │
                    │ • Análises                │
                    │ • Relatórios              │
                    └───────────────────────────┘
```

## 🔧 Componentes Principais

### 1. **Orquestrador de APIs** (`scripts/orchestrator.py`)
- **Função**: Gerencia chamadas para múltiplas APIs
- **Características**:
  - Rate limiting por API
  - Retry automático para 429
  - Estatísticas de requisições
  - Timeout configurável

### 2. **Configuração** (`scripts/config.py`)
- **Função**: Centraliza configurações de APIs
- **Características**:
  - Headers e URLs por API
  - Limites de taxa
  - Variáveis de ambiente

### 3. **Integrações Específicas**
- **CV Vendas** (`scripts/cv_vendas_api.py`): API de relatórios de vendas
- **CV Repasses** (`scripts/cv_repasses_api.py`): API de repasses (mesmas credenciais de CV Vendas)
- **Sienge** (`scripts/sienge_apis.py`): APIs de vendas realizadas/canceladas
- **Processamento** (`scripts/data_processor.py`): Normalização e consolidação

### 4. **Pipeline de Execução**
- **Sistema Completo** (`sistema_completo.py`): Pipeline principal
- **Sistema Otimizado** (`sistema_otimizado.py`): Versão otimizada
- **Upload Funcional** (`upload_vendas_funcional.py`): Upload específico

### 5. **Automação**
- **GitHub Actions** (`.github/workflows/update-database.yml`): Execução agendada
- **Script Wrapper** (`scripts/update_motherduck_vendas.py`): Interface para Actions

### 6. **Dashboard**
- **Streamlit** (`dashboard/`): Interface de visualização
- **Páginas**: Home, Vendas, Leads, Imobiliária, Motivos

## 🔄 Fluxo de Dados

### 1. **Coleta**
```
APIs Externas → Orquestrador → Rate Limiting → Dados Brutos
```

### 2. **Processamento**
```
Dados Brutos → Processador → Normalização → DataFrames
```

### 3. **Armazenamento**
```
DataFrames → MotherDuck → Tabelas Consolidadas
```

### 4. **Visualização**
```
MotherDuck → Dashboard → Visualizações Interativas
```

## 🗄️ Estrutura de Dados

### Tabelas no MotherDuck
- **`main.cv_vendas`**: Dados do CV Vendas
- **`main.sienge_vendas_realizadas`**: Vendas realizadas do Sienge
- **`main.sienge_vendas_canceladas`**: Vendas canceladas do Sienge
- **`main.reservas_abril`**: Dados de reservas (referência)

### Schema Padrão
```python
{
    'id': 'string',
    'data_venda': 'datetime64[ns]',
    'valor_venda': 'float64',
    'nome_cliente': 'string',
    'fonte': 'string',
    'processado_em': 'datetime64[ns]'
}
```

## ⚡ Performance e Otimizações

### Rate Limiting Inteligente
- **Madrugada**: Delay reduzido (0.2s)
- **Dia**: Delay normal (0.3s)
- **Limites por API**: Configuráveis

### Processamento Assíncrono
- **Coleta paralela**: Múltiplas APIs simultaneamente
- **Timeout**: 15 minutos máximo
- **Retry**: Automático para falhas temporárias

### Caching e Persistência
- **MotherDuck**: Armazenamento na nuvem
- **Full Refresh**: Substituição completa das tabelas
- **Idempotência**: Execuções seguras

## 🔒 Segurança

### Credenciais
- **Variáveis de Ambiente**: Todas as chaves em `.env`
- **GitHub Secrets**: Configuração segura no Actions
- **Não Versionadas**: Credenciais nunca no código

### Controle de Acesso
- **Rate Limiting**: Proteção contra sobrecarga
- **Timeouts**: Prevenção de travamentos
- **Validação**: Verificação de dados de entrada

## 📊 Monitoramento

### Logs
- **Estruturados**: Formato consistente
- **Níveis**: INFO, WARNING, ERROR
- **Contexto**: Timestamps e detalhes

### Métricas
- **Requisições**: Contagem por API
- **Tempo**: Duração das operações
- **Sucesso**: Taxa de sucesso por fonte

### Alertas
- **GitHub Actions**: Notificações de falha
- **Timeout**: Alertas de demora
- **Erros**: Logs de falhas

## 🚀 Escalabilidade

### Horizontal
- **Múltiplas APIs**: Fácil adição de fontes
- **Paralelização**: Processamento simultâneo
- **Rate Limiting**: Controle de carga

### Vertical
- **Timeout**: Configurável por ambiente
- **Memória**: Processamento em lotes
- **CPU**: Processamento assíncrono

## 🔮 Evolução Futura

### Próximas Melhorias
- **Cache Redis**: Cache intermediário
- **Streaming**: Processamento em tempo real
- **ML**: Análises preditivas
- **APIs REST**: Interface programática

### Considerações
- **Manutenibilidade**: Código modular
- **Testabilidade**: Testes automatizados
- **Documentação**: Sempre atualizada
