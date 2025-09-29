# 🔗 CV VGV Empreendimentos API - Documentação

## Visão Geral

A API de VGV Empreendimentos do CVCRM foi integrada ao sistema de vendas consolidadas para capturar dados de tabelas de preço e unidades de empreendimentos com filtros específicos para tabelas de financiamento.

## 📊 Endpoint e Configuração

### Endpoint
- **URL**: `https://prati.cvcrm.com.br/api/v1/cv/tabelasdepreco`
- **Método**: GET
- **Autenticação**: Email + Token (mesmas credenciais do CV Vendas)

### Headers
```python
headers = {
    'accept': 'application/json',
    'email': os.environ.get('CVCRM_EMAIL'),
    'token': os.environ.get('CVCRM_TOKEN')
}
```

### Parâmetros de Busca
```python
params = {
    'idempreendimento': id_empreendimento,  # ID do empreendimento (1-20)
    'idtabela': id_tabela                   # ID da tabela (opcional)
}
```

## 🔍 Processamento de Dados

### Teste de IDs
- **Range**: IDs de 1 a 20 (configurável)
- **Validação**: Verifica se empreendimento tem tabelas disponíveis
- **Seleção**: Prioriza tabelas de financiamento, senão usa primeira disponível

### Expansão de Unidades
- **Explode**: Lista de unidades em registros individuais
- **Normalização**: Campos das unidades com prefixo 'unidades.'
- **Limpeza**: Remove colunas 'series' e 'referencia'

### Campos Normalizados
```json
{
  "id_empreendimento": "integer",
  "id_tabela": "integer", 
  "nome_tabela": "string",
  "nome_empreendimento": "string",
  "unidades.etapa": "string",
  "unidades.bloco": "string",
  "unidades.unidade": "string",
  "unidades.idunidade": "string",
  "unidades.area_privativa": "float",
  "unidades.situacao": "string",
  "unidades.valor_total": "float"
}
```

## 🏗️ Implementação

### Arquivo Principal
- **Localização**: `scripts/cv_vgv_empreendimentos_api.py`
- **Classe**: `CVVGVEmpreendimentosAPIClient`
- **Função Principal**: `obter_dados_vgv_empreendimentos()`

### Configuração
- **Arquivo**: `scripts/config.py`
- **Nome da API**: `'cv_vgv_empreendimentos'`
- **Rate Limit**: 60 requisições/minuto

### Integração
- **Sistema Completo**: `sistema_completo.py`
- **Upload**: Tabela `main.vgv_empreendimentos` no MotherDuck
- **Scripts**: `atualizar_vgv_empreendimentos.py`

## 🚀 Uso

### Teste Individual
```bash
python scripts/cv_vgv_empreendimentos_api.py
```

### Teste Completo
```bash
python teste_vgv_empreendimentos.py
```

### Atualização Manual
```bash
python atualizar_vgv_empreendimentos.py
```

### Sistema Completo
```bash
python sistema_completo.py
```

## 📊 Estatísticas e Monitoramento

### Logs de Debug
- Contagem de IDs testados vs válidos
- Nomes de empreendimentos encontrados
- Quantidade de tabelas por empreendimento
- Unidades expandidas por empreendimento

### Métricas
- Total de IDs testados
- Total de IDs válidos encontrados
- Total de unidades processadas
- Taxa de sucesso por empreendimento

## 🔧 Configuração Avançada

### Parâmetros Configuráveis
```python
await client.get_all_empreendimentos(
    inicio=1,                    # ID inicial
    fim=20,                      # ID final
    max_empreendimentos=20       # Limite máximo
)
```

### Rate Limiting
- **Limite**: 60 requisições/minuto
- **Delay**: 0.3s entre requisições
- **Timeout**: 30 segundos por requisição

## 🗄️ Armazenamento

### Tabela no MotherDuck
- **Nome**: `main.vgv_empreendimentos`
- **Schema**: Substituição completa a cada execução
- **Indexação**: Por `id_empreendimento` e `unidades.idunidade`

### Estrutura da Tabela
```sql
CREATE TABLE main.vgv_empreendimentos (
    id_empreendimento INTEGER,
    id_tabela INTEGER,
    nome_tabela VARCHAR,
    nome_empreendimento VARCHAR,
    unidades.etapa VARCHAR,
    unidades.bloco VARCHAR,
    unidades.unidade VARCHAR,
    unidades.idunidade VARCHAR,
    unidades.area_privativa DOUBLE,
    unidades.situacao VARCHAR,
    unidades.valor_total DOUBLE,
    fonte VARCHAR DEFAULT 'vgv_empreendimentos',
    processado_em TIMESTAMP
);
```

## 🔄 Fluxo de Execução

### 1. Teste de IDs
```python
ids_validos = await client.testar_ids_empreendimentos(1, 20)
```

### 2. Processamento por Empreendimento
```python
for id_empreendimento in ids_validos:
    resultado = await client.processar_empreendimento(id_empreendimento)
    # Processar dados...
```

### 3. Expansão de Unidades
```python
df_expandido = df.explode('unidades')
# Normalizar campos das unidades
```

### 4. Consolidação
```python
df_final = processar_dados_vgv_empreendimentos(resultados)
```

### 5. Upload
```python
conn.execute("CREATE OR REPLACE TABLE main.vgv_empreendimentos AS SELECT * FROM df_vgv_empreendimentos")
```

## 🛡️ Tratamento de Erros

### Erros Comuns
- **404**: Empreendimento não encontrado (normal)
- **429**: Rate limit excedido (retry automático)
- **500**: Erro do servidor (log e continuar)

### Estratégias de Recuperação
- Retry automático para 429
- Log detalhado de erros
- Continuação em caso de falha parcial
- Validação de dados antes do upload

## 📈 Performance

### Otimizações
- Teste inteligente de IDs (para quando encontra vazio)
- Seleção automática de tabela de financiamento
- Expansão eficiente de unidades
- Rate limiting inteligente

### Métricas Típicas
- **IDs testados**: 1-20
- **IDs válidos**: 5-15
- **Unidades por empreendimento**: 10-100
- **Tempo total**: 2-5 minutos
- **Taxa de sucesso**: >90%

## 🔮 Melhorias Futuras

### Funcionalidades Planejadas
- Cache de dados intermediários
- Filtros de empreendimento configuráveis
- Análise de tendências de preços
- Alertas automáticos de mudanças

### Otimizações
- Processamento paralelo de empreendimentos
- Compressão de dados
- Indexação avançada
- Métricas em tempo real

## 📚 Referências

- [CVCRM API Documentation](https://prati.cvcrm.com.br/api/v1/)
- [Sistema de Vendas Consolidadas](./README.md)
- [GitHub Actions](./github-actions.md)
- [Troubleshooting](./troubleshooting.md)

---

**Última atualização**: $(date)  
**Status**: ✅ Implementado e funcionando

