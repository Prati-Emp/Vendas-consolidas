# pages/20_Vendas_CV.py
# Página: Vendas CV
# Requisitos:
# - Env: MD_TOKEN ou MOTHERDUCK_TOKEN e (opcional) MD_DATABASE. Default DB: "reservas/main"
# - Tabela: main.cv_vendas (MotherDuck)
# - Colunas esperadas (adaptável):
#   data_venda (TIMESTAMP/DATE), data_reserva (VARCHAR/TIMESTAMP), empreendimento (TEXT),
#   imobiliaria (TEXT), tipovenda (TEXT/origem), valor_contrato (DOUBLE/VARCHAR)
# - Colunas opcionais: meta_periodo
#
# Notas:
# - Normalização de valores: pt-BR "380.000,00", en-US "380,000.00" ou DOUBLE -> DOUBLE
# - VALUE_MULTIPLIER (env) permite corrigir escala sem mexer no código (default 1.0)

import streamlit as st
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from utils import display_navigation

import pandas as pd
from datetime import date
import duckdb as ddb
import os
from dotenv import load_dotenv
import locale

# ------------------------- Config básica -------------------------
st.set_page_config(page_title="Vendas CV", layout="wide")
display_navigation()
st.session_state['current_page'] = "pages/20_Vendas_CV.py"

load_dotenv()

# Locale (best effort)
for loc in ('pt_BR.UTF-8', 'Portuguese_Brazil.1252', 'pt_BR'):
    try:
        locale.setlocale(locale.LC_ALL, loc)
        break
    except locale.Error:
        pass

# Variáveis de ambiente
MD_TOKEN = os.getenv("MD_TOKEN") or os.getenv("MOTHERDUCK_TOKEN")
MD_DATABASE = os.getenv("MD_DATABASE", "reservas/main")
VALUE_MULTIPLIER = float(os.getenv("VALUE_MULTIPLIER", "0.01"))  # <<< valores estão em centavos

st.title("📊 Vendas CV")

# ------------------------- Helpers -------------------------
@st.cache_resource
def connect():
    """Conecta ao MotherDuck (formato compatível com conta free)"""
    if not MD_TOKEN:
        st.error("MOTHERDUCK_TOKEN/MD_TOKEN não encontrado nas variáveis de ambiente.")
        st.stop()
    token = MD_TOKEN.strip().strip('"').strip("'")
    
    # Conectar diretamente ao banco especificado
    if MD_DATABASE == "reservas/main":
        # Para o formato reservas/main, conectar diretamente
        conn = ddb.connect(f"motherduck:reservas?motherduck_token={token}")
    else:
        # Para outros bancos, usar o formato padrão
        conn = ddb.connect(f"motherduck:{MD_DATABASE}?motherduck_token={token}")
    
    return conn

@st.cache_data(ttl=300)
def get_schema():
    """Obtém schema da tabela cv_vendas"""
    con = connect()
    try:
        return con.execute("PRAGMA table_info(cv_vendas)").df()
    except Exception:
        # fallback
        return pd.DataFrame({
            "name": ["data_venda","data_reserva","empreendimento","imobiliaria","tipovenda","valor_contrato"],
            "type": ["TIMESTAMP","VARCHAR","VARCHAR","VARCHAR","VARCHAR","DOUBLE"]
        })

def has(cols, name): return name in cols

def format_currency(value):
    try:
        v = float(value)
        if v >= 1_000_000:
            return f"R$ {v/1_000_000:.1f}Mi"
        if v >= 1_000:
            return f"R$ {v/1_000:.1f}Mil"
        return f"R$ {v:.1f}"
    except Exception:
        return f"R$ {value}"

def format_currency_full(value):
    try:
        s = f"R$ {float(value):,.2f}"
        return s.replace(",", "_").replace(".", ",").replace("_", ".")
    except Exception:
        return f"R$ {value}"

def make_currency_formatter(mode: str):
    if mode == "Valor completo":
        return lambda v: "-" if pd.isna(v) else format_currency_full(v)
    return lambda v: "-" if pd.isna(v) else format_currency(v)

def fmt_pct(x):
    if pd.isna(x) or x is None: return "-"
    try: return f"{float(x)*100:.1f}%"
    except: return f"{x}%"

# ------------------------- Schema & flags -------------------------
schema_df = get_schema()
if "column_name" in schema_df.columns:
    cols = set(schema_df["column_name"].str.lower())
elif "name" in schema_df.columns:
    cols = set(schema_df["name"].str.lower())
