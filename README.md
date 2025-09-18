# 🏢 Dashboard de Reservas - Sistema de Vendas Consolidadas

Sistema completo de integração e consolidação de dados de vendas a partir de múltiplas fontes, com dashboard interativo para análise e visualização.

## 🎯 Funcionalidades

- **Integração com múltiplas APIs**: CVCRM, Sienge, CV Vendas
- **Dashboard interativo**: Streamlit com visualizações em tempo real
- **Armazenamento na nuvem**: MotherDuck para dados consolidados
- **Rate limiting inteligente**: Respeita limites das APIs
- **Processamento assíncrono**: Coleta eficiente de grandes volumes de dados

## 📊 Fontes de Dados

- **CVCRM**: Reservas e Workflow (existentes)
- **Sienge**: Vendas Realizadas e Vendas Canceladas
- **CVCRM**: Relatório de Vendas (CV Vendas)

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

1. **Testar a integração**:
   ```bash
   python scripts/test_integration.py
   ```

2. **Executar upload de dados**:
   ```bash
   python upload_vendas_funcional.py
   ```

3. **Executar a atualização completa no MotherDuck**:
   ```bash
   python scripts/update_motherduck_vendas.py
   ```

4. **Executar o dashboard**:
   ```bash
   streamlit run dashboard/Home.py
   ```
   Acesse: http://localhost:8501

### Tabelas no MotherDuck

- `vendas_consolidadas.main.vendas_consolidadas` (principal)
- `vendas_consolidadas.main.reservas`
- `vendas_consolidadas.main.workflow`
- `vendas_consolidadas.main.sienge_vendas_realizadas`
- `vendas_consolidadas.main.sienge_vendas_canceladas`
- `vendas_consolidadas.main.cv_vendas`

## 🚀 Estrutura do Projeto

```
dash-reservas/
├── dashboard/                 # Dashboard Streamlit
│   ├── Home.py               # Página principal
│   ├── pages/                # Páginas do dashboard
│   └── utils.py              # Utilitários
├── scripts/                  # Scripts principais
│   ├── config.py             # Configurações das APIs
│   ├── cv_vendas_api.py      # API CV Vendas
│   ├── sienge_apis.py        # APIs Sienge
│   ├── orchestrator.py       # Orquestrador de requisições
│   └── update_motherduck_vendas.py  # Pipeline completo
├── upload_vendas_funcional.py # Script de upload otimizado
├── create_vendas_direct.py   # Criação direta de tabelas
├── requirements.txt          # Dependências Python
├── .gitignore               # Arquivos ignorados pelo Git
└── README.md                # Este arquivo
```

## 📝 Observações Importantes

- **Segurança**: As chaves de API devem ser mantidas no `.env` (não versionado)
- **Rate Limiting**: O orquestrador limita requisições para evitar bloqueios das APIs
- **Logs**: Sistema informa progresso e estatísticas durante a execução
- **Timeout**: Scripts têm timeout para evitar travamentos
- **Dashboard**: Interface web para visualização dos dados consolidados

## 🔧 Desenvolvimento

Para contribuir com o projeto:

1. Clone o repositório
2. Crie um ambiente virtual
3. Instale as dependências: `pip install -r requirements.txt`
4. Configure o arquivo `.env` com suas credenciais
5. Execute os testes: `python scripts/test_integration.py`


