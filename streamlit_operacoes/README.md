# ⚙️ Streamlit Operações

Aplicativo independente do dashboard **Operações** baseado na view `informacoes_consolidadas.Jira_status_tarefas`.

## 🚀 Executar localmente

```bash
cd streamlit_operacoes
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
streamlit run app.py
```

Configure o token do MotherDuck no `.env` do projeto raiz (`MOTHERDUCK_TOKEN`) antes de executar.

## 📦 Deploy no Streamlit Cloud
1. Conecte o repositório no Streamlit Cloud.
2. Configure o app apontando para `streamlit_operacoes/app.py`.
3. Defina as variáveis de ambiente (ex.: `MOTHERDUCK_TOKEN`) via **Secrets**.
4. Clique em **Deploy**.

## 🔐 Autenticação
Reutiliza o mesmo `advanced_auth` do dashboard principal. Somente usuários com permissão `operacoes` têm acesso.