else:
    cols = {"data_venda","data_reserva","empreendimento","imobiliaria","tipovenda","valor_contrato"}

COL_DT_VENDA   = "data_venda"      if has(cols,"data_venda") else None
COL_DT_CRIACAO = "data_reserva"    if has(cols,"data_reserva") else None
COL_EMP        = "empreendimento"  if has(cols,"empreendimento") else None
COL_IMOB       = "imobiliaria"     if has(cols,"imobiliaria") else None
COL_ORIGEM     = "tipovenda"       if has(cols,"tipovenda") else None
COL_VALOR      = "valor_contrato"  if has(cols,"valor_contrato") else None
COL_META       = "meta_periodo"    if has(cols,"meta_periodo") else None

if any(v is None for v in [COL_DT_VENDA, COL_VALOR]):
    missing = [c for c in ["data_venda","valor_contrato"] if c not in cols]
    st.error("Colunas mínimas ausentes em cv_vendas: " + ", ".join(missing))
    st.stop()

# ------------------------- Filtros -------------------------
hoje = date.today()
inicio_ano = date(hoje.year, 1, 1)
with st.sidebar:
    st.header("Filtros")
    dti = st.date_input("Data inicial", value=inicio_ano)
    dtf = st.date_input("Data final", value=hoje)

    con = connect()

    if COL_EMP:
        try:
            emp_opts = con.execute(f"SELECT DISTINCT {COL_EMP} FROM cv_vendas WHERE {COL_EMP} IS NOT NULL ORDER BY 1").df()[COL_EMP].tolist()
        except Exception:
            emp_opts = []
        emp = st.selectbox("Empreendimento", ["Todos"] + emp_opts)
    else:
        emp = "Todos"

    if COL_IMOB:
        try:
            imob_opts = con.execute(f"SELECT DISTINCT {COL_IMOB} FROM cv_vendas WHERE {COL_IMOB} IS NOT NULL ORDER BY 1").df()[COL_IMOB].tolist()
        except Exception:
            imob_opts = []
        imob = st.selectbox("Imobiliária", ["Todas"] + imob_opts)
    else:
        imob = "Todas"

    format_mode = st.selectbox("Formatação de valores", ["Auto (Mi/Mil)", "Valor completo"])

# ------------------------- Query base -------------------------
@st.cache_data(ttl=300)
def query_base(dti: date, dtf: date, emp: str, imob: str, value_multiplier: float) -> pd.DataFrame:
    con = connect()

    # Lógica inteligente para detectar se valor está em centavos ou reais
    # Se valor > 1.000.000, provavelmente está em centavos (divide por 100)
    # Se valor < 1.000.000, provavelmente já está em reais (mantém)
    val_expr = f"""
    CASE 
        WHEN CAST({COL_VALOR} AS DOUBLE) > 1000000 THEN 
            CAST({COL_VALOR} AS DOUBLE) * 0.01
        ELSE 
            CAST({COL_VALOR} AS DOUBLE)
    END
    """

    select_cols = [
        f"{COL_DT_VENDA}::DATE AS data_venda",
        f"{val_expr} AS valor_venda"
    ]
    if COL_EMP:        select_cols.append(f"{COL_EMP} AS empreendimento")
    if COL_IMOB:       select_cols.append(f"{COL_IMOB} AS imobiliaria")
    if COL_ORIGEM:     select_cols.append(f"{COL_ORIGEM} AS origem")
    if COL_DT_CRIACAO: select_cols.append(f"{COL_DT_CRIACAO} AS data_criacao")
    if COL_META:       select_cols.append(f"{COL_META} AS meta_periodo")

    sql = f"""
        SELECT {', '.join(select_cols)}
        FROM cv_vendas
        WHERE {COL_DT_VENDA}::DATE BETWEEN ? AND ?
    """
    params = [pd.to_datetime(dti), pd.to_datetime(dtf)]
    if COL_EMP and emp != "Todos":
        sql += f" AND {COL_EMP} = ?"
        params.append(emp)
    if COL_IMOB and imob != "Todas":
        sql += f" AND {COL_IMOB} = ?"
        params.append(imob)

    df = con.execute(sql, params).df()

    # Origem normalizada (interna/externa) — ajuste termos conforme o seu dado real
    if "origem" in df.columns:
        on = df["origem"].astype(str).str.strip().str.lower()
        df["is_interna"] = on.str.contains("investidor|prati|interna|house", case=False, regex=True)
        df["is_externa"] = ~df["is_interna"]
    else:
        df["is_interna"] = False
        df["is_externa"] = False

    # Tempo até a venda (se houver datas)
    if "data_criacao" in df.columns and "data_venda" in df.columns:
        df["data_criacao_conv"] = pd.to_datetime(df["data_criacao"], errors='coerce')
        df["data_venda_conv"] = pd.to_datetime(df["data_venda"], errors='coerce')
        df["tempo_dias"] = (df["data_venda_conv"] - df["data_criacao_conv"]).dt.days
    else:
        df["tempo_dias"] = pd.NA

    return df

