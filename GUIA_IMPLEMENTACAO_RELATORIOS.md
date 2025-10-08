# 📊 Guia de Implementação: Coleta de Relatórios sem API

## 🎯 Visão Geral

Este guia detalha como implementar a coleta automática de dados de relatórios que não possuem API direta, utilizando download automático de arquivos CSV/Excel e web scraping como fallback.

## 🚀 Implementação Passo a Passo

### **1. Configuração Inicial**

#### 1.1. Instalar Dependências
```bash
# Instalar dependências adicionais para web scraping
pip install selenium webdriver-manager
```

#### 1.2. Configurar Chrome/ChromeDriver
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y chromium-browser

# Windows (via Chocolatey)
choco install googlechrome

# macOS (via Homebrew)
brew install --cask google-chrome
```

### **2. Configuração do Sistema**

#### 2.1. Arquivo de Configuração
Copie `config_relatorio_exemplo.env` para `.env` e configure:

```bash
# URLs do Sistema
RELATORIO_LOGIN_URL=https://seu-sistema.com.br/login
RELATORIO_URL=https://seu-sistema.com.br/relatorios/vendas

# Credenciais
RELATORIO_USERNAME=seu_usuario@empresa.com
RELATORIO_PASSWORD=sua_senha_aqui

# Configuração do Download
RELATORIO_TIPO_ARQUIVO=csv
RELATORIO_BOTAO_DOWNLOAD=#btn-download-csv
RELATORIO_SEPARADOR=;
RELATORIO_ENCODING=utf-8
```

#### 2.2. Identificar Elementos do Sistema

**Para encontrar os seletores corretos:**

1. **Acesse o sistema manualmente**
2. **Abra o Developer Tools (F12)**
3. **Identifique os elementos:**

```javascript
// Exemplo de como encontrar seletores
// Botão de download
document.querySelector('#btn-download-csv')

// Campos de login
document.querySelector('input[name="email"]')
document.querySelector('input[name="senha"]')

// Campos de filtro de data
document.querySelector('input[name="data_inicio"]')
document.querySelector('input[name="data_fim"]')

// Tabela de dados
document.querySelector('#tabela-dados')
```

### **3. Teste da Implementação**

#### 3.1. Teste de Configuração
```bash
python teste_relatorio_download.py
```

#### 3.2. Teste Manual
```python
# Teste específico do seu sistema
from scripts.relatorio_download_api import obter_dados_relatorio_download

config = {
    'nome_fonte': 'meu_relatorio',
    'login_url': 'https://meu-sistema.com/login',
    'url': 'https://meu-sistema.com/relatorios',
    'username_field': 'email',
    'password_field': 'senha',
    'username': 'meu_usuario',
    'password': 'minha_senha',
    'tipo_arquivo': 'csv',
    'seletor_botao_download': '#btn-export-csv',
    # ... outras configurações
}

df = await obter_dados_relatorio_download(config)
```

### **4. Integração com Sistema Atual**

#### 4.1. GitHub Actions
Adicione as variáveis ao GitHub Secrets:

```yaml
# .github/workflows/update-database-daily.yml
env:
  # ... variáveis existentes ...
  RELATORIO_LOGIN_URL: ${{ secrets.RELATORIO_LOGIN_URL }}
  RELATORIO_URL: ${{ secrets.RELATORIO_URL }}
  RELATORIO_USERNAME: ${{ secrets.RELATORIO_USERNAME }}
  RELATORIO_PASSWORD: ${{ secrets.RELATORIO_PASSWORD }}
  RELATORIO_TIPO_ARQUIVO: ${{ secrets.RELATORIO_TIPO_ARQUIVO }}
  RELATORIO_BOTAO_DOWNLOAD: ${{ secrets.RELATORIO_BOTAO_DOWNLOAD }}
