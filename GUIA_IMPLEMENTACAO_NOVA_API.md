# 📋 Guia Completo: Implementação de Nova API

Este guia documenta o processo completo para implementar uma nova API no sistema de vendas consolidadas, baseado na nossa experiência com a implementação da API de Contratos de Suprimentos do Sienge.

## 🎯 Visão Geral

O sistema possui uma arquitetura modular que permite adicionar novas APIs facilmente. Cada API segue um padrão consistente de implementação.

## 📁 Estrutura do Sistema

```
scripts/
├── config.py                           # Configurações de todas as APIs
├── update_motherduck_daily.py          # Sistema de atualização diária
├── cv_sienge_contratos_suprimentos_api.py  # Exemplo de nova API
└── [outras_apis_existentes].py
```

## 🚀 Passo a Passo para Nova API

### 1. **Criar Script da API** (`scripts/nova_api.py`)

```python
#!/usr/bin/env python3
"""
Integração com API [Nome da API]
Endpoint: [URL da API]
Credenciais: [Tipo de autenticação]
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd
import requests

from scripts.config import get_api_config

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NovaAPIClient:
    """Cliente para [Nome da API]"""
    
    def __init__(self):
        self.config = get_api_config('nome_da_api')
        if not self.config:
            raise ValueError("Configuração da API não encontrada")
        
        self.base_url = "[URL da API]"
        self.headers = self.config.headers
    
    async def buscar_dados(self, parametros: Dict) -> List[Dict]:
        """Busca dados da API"""
        # Implementar lógica de busca
        pass
    
    def processar_dados(self, dados: List[Dict]) -> pd.DataFrame:
        """Processa dados no formato padrão"""
        # Implementar processamento
        pass

def processar_dados_nova_api(df: pd.DataFrame) -> pd.DataFrame:
    """Processa e padroniza dados da nova API"""
    if df.empty:
        return pd.DataFrame()
    
    # Adicionar colunas padrão
    df['fonte'] = 'nome_da_api'
    df['processado_em'] = datetime.now()
    
    return df

async def obter_dados_nova_api(parametros: Dict) -> pd.DataFrame:
    """Função principal para obter dados da nova API"""
    client = NovaAPIClient()
    dados = await client.buscar_dados(parametros)
    df = client.processar_dados(dados)
    return processar_dados_nova_api(df)
```

### 2. **Configurar em `scripts/config.py`**

Adicionar nova configuração:

```python
elif api_name == 'nome_da_api':
    token = os.environ.get('TOKEN_VARIAVEL', '')
    # Lógica de autenticação específica
    
    return APIConfig(
        name='Nome da API',
        base_url='[URL da API]',
        headers={
            'accept': 'application/json',
            'authorization': auth_header
        },
        rate_limit=50
    )
```

E adicionar na função `get_all_rate_limits()`:

```python
def get_all_rate_limits() -> Dict[str, int]:
    return {
        # ... outras APIs
        'nome_da_api': 50
    }
```

### 3. **Integrar em `scripts/update_motherduck_daily.py`**

#### 3.1. Adicionar coleta de dados:

```python
# X.X Coletar Nova API
print("\nX.X. Coletando dados Nova API...")
try:
    from scripts.nova_api import obter_dados_nova_api
    df_nova_api = await obter_dados_nova_api(parametros)
    print(f"✅ Nova API: {len(df_nova_api)} registros")
except Exception as e:
    df_nova_api = pd.DataFrame()
    print(f"⚠️ Falha ao coletar Nova API: {e}")
```

#### 3.2. Adicionar upload para MotherDuck:

```python
# Upload Nova API
if df_nova_api is not None and not df_nova_api.empty:
    conn.register("df_nova_api", df_nova_api)
    conn.execute("CREATE OR REPLACE TABLE main.nova_api AS SELECT * FROM df_nova_api")
    count_nova = conn.sql("SELECT COUNT(*) FROM main.nova_api").fetchone()[0]
    print(f"✅ Nova API upload: {count_nova:,} registros")
```

#### 3.3. Adicionar nas estatísticas finais:

```python
print(f"   - Nova API: {len(df_nova_api):,} registros")
```

### 4. **Criar Script de Teste**

```python
#!/usr/bin/env python3
"""
Teste da Nova API
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(__file__))

async def test_nova_api():
    print("=== TESTE NOVA API ===")
    
    load_dotenv()
    
    try:
        from scripts.nova_api import obter_dados_nova_api
        
        df = await obter_dados_nova_api(parametros)
        print(f"Registros: {len(df)}")
        
        if not df.empty:
            print("Colunas:", list(df.columns))
            print(df.head())
        
        return True
        
    except Exception as e:
        print(f"Erro: {e}")
        return False

if __name__ == "__main__":
    sucesso = asyncio.run(test_nova_api())
    sys.exit(0 if sucesso else 1)
```

### 5. **Criar Script de Atualização Isolada**

