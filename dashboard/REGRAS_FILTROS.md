# Regras de Filtros - Dashboard de Leads

## 📋 Visão Geral
Este documento registra as regras e exclusões aplicadas aos filtros do dashboard de leads para manter a interface limpa e organizada.

## 🚫 Corretores Ocultos do Filtro

### Regra Aplicada
Os seguintes corretores são **ocultados da lista de seleção** do filtro "Corretor", mas **mantêm seus dados** no conjunto de dados para análise.

### Lista de Corretores Excluídos

| # | Nome do Corretor | Motivo da Exclusão |
|---|------------------|-------------------|
| 1 | ODAIR DIAS DOS SANTOS | Exclusão original (já existente) |
| 2 | Sabrina M. da Silva dos Santos | Solicitação do usuário |
| 3 | Alex Anderson Fritzen da Silva | Solicitação do usuário |
| 4 | DAIANA PINHEIRO FÜHR | Solicitação do usuário |
| 5 | GRAZIELE GODOI | Solicitação do usuário |
| 6 | ROSANGELA CRISTINA BEVILAQUA | Solicitação do usuário |
| 7 | Alan Rafael Giombelli | Solicitação do usuário |
| 8 | Marcos Roberto ferla | Solicitação do usuário |
| 9 | JULIANO RAFAEL SIMON | Solicitação do usuário |
| 10 | HYORRANA LOPES | Solicitação do usuário |
| 11 | Sabrina maria da silva dos santos | Solicitação do usuário |
| 12 | VANESSA CARDOSO NAZARIN | Solicitação do usuário |

## 🔧 Implementação Técnica

### Localização do Código
**Arquivo**: `dashboard/pages/Leads.py`  
**Seção**: Filtros - Corretor (linhas ~106-123)

### Código Implementado
```python
# Lista de corretores a serem ocultados do filtro
corretores_ocultos = [
    "ODAIR DIAS DOS SANTOS",
    "Sabrina M. da Silva dos Santos",
    "Alex Anderson Fritzen da Silva",
    "DAIANA PINHEIRO FÜHR",
    "GRAZIELE GODOI",
    "ROSANGELA CRISTINA BEVILAQUA",
    "Alan Rafael Giombelli",
    "Marcos Roberto ferla",
    "JULIANO RAFAEL SIMON",
    "HYORRANA LOPES",
    "Sabrina maria da silva dos santos",
    "VANESSA CARDOSO NAZARIN"
]

# Remover corretores da lista de seleção
corretores = [c for c in corretores if c not in corretores_ocultos]
```

## 📊 Impacto nos Dados

### ✅ O que é Mantido
- **Dados completos**: Todos os leads desses corretores continuam no conjunto
- **Análises**: Incluídos em todas as tabelas e funis
- **Métricas**: Contabilizados em todos os cálculos
- **Relatórios**: Aparecem nas análises gerais

### ❌ O que é Ocultado
- **Filtro de seleção**: Não aparecem na lista do filtro "Corretor"
- **Interface**: Lista de corretores mais limpa e organizada

## 🔄 Como Adicionar/Remover Corretores

### Para Adicionar um Novo Corretor à Lista de Exclusão
1. Editar o arquivo `dashboard/pages/Leads.py`
2. Localizar a lista `corretores_ocultos`
3. Adicionar o nome exato do corretor na lista
4. Fazer commit das alterações

### Para Remover um Corretor da Lista de Exclusão
1. Editar o arquivo `dashboard/pages/Leads.py`
2. Localizar a lista `corretores_ocultos`
3. Remover o nome do corretor da lista
4. Fazer commit das alterações

## 📅 Histórico de Alterações

| Data | Alteração | Responsável |
|------|-----------|-------------|
| 2025-01-23 | Criação da documentação e registro inicial | Sistema |
| 2025-01-23 | Adição de 11 corretores à lista de exclusão | Usuário |

## ⚠️ Observações Importantes

1. **Case Sensitive**: Os nomes devem ser exatamente como aparecem no banco de dados
2. **Espaços**: Atenção aos espaços extras no início/fim dos nomes
3. **Acentos**: Manter acentos e caracteres especiais exatamente como no banco
4. **Teste**: Sempre testar após adicionar/remover nomes da lista

## 🎯 Objetivo
Manter a interface do dashboard limpa e organizada, ocultando corretores específicos do filtro sem perder os dados para análise.
