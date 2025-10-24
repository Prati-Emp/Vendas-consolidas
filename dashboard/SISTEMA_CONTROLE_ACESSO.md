# 🔐 Sistema de Controle de Acesso

## 📋 **Visão Geral**

O dashboard implementa um sistema de controle de acesso granular que permite diferentes níveis de permissão para usuários específicos.

## 👥 **Níveis de Acesso**

### **Administrador**
- ✅ Acesso total a todas as páginas
- 📄 Páginas disponíveis: Vendas, Leads, Reservas, Motivo Fora do Prazo

### **Usuários Padrão**
- ✅ Acesso limitado
- 📄 Páginas disponíveis: Apenas Vendas

## 🛡️ **Funcionalidades**

- **Autenticação segura** com email e senha
- **Navegação inteligente** que mostra apenas páginas permitidas
- **Proteção contra acesso direto** via URL
- **Interface limpa** sem opções desnecessárias

## 🔧 **Arquitetura**

O sistema é baseado em:
- **Autenticação**: Verificação de credenciais
- **Autorização**: Controle de acesso por página
- **Navegação**: Interface adaptativa baseada em permissões

## 📁 **Arquivos Principais**

- `advanced_auth.py` - Sistema de autenticação
- `utils.py` - Navegação inteligente
- `pages/*.py` - Páginas protegidas

## 🚀 **Como Funciona**

1. **Login**: Usuário faz login com credenciais
2. **Verificação**: Sistema verifica permissões do usuário
3. **Navegação**: Interface mostra apenas páginas permitidas
4. **Proteção**: Acesso direto é bloqueado se não autorizado

---

**💡 Nota**: Para informações técnicas detalhadas sobre implementação, configuração e manutenção, consulte a documentação privada do sistema.
