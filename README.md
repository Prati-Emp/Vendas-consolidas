## Vendas Consolidadas

Integração e consolidação de dados de vendas a partir de múltiplas fontes:

- CVCRM: Reservas e Workflow (existentes)
- Sienge: Vendas Realizadas e Vendas Canceladas
- CVCRM: Relatório de Vendas (CV Vendas)

Os dados são tratados, padronizados e enviados para o MotherDuck, com orquestração de chamadas respeitando limites de requisição (rate limiting).

### Requisitos

- Python 3.10+
- Pip e virtualenv (recomendado)

### Instalação

1. Crie e ative um ambiente virtual (opcional, mas recomendado)
   - Windows PowerShell:
     ```bash
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

### Configuração

Crie um arquivo `.env` na raiz do projeto com as credenciais. Consulte `CONFIGURACAO_APIS.md` para detalhes.

Variáveis essenciais:

```env
# CVCRM (Reservas/Workflow)
CVCRM_EMAIL=seu_email@exemplo.com
CVCRM_TOKEN=seu_token_cvcrm

# MotherDuck
MOTHERDUCK_TOKEN=seu_token_motherduck

# Sienge
SIENGE_BASE_URL=https://api.sienge.com.br
SIENGE_TOKEN=seu_token_sienge

# CV Vendas
CV_VENDAS_BASE_URL=https://prati.cvcrm.com.br/api/v1/cvdw/vendas
CV_VENDAS_EMAIL=seu_email@exemplo.com
CV_VENDAS_TOKEN=seu_token_cv_vendas
```

### Estrutura dos Scripts

- `scripts/config.py`: Carrega e valida configurações/credenciais de todas as APIs
- `scripts/orchestrator.py`: Orquestra chamadas com rate limiting e estatísticas
- `scripts/sienge_apis.py`: Integração Sienge (realizadas/canceladas)
- `scripts/cv_vendas_api.py`: Integração CV Vendas
- `scripts/data_processor.py`: Padronização e consolidação de dados
- `scripts/update_motherduck_vendas.py`: Pipeline completo para o MotherDuck
- `scripts/test_integration.py`: Testes rápidos de integração

### Uso Rápido

1. Testar a integração:
   ```bash
   python scripts/test_integration.py
   ```

2. Executar a atualização completa no MotherDuck:
   ```bash
   python scripts/update_motherduck_vendas.py
   ```

### Tabelas no MotherDuck

- `vendas_consolidadas.main.vendas_consolidadas` (principal)
- `vendas_consolidadas.main.reservas`
- `vendas_consolidadas.main.workflow`
- `vendas_consolidadas.main.sienge_vendas_realizadas`
- `vendas_consolidadas.main.sienge_vendas_canceladas`
- `vendas_consolidadas.main.cv_vendas`

### Observações

- As chaves de API devem ser mantidas no `.env` (não versionado)
- O orquestrador limita requisições para evitar bloqueios das APIs
- Logs informam progresso e estatísticas durante a execução


