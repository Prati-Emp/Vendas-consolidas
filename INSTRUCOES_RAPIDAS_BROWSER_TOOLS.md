# Instruções Rápidas - MCP Browser Tools

## 🚀 Início Rápido

### 1. Iniciar Serviços
```bash
# Opção 1: Script automático
.\iniciar_browser_tools.bat

# Opção 2: Manual
npx @agentdeskai/browser-tools-server@latest
```

### 2. Instalar Extensão Chrome
- Acesse: [Chrome Web Store - BrowserToolsMCP](https://chrome.google.com/webstore)
- Procure por "BrowserToolsMCP" 
- Instale a versão v1.2.0
- Ative a extensão

### 3. Configurar Cursor IDE
- Abra configurações do Cursor
- Vá para MCP Settings
- Use o arquivo: `mcp_config_completo.toml`
- Reinicie o Cursor

### 4. Usar no Cursor
1. Abra o DevTools do Chrome (F12)
2. Vá para a aba "BrowserToolsMCP"
3. No Cursor, digite comandos como:
   - "Capture a screenshot of the current page"
   - "Get console logs from the browser"
   - "Inspect the selected element"
   - "Run an accessibility audit"

## 🔧 Comandos Úteis

### Captura de Dados
- `"Take a screenshot"` - Captura tela atual
- `"Get console logs"` - Obtém logs do console
- `"Get network activity"` - Mostra atividade de rede
- `"Inspect selected element"` - Inspeciona elemento selecionado

### Auditorias
- `"Run accessibility audit"` - Auditoria de acessibilidade
- `"Run performance audit"` - Auditoria de performance
- `"Run SEO audit"` - Auditoria de SEO
- `"Run audit mode"` - Todas as auditorias

### Debug
- `"Enter debugger mode"` - Modo debug completo
- `"Get page information"` - Informações da página
- `"Clear browser logs"` - Limpa logs do navegador

## ⚠️ Troubleshooting

### Servidor não conecta
```bash
# Parar todos os processos Node
taskkill /f /im node.exe

# Reiniciar servidor
npx @agentdeskai/browser-tools-server@latest
```

### Extensão não funciona
1. Feche completamente o Chrome
2. Reinicie o browser-tools-server
3. Abra apenas uma instância do DevTools

### MCP não responde
1. Verifique configuração MCP no Cursor
2. Reinicie o Cursor IDE
3. Confirme uso do `mcp_config_completo.toml`

## 📁 Arquivos Importantes

- `mcp_config_completo.toml` - Configuração principal
- `iniciar_browser_tools.bat` - Script de inicialização
- `GUIA_CONFIGURACAO_MCP_BROWSER.md` - Documentação completa

## 🎯 Casos de Uso

### Inspeção de Elementos
1. Navegue para a página desejada
2. Selecione o elemento no Chrome
3. No Cursor: "Inspect the selected element"
4. Obtenha informações detalhadas do elemento

### Auditoria de Página
1. Abra a página no Chrome
2. No Cursor: "Run audit mode"
3. Receba relatório completo de acessibilidade, performance e SEO

### Debug de Problemas
1. Abra DevTools e vá para "BrowserToolsMCP"
2. No Cursor: "Enter debugger mode"
3. Obtenha logs, screenshots e informações de debug

## 📞 Suporte

- Documentação: `GUIA_CONFIGURACAO_MCP_BROWSER.md`
- GitHub: [Browser Tools MCP](https://github.com/AgentDeskAI/browser-tools-mcp)
- Issues: [GitHub Issues](https://github.com/AgentDeskAI/browser-tools-mcp/issues)

