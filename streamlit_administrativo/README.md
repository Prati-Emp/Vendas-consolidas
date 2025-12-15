# Dashboard Administrativo

Estrutura inicial do conjunto de dashboards do **Administrativo**, seguindo o mesmo padrão utilizado em Operações (autenticação, navegação por abas e proteção por permissões).

## Rodando localmente

```bash
pip install -r streamlit_administrativo/requirements.txt
streamlit run streamlit_administrativo/app.py
```

## Navegação e permissões
- As abas são definidas em `navigation.py`.
- Cada página deve chamar `require_auth` e `require_page_access` com as permissões adequadas (ex.: `administrativo.visao_geral`).

## Deploy
Use o `Procfile` desta pasta para publicar o serviço Streamlit apontando para `streamlit_administrativo/app.py`.

