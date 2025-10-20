# 🚀 Guia do Dashboard de Reservas

## 📋 Visão Geral

O Dashboard de Reservas é uma aplicação Streamlit que permite visualizar e analisar dados de reservas imobiliárias de forma interativa e em tempo real.

## 🎯 Funcionalidades

### ✅ Implementado
- **📊 Relatório de Reservas**: Visão geral com métricas principais
- **🏢 Análise por Empreendimento**: Performance por empreendimento
- **⏱️ Controle de Prazos**: Monitoramento de reservas fora do prazo
- **📈 Funil de Vendas**: Análise do workflow de vendas
- **🔍 Filtros Interativos**: Por data, empreendimento e situação
- **📱 Interface Responsiva**: Design moderno e intuitivo

### 🎨 Páginas Disponíveis
- **Home**: Página principal com visão geral
- **Vendas**: Análise de vendas
- **Imobiliária**: Performance por imobiliária
- **Motivo fora do prazo**: Análise de atrasos
- **Leads**: Gestão de leads
- **Leads Ativos**: Leads em andamento
- **Vendas Sienge**: Integração com sistema Sienge

## 🚀 Como Executar

### Método 1: Scripts Automatizados (Recomendado)

#### Windows (PowerShell):
```powershell
.\executar_dashboard_reservas.ps1
```

#### Windows (CMD):
```cmd
executar_dashboard_reservas.bat
```

### Método 2: Comando Manual

```bash
# Navegar para o diretório dashboard
cd dashboard

# Executar o dashboard
python -m streamlit run Home.py --server.port 8501
```

### Método 3: Do diretório raiz

```bash
# Do diretório raiz do projeto
python -m streamlit run dashboard/Home.py --server.port 8501
```

## 🌐 Acesso ao Dashboard

Após executar qualquer método:

1. **URL Local**: `http://localhost:8501`
2. **URL de Rede**: `http://[seu-ip]:8501`

O navegador deve abrir automaticamente. Se não abrir, acesse manualmente a URL.

## 🔧 Configuração

### Variáveis de Ambiente

O dashboard utiliza as seguintes variáveis de ambiente:

- `MOTHERDUCK_TOKEN`: Token de acesso ao banco MotherDuck

### Configuração Automática

O sistema carrega automaticamente as configurações do arquivo `motherduck_config.env` na raiz do projeto.

## 📊 Estrutura dos Dados

### Tabelas Utilizadas
- `reservas.main.reservas_abril`: Dados principais das reservas
- `reservas.main.workflow_abril`: Dados do workflow de vendas

### Métricas Principais
- **Total de Reservas**: Quantidade de reservas ativas
- **Valor Total**: Soma dos valores dos contratos
- **Fora do Prazo**: Reservas que excederam o tempo limite
- **Tempo Médio**: Tempo médio por situação

## 🎛️ Navegação

### Barra de Navegação
- **Home**: Página principal
- **Vendas**: Análise de vendas
- **Imobiliária**: Performance por imobiliária
- **Motivo fora do prazo**: Análise de atrasos
- **Leads**: Gestão de leads
- **Leads Ativos**: Leads em andamento
- **Vendas Sienge**: Integração Sienge

### Filtros Disponíveis
- **Data Inicial/Final**: Período de análise
- **Empreendimento**: Filtro por empreendimento específico
- **Situação**: Filtro por situação da reserva

## 🔍 Análises Disponíveis

### 1. Reservas por Situação
- Quantidade por situação
- Reservas fora do prazo
- Tempo médio por situação
- Reservas dentro do prazo

### 2. Reservas por Empreendimento
- Performance por empreendimento
- Análise de prazos
- Métricas consolidadas

### 3. Lista Detalhada
- Lista completa de reservas
- Destaque para reservas fora do prazo
- Informações detalhadas de cada reserva

### 4. Análise de Workflow
- Funil de vendas interativo
- Gráfico de barras
- Detalhamento por situação

## 🚨 Solução de Problemas

### Erro: "MOTHERDUCK_TOKEN não encontrado"
```bash
# Verificar se o arquivo motherduck_config.env existe
# E se contém o token correto
```

### Erro: "Dependências não encontradas"
```bash
# Instalar dependências
pip install -r requirements.txt
```

### Erro: "Porta já em uso"
```bash
# Usar porta diferente
python -m streamlit run dashboard/Home.py --server.port 8502
```

### Erro: "Módulo não encontrado"
```bash
# Verificar se está no diretório correto
# Executar do diretório raiz do projeto
```

## 📈 Próximos Passos

1. **Executar o dashboard** usando qualquer método acima
2. **Configurar filtros** na página inicial
3. **Navegar entre páginas** usando a barra de navegação
4. **Explorar os dados** e visualizações
5. **Analisar métricas** e identificar oportunidades

## 🎉 Dashboard Pronto!

O dashboard está configurado e pronto para uso. Todas as funcionalidades estão implementadas e testadas.

---

**📞 Suporte**: Em caso de problemas, verificar logs do Streamlit no terminal ou consultar a documentação técnica.

