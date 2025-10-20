# 🔐 Configuração de Ambiente - Sistema de Vendas Consolidadas

## ⚠️ IMPORTANTE - Arquivo .env

### 🚨 NUNCA SOBRESCREVER O ARQUIVO .env

O arquivo `.env` contém as **credenciais reais** do sistema e **NUNCA** deve ser:
- ❌ Sobrescrito
- ❌ Apagado
- ❌ Versionado no Git
- ❌ Compartilhado

### 📋 Estrutura do Arquivo .env

O arquivo `.env` deve conter as credenciais reais (exemplo abaixo):

```env
# CVCRM - Sistema Principal
CVCRM_EMAIL=seu_email@exemplo.com
CVCRM_TOKEN=seu_token_cvcrm

# Sienge - Sistema Imobiliário  
SIENGE_TOKEN=seu_token_sienge

# MotherDuck - Banco de Dados
MOTHERDUCK_TOKEN=seu_token_motherduck

# URLs das APIs (opcional)
CV_VENDAS_BASE_URL=https://exemplo.cvcrm.com.br/api/v1/cvdw/vendas
SIENGE_BASE_URL=https://api.sienge.com.br/exemplo/public/api/bulk-data/v1

# Flags de controle
SIENGE_SKIP_CANCELADAS=false
CV_REPASSES_ENABLED=true
CV_LEADS_ENABLED=true
```

### 🔧 Como Verificar se Está Funcionando

Para verificar se as credenciais estão corretas:

```bash
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('CVCRM_EMAIL:', os.environ.get('CVCRM_EMAIL')); print('CVCRM_TOKEN:', 'SET' if os.environ.get('CVCRM_TOKEN') else 'NOT_FOUND')"
```

### 📁 Arquivos Relacionados

- **`.env`** - Credenciais reais (NUNCA tocar)
- **`config_exemplo.env`** - Template para referência
- **`.gitignore`** - Garante que .env não seja versionado

### 🚀 Scripts de Execução

Para executar atualizações:

```bash
# Atualizar apenas leads
python atualizar_leads_completo.py

# Atualizar sistema completo
python sistema_completo.py

# Executar dashboard
python dashboard/Home.py
```

### 🔒 Segurança

- ✅ Arquivo `.env` está no `.gitignore`
- ✅ Credenciais nunca são expostas no código
- ✅ Cada ambiente tem suas próprias credenciais
- ✅ Tokens são rotacionados periodicamente

---

**Última atualização**: $(date)  
**Status**: ✅ Configurado e funcionando


