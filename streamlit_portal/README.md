# Portal de Dashboards Prati

App central para reunir links dos apps publicados no Streamlit Cloud.

## Como funciona

- Exige login com o mesmo `advanced_auth` do projeto.
- Mostra **somente** os cards dos apps que o usuário pode acessar (`can_access_page`).
- URLs dos apps são configuradas em `st.secrets`, sem hardcode no código.

## Main file path (deploy)

`streamlit_portal/app.py`

## Secrets esperados (exemplo)

```toml
[portal_links]
vendas = "https://SEU-APP-VENDAS.streamlit.app"
operacoes = "https://SEU-APP-OPERACOES.streamlit.app"
administrativo = "https://SEU-APP-ADMIN.streamlit.app"
tv_comercial = "https://SEU-APP-TV.streamlit.app"
rh_portal = "https://SEU-APP-RH.streamlit.app"
```

