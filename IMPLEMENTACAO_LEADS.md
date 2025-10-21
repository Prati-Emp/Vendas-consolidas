# 🎯 Implementação da API de Leads - Resumo

## ✅ O que foi implementado

### 1. **API de Leads** (`scripts/cv_leads_api.py`)
- ✅ Cliente para API do CVCRM `/cvdw/leads`
- ✅ Paginação automática (500 registros/página)
- ✅ Filtros: manter "Prati" OU imobiliária vazia
- ✅ Rate limiting (60 req/min)
- ✅ Processamento de dados com pandas
- ✅ Logs detalhados e estatísticas

### 2. **Configuração** (`scripts/config.py`)
- ✅ Adicionada configuração para `'cv_leads'`
- ✅ Mesmas credenciais do CV Vendas
- ✅ Rate limit configurado (60 req/min)
- ✅ Headers corretos (email + token)

### 3. **Integração no Sistema** (`sistema_completo.py`)
- ✅ Import da API de Leads
- ✅ Coleta de dados no pipeline principal
- ✅ Upload para tabela `main.cv_leads` no MotherDuck
- ✅ Estatísticas incluídas no resumo final
- ✅ Tratamento de erros e fallback

### 4. **GitHub Actions** (`.github/workflows/update-database.yml`)
- ✅ Flag `CV_LEADS_ENABLED: 'true'` adicionada
- ✅ Execução automática nas segundas e quintas
- ✅ Variáveis de ambiente configuradas

### 5. **Documentação**
- ✅ Documentação específica (`docs/cv-leads-api.md`)
- ✅ Atualização da documentação geral (`docs/apis-externas.md`)
- ✅ Mapa de integrações atualizado

### 6. **Scripts de Teste**
- ✅ `teste_leads.py` - Teste individual da API
- ✅ `teste_sistema_completo_leads.py` - Teste do sistema completo

## 🗄️ Estrutura da Tabela

### Tabela: `main.cv_leads`
```sql
CREATE TABLE main.cv_leads (
    Idlead VARCHAR,
    Data_cad TIMESTAMP,
    Situacao VARCHAR,
    Imobiliaria VARCHAR,
    nome_situacao_anterior_lead VARCHAR,
    gestor VARCHAR,
    empreendimento_primeiro VARCHAR,
    empreendimento_ultimo VARCHAR,
    referencia_data TIMESTAMP,
    data_reativacao TIMESTAMP,
    corretor VARCHAR,
    corretor_ultimo VARCHAR,
    corretor_consolidado VARCHAR,
    tags VARCHAR,
    tag1 VARCHAR,
    tag2 VARCHAR,
    tagN VARCHAR,
    midia_original VARCHAR,
    midia_ultimo VARCHAR,
    midia_consolidada VARCHAR,
    motivo_cancelamento VARCHAR,
    data_cancelamento TIMESTAMP,
    ultima_data_conversao TIMESTAMP,
    descricao_motivo_cancelamento VARCHAR,
    possibilidade_venda VARCHAR,
    score VARCHAR,
    novo VARCHAR,
    retorno VARCHAR,
    data_ultima_alteracao TIMESTAMP,
    campo_[nome_dinamico] VARCHAR,  -- Colunas dinâmicas baseadas nos nomes únicos
    fonte VARCHAR DEFAULT 'cv_leads',
    processado_em TIMESTAMP
);
```

**Nota:** As colunas `campo_[nome_dinamico]` são criadas dinamicamente baseadas nos valores únicos encontrados na coluna `nome` dos campos adicionais. O número e nomes dessas colunas podem variar conforme os dados.

## 🔧 Como usar

### 1. **Teste Individual**
```bash
python teste_leads.py
```

### 2. **Teste do Sistema Completo**
```bash
python teste_sistema_completo_leads.py
```

### 3. **Execução Manual**
```bash
python sistema_completo.py
```

### 4. **Execução Automática**
- GitHub Actions executa automaticamente
- Segundas e quintas às 01:15 UTC (04:15 BRT)
- Flag `CV_LEADS_ENABLED: 'true'` ativa

## 📊 Filtros Aplicados

### Critérios de Inclusão
- ✅ Imobiliária contém "Prati" (case insensitive)
- ✅ Imobiliária vazia ou nula
- ❌ Outras imobiliárias são filtradas

### Exemplo de Filtros
```python
# INCLUÍDO
"Imobiliaria": "Prati Imóveis"
"Imobiliaria": "Prati"
"Imobiliaria": ""
"Imobiliaria": null

# EXCLUÍDO
"Imobiliaria": "Outra Imobiliária"
"Imobiliaria": "Construtora XYZ"
```

## 🚀 Execução

### Variáveis de Ambiente Necessárias
```bash
CVCRM_EMAIL=seu_email@exemplo.com
CVCRM_TOKEN=seu_token_cvcrm
MOTHERDUCK_TOKEN=seu_token_motherduck
```

### Rate Limiting
- **Limite**: 60 requisições/minuto
- **Delay**: 0.0s entre chamadas
- **Timeout**: 30s por requisição

### Performance Esperada
- **Registros/página**: 500
- **Páginas típicas**: 10-50
- **Tempo total**: 2-5 minutos
- **Taxa de sucesso**: >95%

## 📈 Monitoramento

### Logs de Debug
```
=== BUSCANDO LEADS SEM FILTRO DE DATA ===
Filtro imobiliária: 'Prati' (incluir vazias: True)
Página 1: 500 registros (Total: 500)
Debug - Imobiliaria: 'Prati Imóveis', is_prati: True, is_empty: False
...
=== RESUMO ===
Total de registros processados: 5000
Total de registros filtrados (Prati + vazias): 1200
Registros finais salvos: 1200
```

### Estatísticas Finais
```
📊 Resumo:
   - CV Vendas: 1,500 registros
   - CV Repasses: 800 registros
   - CV Leads: 1,200 registros
   - Sienge Realizadas: 300 registros
   - Sienge Canceladas: 50 registros
   - Upload: ✅ Sucesso
```

## 🔍 Troubleshooting

### Problemas Comuns

#### 1. **Nenhum registro encontrado**
- Verificar se há dados na API
- Verificar se os filtros estão corretos
- Verificar credenciais

#### 2. **Erro de timeout**
- Aumentar timeout no teste
- Verificar conectividade
- Verificar rate limiting

#### 3. **Erro de upload**
- Verificar token do MotherDuck
- Verificar conectividade
- Verificar permissões

### Logs de Debug
```bash
# Ativar logs detalhados
export PYTHONPATH=$PWD/scripts:$PWD
python -u scripts/cv_leads_api.py
```

## 🎉 Próximos Passos

### 1. **Validação**
- [ ] Executar teste individual
- [ ] Executar teste completo
- [ ] Verificar dados no MotherDuck
- [ ] Validar no dashboard

### 2. **Produção**
- [ ] Configurar GitHub Actions
- [ ] Monitorar execuções
- [ ] Verificar logs
- [ ] Ajustar configurações se necessário

### 3. **Melhorias Futuras**
- [ ] Cache de dados
- [ ] Filtros de data
- [ ] Análise de tendências
- [ ] Alertas automáticos

## 📚 Referências

- [Documentação da API de Leads](./docs/cv-leads-api.md)
- [APIs Externas](./docs/apis-externas.md)
- [GitHub Actions](./docs/github-actions.md)
- [Arquitetura](./docs/arquitetura.md)

---

**Status**: ✅ **IMPLEMENTAÇÃO CONCLUÍDA**

**Data**: $(date)

**Autor**: Sistema de Vendas Consolidadas



