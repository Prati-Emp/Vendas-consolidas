# 🛡️ Guia de Segurança - Dashboard de Vendas

## 🚨 **PROBLEMA IDENTIFICADO**
Seu dashboard está **PUBLICAMENTE ACESSÍVEL** quando hospedado no Streamlit Cloud com repositório público. Isso significa que **qualquer pessoa com o link pode ver seus dados de vendas**.

## ✅ **SOLUÇÕES IMPLEMENTADAS**

### 1. **Sistema de Autenticação** (Implementado)
- ✅ Login obrigatório para acessar o dashboard
- ✅ Sessão com timeout automático (1 hora)
- ✅ Credenciais configuráveis via arquivo `.env`
- ✅ Hash seguro das senhas

### 2. **Configuração de Segurança**
```bash
# Arquivo .env (criar na pasta streamlit_vendas/)
DASHBOARD_USER=seu_usuario
DASHBOARD_PASSWORD=sua_senha_forte
MOTHERDUCK_TOKEN=seu_token_motherduck
```

## 🔒 **OPÇÕES DE PRIVACIDADE**

### **Opção A: Repositório Privado + Streamlit Pro**
- ✅ **Mais Seguro**: Dashboard completamente privado
- ✅ **Controle Total**: Acesso restrito por usuário
- 💰 **Custo**: ~$20/mês por usuário
- 🔧 **Implementação**: Simples, apenas mudar repositório para privado

### **Opção B: Autenticação + Repositório Público** (Atual)
- ✅ **Gratuito**: Sem custos adicionais
- ✅ **Proteção**: Login obrigatório
- ⚠️ **Limitação**: Código fonte visível (mas dados protegidos)
- 🔧 **Implementação**: Já implementado

### **Opção C: Deploy Privado**
- ✅ **Máxima Segurança**: Controle total do servidor
- ✅ **Sem Custos**: Hospedagem própria
- 🔧 **Implementação**: Docker, Heroku, Railway, etc.

## 🚀 **INSTRUÇÕES DE USO**

### **1. Configurar Credenciais**
```bash
# Na pasta streamlit_vendas/
cp env_example.txt .env

# Editar .env com suas credenciais
DASHBOARD_USER=admin
DASHBOARD_PASSWORD=MinhaSenh@Forte123
```

### **2. Executar Dashboard Seguro**
```bash
cd streamlit_vendas
streamlit run app.py
```

### **3. Acessar Dashboard**
- URL: http://localhost:8501
- Login: Use as credenciais do arquivo `.env`
- Sessão: Expira automaticamente em 1 hora

## 🔐 **MELHORIAS DE SEGURANÇA**

### **Credenciais Fortes**
```bash
# ✅ BOM
DASHBOARD_PASSWORD=MinhaSenh@Forte123

# ❌ RUIM
DASHBOARD_PASSWORD=123456
```

### **Variáveis de Ambiente**
```bash
# Para produção, use variáveis de ambiente do servidor
export DASHBOARD_USER="admin"
export DASHBOARD_PASSWORD="senha_super_forte"
```

### **Autenticação OAuth (Avançado)**
```python
# Para máxima segurança, implementar OAuth
# Google, Microsoft, ou provedor corporativo
```

## 📋 **CHECKLIST DE SEGURANÇA**

### **Antes de Publicar**
- [ ] Arquivo `.env` não está no Git
- [ ] Senhas são fortes e únicas
- [ ] Credenciais não estão hardcoded
- [ ] Teste de login funcionando
- [ ] Timeout de sessão configurado

### **Para Produção**
- [ ] Repositório privado (recomendado)
- [ ] Streamlit Pro/Team ativo
- [ ] Backup das credenciais
- [ ] Monitoramento de acesso
- [ ] Logs de segurança

## 🆘 **TROUBLESHOOTING**

### **Erro: "Credenciais inválidas"**
```bash
# Verificar arquivo .env
cat streamlit_vendas/.env

# Verificar se variáveis estão corretas
DASHBOARD_USER=admin
DASHBOARD_PASSWORD=vendas2024
```

### **Erro: "Token MotherDuck não encontrado"**
```bash
# Adicionar token ao .env
MOTHERDUCK_TOKEN=seu_token_aqui
```

### **Dashboard não carrega**
```bash
# Verificar dependências
pip install -r requirements.txt

# Verificar autenticação
python -c "from auth import check_credentials; print(check_credentials('admin', 'vendas2024'))"
```

## 🎯 **RECOMENDAÇÃO FINAL**

Para **máxima segurança** com seus dados de vendas:

1. **Imediato**: Use o sistema de autenticação implementado
2. **Curto prazo**: Mude o repositório para privado
3. **Longo prazo**: Considere Streamlit Pro para controle total

## 📞 **SUPORTE**

Se precisar de ajuda:
1. Verificar este guia
2. Testar credenciais localmente
3. Verificar logs do Streamlit
4. Contatar administrador do sistema

---

**⚠️ IMPORTANTE**: Dados de vendas são informações sensíveis. Sempre use as melhores práticas de segurança!
