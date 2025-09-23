# 🔧 Troubleshooting - Guia de Resolução de Problemas

## 🚨 Problemas Comuns

### 1. GitHub Actions - Falha na Execução

#### ❌ Problema: "No such file or directory"
```
python: can't open file 'scripts/update_motherduck_vendas.py': [Errno 2] No such file or directory
```

#### ✅ Solução
- **Status**: ✅ **RESOLVIDO**
- **Causa**: Arquivo `scripts/update_motherduck_vendas.py` não existia
- **Ação**: Arquivo criado e commitado
- **Verificação**: Execução manual bem-sucedida

#### 🔍 Como Verificar
1. Acesse **Actions** no GitHub
2. Verifique execuções recentes
3. Confirme status: ✅ Sucesso

---

### 2. Variáveis de Ambiente

#### ❌ Problema: Token não encontrado
```
❌ MOTHERDUCK_TOKEN não encontrado
❌ CVCRM_EMAIL não encontrado
❌ SIENGE_TOKEN não encontrado
```

#### ✅ Solução
1. **Verificar Secrets no GitHub**:
   - Acesse **Settings** → **Secrets and variables** → **Actions**
   - Confirme se todos os secrets estão configurados:
     - `MOTHERDUCK_TOKEN`
     - `CVCRM_EMAIL`
     - `CVCRM_TOKEN`
     - `SIENGE_TOKEN`
     - `CV_VENDAS_BASE_URL`
     - `SIENGE_BASE_URL`

2. **Testar Localmente**:
   ```bash
   # Verificar se .env existe
   ls -la .env
   
   # Verificar conteúdo (sem expor tokens)
   cat .env | grep -E "(TOKEN|EMAIL)" | head -5
   ```

3. **Executar Teste**:
   ```bash
   python scripts/update_motherduck_vendas.py
   ```

---

### 3. Conexão com MotherDuck

#### ❌ Problema: Erro de conexão
```
❌ Erro ao conectar ao MotherDuck
❌ Erro de autenticação
```

#### ✅ Solução
1. **Verificar Token**:
   ```python
   import os
   token = os.environ.get('MOTHERDUCK_TOKEN')
   print(f"Token configurado: {bool(token)}")
   print(f"Tamanho do token: {len(token) if token else 0}")
   ```

2. **Testar Conexão**:
   ```python
   import duckdb
   duckdb.sql("INSTALL motherduck")
   duckdb.sql("LOAD motherduck")
   os.environ['motherduck_token'] = token
   conn = duckdb.connect('md:reservas')
   print("✅ Conexão bem-sucedida")
   ```

3. **Verificar Permissões**:
   - Token deve ter acesso ao database `reservas`
   - Verificar se o workspace existe
   - Confirmar permissões de escrita

---

### 4. Rate Limiting - APIs

#### ❌ Problema: Limite de requisições excedido
```
⚠️ Rate limit excedido para API Sienge
❌ Limite diário de requisições atingido
```

#### ✅ Solução
1. **Verificar Limites**:
   ```python
   # Sienge: 36 requisições por execução
   # CV Vendas: 60 requisições/minuto
   # Execuções: máximo 2 por dia
   ```

2. **Ajustar Estratégia**:
   - Reduzir número de empreendimentos
   - Aumentar delay entre requisições
   - Executar em horários diferentes

3. **Monitorar Uso**:
   ```python
   # Verificar logs do orquestrador
   orchestrator.print_stats()
   ```

---

### 5. Timeout - Execução Longa

#### ❌ Problema: Timeout de execução
```
⏰ Timeout - operação demorou mais de 15 minutos
```

#### ✅ Solução
1. **Verificar Performance**:
   - Analisar logs de tempo por etapa
   - Identificar gargalos
   - Otimizar queries

2. **Ajustar Timeout**:
   ```python
   # Em scripts/update_motherduck_vendas.py
   timeout=900.0  # 15 minutos
   # Aumentar se necessário
   ```

