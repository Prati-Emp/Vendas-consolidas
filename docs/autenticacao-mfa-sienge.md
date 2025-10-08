# AUTENTICAÇÃO MFA SIENGE - PONTOS CRÍTICOS

## ⚠️ ATENÇÃO: LIMITAÇÕES IMPORTANTES

### 1. **NÃO ABRIR OUTRO NAVEGADOR**
- **NUNCA** abrir outro navegador Chrome durante os testes
- O Sienge perde a sessão salva se detectar múltiplas instâncias
- A autenticação MFA é vinculada ao perfil específico do Chrome

### 2. **PRIMEIRA AUTENTICAÇÃO MANUAL OBRIGATÓRIA**
- Na primeira execução, é **OBRIGATÓRIO** fazer login manual
- O usuário deve completar a autenticação MFA no celular
- Após isso, a sessão fica salva no perfil persistente
- **SEM** essa etapa manual inicial, não conseguimos acessar via Sienge ID

### 3. **FLUXO CORRETO DE TESTE**
1. **Primeira vez**: Executar script e fazer login manual + MFA
2. **Próximas vezes**: O script usa o perfil persistente salvo
3. **NUNCA** abrir outro Chrome durante os testes

### 4. **PERFIL PERSISTENTE**
- Localização: `chrome_profile_sienge_persistente_<timestamp>`
- Contém: cookies, sessões, tokens de autenticação
- **CRÍTICO**: Manter o mesmo perfil entre execuções

### 5. **PROBLEMA DO BOTÃO PROSSEGUIR**
- O botão tem link específico: `removerUsuarioLogadoServlet?acao=S`
- Às vezes o modal de "usuário já conectado" aparece
- Solução: Clicar em "PROSSEGUIR" ou navegar diretamente para o servlet

### 6. **CONFIGURAÇÕES IMPORTANTES**
```env
RELATORIO_PAUSA_PARA_MFA=true
RELATORIO_HEADLESS=false
```

### 7. **TROUBLESHOOTING**
- Se perder a sessão: Fazer login manual novamente
- Se aparecer modal "usuário conectado": Clicar "PROSSEGUIR"
- Se falhar: Verificar se não há outro Chrome aberto

## 📝 NOTAS DE DESENVOLVIMENTO

- O sistema usa perfil persistente para manter sessões
- MFA é obrigatório na primeira autenticação
- Botão PROSSEGUIR tem tratamento especial com múltiplos fallbacks
- URL do servlet: `https://pratiemp.sienge.com.br/sienge/removerUsuarioLogadoServlet?acao=S`

---
**Data**: 2025-01-27  
**Status**: Ativo  
**Responsável**: Equipe de Automação

