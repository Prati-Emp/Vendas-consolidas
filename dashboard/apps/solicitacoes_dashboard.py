"""
Dashboard de Solicitações de Compras (dados provenientes de planilhas semanais).
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.utils.md_conn import get_md_connection

# Mapeamento de possíveis nomes das colunas na planilha para nomes canônicos.
COLUMN_ALIASES: Dict[str, List[str]] = {
    "solicitacao": [
        "solicitacao",
        "solicitação",
        "numero_da_solicitacao",
        "numero_solicitacao",
        "n_solicitacao",
        "n_da_solicita_o",
        "id_solicitacao",
        "id",
        "codigo",
    ],
    "status": [
        "status",
        "situacao",
        "situação",
        "situa_o",
        "andamento",
        "status_solicitacao",
        "status_da_solicitacao",
    ],
    "data_solicitacao": [
        "data",
        "data_solicitacao",
        "data_da_solicitacao",
        "dt_solicitacao",
        "data_solicita_o",
        "data_criacao",
        "data_abertura",
        "data_solicitação",
        "data_solicitante",
        "data_pedido",
    ],
    "data_atendimento": [
        "data_atendimento",
        "data_atendida",
        "data_finalizacao",
        "data_finalização",
        "data_conclusao",
        "data_conclusão",
        "data_entrega",
        "data_resolucao",
    ],
    "data_autorizacao": [
        "data_autorizacao",
        "data_autorização",
        "data_autoriza_o",
        "dt_autorizacao",
        "data_aprovacao",
    ],
    "solicitante": [
        "solicitante",
        "requisitante",
        "responsavel",
        "responsável",
        "solicitado_por",
        "solicitante_nome",
        "demandante",
    ],
    "codigo_obra": [
        "codigo_obra",
        "cod_obra",
        "c_d_obra",
        "id_obra",
        "id_empreendimento",
    ],
    "obra": [
        "empreendimento",
        "obra",
        "projeto",
        "pasta",
        "area_demandante",
    ],
    "categoria": [
        "categoria",
        "grupo",
        "tipo_demanda",
        "natureza",
    ],
    "descricao": [
        "descricao",
        "descrição",
        "descricao_da_demanda",
        "descricao_solicitacao",
        "descricao_material",
        "observacao",
        "observa_o_da_solicita_o",
    ],
    "codigo_insumo": [
        "codigo_insumo",
        "cod_insumo",
        "c_d_insumo",
        "id_insumo",
        "codigo_item",
    ],
    "item": [
        "item",
        "insumo",
        "material",
        "produto",
        "servico",
        "descri_o_insumo",
        "descricao_insumo",
        "descricao_item",
    ],
    "insumos": [
        "qtd_insumos",
        "qtde_insumos",
        "quantidade_insumos",
        "quantidade_itens",
        "qtd_itens",
        "total_insumos",
        "quantidade_total",
    ],
    "valor_total": [
        "valor_total",
        "valor",
        "valor_previsto",
        "custo_estimado",
    ],
    "prioridade": [
        "prioridade",
        "criticidade",
        "grau",
    ],
    "_ingested_at": [
        "_ingested_at",
        "_atualizado_em",
        "_ingestao",
        "ingest_timestamp",
    ],
}

STATUS_KEYWORDS = {
    "aberta": ["abert", "penden", "aguard", "andamento", "analise", "aprova"],
    "atendida": ["atend", "conclu", "finaliz", "aprovad", "liberad", "entreg"],
    "cancelada": ["cancel", "recus", "negad"],
}


@dataclass(frozen=True)
class DatasetMeta:
    mapping: Dict[str, str]
    last_update: Optional[datetime]


def _normalize_text(value: str) -> str:
    """Remove acentos e deixa em minúsculas para comparação."""
    if not isinstance(value, str):
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return normalized.strip().lower()


def _detect_columns(columns: List[str]) -> Dict[str, str]:
    """Detecta quais colunas estão presentes usando aliases."""
    mapping: Dict[str, str] = {}
    used_columns: set[str] = set()
    normalized_aliases = {
        key: [_normalize_text(alias) for alias in aliases]
        for key, aliases in COLUMN_ALIASES.items()
    }

    for col in columns:
        normalized_col = _normalize_text(col)
        for canonical, candidates in normalized_aliases.items():
            if canonical in mapping:
                continue
            if normalized_col in candidates or any(
                normalized_col.startswith(candidate) or candidate in normalized_col
                for candidate in candidates
            ):
                if col not in used_columns:
                    mapping[canonical] = col
                    used_columns.add(col)
                break
    return mapping


@st.cache_data(ttl=600)
def load_solicitacoes_raw() -> pd.DataFrame:
    """Carrega os dados crus da tabela de solicitações no MotherDuck."""
    md_conn = get_md_connection()
    sql = "SELECT * FROM planilhas.relacao_de_solicitacoes_de_compras"
    return md_conn.run_query(sql)


def prepare_dataset(df: pd.DataFrame) -> Tuple[pd.DataFrame, DatasetMeta]:
    """Renomeia colunas para o padrão esperado e calcula campos auxiliares."""
    if df.empty:
        return df, DatasetMeta(mapping={}, last_update=None)

    mapping = _detect_columns(df.columns.tolist())
    # Inverter mapeamento para renomear (atenção a duplicatas)
    canonical_names = {}
    for canonical, actual in mapping.items():
        if actual not in canonical_names:
             canonical_names[actual] = canonical
        # Se uma coluna 'actual' mapeia para múltiplos canônicos (não deve acontecer pela lógica de _detect_columns)
        # ou se múltiplos 'actual' mapeiam para o mesmo 'canonical' -> isso gera colunas duplicadas no rename.
        
    # Para evitar colunas duplicadas no destino (ex: c_d_obra -> obra E obra -> obra),
    # precisamos garantir que apenas uma coluna original mapeie para cada nome canônico.
    # A prioridade será dada à coluna que tiver o nome mais próximo ou simplesmente a primeira encontrada.
    
    used_canonicals = set()
    final_rename_map = {}
    
    # Ordenar itens para determinismo? O _detect_columns já varre colunas na ordem.
    # Vamos inverter mapping: {canonical: actual}. Se houver conflito, o _detect_columns já resolveu?
    # Não, _detect_columns retorna {canonical: actual}. 
    # Se tivermos canonical="obra" -> actual="c_d_obra" E canonical="outra_coisa" -> actual="obra"...
    # O problema é se tivermos colunas originais "c_d_obra" e "obra".
    # _detect_columns vai varrer colunas.
    # 1. c_d_obra: matches "obra" alias? Sim (se c_d_obra estiver na lista ou regex).
    # 2. obra: matches "obra" alias? Sim.
    # Se _detect_columns atribui mapping["obra"] = "c_d_obra", depois vê "obra", 
    # ele verifica `if canonical in mapping: continue`. 
    # Então se "c_d_obra" pegou o slot "obra", a coluna "obra" original NÃO entra no mapping para "obra".
    # MAS, a coluna "obra" original continua existindo no dataframe.
    # Ao fazer df.rename(columns={"c_d_obra": "obra"}), teremos duas colunas "obra": a renomeada e a original.
    
    canonical_to_actual = mapping
    
    # Rename apenas das colunas que foram mapeadas
    rename_dict = {actual: canonical for canonical, actual in canonical_to_actual.items()}
    
    prepared = df.rename(columns=rename_dict).copy()
    
    # Remover colunas duplicadas resultantes do rename
    # (ex: se existia 'obra' e 'c_d_obra' -> 'obra', agora temos duas 'obra')
    prepared = prepared.loc[:, ~prepared.columns.duplicated()]

    if "data_solicitacao" in prepared.columns:
        prepared["data_solicitacao"] = pd.to_datetime(
            prepared["data_solicitacao"], errors="coerce", dayfirst=True
        )
    if "data_atendimento" in prepared.columns:
        prepared["data_atendimento"] = pd.to_datetime(
            prepared["data_atendimento"], errors="coerce", dayfirst=True
        )
    if "data_autorizacao" in prepared.columns:
        prepared["data_autorizacao"] = pd.to_datetime(
            prepared["data_autorizacao"], errors="coerce", dayfirst=True
        )

    # Quantidade de insumos: tenta coluna explícita, senão deriva de quantidades
    if "insumos" in prepared.columns:
        prepared["insumos"] = (
            pd.to_numeric(prepared["insumos"], errors="coerce").fillna(0).astype(float)
        )
    else:
        # Tabela de solicitações atual: usar quant_cotada_reservada_dispon_vel se existir,
        # senão somar quant_pendente + quant_atendida como proxy de quantidade de itens.
        if "quant_cotada_reservada_dispon_vel" in df.columns:
            prepared["insumos"] = (
                pd.to_numeric(df["quant_cotada_reservada_dispon_vel"], errors="coerce")
                .fillna(0)
                .astype(float)
            )
        else:
            qty_cols = [c for c in ["quant_pendente", "quant_atendida"] if c in df.columns]
            if qty_cols:
                prepared["insumos"] = (
                    df[qty_cols]
                    .apply(pd.to_numeric, errors="coerce")
                    .fillna(0)
                    .sum(axis=1)
                    .astype(float)
                )
    if "valor_total" in prepared.columns:
        prepared["valor_total"] = pd.to_numeric(
            prepared["valor_total"], errors="coerce"
        )

    # Normalização de Obra/Empreendimento
    # Combinar código + nome para exibição, priorizando "Código - Nome"
    
    # 1. Tentar identificar colunas de código e nome separadamente
    code_col = "codigo_obra" if "codigo_obra" in prepared.columns else None
    name_col = "obra" if "obra" in prepared.columns else None
    
    if code_col and name_col:
        def combine_obra_name(row):
            c = str(row[code_col]).strip() if pd.notna(row[code_col]) else ""
            # Remove .0 de floats
            if c.endswith(".0"):
                c = c[:-2]
            
            n = str(row[name_col]).strip() if pd.notna(row[name_col]) else ""
            
            if c and n:
                # Se o nome já começa com o código (ex: "32 - Obra"), não duplica
                if n.startswith(c):
                    return n
                return f"{c} - {n}"
            elif n:
                return n
            elif c:
                return c
            return "Desconhecido"
            
        prepared["obra"] = prepared.apply(combine_obra_name, axis=1)
        
    elif code_col and not name_col:
        # Só tem código, usa ele como obra
        prepared["obra"] = prepared[code_col].fillna("Desconhecido").astype(str).apply(lambda x: x[:-2] if x.endswith(".0") else x)

    elif name_col:
         # Só tem nome, mantém (aplica normalização antiga se necessário, mas vamos simplificar)
         pass

    # Garantir que 'obra' seja string para evitar erros de groupby
    if "obra" in prepared.columns:
        prepared["obra"] = prepared["obra"].fillna("Desconhecido").astype(str)

    # Combinar código + descrição do insumo para exibição
    desc_col = None
    if "item" in prepared.columns:
        desc_col = "item"
    elif "descricao" in prepared.columns:
        desc_col = "descricao"

    if "codigo_insumo" in prepared.columns:
        def combine_codigo_descricao(row):
            val_code = row.get("codigo_insumo")
            if pd.notna(val_code):
                # Trata floats que parecem ints (ex: 837.0 -> "837")
                if isinstance(val_code, float) and val_code.is_integer():
                    codigo = str(int(val_code))
                else:
                    codigo = str(val_code).strip()
            else:
                codigo = ""

            descricao = ""
            if desc_col and pd.notna(row.get(desc_col)):
                descricao = str(row.get(desc_col)).strip()

            if codigo and descricao:
                # Se a descrição for muito parecida com o código, usa só um
                if codigo in descricao or descricao in codigo:
                    return descricao if len(descricao) > len(codigo) else codigo
                return f"{codigo} - {descricao}"
            elif descricao:
                return descricao
            elif codigo:
                return codigo
            return "Sem informação"

        prepared["item_completo"] = prepared.apply(combine_codigo_descricao, axis=1)
    elif desc_col:
        prepared["item_completo"] = prepared[desc_col].fillna("Sem informação").astype(str)
    else:
        prepared["item_completo"] = "Sem informação"

    if "status" in prepared.columns:
        prepared["status_bucket"] = prepared["status"].apply(classify_status)
    else:
        prepared["status_bucket"] = "desconhecido"

    if "data_solicitacao" in prepared.columns and "data_atendimento" in prepared.columns:
        prepared["lead_time_dias"] = (
            prepared["data_atendimento"] - prepared["data_solicitacao"]
        ).dt.days
    else:
        prepared["lead_time_dias"] = None
        
    # Novos tempos de ciclo
    if "data_solicitacao" in prepared.columns and "data_autorizacao" in prepared.columns:
        prepared["tempo_aprovacao_dias"] = (
            prepared["data_autorizacao"] - prepared["data_solicitacao"]
        ).dt.days
    else:
        prepared["tempo_aprovacao_dias"] = None
        
    if "data_autorizacao" in prepared.columns and "data_atendimento" in prepared.columns:
        prepared["tempo_compra_dias"] = (
            prepared["data_atendimento"] - prepared["data_autorizacao"]
        ).dt.days
    else:
        prepared["tempo_compra_dias"] = None

    if "data_solicitacao" in prepared.columns:
        prepared["dias_em_aberto"] = (
            datetime.now() - prepared["data_solicitacao"]
        ).dt.days

    last_update_col = mapping.get("_ingested_at") or (
        "_ingested_at" if "_ingested_at" in df.columns else None
    )
    last_update = None
    if last_update_col and last_update_col in prepared.columns:
        last_update = pd.to_datetime(prepared[last_update_col], errors="coerce").max()

    return prepared, DatasetMeta(mapping=mapping, last_update=last_update)


def classify_status(value: Optional[str]) -> str:
    """Classifica o status em buckets open/attended/cancelled/outros."""
    normalized = _normalize_text(value) if value is not None else ""
    if not normalized:
        return "desconhecido"
    for bucket, keywords in STATUS_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            return bucket
    return "outros"


def _format_int(value: Optional[float]) -> str:
    if value is None or pd.isna(value):
        return "0"
    return f"{int(value):,}".replace(",", ".")


def _format_float(value: Optional[float]) -> str:
    if value is None or pd.isna(value):
        return "0,0"
    return f"{value:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _default_period(df: pd.DataFrame) -> Tuple[date, date]:
    today = datetime.now().date()
    first_day_current_year = date(today.year, 1, 1)

    if "data_solicitacao" not in df.columns or df["data_solicitacao"].dropna().empty:
        return first_day_current_year, today

    min_date = df["data_solicitacao"].dropna().min().date()
    max_date = df["data_solicitacao"].dropna().max().date()

    # Começar no primeiro dia do ano corrente, respeitando o intervalo de dados
    start = max(min_date, first_day_current_year)
    if start > max_date:
        start = max_date

    return start, max_date


def _safe_unique_sorted(df: pd.DataFrame, column: str) -> List:
    """Retorna valores únicos ordenados de uma coluna, de forma resiliente a erros."""
    if column not in df.columns:
        return []
    try:
        series = df[column]
        # Preferir API pandas quando disponível
        if hasattr(series, "dropna"):
            values = series.dropna().unique()
        else:
            values = pd.unique([v for v in series if v is not None])
        cleaned = [v for v in values if not pd.isna(v)]
        return sorted(cleaned)
    except Exception:
        # Em caso de qualquer erro inesperado, evita quebrar a página
        return []


def apply_filters(
    df: pd.DataFrame,
    *,
    data_inicio: Optional[date],
    data_fim: Optional[date],
    status: List[str],
    solicitantes: List[str],
    obras: List[str],
    categorias: List[str],
    search: str,
) -> pd.DataFrame:
    if df.empty:
        return df

    filtered = df.copy()

    if data_inicio and "data_solicitacao" in filtered.columns:
        filtered = filtered[
            filtered["data_solicitacao"].dt.date >= pd.to_datetime(data_inicio).date()
        ]
    if data_fim and "data_solicitacao" in filtered.columns:
        filtered = filtered[
            filtered["data_solicitacao"].dt.date <= pd.to_datetime(data_fim).date()
        ]
    if status and "status" in filtered.columns:
        filtered = filtered[filtered["status"].isin(status)]
    if status and "status" not in filtered.columns:
        st.warning("Filtro de status ignorado — coluna não encontrada.")
    if solicitantes and "solicitante" in filtered.columns:
        filtered = filtered[filtered["solicitante"].isin(solicitantes)]
    if obras and "obra" in filtered.columns:
        filtered = filtered[filtered["obra"].isin(obras)]
    if categorias and "categoria" in filtered.columns:
        filtered = filtered[filtered["categoria"].isin(categorias)]
    if search and "solicitacao" in filtered.columns:
        search_lower = search.lower().strip()
        filtered = filtered[
            filtered["solicitacao"].astype(str).str.lower().str.contains(search_lower)
        ]

    return filtered


def compute_kpis(df: pd.DataFrame) -> Dict[str, float]:
    if df.empty:
        return {
            "ultimos_90": 0,
            "abertas_ultimos_30": 0,
            "abertas_ultimos_60": 0,
            "abertas": 0,
            "total_solicitacoes": 0,
            "canceladas": 0,
            "atendidas": 0,
            "insumos": 0,
            "lead_time_medio": 0.0,
            "tempo_aprovacao": 0.0,
            "tempo_compra": 0.0,
            "pct_atendidas": 0.0,
            "pct_canceladas": 0.0,
            "pct_abertas": 0.0,
        }

    today = datetime.now()
    ninety_days_ago = today - timedelta(days=90)
    sixty_days_ago = today - timedelta(days=60)
    thirty_days_ago = today - timedelta(days=30)
    solicitacao_col = "solicitacao" if "solicitacao" in df.columns else None
    
    # Para KPIs de volume, precisamos desduplicar por número da solicitação
    if solicitacao_col:
        # Criar um dataframe de solicitações únicas para contagem correta
        # Assumimos que status/datas são consistentes por solicitação ou pegamos o primeiro
        df_unique = df.drop_duplicates(subset=[solicitacao_col])
    else:
        df_unique = df

    if "data_solicitacao" in df_unique.columns and solicitacao_col:
        ultimos_90 = df_unique[df_unique["data_solicitacao"] >= ninety_days_ago][solicitacao_col].nunique()
        # Solicitações criadas nos últimos 30 e 60 dias (independente do status)
        abertas_ultimos_30 = df_unique[df_unique["data_solicitacao"] >= thirty_days_ago][solicitacao_col].nunique()
        abertas_ultimos_60 = df_unique[df_unique["data_solicitacao"] >= sixty_days_ago][solicitacao_col].nunique()
    else:
        ultimos_90 = 0
        abertas_ultimos_30 = 0
        abertas_ultimos_60 = 0

    # Abertas total (todas as que estão com status "aberta" atualmente)
    abertas = (df_unique["status_bucket"] == "aberta").sum() if "status_bucket" in df_unique.columns else 0
    
    # Total de solicitações (todas as solicitações únicas)
    if solicitacao_col:
        total_solicitacoes = df_unique[solicitacao_col].nunique()
    else:
        total_solicitacoes = len(df_unique) if df_unique is not None else 0
    
    # Canceladas
    canceladas = (df_unique["status_bucket"] == "cancelada").sum() if "status_bucket" in df_unique.columns else 0
    
    # Atendidas
    atendidas = (df_unique["status_bucket"] == "atendida").sum() if "status_bucket" in df_unique.columns else 0
    
    # Insumos continua sendo a soma de tudo (linhas ou qtd declarada)
    insumos_total = df["insumos"].sum() if "insumos" in df.columns else 0

    # Percentuais por status em relação ao total
    def _pct(part: float, total: float) -> float:
        if not total:
            return 0.0
        return round((part / total) * 100, 1)

    pct_atendidas = _pct(atendidas, total_solicitacoes)
    pct_canceladas = _pct(canceladas, total_solicitacoes)
    pct_abertas = _pct(abertas, total_solicitacoes)

    lead_time_medio = (
        df_unique.loc[df_unique["status_bucket"] == "atendida", "lead_time_dias"].mean()
        if "lead_time_dias" in df_unique.columns and "status_bucket" in df_unique.columns
        else None
    )
    
    tempo_aprovacao_medio = (
        df_unique["tempo_aprovacao_dias"].mean()
        if "tempo_aprovacao_dias" in df_unique.columns
        else None
    )
    tempo_compra_medio = (
        df_unique.loc[df_unique["status_bucket"] == "atendida", "tempo_compra_dias"].mean()
        if "tempo_compra_dias" in df_unique.columns and "status_bucket" in df_unique.columns
        else None
    )

    return {
        "ultimos_90": int(ultimos_90),
        "abertas_ultimos_30": int(abertas_ultimos_30),
        "abertas_ultimos_60": int(abertas_ultimos_60),
        "abertas": int(abertas),
        "total_solicitacoes": int(total_solicitacoes),
        "canceladas": int(canceladas),
        "atendidas": int(atendidas),
        "insumos": float(insumos_total),
        "lead_time_medio": lead_time_medio or 0.0,
        "tempo_aprovacao": tempo_aprovacao_medio or 0.0,
        "tempo_compra": tempo_compra_medio or 0.0,
        "pct_atendidas": pct_atendidas,
        "pct_canceladas": pct_canceladas,
        "pct_abertas": pct_abertas,
    }


def render_distributions(df: pd.DataFrame) -> None:
    # Para gráficos de contagem, usar dataframe único por solicitação
    solicitacao_col = "solicitacao" if "solicitacao" in df.columns else None
    if solicitacao_col:
        df_unique = df.drop_duplicates(subset=[solicitacao_col])
    else:
        df_unique = df

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "Status e Tendência",
            "Solicitantes e Obras",
            "Top Insumos",
            "Tabela Detalhada",
        ]
    )

    with tab1:
        # Gráfico de status removido (informação já coberta pelos cards)

        # Gráfico de Tendência Temporal
        st.subheader("Tendência de Solicitações ao Longo do Tempo")
        if "data_solicitacao" in df_unique.columns:
            timeline = (
                df_unique.dropna(subset=["data_solicitacao"])
                .assign(mes=lambda d: d["data_solicitacao"].dt.to_period("M").dt.to_timestamp())
                .groupby("mes")
                .agg(
                    total=("solicitacao", "nunique") if "solicitacao" in df_unique.columns else ("data_solicitacao", "count"),
                    abertas=("status_bucket", lambda s: (s == "aberta").sum()) if "status_bucket" in df_unique.columns else None
                )
                .reset_index()
            )
            
            if "abertas" in timeline.columns and timeline["abertas"].notna().any():
                timeline["atendidas"] = timeline["total"] - timeline["abertas"]
                
                # Gráfico de área empilhada
                fig_timeline = go.Figure()
                
                fig_timeline.add_trace(go.Scatter(
                    name="Atendidas",
                    x=timeline["mes"],
                    y=timeline["atendidas"],
                    mode="lines+markers",
                    fill="tozeroy",
                    marker=dict(color="#22c55e", size=8),
                    line=dict(color="#22c55e", width=2),
                    hovertemplate="<b>%{x|%b %Y}</b><br>Atendidas: %{y}<extra></extra>"
                ))
                
                fig_timeline.add_trace(go.Scatter(
                    name="Abertas",
                    x=timeline["mes"],
                    y=timeline["abertas"],
                    mode="lines+markers",
                    fill="tonexty",
                    marker=dict(color="#f97316", size=8),
                    line=dict(color="#f97316", width=2),
                    hovertemplate="<b>%{x|%b %Y}</b><br>Abertas: %{y}<extra></extra>"
                ))
                
                fig_timeline.update_layout(
                    xaxis_title="Mês",
                    yaxis_title="Qtd. Solicitações Únicas",
                    hovermode="x unified",
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    ),
                    height=400
                )
            else:
                # Fallback: gráfico de linha simples
                fig_timeline = px.line(
                    timeline,
                    x="mes",
                    y="total",
                    markers=True,
                )
                fig_timeline.update_traces(
                    line=dict(color="#3b82f6", width=3),
                    marker=dict(color="#3b82f6", size=8)
                )
                fig_timeline.update_layout(
                    xaxis_title="Mês",
                    yaxis_title="Qtd. Solicitações Únicas",
                    hovermode="x unified",
                    height=400
                )
            
            st.plotly_chart(fig_timeline, use_container_width=True)
        else:
            st.info("Não foi possível gerar a linha do tempo (coluna de data ausente).")

    with tab2:
        col1, col2 = st.columns(2)
        if "solicitante" in df_unique.columns and "solicitacao" in df_unique.columns:
            top_solicitantes = (
                df_unique.groupby("solicitante")
                .agg(
                    total_solicitacoes=("solicitacao", "nunique"),
                    abertas=("status_bucket", lambda s: (s == "aberta").sum()),
                )
                .reset_index()
                .assign(
                    atendidas=lambda x: x["total_solicitacoes"] - x["abertas"]
                )
                .sort_values("total_solicitacoes", ascending=False)
                .head(10)
            )
            
            # Gráfico de barras empilhadas para solicitantes
            fig_bar = go.Figure()
            fig_bar.add_trace(go.Bar(
                name="Atendidas",
                x=top_solicitantes["atendidas"],
                y=top_solicitantes["solicitante"],
                orientation="h",
                marker=dict(color="#22c55e"),
                text=top_solicitantes["atendidas"],
                textposition="inside",
                hovertemplate="<b>%{y}</b><br>Atendidas: %{x}<extra></extra>"
            ))
            fig_bar.add_trace(go.Bar(
                name="Abertas",
                x=top_solicitantes["abertas"],
                y=top_solicitantes["solicitante"],
                orientation="h",
                marker=dict(color="#f97316"),
                text=top_solicitantes["abertas"],
                textposition="inside",
                hovertemplate="<b>%{y}</b><br>Abertas: %{x}<extra></extra>"
            ))
            fig_bar.add_trace(go.Scatter(
                x=top_solicitantes["total_solicitacoes"],
                y=top_solicitantes["solicitante"],
                mode="text",
                text=top_solicitantes["total_solicitacoes"].astype(str),
                textposition="middle right",
                textfont=dict(color="white", size=12),
                showlegend=False,
                hoverinfo="skip"
            ))
            fig_bar.update_layout(
                barmode="stack",
                yaxis=dict(autorange="reversed", type="category"),
                xaxis_title="Qtd. Solicitações Únicas",
                yaxis_title="Solicitante",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ),
                hovermode="y unified"
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        elif "solicitante" not in df_unique.columns:
            st.info("Não há coluna de solicitante para gerar ranking.")
        else:
            st.info("Coluna de número da solicitação não encontrada para gerar ranking.")

        # Gráfico de barras empilhadas para obras/empreendimentos
        if "obra" in df_unique.columns or "obra_completa" in df_unique.columns:
            obra_col = "obra_completa" if "obra_completa" in df_unique.columns else "obra"
            
            obras_df = (
                df_unique.groupby(obra_col)
                .agg(
                    total_solicitacoes=("solicitacao", "nunique"),
                    abertas=("status_bucket", lambda s: (s == "aberta").sum()),
                    lead_time=("lead_time_dias", "mean"),
                )
                .reset_index()
                .assign(
                    atendidas=lambda x: x["total_solicitacoes"] - x["abertas"]
                )
                .sort_values("total_solicitacoes", ascending=False)
            )
            
            # Gráfico de barras empilhadas
            st.subheader("Empreendimentos / Áreas por Status de Solicitação")
            
            # Preparar dados para gráfico (top 20 para melhor visualização)
            obras_plot = obras_df.head(20).copy()
            
            # Função para truncar texto se necessário
            def make_label_obra(val):
                s = str(val)
                if len(s) > 60:
                    return s[:57] + "..."
                return s
            
            obras_plot["label_curto"] = obras_plot[obra_col].apply(make_label_obra)
            
            fig_obras = go.Figure()
            fig_obras.add_trace(go.Bar(
                name="Atendidas",
                x=obras_plot["atendidas"],
                y=obras_plot["label_curto"],
                orientation="h",
                marker=dict(color="#22c55e"),
                text=obras_plot["atendidas"],
                textposition="inside",
                hovertemplate="<b>%{y}</b><br>Atendidas: %{x}<extra></extra>"
            ))
            fig_obras.add_trace(go.Bar(
                name="Abertas",
                x=obras_plot["abertas"],
                y=obras_plot["label_curto"],
                orientation="h",
                marker=dict(color="#f97316"),
                text=obras_plot["abertas"],
                textposition="inside",
                hovertemplate="<b>%{y}</b><br>Abertas: %{x}<extra></extra>"
            ))
            fig_obras.add_trace(go.Scatter(
                x=obras_plot["total_solicitacoes"],
                y=obras_plot["label_curto"],
                mode="text",
                text=obras_plot["total_solicitacoes"].astype(str),
                textposition="middle right",
                textfont=dict(color="white", size=12),
                showlegend=False,
                hoverinfo="skip"
            ))
            fig_obras.update_layout(
                barmode="stack",
                yaxis=dict(autorange="reversed", type="category"),
                xaxis_title="Quantidade de Solicitações",
                yaxis_title="Empreendimento / Área",
                height=800,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ),
                hovermode="y unified"
            )
            st.plotly_chart(fig_obras, use_container_width=True)
            
            # Tabela completa abaixo do gráfico
            st.subheader("Detalhamento Completo")
            st.dataframe(
                obras_df.rename(
                    columns={
                        obra_col: "Empreendimento / Área",
                        "total_solicitacoes": "Solicitações Únicas",
                        "abertas": "Abertas",
                        "lead_time": "Lead time médio (dias)",
                    }
                ),
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Empreendimento / Área": st.column_config.TextColumn(
                        "Empreendimento / Área",
                        width="large"
                    ),
                    "Solicitações Únicas": st.column_config.NumberColumn(
                        "Solicitações Únicas",
                        format="%d"
                    ),
                    "Abertas": st.column_config.NumberColumn(
                        "Abertas",
                        format="%d"
                    ),
                    "Lead time médio (dias)": st.column_config.NumberColumn(
                        "Lead time médio (dias)",
                        format="%.1f"
                    ),
                }
            )
        else:
            st.info("Informações de empreendimento não encontradas.")

    with tab3:
        if "item_completo" in df.columns:
            # Agrupar por item completo (código + descrição) e contar status
            # Precisamos contar solicitações únicas, não linhas
            solicitacao_col = "solicitacao" if "solicitacao" in df.columns else None
            
            if solicitacao_col and "status_bucket" in df.columns:
                # Agrupar por item e solicitação para contar únicos
                df_items = df.groupby(["item_completo", solicitacao_col]).agg(
                    status_bucket=("status_bucket", "first")
                ).reset_index()
                
                top_itens = (
                    df_items.groupby("item_completo")
                    .agg(
                        total_solicitacoes=(solicitacao_col, "nunique"),
                        abertas=("status_bucket", lambda s: (s == "aberta").sum())
                    )
                    .reset_index()
                    .assign(
                        atendidas=lambda x: x["total_solicitacoes"] - x["abertas"]
                    )
                    .sort_values("total_solicitacoes", ascending=False)
                    .head(30)
                )
            else:
                # Fallback: contar linhas se não tiver status_bucket ou solicitacao
                top_itens = (
                    df.groupby("item_completo")
                    .agg(
                        total_solicitacoes=("item_completo", "count"),
                        abertas=("status_bucket", lambda s: (s == "aberta").sum()) if "status_bucket" in df.columns else ("item_completo", lambda x: 0)
                    )
                    .reset_index()
                    .assign(
                        atendidas=lambda x: x["total_solicitacoes"] - x["abertas"]
                    )
                    .sort_values("total_solicitacoes", ascending=False)
                    .head(30)
                )
            
            # Gráfico primeiro (em cima) - Barras empilhadas
            if len(top_itens) > 10:
                st.subheader("Top Insumos por Status de Solicitação")
                
                # Preparar dados para gráfico empilhado
                top_itens_plot = top_itens.head(15).copy()
                
                # Função para truncar texto mantendo informação relevante
                def make_label(val):
                    s = str(val)
                    if len(s) > 50:
                        return s[:47] + "..."
                    return s

                top_itens_plot["label_curto"] = top_itens_plot["item_completo"].apply(make_label)
                
                # Criar gráfico de barras empilhadas
                fig_itens = go.Figure()
                
                # Barra de atendidas (verde/azul claro)
                fig_itens.add_trace(go.Bar(
                    name="Atendidas",
                    x=top_itens_plot["atendidas"],
                    y=top_itens_plot["label_curto"],
                    orientation="h",
                    marker=dict(color="#22c55e"),  # Verde
                    text=top_itens_plot["atendidas"],
                    textposition="inside",
                    hovertemplate="<b>%{y}</b><br>Atendidas: %{x}<extra></extra>"
                ))
                
                # Barra de abertas (vermelho/laranja)
                fig_itens.add_trace(go.Bar(
                    name="Abertas",
                    x=top_itens_plot["abertas"],
                    y=top_itens_plot["label_curto"],
                    orientation="h",
                    marker=dict(color="#f97316"),  # Laranja
                    text=top_itens_plot["abertas"],
                    textposition="inside",
                    hovertemplate="<b>%{y}</b><br>Abertas: %{x}<extra></extra>"
                ))
                
                # Adicionar texto com total no final da barra
                fig_itens.add_trace(go.Scatter(
                    x=top_itens_plot["total_solicitacoes"],
                    y=top_itens_plot["label_curto"],
                    mode="text",
                    text=top_itens_plot["total_solicitacoes"].astype(str),
                    textposition="middle right",
                    textfont=dict(color="white", size=12),
                    showlegend=False,
                    hoverinfo="skip"
                ))
                
                fig_itens.update_layout(
                    barmode="stack",
                    yaxis=dict(autorange="reversed", type="category"),
                    xaxis_title="Quantidade de Solicitações",
                    yaxis_title="Insumo",
                    height=600,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    ),
                    hovermode="y unified"
                )
                
                st.plotly_chart(fig_itens, use_container_width=True)
            
            # Tabela depois (embaixo) - Código - Descrição, Total e Abertas
            st.subheader("Top 30 Insumos mais solicitados")
            st.dataframe(
                top_itens[["item_completo", "total_solicitacoes", "abertas"]].rename(columns={
                    "item_completo": "Código - Descrição",
                    "total_solicitacoes": "Total Solicitações",
                    "abertas": "Abertas"
                }),
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Código - Descrição": st.column_config.TextColumn(
                        "Código - Descrição",
                        width="large"
                    ),
                    "Total Solicitações": st.column_config.NumberColumn(
                        "Total Solicitações",
                        format="%d"
                    ),
                    "Abertas": st.column_config.NumberColumn(
                        "Abertas",
                        format="%d"
                    ),
                }
            )
        else:
            st.info("Coluna de itens/insumos não identificada para gerar ranking.")

    with tab4:
        display_columns = [
            col
            for col in ["solicitacao", "status", "data_solicitacao", "data_atendimento", "solicitante", "obra", "categoria", "item", "insumos", "valor_total"]
            if col in df.columns
        ]
        if not display_columns:
            display_columns = df.columns.tolist()
        st.dataframe(
            df[display_columns].sort_values(
                "data_solicitacao", ascending=False
            )
            if "data_solicitacao" in display_columns
            else df[display_columns],
            hide_index=True,
            use_container_width=True,
        )
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Baixar CSV filtrado",
            data=csv,
            file_name="solicitacoes_de_compras.csv",
            mime="text/csv",
        )


def render_solicitacoes_dashboard(*, show_title: bool = True, show_caption: bool = True) -> None:
    """Renderiza toda a página de Solicitação de Compras."""
    with st.spinner("Carregando solicitações..."):
        raw_df = load_solicitacoes_raw()

    prepared_df, meta = prepare_dataset(raw_df)

    if prepared_df.empty:
        st.warning("Nenhuma solicitação disponível no momento.")
        return

    if show_title:
        st.title("📝 Solicitações de Compras")
        if show_caption:
            st.caption("Monitoramento semanal das demandas enviadas ao time de Compras")

    last_update_label = (
        meta.last_update.strftime("%d/%m/%Y %H:%M") if isinstance(meta.last_update, (datetime, pd.Timestamp)) else "sem registro"
    )
    st.info(
        f"Esta página é atualizada **semanalmente**. "
        f"Última carga conhecida: **{last_update_label}**."
    )

    start_default, end_default = _default_period(prepared_df)
    with st.sidebar:
        st.header("Filtros - Solicitação de Compras")
        st.caption("Filtros independentes desta página.")

        if "data_solicitacao" in prepared_df.columns:
            data_inicio = st.date_input(
                "Data inicial",
                value=start_default,
                min_value=prepared_df["data_solicitacao"].min().date()
                if prepared_df["data_solicitacao"].notna().any()
                else start_default,
            )
            data_fim = st.date_input(
                "Data final",
                value=end_default,
                max_value=end_default,
            )
        else:
            data_inicio = data_fim = None
            st.warning("Coluna de data não encontrada — filtro temporal desativado.")

        search = st.text_input(
            "Filtrar por Nº solicitação",
            placeholder="Digite parte do código...",
        )

        status_options = _safe_unique_sorted(prepared_df, "status")
        status_selected = st.multiselect(
            "Status",
            options=status_options,
        )

        solicitante_options = _safe_unique_sorted(prepared_df, "solicitante")
        solicitante_selected = st.multiselect(
            "Solicitante",
            options=solicitante_options,
        )

        obra_options = _safe_unique_sorted(prepared_df, "obra")
        obra_selected = st.multiselect(
            "Empreendimento / Área",
            options=obra_options,
        )

        categoria_options = _safe_unique_sorted(prepared_df, "categoria")
        categoria_selected = st.multiselect(
            "Categoria",
            options=categoria_options,
        )

    filtered_df = apply_filters(
        prepared_df,
        data_inicio=data_inicio,
        data_fim=data_fim,
        status=status_selected,
        solicitantes=solicitante_selected,
        obras=obra_selected,
        categorias=categoria_selected,
        search=search,
    )

    if filtered_df.empty:
        st.warning("Nenhuma solicitação encontrada para os filtros aplicados.")
        return

    st.markdown("### 📌 Indicadores Principais")
    kpis = compute_kpis(filtered_df)

    total = kpis.get("total_solicitacoes", 0)

    def _pct_delta(pct: float) -> str:
        if not total:
            return "0% do total"
        return f"{pct:.1f}% do total"

    # Linha 1: Status principais com % do total + insumos
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total de solicitações", _format_int(total), help="Solicitações únicas no conjunto filtrado.")
    col2.metric(
        "Atendidas",
        _format_int(kpis["atendidas"]),
        delta=_pct_delta(kpis["pct_atendidas"]),
        help="Solicitações concluídas (status 'atendida').",
    )
    col3.metric(
        "Canceladas",
        _format_int(kpis["canceladas"]),
        delta=_pct_delta(kpis["pct_canceladas"]),
        help="Solicitações canceladas.",
    )
    col4.metric(
        "Abertas (total)",
        _format_int(kpis["abertas"]),
        delta=_pct_delta(kpis["pct_abertas"]),
        help="Solicitações que ainda não foram atendidas.",
    )
    col5.metric("Qtd. de insumos", _format_int(kpis["insumos"]), help="Soma da quantidade de insumos nas solicitações.")

    # Linha 2: Volumes recentes e tempos
    col6, col7, col8, col9, col10 = st.columns(5)
    col6.metric("Solicitações (últ. 90 dias)", _format_int(kpis["ultimos_90"]), help="Solicitações criadas nos últimos 90 dias.")
    col7.metric("Solicitações (últ. 30 dias)", _format_int(kpis["abertas_ultimos_30"]), help="Solicitações criadas nos últimos 30 dias.")
    col8.metric(
        "Tempo Aprovação (dias)",
        _format_float(kpis["tempo_aprovacao"]),
        help="Tempo médio entre Solicitação e Autorização.",
    )
    col9.metric(
        "Tempo Compra (dias)",
        _format_float(kpis["tempo_compra"]),
        help="Tempo médio entre Autorização e Atendimento/Entrega.",
    )
    col10.metric(
        "Lead time Total (dias)",
        _format_float(kpis["lead_time_medio"]),
        help="Tempo total médio (Solicitação até Atendimento). Considera apenas solicitações atendidas.",
    )

    st.markdown("---")
    st.subheader("🔎 Principais insights")
    insights = [
        f"{_format_int(kpis['abertas'])} solicitações aguardam atendimento.",
        f"{_format_int(kpis['atendidas'])} solicitações foram concluídas no período filtrado.",
        f"Tempo médio de aprovação: {_format_float(kpis['tempo_aprovacao'])} dias." if kpis["tempo_aprovacao"] > 0 else "Sem dados de aprovação.",
        f"Tempo médio de compra: {_format_float(kpis['tempo_compra'])} dias." if kpis["tempo_compra"] > 0 else "Sem dados de compra.",
    ]
    st.markdown("\n".join(f"- {item}" for item in insights))

    st.markdown("---")
    render_distributions(filtered_df)


