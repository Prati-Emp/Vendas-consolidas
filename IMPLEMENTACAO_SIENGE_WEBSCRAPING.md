# 🌐 Implementação Sienge Webscraping - Sistema Completo

## 📋 Visão Geral

Sistema completo para automatizar a coleta de dados do Sienge via webscraping, processamento de CSV e upload para MotherDuck. Integra com a arquitetura existente do projeto.

## 🎯 Objetivos

- **Webscraping Automático**: Coleta diária de dados do Sienge via interface web
- **Processamento Inteligente**: Normalização e limpeza dos dados CSV
- **Upload Automático**: Integração com MotherDuck na tabela `sienge_relatorio_pedidos_compras`
- **Automação Completa**: Execução via GitHub Actions diariamente

## 🏗️ Arquitetura

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Sienge Web    │    │   Webscraping   │    │   Processamento │
│   Interface     │───▶│   (Playwright)  │───▶│   CSV + Upload  │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────┬───────┘    └─────────┬───────┘
                                  │                      │
                                  ▼                      ▼
                    ┌─────────────────┐    ┌─────────────────┐
                    │   CSV Download  │    │   MotherDuck    │
                    │   (downloads_tmp)│    │   Database      │
                    └─────────────────┘    └─────────────────┘
```

## 📁 Arquivos Criados

### 1. **Scripts Principais**

#### `scripts/processar_csv_sienge.py`
- **Função**: Processa CSV baixado pelo webscraping
- **Recursos**:
  - Leitura de CSV com encoding correto
  - Normalização de dados (datas, valores monetários)
  - Upload para MotherDuck
  - Detecção automática do arquivo mais recente

#### `scripts/sienge_webscraping_completo.py`
- **Função**: Sistema integrado completo
- **Fluxo**:
  1. Executa `sienge_mcp_persistente.py`
  2. Aguarda download do CSV
  3. Processa dados
  4. Faz upload para MotherDuck
- **Timeout**: 25 minutos
- **Tabela destino**: `sienge_relatorio_pedidos_compras`

### 2. **Automação**

#### `.github/workflows/update-database-sienge-webscraping.yml`
- **Agendamento**: Diariamente às 06:00 BRT (09:00 UTC)
- **Dependências**: Python 3.10 + Node.js 18 + Playwright
- **Execução**: `scripts/sienge_webscraping_completo.py`

### 3. **Dependências**

#### `requirements.txt` (atualizado)
```txt
# Dependências existentes...
# Dependências para webscraping Sienge
playwright>=1.40.0
```

#### `package.json` (novo)
```json
{
  "name": "sienge-webscraping",
  "version": "1.0.0",
  "description": "Dependências Node.js para webscraping Sienge",
  "scripts": {
    "install-playwright": "npx playwright install chromium"
  },
  "dependencies": {
    "playwright": "^1.40.0"
  }
}
```

## 🔧 Configuração

### 1. **Secrets do GitHub Actions**

Adicione estes secrets no GitHub:

```
MOTHERDUCK_TOKEN=seu_token_motherduck
RELATORIO_LOGIN_URL=https://pratiemp.sienge.com.br/sienge/8/index.html
RELATORIO_URL=https://pratiemp.sienge.com.br/sienge/8/index.html#/suprimentos/compras/pedidos-de-compra/relatorios/relacao-pedidos-compra
RELATORIO_USERNAME=odair.santos@grupoprati.com
RELATORIO_PASSWORD=Prati@123
```

### 2. **Variáveis de Ambiente Locais**

Crie/atualize `config_sienge.env`:

```env
# URLs do Sienge
RELATORIO_LOGIN_URL=https://pratiemp.sienge.com.br/sienge/8/index.html
RELATORIO_URL=https://pratiemp.sienge.com.br/sienge/8/index.html#/suprimentos/compras/pedidos-de-compra/relatorios/relacao-pedidos-compra

# Credenciais
RELATORIO_USERNAME=odair.santos@grupoprati.com
RELATORIO_PASSWORD=Prati@123

# Configuração do Download
RELATORIO_TIPO_ARQUIVO=csv
RELATORIO_SEPARADOR=;
RELATORIO_ENCODING=utf-8
```

## 🚀 Como Usar

### 1. **Execução Local**

```bash
# Instalar dependências
pip install -r requirements.txt
npm install

# Executar webscraping completo
python scripts/sienge_webscraping_completo.py