3. **Otimizar Pipeline**:
   - Reduzir dados coletados
   - Implementar cache
   - Paralelizar operações

---

### 6. Dados Vazios - APIs

#### ❌ Problema: Nenhum dado coletado
```
⚠️ Nenhum dado coletado
⚠️ Nenhum registro encontrado
```

#### ✅ Solução
1. **Verificar APIs**:
   ```bash
   # Testar APIs individualmente
   python scripts/cv_vendas_api.py
   python scripts/sienge_apis.py
   ```

2. **Verificar Parâmetros**:
   - Datas de início/fim
   - Filtros de empreendimentos
   - Parâmetros de paginação

3. **Verificar Logs**:
   - Analisar respostas das APIs
   - Verificar status codes
   - Confirmar estrutura de dados

---

### 7. Dashboard - Erro de Conexão

#### ❌ Problema: Dashboard não carrega
```
❌ Erro ao conectar ao MotherDuck
❌ Tabela não encontrada
```

#### ✅ Solução
1. **Verificar Conexão**:
   ```python
   # Em dashboard/Home.py
   conn = duckdb.connect('md:reservas')
   tables = conn.sql("SHOW TABLES").fetchall()
   print(f"Tabelas disponíveis: {tables}")
   ```

2. **Verificar Tabelas**:
   ```sql
   SELECT COUNT(*) FROM main.cv_vendas;
   SELECT COUNT(*) FROM main.sienge_vendas_realizadas;
   SELECT COUNT(*) FROM main.sienge_vendas_canceladas;
   ```

3. **Verificar Dados**:
   - Confirmar se pipeline executou
   - Verificar se dados foram carregados
   - Analisar logs do GitHub Actions

---

## 🔍 Diagnóstico Avançado

### 1. Logs Detalhados

#### Ativar Debug
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### Logs por Componente
```python
# Orquestrador
logger = logging.getLogger('orchestrator')
logger.setLevel(logging.DEBUG)

# APIs
logger = logging.getLogger('cv_vendas_api')
logger.setLevel(logging.DEBUG)
```

### 2. Métricas de Performance

#### Tempo por Etapa
```python
import time
start_time = time.time()
# ... operação ...
duration = time.time() - start_time
print(f"Operação demorou: {duration:.2f}s")
```

#### Uso de Memória
```python
import psutil
process = psutil.Process()
memory_mb = process.memory_info().rss / 1024 / 1024
print(f"Uso de memória: {memory_mb:.2f} MB")
```

### 3. Testes de Conectividade

#### Testar APIs
```python
# CV Vendas
result = await client.get_pagina(1)
print(f"CV Vendas: {result['success']}")

# Sienge
result = await client.get_vendas_realizadas('2024-01-01', '2024-12-31')
print(f"Sienge: {result['success']}")
```

#### Testar MotherDuck
```python
conn = duckdb.connect('md:reservas')
result = conn.sql("SELECT 1").fetchone()
print(f"MotherDuck: {result[0] == 1}")
```

---

## 🛠️ Ferramentas de Debug

