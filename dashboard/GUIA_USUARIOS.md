# 👥 Guia de Gerenciamento de Usuários

## 🔐 **Sistema Atual (Simples)**

### **Arquivo**: `dashboard/.env`
```bash
DASHBOARD_USER=admin
DASHBOARD_PASSWORD=vendas2024
```

**Para alterar usuário/senha:**
1. Edite o arquivo `.env`
2. Mude `DASHBOARD_USER` e `DASHBOARD_PASSWORD`
3. Reinicie o dashboard

---

## 👥 **Sistema Multi-Usuário (Recomendado)**

### **Arquivo**: `dashboard/multi_auth.py`

### **Usuários Padrão:**
```python
USERS_DATABASE = {
    "admin": {
        "password": "vendas2024",
        "role": "admin",
        "name": "Administrador",
        "email": "admin@empresa.com"
    },
    "gerente": {
        "password": "gerente2024", 
        "role": "manager",
        "name": "Gerente de Vendas",
        "email": "gerente@empresa.com"
    },
    "analista": {
        "password": "analista2024",
        "role": "analyst", 
        "name": "Analista de Dados",
        "email": "analista@empresa.com"
    }
}
```

### **Como Adicionar Novos Usuários:**

1. **Edite o arquivo** `dashboard/multi_auth.py`
2. **Adicione na seção** `USERS_DATABASE`:
```python
"novo_usuario": {
    "password": "senha_forte_123",
    "role": "analyst",  # admin, manager, analyst
    "name": "Nome Completo",
    "email": "email@empresa.com"
}
```

### **Níveis de Acesso:**
- **`admin`**: Acesso total + gerenciamento de usuários
- **`manager`**: Acesso a relatórios + dados sensíveis
- **`analyst`**: Acesso básico aos dashboards

---

## 🚀 **Implementar Sistema Multi-Usuário**

### **1. Substituir Autenticação:**
```python
# Em cada página, trocar:
from auth import require_auth

# Por:
from multi_auth import require_auth
```

### **2. Configurar no Streamlit Cloud:**
```bash
# Variáveis de ambiente (opcional)
DASHBOARD_USER=admin
DASHBOARD_PASSWORD=vendas2024
```

---

## 🔧 **Comandos Úteis**

### **Adicionar Usuário Rapidamente:**
```python
# No arquivo multi_auth.py, adicionar:
add_user("novo_usuario", "senha123", "analyst", "Nome", "email@empresa.com")
```

### **Listar Usuários:**
```python
# Para ver todos os usuários:
users = list_users()
print(users)
```

### **Verificar Permissões:**
```python
# Verificar se é admin:
if is_admin():
    print("Usuário é administrador")
```

---

## 🛡️ **Segurança**

### **Senhas Fortes:**
- ✅ **BOM**: `MinhaSenh@Forte123`
- ❌ **RUIM**: `123456`

### **Boas Práticas:**
1. **Senhas únicas** para cada usuário
2. **Roles apropriados** (não dar admin para todos)
3. **Backup** do arquivo de usuários
4. **Monitoramento** de acessos

### **Para Produção:**
- Use **banco de dados** em vez de arquivo
- Implemente **hash de senhas**
- Configure **logs de acesso**
- Use **autenticação OAuth**

---

## 📋 **Checklist de Usuários**

### **Antes de Adicionar:**
- [ ] Senha forte definida
- [ ] Role apropriado selecionado
- [ ] Email válido
- [ ] Nome completo

### **Após Adicionar:**
- [ ] Testar login
- [ ] Verificar permissões
- [ ] Documentar acesso
- [ ] Treinar usuário

---

## 🆘 **Troubleshooting**

### **Usuário não consegue fazer login:**
1. Verificar se usuário existe em `USERS_DATABASE`
2. Confirmar senha correta
3. Verificar se role está definido

### **Erro de permissão:**
1. Verificar se `is_admin()` retorna True
2. Confirmar role do usuário
3. Verificar se função requer admin

### **Sessão expira muito rápido:**
1. Ajustar `SESSION_TIMEOUT` em `multi_auth.py`
2. Verificar se usuário está ativo
3. Confirmar se não há conflitos de sessão

---

## 📞 **Suporte**

Para dúvidas sobre gerenciamento de usuários:
1. Verificar este guia
2. Testar em ambiente local
3. Verificar logs do Streamlit
4. Contatar administrador do sistema

---

**🔐 Lembre-se: Dados de vendas são informações sensíveis. Gerencie usuários com responsabilidade!**
