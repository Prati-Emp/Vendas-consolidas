# Integração de Dashboards - Repositório Reservas

## Resumo da Integração

Este documento descreve a integração completa dos dashboards do repositório `dash-reservas` para o repositório atual `Vendas_Consolidadas`, conforme solicitado.

## Estrutura Final Implementada

### Dashboard Principal
- **Home.py** - Dashboard de reservas (versão do dash-reservas)
- **config.py** - Configuração segura de tokens (novo)
- **utils.py** - Navegação com 7 botões (atualizado)

### Páginas do Dashboard
1. **Vendas.py** - Análise de vendas com metas hardcoded (versão do dash-reservas)
2. **Imobiliaria.py** - Análise de imobiliárias (versão do dash-reservas)
3. **Leads.py** - Funil de leads completo (versão do dash-reservas)
4. **Leads_Ativos.py** - Funil de leads ativos (versão do dash-reservas)
5. **Motivo_fora_do_prazo.py** - Análise de reservas fora do prazo (versão do dash-reservas)
6. **Vendas_Sienge.py** - Dashboard de vendas consolidadas (novo, baseado em vendas_consolidadas/app.py)

### Utilitários
- **dashboard/utils/md_conn.py** - Conexões e queries MotherDuck (movido de vendas_consolidadas)
- **dashboard/utils/formatters.py** - Formatadores (movido de vendas_consolidadas)

## Navegação Atualizada

A navegação agora possui 7 botões:
1. **Home** - Dashboard principal de reservas
2. **Vendas** - Análise de vendas (reservas)
3. **Imobiliária** - Análise de imobiliárias
4. **Motivo fora do prazo** - Análise de reservas fora do prazo
5. **Leads** - Funil de leads completo
6. **Leads Ativos** - Funil de leads ativos
7. **Vendas Sienge** - Dashboard de vendas consolidadas (novo)

## Bancos de Dados

### MotherDuck Database `reservas`
Usado pelas páginas:
- Home.py
- Vendas.py
- Imobiliaria.py
- Leads.py
- Leads_Ativos.py
- Motivo_fora_do_prazo.py

### MotherDuck Database `informacoes_consolidadas`
Usado pela página:
- Vendas_Sienge.py

## Arquivos Removidos

- **dashboard/pages/20_Vendas_CV.py** - Removido (não mais necessário)

## Arquivos de Backup

- **dashboard_backup/** - Backup completo da pasta dashboard original

## Configuração de Segurança

O arquivo `config.py` foi adicionado para gerenciar tokens de forma segura:
- MotherDuck tokens
- Credenciais CVCRM
- Headers de API

## Compatibilidade

- Ambos os sistemas usam Streamlit, Pandas, DuckDB, Plotly
- Mesmo sistema de autenticação MotherDuck
- Formatação de moeda similar
- Estrutura de páginas compatível

## Próximos Passos

1. Testar todas as páginas do dashboard
2. Verificar conexões com ambos os bancos de dados
3. Validar navegação entre páginas
4. Remover pasta `vendas_consolidadas/` após confirmação de funcionamento
5. Atualizar documentação conforme necessário

## Data da Integração

**Data:** 17 de outubro de 2025
**Status:** ✅ Integração Completa
**Teste:** ✅ Dashboard executado com sucesso
