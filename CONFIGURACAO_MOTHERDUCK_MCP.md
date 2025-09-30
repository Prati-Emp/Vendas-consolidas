# Configuração do MotherDuck MCP

Este documento explica como instalar e configurar o MCP (Model Context Protocol) do MotherDuck no seu projeto.

## ✅ Status da Instalação

- ✅ MCP Server MotherDuck instalado
- ✅ Token configurado
- ✅ Conexão com MotherDuck funcionando
- ✅ Arquivos de configuração criados

## Arquivos Criados

1. **`motherduck_config.env`** - Arquivo com o token do MotherDuck
2. **`mcp_config.toml`** - Configuração do servidor MCP
3. **`teste_motherduck_mcp.py`** - Script de teste da conexão
4. **`configurar_mcp_motherduck.py`** - Script de configuração

## Como Usar

### 1. Conexão Direta (Recomendado)

```python
import duckdb
import os
from dotenv import load_dotenv

# Carregar token
load_dotenv('motherduck_config.env')
token = os.getenv('MOTHERDUCK_TOKEN')

# Conectar ao MotherDuck
conn = duckdb.connect(f'md:?motherduck_token={token}')

# Executar consultas
result = conn.execute("SELECT * FROM my_db.minha_tabela").fetchall()
```

### 2. Usando o Servidor MCP

O servidor MCP está localizado em:
```
C:\Users\Odair_Santos\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\LocalCache\local-packages\Python313\Scripts\mcp-server-motherduck.exe
```

Para executar manualmente:
```bash
mcp-server-motherduck --token SEU_TOKEN
```

### 3. Configuração no Cursor

Para usar com o Cursor, adicione ao arquivo de configuração do MCP:

```toml
[mcp.servers.motherduck]
command = "C:\\Users\\Odair_Santos\\AppData\\Local\\Packages\\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\\LocalCache\\local-packages\\Python313\\Scripts\\mcp-server-motherduck.exe"
args = ["--token", "${MOTHERDUCK_TOKEN}"]
env = {"MOTHERDUCK_TOKEN": "${MOTHERDUCK_TOKEN}"}
```

## Testando a Configuração

Execute o script de teste:
```bash
python teste_motherduck_mcp.py
```

Este script irá:
- Verificar se o token está configurado
- Testar a conexão com MotherDuck
- Listar os databases disponíveis
- Verificar se o servidor MCP está funcionando

## Databases Disponíveis

Com base no teste realizado, os seguintes databases estão disponíveis:
- `md_information_schema`
- `my_db`
- `reservas`
- `sample_data`

## Comandos Úteis

### Listar todas as tabelas
```sql
SELECT table_name FROM information_schema.tables WHERE table_schema = 'my_db';
```

### Verificar estrutura de uma tabela
```sql
DESCRIBE my_db.minha_tabela;
```

### Executar consulta personalizada
```sql
SELECT * FROM my_db.minha_tabela LIMIT 10;
```

## Troubleshooting

### Problema: "Token não encontrado"
**Solução:** Verifique se o arquivo `motherduck_config.env` existe e contém o token correto.

### Problema: "Servidor MCP não encontrado"
**Solução:** Execute `pip install mcp-server-motherduck` novamente.

### Problema: "Conexão falhou"
**Solução:** Verifique se o token está válido e se você tem acesso à internet.

## Próximos Passos

1. **Integrar com o projeto existente**: Use a conexão direta do DuckDB nos seus scripts
2. **Configurar no Cursor**: Adicione a configuração MCP no Cursor para usar via interface
3. **Automatizar**: Use os scripts criados para automatizar a configuração em outros ambientes

## Arquivos de Configuração

- **Token**: `motherduck_config.env`
- **MCP Config**: `mcp_config.toml`
- **Teste**: `teste_motherduck_mcp.py`
- **Setup**: `configurar_mcp_motherduck.py`

Todos os arquivos estão prontos para uso e a conexão com o MotherDuck está funcionando perfeitamente!
