# 📅 Atualização do Cronograma de Execução

## Visão Geral

Este documento descreve as mudanças implementadas no sistema de atualização automática para otimizar a frequência de execução das APIs, mantendo a eficiência e respeitando as limitações específicas de cada integração.

## 🎯 Objetivos das Mudanças

- **Atualização Diária**: APIs que podem ser executadas diariamente
- **Atualização 2x/Semana**: APIs Sienge com limitações específicas
- **Segurança**: Implementação sem interrupção do sistema atual
- **Flexibilidade**: Fácil manutenção e ajustes futuros

## 📊 Mapeamento de APIs

### APIs com Atualização Diária
- ✅ **CV Vendas** - Relatórios de vendas
- ✅ **CV Repasses** - Dados de repasses
- ✅ **CV Leads** - Dados de leads
- ✅ **CV Repasses Workflow** - Workflow de repasses

### APIs com Atualização 2x/Semana (Sienge)
- ⚠️ **Sienge Vendas Realizadas** - Domingos 23:40 e Quartas 01:15
- ⚠️ **Sienge Vendas Canceladas** - Domingos 23:40 e Quartas 01:15

## 🚀 Implementação

### 1. Workflows GitHub Actions

#### Workflow Diário (`.github/workflows/update-database-daily.yml`)
```yaml
# Execução: Diariamente às 05:00 BRT (08:00 UTC)
- cron: '0 8 * * *'
```

**APIs Executadas:**
- CV Vendas
- CV Repasses  
- CV Leads
- CV Repasses Workflow

**Script:** `scripts/update_motherduck_daily.py`

#### Workflow Sienge (`.github/workflows/update-database-sienge.yml`)
```yaml
# Execução: Domingo 23:40 BRT (02:40 UTC) e Quarta 01:15 BRT (04:15 UTC)
- cron: '40 2 * * 0'  # Domingo
- cron: '15 4 * * 3'  # Quarta-feira
```

**APIs Executadas:**
- Sienge Vendas Realizadas
- Sienge Vendas Canceladas

**Script:** `scripts/update_motherduck_sienge.py`

### 2. Scripts de Execução

#### Script Diário (`update_motherduck_daily.py`)
- **Função**: Executa apenas APIs não-Sienge
- **Timeout**: 15 minutos
- **Rate Limiting**: Otimizado para execução diária
- **Tratamento de Erros**: Robusto com fallbacks

#### Script Sienge (`update_motherduck_sienge.py`)
- **Função**: Executa apenas APIs Sienge
- **Delay**: 5 minutos entre vendas realizadas e canceladas
- **Timeout**: 15 minutos
- **Rate Limiting**: Conservador (2x/semana)

### 3. Workflow Original (Desabilitado)

O workflow original (`update-database.yml`) foi desabilitado mas mantido como backup:
- **Status**: Comentado (não executa automaticamente)
- **Disponível**: Para execução manual se necessário
- **Backup**: Em caso de problemas com os novos workflows

## ⏰ Cronograma de Execução

### Segunda a Sábado
- **05:00 BRT**: Atualização diária (CV Vendas, Repasses, Leads, Workflow)
- **Duração**: ~5-10 minutos
- **APIs**: 4 APIs simultâneas

### Domingo
- **23:40 BRT**: Atualização Sienge (Vendas Realizadas e Canceladas)
- **05:00 BRT**: Atualização diária (CV Vendas, Repasses, Leads, Workflow)
- **Duração**: ~15-20 minutos total

### Quarta-feira
- **01:15 BRT**: Atualização Sienge (Vendas Realizadas e Canceladas)
- **05:00 BRT**: Atualização diária (CV Vendas, Repasses, Leads, Workflow)
- **Duração**: ~15-20 minutos total

## 🔧 Configuração

### Variáveis de Ambiente

#### Workflow Diário
```yaml
env:
  MOTHERDUCK_TOKEN: ${{ secrets.MOTHERDUCK_TOKEN }}
  CVCRM_EMAIL: ${{ secrets.CVCRM_EMAIL }}
  CVCRM_TOKEN: ${{ secrets.CVCRM_TOKEN }}
  CV_VENDAS_BASE_URL: ${{ secrets.CV_VENDAS_BASE_URL }}
  DAILY_UPDATE_MODE: 'true'
  SKIP_SIENGE_APIS: 'true'
```

#### Workflow Sienge
```yaml
env:
  MOTHERDUCK_TOKEN: ${{ secrets.MOTHERDUCK_TOKEN }}
  SIENGE_BASE_URL: ${{ secrets.SIENGE_BASE_URL }}
  SIENGE_TOKEN: ${{ secrets.SIENGE_TOKEN }}
  SIENGE_ONLY_MODE: 'true'
  SIENGE_SKIP_CANCELADAS: 'false'
```

## 📊 Benefícios

### 1. **Eficiência**
- APIs diárias executam mais frequentemente
- Dados mais atualizados para análise
- Redução de latência nos relatórios

### 2. **Economia de Recursos**
- Sienge executa apenas quando necessário
- Rate limiting otimizado por tipo de API
- Redução de requisições desnecessárias

### 3. **Flexibilidade**
- Fácil ajuste de horários
- Execução manual disponível
- Workflows independentes

### 4. **Segurança**
- Implementação sem interrupção
- Workflow original como backup
- Testes manuais antes da ativação

## 🧪 Testes e Validação

### 1. **Teste Manual**
```bash
# Testar workflow diário
gh workflow run update-database-daily.yml

# Testar workflow Sienge
gh workflow run update-database-sienge.yml
```

### 2. **Validação de Dados**
- Verificar contagem de registros
- Validar timestamps de atualização
- Confirmar integridade dos dados

### 3. **Monitoramento**
- Logs de execução
- Taxa de sucesso
- Tempo de execução

## 🔄 Rollback

Em caso de problemas, é possível reativar o workflow original:

1. **Descomentar** o schedule no `update-database.yml`
2. **Comentar** os schedules nos novos workflows
3. **Executar** manualmente para validar

## 📈 Métricas Esperadas

### Antes da Mudança
- **Frequência**: 2x/semana (segunda e quinta)
- **APIs**: Todas simultaneamente
- **Duração**: ~10-15 minutos

### Após a Mudança
- **Frequência Diária**: 6x/semana (segunda a sábado)
- **Frequência Sienge**: 2x/semana (domingo e quarta)
- **Duração Diária**: ~5-10 minutos
- **Duração Sienge**: ~10-15 minutos

## 🚨 Considerações Importantes

### 1. **Rate Limiting**
- Sienge mantém limitações rigorosas
- CV APIs podem ser executadas mais frequentemente
- Monitoramento de limites essencial

### 2. **Dependências**
- Scripts independentes
- Falha em um não afeta o outro
- Recuperação automática

### 3. **Manutenção**
- Logs separados por tipo
- Debugging mais fácil
- Ajustes independentes

## 🔮 Próximos Passos

### 1. **Ativação Gradual**
- Testar workflows manualmente
- Validar dados por 1 semana
- Ativar execução automática

### 2. **Monitoramento**
- Dashboard de métricas
- Alertas de falha
- Relatórios de performance

### 3. **Otimizações Futuras**
- Cache intermediário
- Processamento paralelo
- ML para previsão de falhas

## 📚 Referências

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Cron Schedule Syntax](https://crontab.guru/)
- [Sistema de Vendas Consolidadas - Arquitetura](./arquitetura.md)
- [APIs Externas - Documentação](./apis-externas.md)

---

*Última atualização: $(date)*
*Versão: 1.0*
*Status: Implementado - Aguardando Testes*



