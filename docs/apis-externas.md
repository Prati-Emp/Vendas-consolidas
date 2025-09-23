# 🔌 APIs Externas - Integrações

## Visão Geral

O sistema integra com três principais fontes de dados através de APIs REST, cada uma com suas características específicas de autenticação, rate limiting e estrutura de dados.

## 📊 Mapa de Integrações

```
┌─────────────────────────────────────────────────────────────┐
│                    SISTEMA DE VENDAS                        │
│                     CONSOLIDADAS                             │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   CVCRM     │ │   SIENGE    │ │ CV VENDAS   │
│             │ │             │ │             │
│ • Reservas  │ │ • Vendas    │ │ • Relatório │
│ • Workflow  │ │   Realizadas│ │   de Vendas │
│             │ │ • Vendas    │ │             │
│             │ │   Canceladas│ │             │
└─────────────┘ └─────────────┘ └─────────────┘
```

## 🔗 CVCRM - Sistema Principal

### Endpoints
- **Base URL**: `https://prati.cvcrm.com.br/api/v1/`
- **Reservas**: `/reservas`
- **Workflow**: `/workflow`
- **CV Vendas**: `/cvdw/vendas`

### Autenticação
```python
headers = {
    'accept': 'application/json',
    'email': os.environ.get('CVCRM_EMAIL'),
    'token': os.environ.get('CVCRM_TOKEN')
}
```

### Rate Limiting
- **Limite**: 60 requisições/minuto
- **Estratégia**: Delay adaptativo por horário
- **Madrugada**: 0.2s entre requisições
- **Dia**: 0.3s entre requisições

### Estrutura de Dados

#### Reservas
```json
{
  "dados": [
    {
      "id": "string",
      "referencia_data": "YYYY-MM-DD",
      "valor_contrato": "R$ 1.000,00",
      "nome_cliente": "string",
      "email_cliente": "string",
      "telefone_cliente": "string",
      "cpf_cliente": "string",
      "produto": "string",
      "destino": "string",
      "origem": "string",
      "status": "string"
    }
  ],
  "total_registros": 1000,
  "pagina_atual": 1,
  "total_paginas": 10
}
```

#### CV Vendas
```json
{
  "dados": [
    {
      "id_venda": "string",
      "data_venda": "YYYY-MM-DD",
      "data_contrato": "YYYY-MM-DD",
      "data_emissao": "YYYY-MM-DD",
      "data_viagem": "YYYY-MM-DD",
      "valor_venda": "R$ 1.000,00",
      "valor_contrato": "R$ 1.000,00",
      "valor_comissao": "R$ 100,00",
      "valor_imposto": "R$ 50,00",
      "nome_cliente": "string",
      "email_cliente": "string",
      "telefone_cliente": "string",
      "cpf_cliente": "string",
      "produto": "string",
      "destino": "string",
      "origem": "string",
      "categoria": "string",
      "status": "string"
    }
  ]
}
```

## 🏢 Sienge - Sistema Imobiliário

### Endpoints
- **Base URL**: `https://api.sienge.com.br/pratiemp/public/api/bulk-data/v1`
- **Vendas Realizadas**: `/sales?situation=SOLD`
- **Vendas Canceladas**: `/sales?situation=CANCELED`

### Autenticação
```python
headers = {
    'accept': 'application/json',
    'authorization': f'Basic {os.environ.get("SIENGE_TOKEN")}'
}
```

### Rate Limiting
- **Limite**: 50 requisições/minuto
- **Controle Diário**: 36 requisições por execução
- **Execuções**: 2 por dia máximo
- **Delay**: 0.5s entre requisições

### Parâmetros de Filtro
```python
params = {
    'enterpriseId': int(empreendimento_id),
    'createdAfter': '2020-01-01',
    'createdBefore': data_fim,
    'situation': 'SOLD'  # ou 'CANCELED'
}
```

### Estrutura de Dados

#### Vendas Realizadas/Canceladas
```json
{
  "data": [
    {
      "id": "string",
      "enterpriseId": 19,
      "receivableBillId": "string",
      "refundBillId": "string",
      "proRataIndexer": "string",
      "number": "string",
      "situation": "SOLD",
      "externalId": "string",
      "note": "string",
      "cancellationReason": "string",
      "interestType": "string",
      "lateInterestCalculationType": "string",
      "financialInstitutionNumber": "string",
      "discountType": "string",
      "correctionType": "string",
      "anualCorrectionType": "string",
      "associativeCredit": "string",
      "discountPercentage": 0.0,
      "value": 1000.0,
      "totalSellingValue": 1000.0,
      "interestPercentage": 0.0,
      "fineRate": 0.0,
      "dailyLateInterestValue": 0.0,
      "creationDate": "YYYY-MM-DD",
      "contractDate": "YYYY-MM-DD",
      "issueDate": "YYYY-MM-DD",
      "cancellationDate": "YYYY-MM-DD",
      "financialInstitutionDate": "YYYY-MM-DD",
      "customers": [],
      "units": [],
      "paymentConditions": [],
      "brokers": []
    }
  ]
}
```