df = query_base(dti, dtf, emp, imob, VALUE_MULTIPLIER)

# --- SANITY CHECK (debug leve no app) ---
with st.expander("🔎 Diagnóstico rápido de valores (debug)"):
    # Botão para limpar cache
    if st.button("🔄 Limpar Cache e Recarregar"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()
    
    if "valor_venda" in df.columns and len(df) > 0:
        stats = {
            "dtype(valor_venda)": str(df["valor_venda"].dtype),
            "total_registros": len(df),
            "min": float(df["valor_venda"].min()),
            "p25": float(df["valor_venda"].quantile(0.25)),
            "p50": float(df["valor_venda"].median()),
            "p75": float(df["valor_venda"].quantile(0.75)),
            "p95": float(df["valor_venda"].quantile(0.95)),
            "max": float(df["valor_venda"].max()),
            "sum": float(df["valor_venda"].sum()),
            "VALUE_MULTIPLIER": VALUE_MULTIPLIER,
        }
        st.write("**Estatísticas dos valores:**")
        st.json(stats)
        
        # Mostrar primeiros valores formatados
        st.write("**Primeiros 5 valores (bruto vs formatado):**")
        if len(df) > 0:
            sample_df = df[["data_venda", "valor_venda"]].head().copy()
            sample_df["valor_formatado_auto"] = sample_df["valor_venda"].apply(lambda x: format_currency(x))
            sample_df["valor_formatado_full"] = sample_df["valor_venda"].apply(lambda x: format_currency_full(x))
            st.dataframe(sample_df)
            
        # Análise da lógica de detecção automática
        st.write("**Análise da detecção automática de escala:**")
        st.info("🧠 Lógica aplicada: Se valor bruto > 1.000.000 → divide por 100 (centavos→reais), senão mantém")
        
        # Mostrar quantos valores foram convertidos
        sample_raw = df.head(10)
        if len(sample_raw) > 0:
            st.write("**Amostra da conversão aplicada:**")
            debug_conversion = []
            for _, row in sample_raw.iterrows():
                valor_original = row['valor_venda'] 
                # Simular a lógica reversa para mostrar o valor bruto original
                if valor_original < 10000:  # Se resultado é baixo, provavelmente veio de centavos
                    valor_bruto = valor_original * 100
                    conversao = f"{valor_bruto:,.0f} (centavos) → {valor_original:,.0f} (reais)"
                else:
                    valor_bruto = valor_original
                    conversao = f"{valor_bruto:,.0f} (já em reais)"
                
                debug_conversion.append({
                    "Data": row['data_venda'],
                    "Conversão": conversao,
                    "Resultado": format_currency(valor_original)
                })
            
            st.dataframe(pd.DataFrame(debug_conversion))
    else:
        st.write("Nenhum dado encontrado ou coluna valor_venda ausente")

# ------------------------- KPIs -------------------------
currency_formatter = make_currency_formatter(format_mode)
col1, col2, col3, col4, col5 = st.columns(5)

total_vendas = len(df)
with col1:
    st.metric("Total de Vendas", f"{total_vendas:,}".replace(",", "."))

valor_total = float(df["valor_venda"].sum()) if "valor_venda" in df else 0.0
with col2:
    st.metric("Valor Total em Vendas", currency_formatter(valor_total))

if COL_META and "meta_periodo" in df.columns:
    meta_val = float(df["meta_periodo"].sum())
    ating = (valor_total / meta_val) if meta_val > 0 else None
    with col3:
        st.metric("Meta do Período", currency_formatter(meta_val),
                  delta=(f"{ating*100:.1f}% atingido" if ating is not None else None))
else:
    with col3:
        st.metric("Meta do Período", "—")

if "is_interna" in df.columns and df.shape[0] > 0:
    qtd_int = int(df["is_interna"].sum())
    taxa_house = qtd_int / total_vendas if total_vendas > 0 else None
    with col4:
        st.metric("Taxa House", fmt_pct(taxa_house) if taxa_house is not None else "—")
else:
    with col4:
        st.metric("Taxa House", "—")

if "tempo_dias" in df.columns and df["tempo_dias"].notna().any():
    tempo_medio = float(df["tempo_dias"].dropna().mean())
    with col5:
        st.metric("Tempo Médio até a Venda", f"{tempo_medio:.0f} dias")
else:
    with col5:
        st.metric("Tempo Médio até a Venda", "—")

st.markdown("---")

# ------------------------- Bloco: Interna x Externa -------------------------
st.subheader("Análise Vendas House x Imobiliárias")
if "is_interna" in df.columns:
    resumo = pd.DataFrame([
        {"Origem": "Venda Interna (Prati)",
         "Quantidade": int(df["is_interna"].sum()),
         "Valor Total": df.loc[df["is_interna"], "valor_venda"].sum()},
        {"Origem": "Venda Externa (Imobiliárias)",
         "Quantidade": int(df["is_externa"].sum()),
         "Valor Total": df.loc[df["is_externa"], "valor_venda"].sum()},
    ])
    resumo["Valor Total"] = resumo["Valor Total"].apply(currency_formatter)
    st.dataframe(resumo, use_container_width=True)

    st.download_button("⬇️ Baixar resumo (CSV)",
                       resumo.to_csv(index=False).encode("utf-8"),
                       "resumo_vendas_cv.csv", "text/csv")
else:
    st.info("Coluna de origem/tipovenda não encontrada — bloco ocultado.")

st.markdown("---")

# ------------------------- Bloco: Por Empreendimento -------------------------
st.subheader("Vendas House x Imobiliárias por Empreendimento")
if COL_EMP and "empreendimento" in df.columns:
    g = df.groupby("empreendimento", dropna=False)
    emp_df = pd.DataFrame({
        "Quantidade (Interna)": g["is_interna"].sum().astype(int),
        "Quantidade (Externa)": g["is_externa"].sum().astype(int),
        "Valor Total (Interna)": g.apply(lambda x: x.loc[x["is_interna"], "valor_venda"].sum()),
        "Valor Total (Externa)": g.apply(lambda x: x.loc[x["is_externa"], "valor_venda"].sum()),
    }).reset_index()

    # Totais
    total_row = {
        "empreendimento": "Total",
        "Quantidade (Interna)": int(df["is_interna"].sum()),
        "Quantidade (Externa)": int(df["is_externa"].sum()),
        "Valor Total (Interna)": df.loc[df["is_interna"], "valor_venda"].sum(),
        "Valor Total (Externa)": df.loc[df["is_externa"], "valor_venda"].sum(),
    }
    emp_df = pd.concat([emp_df, pd.DataFrame([total_row])], ignore_index=True)

    for c in ["Valor Total (Interna)", "Valor Total (Externa)"]:
        emp_df[c] = emp_df[c].apply(currency_formatter)

    st.dataframe(emp_df, use_container_width=True)
    st.download_button("⬇️ Baixar por Empreendimento (CSV)",
                       emp_df.to_csv(index=False).encode("utf-8"),
                       "vendas_por_empreendimento_cv.csv", "text/csv")
else:
    st.info("Coluna de empreendimento não encontrada — bloco ocultado.")

st.markdown("---")

# ------------------------- Taxa de Conversão (placeholder) -------------------------
st.subheader("Taxa de Conversão de Vendas")
st.info("Requer dados de funil (ex.: leads/oportunidades) — não disponível em cv_vendas.")

st.markdown("---")

# ------------------------- Tabela Detalhada -------------------------
st.subheader("Lista Detalhada de Vendas")
cols_show = ["data_venda", "valor_venda"]
if "empreendimento" in df.columns: cols_show.append("empreendimento")
if "imobiliaria" in df.columns:    cols_show.append("imobiliaria")
if "origem" in df.columns:         cols_show.append("origem")

df_exibir = df[cols_show].copy()
df_exibir["valor_venda"] = df_exibir["valor_venda"].apply(currency_formatter)
df_exibir.columns = [c.replace("_"," ").title() for c in df_exibir.columns]
st.dataframe(df_exibir, use_container_width=True)

st.download_button("⬇️ Baixar lista detalhada (CSV)",
                   df_exibir.to_csv(index=False).encode("utf-8"),
                   "lista_vendas_cv.csv", "text/csv")

if __name__ == "__main__":
    pass
