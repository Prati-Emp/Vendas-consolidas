# Regras de Status de Leads

## Visão Geral
As colunas de status são criadas automaticamente baseadas nas tags dos leads, seguindo uma lógica hierárquica que reflete o funil de vendas.

## Colunas de Status

### 1. status_venda_realizada
- **Descrição**: Indica se o lead chegou ao final do funil (venda realizada)
- **Valores**: "Sim" ou "Não"
- **Tags detectadas**: "venda realizada", "vendarealizada"

### 2. status_reserva
- **Descrição**: Indica se o lead fez uma reserva
- **Valores**: "Sim" ou "Não"
- **Tags detectadas**: "reserva"

### 3. status_visita_realizada
- **Descrição**: Indica se o lead realizou uma visita
- **Valores**: "Sim" ou "Não"
- **Tags detectadas**: "visita realizada", "visitarealizada"

### 4. status_em_atendimento
- **Descrição**: Indica se o lead está em atendimento
- **Valores**: "Sim" ou "Não"
- **Tags detectadas**: "em atendimento" (apenas esta variação, não "em atendimento corretor")

### 5. status_descoberta
- **Descrição**: Indica se o lead passou pela fase de descoberta
- **Valores**: "Sim" ou "Não"
- **Tags detectadas**: "descoberta"

### 6. status_qualificacao
- **Descrição**: Indica se o lead foi qualificado
- **Valores**: "Sim" ou "Não"
- **Tags detectadas**: "qualificação", "qualificacao", "qualificaçao"

## Lógica Hierárquica

A hierarquia segue a ordem do funil de vendas (do final para o início):

1. **venda realizada** (final do funil)
2. **reserva**
3. **visita realizada**
4. **em atendimento**
5. **descoberta**
6. **qualificação** (início do funil)

### Regras de Preenchimento

- **Se "venda realizada"**: TODOS os status = "Sim"
- **Se "reserva"**: reserva, visita realizada, em atendimento, descoberta, qualificação = "Sim"
- **Se "visita realizada"**: visita realizada, em atendimento, descoberta, qualificação = "Sim"
- **Se "em atendimento"**: em atendimento, descoberta, qualificação = "Sim"
- **Se "descoberta"**: descoberta, qualificação = "Sim"
- **Se "qualificação"**: apenas qualificação = "Sim"

## Tratamento de Tags

### Palavras Concatenadas
O sistema detecta automaticamente palavras concatenadas (sem espaços):
- "vendarealizada" → detecta "venda realizada"
- "visitarealizada" → detecta "visita realizada"

### Busca Dinâmica
- Percorre todas as colunas tag1, tag2, tag3... tagN
- Funciona automaticamente quando novas colunas de tags são adicionadas
- Busca case-insensitive (não diferencia maiúsculas/minúsculas)

### Exclusões Específicas
- "em atendimento corretor" NÃO é detectado como "em atendimento"
- Apenas "em atendimento" é considerado

## Exemplos Práticos

### Exemplo 1: Lead com venda realizada
**Tags**: ["qualificação", "descoberta", "em atendimento", "visita realizada", "reserva", "venda realizada"]
**Resultado**:
- status_venda_realizada: "Sim"
- status_reserva: "Sim"
- status_visita_realizada: "Sim"
- status_em_atendimento: "Sim"
- status_descoberta: "Sim"
- status_qualificacao: "Sim"

### Exemplo 2: Lead em atendimento
**Tags**: ["qualificação", "descoberta", "em atendimento"]
**Resultado**:
- status_venda_realizada: "Não"
- status_reserva: "Não"
- status_visita_realizada: "Não"
- status_em_atendimento: "Sim"
- status_descoberta: "Sim"
- status_qualificacao: "Sim"

### Exemplo 3: Lead apenas qualificado
**Tags**: ["qualificação"]
**Resultado**:
- status_venda_realizada: "Não"
- status_reserva: "Não"
- status_visita_realizada: "Não"
- status_em_atendimento: "Não"
- status_descoberta: "Não"
- status_qualificacao: "Sim"

## Implementação Técnica

### Processamento
1. Inicializa todas as colunas de status como "Não"
2. Percorre todas as colunas de tags dinamicamente
3. Coleta todas as tags não vazias da linha
4. Verifica cada status nas tags (com variações)
5. Aplica lógica hierárquica baseada no status mais avançado encontrado

### Performance
- Processamento linha por linha para garantir precisão
- Busca otimizada em todas as colunas de tags
- Detecção automática de novas colunas de tags

## Manutenção

### Adicionando Novos Status
1. Adicionar nova entrada em `status_definitions`
2. Definir variações de tags (incluindo concatenadas)
3. Atualizar lógica hierárquica se necessário
4. Documentar nova regra

### Adicionando Novas Variações de Tags
1. Adicionar variação na lista correspondente em `status_definitions`
2. Testar com dados reais
3. Atualizar documentação se necessário
