# ⚡ Regras de Acesso - Resumo Rápido

## 🎯 **Regras Atuais**

### **Odair Santos (odair.santos@grupoprati.com)**
- ✅ **Acesso**: Todas as páginas
- 📄 **Páginas**: Vendas, Leads, Reservas, Motivo Fora do Prazo

### **Demais Usuários**
- ✅ **Acesso**: Apenas Vendas
- ❌ **Bloqueadas**: Leads, Reservas, Motivo Fora do Prazo

---

## 🔧 **Arquivos Principais**

| Arquivo | Função | Localização |
|---------|--------|-------------|
| `advanced_auth.py` | Sistema de autenticação e permissões | `dashboard/` |
| `utils.py` | Navegação inteligente | `dashboard/` |
| `pages/*.py` | Páginas protegidas | `dashboard/pages/` |

---

## ⚙️ **Como Modificar Acesso**

### **1. Adicionar Usuário com Acesso Total**
```python
# Em advanced_auth.py, função get_user_pages():
if user_data.get('email') in ['odair.santos@grupoprati.com', 'novo.admin@empresa.com']:
    return ['vendas', 'leads', 'reservas', 'motivo_fora_prazo']
```

### **2. Adicionar Usuário com Acesso Limitado**
```python
# Em advanced_auth.py, USERS_DATABASE:
"novo.usuario@empresa.com": {
    "password": "Senha123!",
    "role": "analyst",
    "name": "Novo Usuário",
    "department": "Vendas",
    "created": "2024-10-22",
    "last_login": None,
    "active": True
}
```

### **3. Modificar Permissões de Usuário Específico**
```python
# Em get_user_pages(), adicionar lógica específica:
if user_data.get('email') == 'usuario.especial@empresa.com':
    return ['vendas', 'leads']  # Apenas Vendas e Leads
```

---

## 🚨 **Problemas Comuns**

| Problema | Causa | Solução |
|----------|-------|---------|
| "Acesso negado" para Odair | Email não detectado | Verificar `user_data["email"]` |
| Páginas não carregam | Importação circular | Mover import para dentro da função |
| Botões não aparecem | Permissão incorreta | Verificar `get_user_pages()` |

---

## 📝 **Checklist Rápido**

- [ ] Usuário logado corretamente?
- [ ] Email sendo salvo em `user_data`?
- [ ] Função `get_user_pages()` retornando páginas corretas?
- [ ] Navegação mostrando botões permitidos?
- [ ] Páginas protegidas com `require_page_access()`?

---

## 🎯 **Comandos Úteis**

```bash
# Verificar status do sistema
git status

# Fazer backup antes de mudanças
git commit -m "Backup antes de alterar permissões"

# Aplicar mudanças
git add .
git commit -m "Alterar permissões de acesso"
git push origin main
```

---

**💡 Dica**: Sempre teste as mudanças em ambiente de desenvolvimento antes de aplicar em produção!