## 🏗️ Empreendimentos Sienge

### Fonte de Dados
- **Tabela**: `reservas.main.reservas_abril`
- **Colunas**: `idempreendimento`, `empreendimento`
- **Filtro**: `idempreendimento IS NOT NULL`

### Empreendimento Fixo
```python
empreendimento_fixo = {
    'id': 19,
    'nome': 'Ondina II'
}
```

### Query de Busca
```sql
SELECT DISTINCT 
    idempreendimento,
    empreendimento
FROM reservas.main.reservas_abril 
WHERE idempreendimento IS NOT NULL
ORDER BY empreendimento
```

## ⚡ Orquestração de APIs

### Classe Principal: `APIOrchestrator`

```python
class APIOrchestrator:
    def __init__(self):
        self.rate_limiters = {}
        self.request_history = []
        self.lock = threading.Lock()
    
    async def make_request(self, api_name, url, headers, params=None, data=None):
        # Rate limiting
        # Retry logic
        # Error handling
        # Statistics
```

### Rate Limiting por API

```python
rate_limits = {
    'cv_vendas': 60,
    'sienge_vendas_realizadas': 50,
    'sienge_vendas_canceladas': 50
}
```

### Controle de Janela
- **Janela**: 60 segundos
- **Contador**: Deque de timestamps
- **Limpeza**: Automática de registros antigos

## 🔄 Fluxo de Coleta

### 1. **CV Vendas**
```
Cliente → Paginação → Rate Limiting → Dados Brutos
```

### 2. **Sienge**
```
Empreendimentos → Loop por ID → Rate Limiting → Dados Brutos
```

### 3. **Processamento**
```
Dados Brutos → Normalização → DataFrames → MotherDuck
```

## 🛡️ Tratamento de Erros

### Códigos de Status
- **200**: Sucesso
- **429**: Rate limit excedido → Retry automático
- **404**: Fim dos dados → Parar paginação
- **500**: Erro do servidor → Log e continuar

### Estratégias de Retry
```python
if response.status == 429:
    retry_after = int(response.headers.get('Retry-After', '5'))
    wait = max(5, retry_after)
    await asyncio.sleep(wait)
    return await self.make_request(...)
```

### Timeouts
- **Por requisição**: 30 segundos
- **Pipeline completo**: 15 minutos
- **Por API**: Configurável

## 📊 Estatísticas

### Métricas Coletadas
- **Total de requisições**: Por API
- **Taxa de sucesso**: Por API
- **Tempo médio**: Por requisição
- **Falhas**: Por tipo de erro

### Logs Estruturados
```python
logger.info(f"✅ {api_name}: {response_time:.2f}s")
logger.warning(f"⚠️ {api_name}: Status {response.status}")
logger.error(f"❌ {api_name}: Erro - {str(e)}")
```

## 🔧 Configuração

### Variáveis de Ambiente
```bash
# CVCRM
CVCRM_EMAIL=seu_email@exemplo.com
CVCRM_TOKEN=seu_token_cvcrm

# Sienge
SIENGE_TOKEN=seu_token_sienge_basic

# MotherDuck
MOTHERDUCK_TOKEN=seu_token_motherduck
```

### Configuração por API
```python
def get_api_config(api_name):
    if api_name == 'cv_vendas':
        return APIConfig(
            name='CV Vendas',
            base_url='https://prati.cvcrm.com.br/api/v1/cvdw/vendas',
            headers={'accept': 'application/json', 'email': ..., 'token': ...},
            rate_limit=60
        )
```

## 🚀 Otimizações

### Coleta Inteligente
- **Madrugada**: Rate limiting mais agressivo
- **Dia**: Rate limiting conservador
- **Timeout**: Adaptativo por horário

### Processamento Paralelo
- **APIs simultâneas**: CV Vendas + Sienge
- **Empreendimentos**: Loop sequencial (rate limit)
- **Paginação**: Paralela por API

### Cache e Persistência
- **MotherDuck**: Armazenamento final
- **Full Refresh**: Substituição completa
- **Idempotência**: Execuções seguras

## 🔮 Melhorias Futuras

### Novas Integrações
- **APIs adicionais**: Fácil extensão
- **Webhooks**: Notificações em tempo real
- **Streaming**: Processamento contínuo

### Otimizações
- **Cache Redis**: Cache intermediário
- **Batch Processing**: Processamento em lotes
- **ML**: Análises preditivas

### Monitoramento
- **Health Checks**: Verificação de APIs
- **Alertas**: Notificações de falhas
- **Métricas**: Dashboard de performance
