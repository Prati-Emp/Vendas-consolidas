# 🔐 Configuração de Secrets do GitHub Actions - Jira

## 📋 Variáveis Necessárias

Para que a API do Jira funcione corretamente no GitHub Actions, você precisa adicionar as seguintes variáveis como **Secrets** no repositório:

### ✅ **Secrets Obrigatórios para Jira:**

1. **`JIRA_URL`**
   - **Valor:** `https://prati-empreendimentos.atlassian.net`
   - **Descrição:** URL base do Jira (sem `/rest/api/3`)
   - **Exemplo:** `https://prati-empreendimentos.atlassian.net`

2. **`JIRA_EMAIL`**
   - **Valor:** Seu e-mail do Jira
   - **Descrição:** E-mail usado para autenticação no Jira
   - **Exemplo:** `odair.santos@grupoprati.com`

3. **`JIRA_TOKEN`**
   - **Valor:** Seu token de API do Jira
   - **Descrição:** Token de autenticação do Jira (API Token)
   - **Exemplo:** `ATATT3xFfGF01iv65L6Zp7ChRvWnvFf9p582rZkyWGlhGLswg4udjk-q_YoLN3LkGYqaB-_6f_d4_HBJZV_bL46sIKJMnCn1E3oUwIPunoav2pp3So8MX4Ulnac-n3T20XSQj06VOtgpePDJY3ymEqbxI72bsPW25zuchp3aRLW07pYC3yAlG4Y=06CCD10A`
   - **Nota:** Este é um token longo. Copie o valor completo do arquivo `.env`

### 📝 **Como Adicionar Secrets no GitHub:**

1. Acesse o repositório no GitHub
2. Vá em **Settings** → **Secrets and variables** → **Actions**
3. Clique em **New repository secret**
4. Adicione cada uma das variáveis acima:
   - **Name:** `JIRA_URL` → **Secret:** `https://prati-empreendimentos.atlassian.net`
   - **Name:** `JIRA_EMAIL` → **Secret:** `odair.santos@grupoprati.com`
   - **Name:** `JIRA_TOKEN` → **Secret:** (cole o token completo do .env)

### ✅ **Secrets Já Existentes (Não Precisa Adicionar):**

Estes secrets já devem estar configurados:
- `MOTHERDUCK_TOKEN` - Token do MotherDuck (já existe)

### 🔍 **Verificação:**

Após adicionar os secrets, o workflow `.github/workflows/update-database-jira.yml` será executado automaticamente:
- **Horário:** Diariamente às 01:00 BRT (04:00 UTC)
- **Tabela criada:** `main.jira_issues` no banco `reservas` (MotherDuck)

### 📊 **Estrutura da Tabela:**

A tabela `main.jira_issues` conterá todas as colunas do exportar_issues_jira.py:
- A - Tipo de item
- B - Chave
- C - Resumo
- D - Responsável
- E - Relator
- F - Prioridade
- G - Status
- H - Resolução
- I - Criado
- J - Atualizado(a)
- K - Data limite
- L - Descrição
- M - Status Transition
- N - Status Transition.to
- O - Status Transition.from
- P - Status Transition.authorDisplayName
- Q - Status Transition.authorEmail
- R - Status Transition.date
- S - Status Transition.id
- T - Data Início corrigida
- U - Data Fim corrigida
- V - Data original início
- W - Data original fim
- X - Start date
- Y - Dias para conclusão de Tarefa
- Z - Projeto.name
- AA - Pai
- fonte (coluna de controle)
- processado_em (coluna de controle)

### ⚠️ **Importante:**

- O token do Jira é sensível. **NUNCA** commite o token no código
- Mantenha o token seguro e atualize se necessário
- O workflow tem timeout de 90 minutos (Jira pode ser demorado)

