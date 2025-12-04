# ⚙️ Streamlit Operações

Aplicativo independente do dashboard **Operações** baseado na view `informacoes_consolidadas.Jira_status_tarefas`.

## 🧱 Estrutura

- `app.py`: roteador principal que autentica o usuário e redireciona para a primeira página liberada.
- `pages/1_Jira.py`: monitoramento completo das tarefas do Jira.
- `pages/2_Solicitacao_de_Compras.py`: visão semanal das solicitações de compras (KPIs, filtros e detalhamento).
- `pages/3_Pedidos_de_Compras.py`: indicadores consolidados de pedidos de compras.
- `navigation.py`: navegação horizontal entre as páginas, respeitando permissões do `advanced_auth`.

## 🚀 Executar localmente

```bash
cd streamlit_operacoes
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
streamlit run app.py
```

Após iniciar, escolha a página desejada pela navegação superior (Jira, Solicitação de compras ou Pedidos de compras). Cada página roda isoladamente, com filtros exclusivos.

> Configure o token do MotherDuck no `.env` do projeto raiz (`MOTHERDUCK_TOKEN`) antes de executar.

## 📦 Deploy no Streamlit Cloud
1. Conecte o repositório no Streamlit Cloud.
2. Configure o app apontando para `streamlit_operacoes/app.py`.
3. Defina as variáveis de ambiente (ex.: `MOTHERDUCK_TOKEN`) via **Secrets**.
4. Clique em **Deploy**.

## 🔐 Autenticação
Reutiliza o mesmo `advanced_auth` do dashboard principal. Somente usuários com permissão `operacoes` têm acesso.


