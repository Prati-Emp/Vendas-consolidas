# Regras de Exclusão - Dashboard de Leads

## 📋 Visão Geral
Este documento registra as regras de exclusão aplicadas ao dashboard de leads para remover completamente corretores específicos de todas as análises.

## 🚫 Corretores Removidos Completamente

### Regra Aplicada
Os seguintes corretores são **completamente removidos** do conjunto de dados do dashboard, incluindo todas as análises, tabelas e funis.

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
**Seção**: Remoção de Corretores Específicos (linhas ~75-95)

### Código Implementado
```python
# Lista de corretores a serem removidos completamente dos dados
corretores_removidos = [
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

# Remover leads desses corretores do conjunto de dados
leads_df = leads_df[~leads_df['corretor_consolidado'].isin(corretores_removidos)]
```

## 📊 Impacto nos Dados

### ❌ O que é Removido Completamente
- **Dados**: Todos os leads desses corretores são removidos do conjunto
- **Análises**: Não aparecem em nenhuma tabela ou funil
- **Métricas**: Não são contabilizados em nenhum cálculo
- **Relatórios**: Não aparecem em nenhuma análise
- **Filtros**: Não aparecem na lista do filtro "Corretor"
- **Interface**: Dashboard focado apenas em corretores ativos

### ✅ O que é Mantido
- **Performance**: Dashboard mais rápido e focado
- **Clareza**: Análises mais limpas e relevantes
- **Gestão**: Foco em corretores ativos e produtivos

## 🔄 Como Adicionar/Remover Corretores

### Para Adicionar um Novo Corretor à Lista de Exclusão
1. Editar o arquivo `dashboard/pages/Leads.py`
2. Localizar a lista `corretores_removidos`
3. Adicionar o nome exato do corretor na lista
4. Fazer commit das alterações

### Para Remover um Corretor da Lista de Exclusão
1. Editar o arquivo `dashboard/pages/Leads.py`
2. Localizar a lista `corretores_removidos`
3. Remover o nome do corretor da lista
4. Fazer commit das alterações

## 📅 Histórico de Alterações

| Data | Alteração | Responsável |
|------|-----------|-------------|
| 2025-01-23 | Criação da documentação e registro inicial | Sistema |
| 2025-01-23 | Adição de 11 corretores à lista de exclusão | Usuário |
| 2025-01-23 | **MUDANÇA DE REGRA**: Remoção completa dos dados (não apenas do filtro) | Usuário |

## ⚠️ Observações Importantes

1. **Case Sensitive**: Os nomes devem ser exatamente como aparecem no banco de dados
2. **Espaços**: Atenção aos espaços extras no início/fim dos nomes
3. **Acentos**: Manter acentos e caracteres especiais exatamente como no banco
4. **Teste**: Sempre testar após adicionar/remover nomes da lista

## 🎯 Objetivo
Remover completamente corretores específicos do dashboard para focar apenas em corretores ativos e relevantes, melhorando a performance e clareza das análises.
