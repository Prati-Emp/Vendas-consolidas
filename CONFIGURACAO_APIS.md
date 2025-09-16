# Configuração das APIs - Vendas Consolidadas

## Variáveis de Ambiente Necessárias

Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:

### APIs Existentes (CVCRM)
```env
CVCRM_EMAIL=seu_email@exemplo.com
CVCRM_TOKEN=seu_token_cvcrm
```

### MotherDuck
```env
MOTHERDUCK_TOKEN=seu_token_motherduck
```

### Novas APIs - Sienge
```env
SIENGE_BASE_URL=https://api.sienge.com.br
SIENGE_TOKEN=seu_token_sienge
```

### Nova API - CV Vendas
```env
CV_VENDAS_BASE_URL=https://prati.cvcrm.com.br/api/v1/cvdw/vendas
CV_VENDAS_EMAIL=seu_email@exemplo.com
CV_VENDAS_TOKEN=seu_token_cv_vendas
```

### Configurações Opcionais
```env
LOG_LEVEL=INFO
MAX_RETRIES=3
TIMEOUT=30
```

## Estrutura das APIs

### 1. APIs Existentes (mantidas)
- **Reservas**: `https://prati.cvcrm.com.br/api/v1/cvdw/reservas`
- **Workflow**: `https://prati.cvcrm.com.br/api/v1/cvdw/reservas/workflow/tempo`

### 2. Novas APIs - Sienge
- **Vendas Realizadas**: `{SIENGE_BASE_URL}/vendas/realizadas`
- **Vendas Canceladas**: `{SIENGE_BASE_URL}/vendas/canceladas`

### 3. Nova API - CV Vendas
- **Relatório de Vendas**: `{CV_VENDAS_BASE_URL}/relatorio/vendas`

## Limites de Taxa (Rate Limits)

- **CVCRM (Reservas/Workflow)**: 20 req/min
- **Sienge**: 30 req/min
- **CV Vendas**: 25 req/min

## Como Executar

### 1. Instalar Dependências
```bash
pip install -r requirements.txt
```

### 2. Configurar Variáveis de Ambiente
Copie o arquivo `.env.example` para `.env` e preencha com suas credenciais.

### 3. Executar Atualização Completa
```bash
python scripts/update_motherduck_vendas.py
```

### 4. Executar APIs Individuais (para teste)
```bash
# Testar configurações
python scripts/config.py

# Testar orquestrador
python scripts/orchestrator.py

# Testar APIs do Sienge
python scripts/sienge_apis.py

# Testar API CV Vendas
python scripts/cv_vendas_api.py

# Testar processador de dados
python scripts/data_processor.py
```

## Estrutura das Tabelas no MotherDuck

### Tabela Principal
- `vendas_consolidadas.main.vendas_consolidadas` - Dados consolidados de todas as fontes

### Tabelas Individuais
- `vendas_consolidadas.main.reservas` - Dados de reservas
- `vendas_consolidadas.main.workflow` - Dados de workflow
- `vendas_consolidadas.main.sienge_vendas_realizadas` - Vendas realizadas do Sienge
- `vendas_consolidadas.main.sienge_vendas_canceladas` - Vendas canceladas do Sienge
- `vendas_consolidadas.main.cv_vendas` - Relatório de vendas do CV

## Schema Padrão

Todas as tabelas seguem um schema padrão com as seguintes colunas principais:

### Identificadores
- `id`, `id_contrato`, `id_cliente`, `id_venda`

### Datas
- `data_venda`, `data_contrato`, `data_cancelamento`, `data_emissao`, `data_viagem`

### Valores Monetários
- `valor_venda`, `valor_contrato`, `valor_cancelamento`, `valor_comissao`, `valor_imposto`

### Informações do Cliente
- `nome_cliente`, `email_cliente`, `telefone_cliente`, `cpf_cliente`

### Informações do Produto/Serviço
- `produto`, `destino`, `origem`, `categoria`

### Status e Metadados
- `status`, `tipo_venda`, `fonte`, `processado_em`

## Monitoramento

O sistema inclui:
- Logs detalhados de todas as operações
- Estatísticas de requisições por API
- Relatórios de consolidação de dados
- Tratamento de erros e retry automático
- Rate limiting para respeitar limites das APIs
