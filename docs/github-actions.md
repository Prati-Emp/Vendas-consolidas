# 🚀 GitHub Actions - Pipeline de Automação

## Visão Geral

O sistema utiliza GitHub Actions para automatizar a atualização dos dados no MotherDuck, executando às 01:15 UTC (04:15 BRT) nas segundas e quintas-feiras.

## 📋 Workflows Mensais (dia 5 e dia 7)

| Workflow | Arquivo | Agendamento | Descrição |
|----------|---------|-------------|-----------|
| **Stock Inventories** | `update-database-stock-inventories.yml` | Dia **5** de cada mês, 05:00 UTC | API Sienge Stock Inventories → `operacoes.sienge_stock_inventories` (atualização incremental por `Data_Snapshot`) |
| **Medições** | `update-database-medicoes.yml` | Dia **7** de cada mês, 05:00 UTC | API Sienge Building Cost Estimation Items → `operacoes.sienge_medicoes` |

Credenciais: `SIENGE_TOKEN` e `MOTHERDUCK_TOKEN` (mesmos já configurados no repositório). Stock Inventories não usa modo inicial; cada execução grava um snapshot com `Data_Snapshot` = último dia do mês anterior.

---

## 📋 Workflow Atual (principal)

### Arquivo: `.github/workflows/update-database.yml`

```yaml
name: Update Database - Madrugada

on:
  schedule:
    # Executar às 01:15 da manhã (4:15 BRT) - Segunda e Quinta-feira
    - cron: '15 1 * * 1'  # Segunda-feira
    - cron: '15 1 * * 4'  # Quinta-feira
  workflow_dispatch:
    inputs:
      reason:
        description: 'Razão para executar a atualização'
        required: false
        default: 'Atualização manual'
        type: string
```

## 🔧 Configuração do Ambiente

### Variáveis de Ambiente (Secrets)
```yaml
env:
  MOTHERDUCK_TOKEN: ${{ secrets.MOTHERDUCK_TOKEN }}
  # Pausar canceladas temporariamente (apenas realizadas)
  SIENGE_SKIP_CANCELADAS: 'true'
  CVCRM_EMAIL: ${{ secrets.CVCRM_EMAIL }}
  CVCRM_TOKEN: ${{ secrets.CVCRM_TOKEN }}
  CV_VENDAS_BASE_URL: ${{ secrets.CV_VENDAS_BASE_URL }}
  SIENGE_BASE_URL: ${{ secrets.SIENGE_BASE_URL }}
  SIENGE_TOKEN: ${{ secrets.SIENGE_TOKEN }}
  PYTHONPATH: ${{ github.workspace }}/scripts:${{ github.workspace }}
```

### Dependências Instaladas
```bash
python -m pip install --upgrade pip
pip install duckdb==1.2.2
pip install -r requirements.txt
```

## 📊 Passos do Workflow

### 1. **Setup do Ambiente**
```yaml
- uses: actions/checkout@v3
- name: Set up Python
  uses: actions/setup-python@v4
  with:
    python-version: '3.10'
```

### 2. **Instalação de Dependências**
```yaml
- name: Install dependencies
  run: |
    python -m pip install --upgrade pip
    pip install duckdb==1.2.2
    pip install -r requirements.txt
```

### 3. **Configuração de Permissões**
```yaml
- name: Set file permissions
  run: chmod +x scripts/*.py
```

### 4. **Execução da Atualização**
```yaml
- name: Update database
  env:
    MOTHERDUCK_TOKEN: ${{ secrets.MOTHERDUCK_TOKEN }}
    CVCRM_EMAIL: ${{ secrets.CVCRM_EMAIL }}
    CVCRM_TOKEN: ${{ secrets.CVCRM_TOKEN }}
    SIENGE_TOKEN: ${{ secrets.SIENGE_TOKEN }}
    # Controle de execução (Sienge: 2x/semana, CV: diário)
    SIENGE_SKIP_CANCELADAS: ${{ vars.SIENGE_SKIP_CANCELADAS || 'false' }}
    CV_REPASSES_ENABLED: 'true'
  run: |
    echo "🌙 Iniciando atualização do MotherDuck (madrugada)..."
    python -u scripts/update_motherduck_vendas.py
```

