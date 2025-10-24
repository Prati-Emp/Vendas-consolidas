# 🔐 Sistema de Controle de Acesso por Páginas

## 📋 **Visão Geral**

O sistema implementa **controle de acesso granular** baseado no **role do usuário**, permitindo que diferentes usuários vejam apenas as páginas autorizadas.

## 👥 **Usuários e Permissões**

### **Odair Santos (odair.santos@grupoprati.com)**
- ✅ **Acesso total**: Todas as páginas
- 📄 **Páginas disponíveis**: Vendas, Leads, Reservas, Motivo Fora do Prazo

### **Demais Usuários (Gustavo, Lucas, José, Evelyn)**
- ✅ **Acesso limitado**: Apenas página de Vendas
- 📄 **Páginas disponíveis**: Vendas
- ❌ **Páginas bloqueadas**: Leads, Reservas, Motivo Fora do Prazo

## 🛡️ **Como Funciona**

### **1. Autenticação**
```python
# Cada página verifica se o usuário está logado
require_auth()
```

### **2. Controle de Página**
```python
# Cada página verifica se o usuário tem permissão
require_page_access("nome_da_pagina")
```

### **3. Navegação Inteligente**
- **Botões aparecem apenas** para páginas que o usuário pode acessar
- **Acesso direto via URL** é bloqueado com mensagem de erro
- **Páginas disponíveis** são mostradas quando acesso é negado

## 📁 **Estrutura de Páginas**

| Página | Arquivo | Acesso |
|--------|---------|--------|
| **Vendas** | `pages/Vendas.py` | Odair + Demais usuários |
| **Leads** | `pages/Leads.py` | Apenas Odair |
| **Reservas** | `Reservas.py` | Apenas Odair |
| **Motivo Fora do Prazo** | `pages/Motivo_fora_do_prazo.py` | Apenas Odair |

## 🔧 **Configuração de Novos Usuários**

### **Adicionar Usuário com Acesso Limitado:**
```python
# No arquivo advanced_auth.py, adicionar:
"novo.analista@empresa.com": {
    "password": "Senha123!",
    "role": "analyst",  # Só vê Vendas e Leads
    "name": "Novo Analista",
    "department": "Análise",
    "created": "2024-10-22",
    "last_login": None,
    "active": True
}
```

### **Adicionar Usuário com Acesso Completo:**
```python
"novo.gerente@empresa.com": {
    "password": "Senha123!",
    "role": "manager",  # Vê todas as páginas
    "name": "Novo Gerente",
    "department": "Vendas",
    "created": "2024-10-22",
    "last_login": None,
    "active": True
}
```

## 🚀 **Implementação Técnica**

### **1. Verificação de Página**
```python
def require_page_access(page_name: str):
    if not can_access_page(page_name):
        st.error("🚫 Acesso negado!")
        st.stop()
```

### **2. Navegação Dinâmica**
```python
# Só mostra botões para páginas permitidas
for item_name, page_key, page_path in nav_items:
    if can_access_page(page_key):
        # Mostrar botão
```

### **3. Mapeamento de Permissões**
```python
def get_user_pages(user_data: Dict) -> List[str]:
    # Odair tem acesso total
    if user_data.get('email') == 'odair.santos@grupoprati.com':
        return ['vendas', 'leads', 'reservas', 'motivo_fora_prazo']
    
    # Todos os demais usuários veem apenas Vendas
    return ['vendas']
```

## ✅ **Benefícios**

1. **Segurança**: Dados sensíveis protegidos por role
2. **Usabilidade**: Interface limpa, sem opções desnecessárias
3. **Flexibilidade**: Fácil adição de novos usuários e permissões
4. **Auditoria**: Controle de quem acessa o quê

## 🔄 **Fluxo de Acesso**

1. **Login** → Verificação de credenciais
2. **Navegação** → Mostra apenas páginas permitidas
3. **Acesso Direto** → Bloqueia com mensagem de erro
4. **Sessão** → Expira em 1 hora automaticamente

---

**💡 Dica**: Para alterar permissões, edite o arquivo `advanced_auth.py` na função `get_user_pages()`.