```python
#!/usr/bin/env python3
"""
Atualização isolada da Nova API
"""

import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

sys.path.append(os.path.dirname(__file__))

async def atualizar_nova_api():
    print("=== ATUALIZACAO ISOLADA NOVA API ===")
    
    load_dotenv()
    
    try:
        from scripts.nova_api import obter_dados_nova_api
        import duckdb
        
        # 1. Coletar dados
        df = await obter_dados_nova_api(parametros)
        print(f"Dados coletados: {len(df)} registros")
        
        # 2. Upload para MotherDuck
        duckdb.sql("INSTALL motherduck")
        duckdb.sql("LOAD motherduck")
        
        token = os.environ.get('MOTHERDUCK_TOKEN', '').strip()
        duckdb.sql(f"SET motherduck_token='{token}'")
        conn = duckdb.connect('md:reservas')
        
        conn.register("df_nova_api", df)
        conn.execute("CREATE OR REPLACE TABLE main.nova_api AS SELECT * FROM df_nova_api")
        count = conn.sql("SELECT COUNT(*) FROM main.nova_api").fetchone()[0]
        print(f"Upload: {count:,} registros")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"Erro: {e}")
        return False

if __name__ == "__main__":
    sucesso = asyncio.run(atualizar_nova_api())
    sys.exit(0 if sucesso else 1)
```

## 🔧 Configurações Necessárias

### Variáveis de Ambiente

Adicionar no arquivo `.env`:

```bash
# Para APIs que usam token
NOVA_API_TOKEN=seu_token_aqui

# Para APIs que usam email/token
NOVA_API_EMAIL=seu_email@exemplo.com
NOVA_API_TOKEN=seu_token_aqui
```

### Configuração do GitHub Actions

Se necessário, adicionar as novas variáveis nos secrets do repositório:
- `NOVA_API_TOKEN`
- `NOVA_API_EMAIL`

## 🧪 Processo de Teste

### 1. **Teste Isolado**
```bash
python teste_nova_api.py
```

### 2. **Atualização Isolada**
```bash
python atualizar_nova_api.py
```

### 3. **Verificação no MotherDuck**
```python
# Script para verificar se a tabela foi criada
import duckdb
conn = duckdb.connect('md:reservas')
count = conn.sql("SELECT COUNT(*) FROM main.nova_api").fetchone()[0]
print(f"Registros na tabela: {count}")
```

## 📊 Padrões de Dados

### Colunas Obrigatórias
Toda nova API deve incluir:
- `fonte`: Nome da API (ex: 'nova_api')
- `processado_em`: Timestamp de processamento

### Tipos de Dados
- **Datas**: Converter para `datetime64[ns]`
- **Valores monetários**: Converter para `float64`
- **IDs**: Converter para `string` ou `Int64`
- **Textos**: Manter como `string`

## ⚠️ Problemas Comuns e Soluções

### 1. **Erro 401 (Unauthorized)**
- Verificar se o token está correto
- Verificar se há caracteres extras no token
- Verificar se a API suporta o endpoint

### 2. **Erro de Importação**
- Verificar se o arquivo está em `scripts/`
- Verificar se as dependências estão instaladas
- Verificar se o `sys.path.append()` está correto

### 3. **Tabela não criada no MotherDuck**
- Verificar se o `MOTHERDUCK_TOKEN` está correto
- Verificar se há dados para upload
- Verificar se a conexão está funcionando

### 4. **Dados não aparecem no Dashboard**
- Verificar se a tabela foi criada no schema correto
- Verificar se os dados estão no formato esperado
- Verificar se o dashboard está configurado para a nova tabela

## 🎯 Checklist de Implementação

- [ ] Script da API criado em `scripts/`
- [ ] Configuração adicionada em `config.py`
- [ ] Integração adicionada em `update_motherduck_daily.py`
- [ ] Script de teste criado
- [ ] Script de atualização isolada criado
- [ ] Variáveis de ambiente configuradas
- [ ] Teste isolado executado com sucesso
- [ ] Atualização isolada executada com sucesso
- [ ] Tabela criada no MotherDuck
- [ ] Dados validados no banco
- [ ] Arquivos temporários removidos
- [ ] Commit e push realizados

## 📝 Exemplo Real: API Contratos Suprimentos

### Arquivos Criados:
- `scripts/cv_sienge_contratos_suprimentos_api.py`
- `teste_sienge_contratos_suprimentos.py` (removido)
- `atualizar_sienge_contratos_suprimentos.py` (removido)

### Modificações:
- `scripts/config.py` - Adicionada configuração
- `scripts/update_motherduck_daily.py` - Adicionada integração

### Resultado:
- **321 registros** coletados
- **129 fornecedores únicos**
- **220 contratos únicos**
- Tabela `sienge_contratos_suprimentos` criada no MotherDuck

## 🚀 Próximos Passos

Após implementar uma nova API:

1. **Monitorar** a execução diária no GitHub Actions
2. **Validar** os dados no dashboard
3. **Documentar** a nova API na documentação do projeto
4. **Configurar** alertas se necessário
5. **Otimizar** performance se necessário

---

**Nota**: Este guia foi criado baseado na implementação bem-sucedida da API de Contratos de Suprimentos do Sienge. Use como referência para futuras implementações.
