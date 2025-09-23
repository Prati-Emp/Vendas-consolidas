# 📥 Como Baixar Dados do MotherDuck

Este guia explica como baixar os dados da tabela `sienge_vendas_realizadas` do banco de dados MotherDuck para validação.

## 🚀 Scripts Disponíveis

### 1. `testar_conexao_motherduck.py`
- **Função**: Testa se a conexão com o MotherDuck está funcionando
- **Uso**: Execute antes do script principal para verificar credenciais

### 2. `baixar_sienge_vendas_realizadas.py`
- **Função**: Baixa todos os dados da tabela e exporta para CSV
- **Uso**: Script principal para obter os dados

## ⚙️ Configuração

### 1. Instalar Dependências
```bash
pip install duckdb python-dotenv pandas
```

### 2. Configurar Credenciais
Crie um arquivo `.env` na raiz do projeto com:
```bash
MOTHERDUCK_TOKEN=seu_token_motherduck_aqui
```

### 3. Testar Conexão
```bash
python testar_conexao_motherduck.py
```

### 4. Baixar Dados
```bash
python baixar_sienge_vendas_realizadas.py
```

## 📊 O que o Script Faz

1. **Conecta** ao MotherDuck usando suas credenciais
2. **Verifica** se a tabela `sienge_vendas_realizadas` existe
3. **Obtém estatísticas** da tabela (total de registros, datas)
4. **Baixa todos os dados** da tabela
5. **Exporta para CSV** com timestamp no nome
6. **Mostra preview** dos dados baixados

## 📁 Arquivo de Saída

O script gera um arquivo CSV com formato:
```
sienge_vendas_realizadas_YYYYMMDD_HHMMSS.csv
```

## 🔍 Estrutura dos Dados

A tabela `sienge_vendas_realizadas` contém dados de vendas do sistema Sienge, incluindo:
- Informações da venda (ID, valor, data)
- Dados do cliente
- Informações do empreendimento
- Status e datas importantes

## ⚠️ Troubleshooting

### Erro: "MOTHERDUCK_TOKEN não encontrado"
- Verifique se o arquivo `.env` existe
- Confirme se a variável está configurada corretamente

### Erro: "Tabela não encontrada"
- Verifique se o pipeline de dados foi executado
- Confirme se a tabela foi criada no schema correto

### Erro de conexão
- Verifique se o token do MotherDuck está correto
- Confirme se há conectividade com a internet

## 📞 Suporte

Para dúvidas ou problemas:
1. Verifique a documentação em `docs/`
2. Execute o script de teste primeiro
3. Consulte os logs de erro para detalhes