### 5. **Notificações**
```yaml
- name: Notify success
  if: success()
  run: echo "✅ Database updated successfully at $(date)"

- name: Notify failure
  if: failure()
  run: echo "❌ Database update failed at $(date)"
```

## 🎯 Script de Execução

### Arquivo: `scripts/update_motherduck_vendas.py`

**Função**: Wrapper inteligente que executa o pipeline completo

**Características**:
- ✅ Validação de variáveis de ambiente
- ✅ Timeout de 15 minutos
- ✅ Logs detalhados
- ✅ Códigos de saída apropriados
- ✅ Tratamento de erros

**Fluxo**:
1. Verifica variáveis de ambiente
2. Importa `sistema_completo.py`
3. Executa pipeline com timeout
4. Retorna status de sucesso/falha

## 📈 Monitoramento

### Logs do GitHub Actions
- **Timestamp**: Hora de execução
- **Duração**: Tempo total de execução
- **Status**: Sucesso/Falha
- **Detalhes**: Logs do pipeline

### Métricas Importantes
- **Tempo de Execução**: ~5-10 minutos
- **Taxa de Sucesso**: 100% (após correção)
- **Dados Processados**: Varia por dia
- **APIs Chamadas**: CV Vendas + Sienge

## 🔍 Troubleshooting

### Problemas Comuns

#### 1. **Arquivo não encontrado**
```
python: can't open file 'scripts/update_motherduck_vendas.py'
```
**Solução**: ✅ **RESOLVIDO** - Arquivo criado

#### 2. **Variáveis de ambiente faltando**
```
❌ MOTHERDUCK_TOKEN não encontrado
```
**Solução**: Verificar secrets no GitHub

#### 3. **Timeout**
```
⏰ Timeout - operação demorou mais de 15 minutos
```
**Solução**: Otimizar pipeline ou aumentar timeout

#### 4. **Erro de conexão**
```
❌ Erro ao conectar ao MotherDuck
```
**Solução**: Verificar token e conectividade

### Logs de Debug

#### Sucesso
```
🌙 INICIANDO ATUALIZAÇÃO DO MOTHERDUCK (MADRUGADA)
✅ Todas as variáveis de ambiente estão configuradas
🚀 Executando pipeline completo de atualização...
✅ ATUALIZAÇÃO CONCLUÍDA COM SUCESSO!
```

#### Falha
```
❌ ERRO INESPERADO: [detalhes do erro]
🔍 Verifique a configuração e conectividade
```

## 🛠️ Manutenção

### Execução Manual
1. Acesse **Actions** no GitHub
2. Selecione **Update Database - Madrugada**
3. Clique em **Run workflow**
4. Adicione motivo (opcional)
5. Clique em **Run workflow**

### Verificação de Status
1. Acesse **Actions** → **Update Database - Madrugada**
2. Verifique execuções recentes
3. Clique na execução para ver logs
4. Verifique status: ✅ Sucesso / ❌ Falha

### Atualização de Secrets
1. Acesse **Settings** → **Secrets and variables** → **Actions**
2. Adicione/edite secrets necessários
3. Teste com execução manual

## 📊 Histórico de Execuções

### Status Atual
- ✅ **Última execução**: Sucesso
- ✅ **Pipeline**: Funcionando
- ✅ **Dados**: Atualizados
- ✅ **Dashboard**: Operacional

### Próximas Execuções
- **Agendada**: 01:15 UTC (04:15 BRT)
- **Frequência**: Diária
- **Duração estimada**: 5-10 minutos

## 🔮 Melhorias Futuras

### Monitoramento Avançado
- **Alertas**: Notificações por email/Slack
- **Métricas**: Dashboard de métricas
- **Logs**: Centralização de logs

### Otimizações
- **Cache**: Cache de dados intermediários
- **Paralelização**: Execução paralela de APIs
- **Retry**: Retry inteligente para falhas

### Integração
- **Webhooks**: Notificações externas
- **APIs**: Interface programática
- **CI/CD**: Pipeline mais robusto

## 📚 Referências

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Cron Schedule Syntax](https://crontab.guru/)
- [Python in GitHub Actions](https://docs.github.com/en/actions/using-python)
- [Secrets Management](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
