# Guia de Configuração MCP Browser Tools

## Visão Geral

O MCP Browser Tools permite inspecionar elementos de páginas web diretamente do Cursor IDE, capturando screenshots, logs do console, atividade de rede e elementos DOM.

## Componentes Instalados

### 1. MCP Server (browser-tools-mcp)
- ✅ **Instalado**: `@agentdeskai/browser-tools-mcp@1.2.1`
- **Função**: Servidor MCP que se comunica com o Cursor IDE
- **Status**: Configurado e pronto para uso

### 2. Node Server (browser-tools-server)
- ✅ **Instalado**: `@agentdeskai/browser-tools-server@latest`
- **Função**: Servidor intermediário entre a extensão Chrome e o MCP server
- **Status**: Executando em background

### 3. Chrome Extension
- ⚠️ **Pendente**: BrowserToolsMCP Chrome Extension v1.2.0
- **Download**: [Link da Extensão](https://chrome.google.com/webstore/detail/browsertools-mcp/...)
- **Função**: Captura dados do navegador (screenshots, logs, elementos)

## Configuração Atual

### Arquivo de Configuração MCP
O projeto já possui configuração MCP em `mcp_config_completo.toml`:

```toml
# Configuração do servidor Browser Tools
[mcp.servers.browser-tools]
command = "mcp-server-browser-tools"
args = []
env = {}

# Configurações específicas do navegador
[mcp.servers.browser-tools.config]
user_data_dir = "chrome_profile_sienge_persistente"
profile_directory = "SiengeProfile"
download_directory = "downloads_tmp"
# ... outras configurações
```

## Como Usar

### 1. Instalar a Extensão Chrome
1. Acesse o Chrome Web Store
2. Procure por "BrowserToolsMCP" ou use o link direto
3. Instale a extensão v1.2.0
4. Ative a extensão

### 2. Configurar o Cursor IDE
1. Abra as configurações do Cursor
2. Vá para MCP Settings
3. Use o arquivo `mcp_config_completo.toml` como configuração
4. Reinicie o Cursor

### 3. Iniciar os Serviços
```bash
# Terminal 1: Servidor Node.js (já executando)
npx @agentdeskai/browser-tools-server@latest

# Terminal 2: MCP Server (se necessário)
npx @agentdeskai/browser-tools-mcp@latest
```

### 4. Usar no Cursor
1. Abra o DevTools do Chrome (F12)
2. Vá para a aba "BrowserToolsMCP"
3. No Cursor, use comandos como:
   - "Capture a screenshot of the current page"
   - "Get console logs from the browser"
   - "Inspect the selected element"
   - "Run an accessibility audit"

## Funcionalidades Disponíveis

### Captura de Dados
- **Screenshots**: Captura automática de telas
- **Console Logs**: Monitoramento de logs do console
- **Network Activity**: Rastreamento de requisições XHR
- **DOM Elements**: Inspeção de elementos selecionados

### Auditorias Automáticas
- **Accessibility**: Verificação de conformidade WCAG
- **Performance**: Análise de performance com Lighthouse
- **SEO**: Avaliação de otimização para motores de busca
- **Best Practices**: Verificação de boas práticas web
- **NextJS**: Auditoria específica para aplicações NextJS

### Modos Especiais
- **Audit Mode**: Executa todas as auditorias em sequência
- **Debugger Mode**: Executa todas as ferramentas de debug

## Troubleshooting

### Problemas Comuns

1. **"No server found during discovery"**
   - Verifique se o browser-tools-server está executando
   - Reinicie ambos os servidores

2. **Extensão não conecta**
   - Feche completamente o Chrome
   - Reinicie o browser-tools-server
   - Abra apenas uma instância do DevTools

3. **MCP não responde no Cursor**
   - Verifique a configuração MCP no Cursor
   - Reinicie o Cursor IDE
   - Confirme que o arquivo `mcp_config_completo.toml` está sendo usado

### Logs e Debug
- Logs do servidor: Verifique o terminal onde o browser-tools-server está executando
- Logs da extensão: Abra o DevTools e vá para a aba "BrowserToolsMCP"
- Logs do MCP: Verifique o console do Cursor

## Arquivos de Configuração

- `mcp_config_completo.toml`: Configuração completa (MotherDuck + Browser Tools)
- `mcp_browser_config.toml`: Configuração apenas do Browser Tools
- `mcp_config.toml`: Configuração apenas do MotherDuck

## Próximos Passos

1. ✅ Instalar extensão Chrome
2. ✅ Configurar Cursor IDE
3. ✅ Testar funcionalidades básicas
4. ✅ Documentar casos de uso específicos

## Comandos Úteis

```bash
# Verificar se os servidores estão rodando
netstat -an | findstr :3025

# Reiniciar servidores
taskkill /f /im node.exe
npx @agentdeskai/browser-tools-server@latest

# Verificar instalação MCP
npx @agentdeskai/browser-tools-mcp@latest --help
```

## Suporte

- Documentação oficial: [GitHub Browser Tools MCP](https://github.com/AgentDeskAI/browser-tools-mcp)
- Issues: [GitHub Issues](https://github.com/AgentDeskAI/browser-tools-mcp/issues)
- Comunidade: [Discord/Forum do projeto]