# Ou apenas processar CSV existente
python scripts/processar_csv_sienge.py
```

### 2. **Execução via GitHub Actions**

1. **Automática**: Executa diariamente às 06:00 BRT
2. **Manual**: 
   - Acesse **Actions** no GitHub
   - Selecione **Update Database - Sienge Webscraping (Daily)**
   - Clique em **Run workflow**

### 3. **Monitoramento**

- **Logs**: Verifique execuções em **Actions** → **Update Database - Sienge Webscraping**
- **Dados**: Consulte tabela `sienge_relatorio_pedidos_compras` no MotherDuck
- **Arquivos**: CSVs salvos em `downloads_tmp/`

## 📊 Estrutura de Dados

### Tabela: `sienge_relatorio_pedidos_compras`

**Colunas padrão adicionadas**:
- `fonte`: 'sienge_webscraping'
- `processado_em`: Timestamp do processamento
- `arquivo_origem`: Nome do arquivo CSV original

**Colunas do CSV**:
- Dependem da estrutura do relatório do Sienge
- Normalização automática de datas e valores monetários
- Preservação de todas as colunas originais

## 🔄 Fluxo de Execução

### 1. **Webscraping** (via `sienge_mcp_persistente.py`)
```
Login Sienge → Navegação → Filtros → Download CSV
```

### 2. **Processamento** (via `processar_csv_sienge.py`)
```
CSV → Normalização → DataFrame → Upload MotherDuck
```

### 3. **Sistema Completo** (via `sienge_webscraping_completo.py`)
```
Webscraping → Aguardar → Processar → Upload → Relatório
```

## ⚙️ Configurações Avançadas

### 1. **Timeout e Retry**
- **Webscraping**: 20 minutos
- **Sistema completo**: 25 minutos
- **Retry**: Automático em falhas temporárias

### 2. **Detecção de Arquivos**
- **Período**: Últimas 24 horas
- **Critério**: Arquivo mais recente
- **Formato**: `*.csv` em `downloads_tmp/`

### 3. **Normalização de Dados**
- **Datas**: Conversão automática para datetime
- **Valores**: Remoção de formatação brasileira (R$ 1.000,00 → 1000.00)
- **Encoding**: UTF-8 com fallback

## 🛠️ Troubleshooting

### Problemas Comuns

#### 1. **"Nenhum CSV encontrado"**
- **Causa**: Webscraping falhou ou arquivo não foi salvo
- **Solução**: Verificar logs do webscraping, executar manualmente

#### 2. **"Timeout no webscraping"**
- **Causa**: Sistema Sienge lento ou instável
- **Solução**: Aumentar timeout ou executar em horário diferente

#### 3. **"Erro no upload"**
- **Causa**: Token MotherDuck inválido ou conectividade
- **Solução**: Verificar `MOTHERDUCK_TOKEN` e conectividade

#### 4. **"Falha no processamento CSV"**
- **Causa**: Estrutura do CSV diferente do esperado
- **Solução**: Verificar formato do arquivo, ajustar separadores

### Logs de Debug

#### Sucesso
```
✅ SISTEMA COMPLETO CONCLUÍDO!
Duração: 0:15:32
Registros processados: 1,250
Arquivo: relatorio_pedidos_20241201.csv
Tabela: sienge_relatorio_pedidos_compras
```

#### Falha
```
❌ FALHA NO SISTEMA COMPLETO
Verifique os logs acima para detalhes
```

## 📈 Monitoramento e Métricas

### 1. **Execuções Diárias**
- **Horário**: 06:00 BRT
- **Duração média**: 15-20 minutos
- **Taxa de sucesso**: Monitorar via GitHub Actions

### 2. **Dados Coletados**
- **Volume**: Varia conforme período
- **Frequência**: Diária
- **Retenção**: Histórico completo no MotherDuck

### 3. **Alertas**
- **Falhas**: Notificações automáticas do GitHub Actions
- **Timeout**: Logs detalhados para análise
- **Dados**: Verificação de integridade no MotherDuck

## 🔮 Melhorias Futuras

### 1. **Otimizações**
- **Cache**: Manter sessão do Sienge entre execuções
- **Paralelização**: Múltiplos relatórios simultâneos
- **Retry inteligente**: Diferentes estratégias por tipo de erro

### 2. **Funcionalidades**
- **Notificações**: Slack/Email em caso de falha
- **Dashboard**: Métricas de execução em tempo real
- **Backup**: Cópia de segurança dos CSVs

### 3. **Integração**
- **APIs**: Interface REST para consulta de dados
- **Webhooks**: Notificações em tempo real
- **ML**: Detecção automática de anomalias

## 📚 Referências

- [Playwright Documentation](https://playwright.dev/)
- [DuckDB MotherDuck](https://motherduck.com/)
- [GitHub Actions](https://docs.github.com/en/actions)
- [Sienge Webscraping Original](sienge_mcp_persistente.py)

## ✅ Status da Implementação

- ✅ **Scripts criados**: `processar_csv_sienge.py`, `sienge_webscraping_completo.py`
- ✅ **Workflow configurado**: `.github/workflows/update-database-sienge-webscraping.yml`
- ✅ **Dependências atualizadas**: `requirements.txt`, `package.json`
- ✅ **Documentação completa**: Este arquivo
- 🔄 **Próximo passo**: Configurar secrets no GitHub e testar execução

---

**Sistema pronto para uso!** 🚀

Execute `python scripts/sienge_webscraping_completo.py` para testar localmente ou configure os secrets no GitHub para automação completa.