### 1. Script de Diagnóstico
```python
#!/usr/bin/env python3
"""
Script de diagnóstico do sistema
"""
import os
import asyncio
from dotenv import load_dotenv

async def diagnosticar_sistema():
    print("🔍 DIAGNÓSTICO DO SISTEMA")
    print("=" * 50)
    
    # 1. Variáveis de ambiente
    print("1. Verificando variáveis de ambiente...")
    required_vars = ['MOTHERDUCK_TOKEN', 'CVCRM_EMAIL', 'CVCRM_TOKEN', 'SIENGE_TOKEN']
    for var in required_vars:
        value = os.environ.get(var)
        status = "✅" if value else "❌"
        print(f"   {status} {var}: {'Configurado' if value else 'Não encontrado'}")
    
    # 2. Teste de conexão MotherDuck
    print("\n2. Testando conexão com MotherDuck...")
    try:
        import duckdb
        duckdb.sql("INSTALL motherduck")
        duckdb.sql("LOAD motherduck")
        os.environ['motherduck_token'] = os.environ.get('MOTHERDUCK_TOKEN')
        conn = duckdb.connect('md:reservas')
        tables = conn.sql("SHOW TABLES").fetchall()
        print(f"   ✅ Conexão bem-sucedida - {len(tables)} tabelas")
        conn.close()
    except Exception as e:
        print(f"   ❌ Erro na conexão: {e}")
    
    # 3. Teste de APIs
    print("\n3. Testando APIs...")
    try:
        from scripts.cv_vendas_api import CVVendasAPIClient
        client = CVVendasAPIClient()
        result = await client.get_pagina(1)
        status = "✅" if result['success'] else "❌"
        print(f"   {status} CV Vendas: {result.get('error', 'OK')}")
    except Exception as e:
        print(f"   ❌ Erro na API CV Vendas: {e}")
    
    print("\n🏁 Diagnóstico concluído")

if __name__ == "__main__":
    load_dotenv()
    asyncio.run(diagnosticar_sistema())
```

### 2. Monitor de Performance
```python
#!/usr/bin/env python3
"""
Monitor de performance do sistema
"""
import time
import psutil
import asyncio
from datetime import datetime

class PerformanceMonitor:
    def __init__(self):
        self.start_time = time.time()
        self.memory_start = psutil.Process().memory_info().rss
    
    def log_metric(self, name, value):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {name}: {value}")
    
    def log_memory(self):
        current_memory = psutil.Process().memory_info().rss
        memory_mb = current_memory / 1024 / 1024
        self.log_metric("Memória", f"{memory_mb:.2f} MB")
    
    def log_duration(self, operation):
        duration = time.time() - self.start_time
        self.log_metric(f"Duração {operation}", f"{duration:.2f}s")
    
    def log_cpu(self):
        cpu_percent = psutil.cpu_percent()
        self.log_metric("CPU", f"{cpu_percent:.1f}%")

# Uso
monitor = PerformanceMonitor()
monitor.log_memory()
monitor.log_cpu()
```

---

## 📞 Suporte e Escalação

### 1. Níveis de Suporte

#### Nível 1 - Básico
- **Problemas**: Configuração, variáveis de ambiente
- **Tempo**: < 1 hora
- **Recursos**: Documentação, logs

#### Nível 2 - Intermediário
- **Problemas**: APIs, performance, dados
- **Tempo**: < 4 horas
- **Recursos**: Scripts de diagnóstico, análise de logs

#### Nível 3 - Avançado
- **Problemas**: Arquitetura, escalabilidade
- **Tempo**: < 24 horas
- **Recursos**: Análise profunda, otimizações

### 2. Processo de Escalação

1. **Identificar Problema**
   - Coletar logs
   - Reproduzir erro
   - Documentar contexto

2. **Tentar Soluções**
   - Consultar documentação
   - Executar diagnósticos
   - Aplicar correções conhecidas

3. **Escalar se Necessário**
   - Documentar tentativas
   - Coletar evidências
   - Contatar suporte técnico

### 3. Contatos de Emergência

- **GitHub Issues**: Para bugs e melhorias
- **Email**: Para problemas críticos
- **Slack**: Para suporte em tempo real
- **Documentação**: Para consulta rápida

---

## 📚 Recursos Adicionais

### Links Úteis
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [DuckDB Documentation](https://duckdb.org/docs/)
- [MotherDuck Documentation](https://motherduck.com/docs/)
- [Streamlit Documentation](https://docs.streamlit.io/)

### Scripts de Apoio
- `scripts/diagnostico.py`: Diagnóstico completo
- `scripts/performance.py`: Monitor de performance
- `scripts/teste_apis.py`: Teste de APIs
- `scripts/verificar_dados.py`: Verificação de dados

---

*Última atualização: 2024-09-23*
*Próxima revisão: 2024-10-23*
