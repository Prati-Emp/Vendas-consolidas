# 🚀 Como Executar o Dashboard de Repasses

## 📋 Pré-requisitos

- Python 3.8+ instalado
- Dependências do projeto (já instaladas)

## 🎯 Métodos de Execução

### Método 1: Scripts Automatizados (Recomendado)

#### Windows (PowerShell):
```powershell
.\executar_dashboard.ps1
```

#### Windows (CMD):
```cmd
executar_dashboard.bat
```

### Método 2: Comando Manual

#### Opção A: Via Python Module
```bash
# Do diretório raiz do projeto
python -m streamlit run repasses/dashboard_app/app.py
```

#### Opção B: Via Script de Execução
```bash
# Do diretório raiz do projeto
python -m streamlit run repasses/run_dashboard.py
```

### Método 3: Execução Direta

```bash
# Navegar para o diretório repasses
cd repasses

# Executar o dashboard
python -m streamlit run dashboard_app/app.py
```

## 🌐 Acesso ao Dashboard

Após executar qualquer um dos métodos acima:

1. **URL Local**: `http://localhost:8501`
2. **URL de Rede**: `http://[seu-ip]:8501`

O navegador deve abrir automaticamente. Se não abrir, acesse manualmente a URL.

## 🎛️ Navegação no Dashboard

### Sidebar de Navegação
- **🏠 Overview** - Visão geral e KPIs
- **📊 Por Empreendimento** - Análise por empreendimento
- **🏦 Banco & Correspondente** - Performance por banco
- **⏱️ SLA & Bottlenecks** - Análise de tempos
- **🔍 Qualidade de Dados** - Monitoramento de dados

### Filtros Globais
- Configure os filtros na página inicial
- Os filtros se aplicam a todas as páginas
- Filtros persistem durante a navegação

## 🔧 Solução de Problemas

### Erro: "streamlit não é reconhecido"
```bash
# Instalar Streamlit
python -m pip install streamlit

# Ou instalar todas as dependências
python -m pip install -r requirements.txt
```

### Erro: "Módulo não encontrado"
```bash
# Verificar se está no diretório correto
pwd  # Deve mostrar: .../Vendas_Consolidadas

# Executar do diretório raiz
python -m streamlit run repasses/dashboard_app/app.py
```

### Erro: "Porta já em uso"
```bash
# O Streamlit tentará usar a próxima porta disponível
# Ou especificar uma porta diferente:
python -m streamlit run repasses/dashboard_app/app.py --server.port 8502
```

## 📊 Funcionalidades do Dashboard

### ✅ Implementado
- ✅ Navegação unificada entre páginas
- ✅ Filtros globais compartilhados
- ✅ Interface responsiva
- ✅ Exportação de dados (CSV)
- ✅ Gráficos interativos
- ✅ Métricas em tempo real

### 🎨 Interface
- **Design**: Moderno e intuitivo
- **Cores**: Esquema consistente por estágio
- **Layout**: Wide layout para melhor visualização
- **Navegação**: Sidebar lateral com botões

## 🚀 Próximos Passos

1. **Executar o dashboard** usando qualquer método acima
2. **Configurar filtros** na página inicial
3. **Navegar entre páginas** usando a sidebar
4. **Explorar os dados** e visualizações
5. **Exportar relatórios** conforme necessário

## 📞 Suporte

Se encontrar problemas:
1. Verificar se todas as dependências estão instaladas
2. Executar o script de teste: `python repasses/test_dashboard.py`
3. Verificar logs do Streamlit no terminal
4. Consultar a documentação em `repasses/dashboard_app/README.md`

---

**🎉 Dashboard pronto para uso!**