```

#### 4.2. Execução Diária
O sistema já está integrado ao `scripts/update_motherduck_daily.py` e será executado automaticamente.

### **5. Estrutura de Dados**

#### 5.1. Tabela no MotherDuck
```sql
-- Tabela criada automaticamente
CREATE TABLE main.relatorio_download (
    ID_Relatorio VARCHAR,
    Data_Relatorio DATE,
    Valor_Relatorio DECIMAL,
    Cliente_Relatorio VARCHAR,
    fonte VARCHAR,
    processado_em TIMESTAMP,
    data_coleta DATE
);
```

#### 5.2. Mapeamento de Colunas
Configure o mapeamento conforme seu relatório:

```python
'mapeamento_colunas': {
    'id_venda': 'ID_Venda',
    'data_venda': 'Data_Venda', 
    'valor': 'Valor_Venda',
    'cliente': 'Nome_Cliente',
    'vendedor': 'Vendedor'
}
```

### **6. Configurações por Tipo de Sistema**

#### 6.1. Sistema com Botão de Download
```python
config = {
    'seletor_botao_download': 'button[data-action="export-csv"]',
    'tipo_arquivo': 'csv'
}
```

#### 6.2. Sistema com Link de Download
```python
config = {
    'seletor_botao_download': 'a[href*="download"]',
    'tipo_arquivo': 'excel'
}
```

#### 6.3. Sistema com Formulário
```python
config = {
    'seletor_botao_download': 'input[type="submit"][value="Exportar"]',
    'tipo_arquivo': 'csv'
}
```

### **7. Troubleshooting**

#### 7.1. Problemas Comuns

**Erro: "Elemento não encontrado"**
```python
# Solução: Aguardar carregamento
'aguardar_elemento': '#tabela-dados tbody tr'
```

**Erro: "Download não iniciado"**
```python
# Solução: Aumentar tempo de espera
await asyncio.sleep(10)  # Aguardar download
```

**Erro: "Login falhou"**
```python
# Solução: Verificar credenciais e campos
'username_field': 'email',  # Ajustar conforme sistema
'password_field': 'senha'    # Ajustar conforme sistema
```

#### 7.2. Logs de Debug
```python
# Ativar logs detalhados
import logging
logging.basicConfig(level=logging.DEBUG)
```

### **8. Monitoramento**

#### 8.1. Verificar Execução
```sql
-- Verificar dados coletados
SELECT COUNT(*) FROM main.relatorio_download;

-- Verificar última coleta
SELECT MAX(processado_em) FROM main.relatorio_download;
```

#### 8.2. Dashboard
Os dados aparecerão automaticamente no dashboard existente.

### **9. Exemplos de Configuração**

#### 9.1. Sistema de Vendas
```python
config_vendas = {
    'nome_fonte': 'sistema_vendas',
    'login_url': 'https://vendas.empresa.com/login',
    'url': 'https://vendas.empresa.com/relatorios/vendas',
    'username_field': 'email',
    'password_field': 'senha',
    'username': 'vendas@empresa.com',
    'password': 'senha123',
    'tipo_arquivo': 'csv',
    'seletor_botao_download': '#export-csv',
    'filtros': {
        'data_inicio': '2024-01-01',
        'data_fim': '2024-12-31',
        'campo_data_inicio': 'data_inicio',
        'campo_data_fim': 'data_fim'
    }
}
```

#### 9.2. Sistema Financeiro
```python
config_financeiro = {
    'nome_fonte': 'sistema_financeiro',
    'login_url': 'https://financeiro.empresa.com/login',
    'url': 'https://financeiro.empresa.com/relatorios',
    'username_field': 'usuario',
    'password_field': 'senha',
    'username': 'financeiro',
    'password': 'senha456',
    'tipo_arquivo': 'excel',
    'seletor_botao_download': 'button[data-export="excel"]',
    'separador_csv': ';',
    'encoding': 'latin1'
}
```

### **10. Próximos Passos**

1. **Configure as credenciais** no arquivo `.env`
2. **Execute o teste** com `python teste_relatorio_download.py`
3. **Ajuste os seletores** conforme seu sistema
4. **Teste a integração** com o sistema diário
5. **Monitore a execução** via GitHub Actions

## 📞 Suporte

Para dúvidas ou problemas:
1. Verifique os logs de execução
2. Teste os seletores manualmente
3. Valide as credenciais
4. Consulte a documentação do sistema de origem

---

**✅ Sistema pronto para coleta automática de relatórios!**

