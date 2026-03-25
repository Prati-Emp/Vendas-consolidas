"""
Dashboard de Acompanhamento de Solicitações - Quadros Kanban do Jira DHO.
Exibe 4 quadros: Rotinas Trabalhistas, Movimentações (MC), Requisição de Vaga (RC), Treinamentos (T&D).
"""

from __future__ import annotations

import html
import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from dashboard.utils.md_conn import get_md_connection
from advanced_auth import get_current_user

# Mapeamento: coluna "Motivo_da_Requisição" conforme filtros do Jira
# Fonte: filtros dos quadros Kanban do Jira (RH/DHO)
BOARD_FILTERS: Dict[str, Dict[str, Any]] = {
    "requisicao_vaga_rc": {
        "label": "📝 Requisição de Vaga (RC)",
        "col": "Motivo_da_Requisição",
        "values": ["Aumento de Quadro", "Substituição"],
    },
    "movimentacoes_mc": {
        "label": "🔄 Movimentações (MC)",
        "col": "Motivo_da_Requisição",
        "values": [
            "Alteração Salarial", "Promoção", "Mudança de CNPJ",
            "Mudança de horário", "Movimentação"
        ],
    },
    "treinamentos_td": {
        "label": "🎓 Treinamentos (T&D)",
        "col": "Motivo_da_Requisição",
        "values": ["Treinamentos"],
    },
    "rotinas_trabalhistas": {
        "label": "📋 Rotinas Trabalhistas",
        "col": "Motivo_da_Requisição",
        "values": ["Afastamento", "Demissão", "Férias"],
    },
}

# Mapeamento de nomes de colunas/status para exibição (status_original → nome_exibido)
# Ajuste conforme os nomes desejados para cada quadro
STATUS_DISPLAY_NAMES: Dict[str, Dict[str, str]] = {
    "treinamentos_td": {
        "Backlog": "SOLICITAÇÕES",
        "Aprovação Diretoria": "DIRETORIA",
        "Aprovação Presidência": "PRESIDÊNCIA",
        "Aprovado": "APROVADO",
        "Finalizado": "FINALIZADO",
        "Rejeitado": "REJEITADO",
    },
    "rotinas_trabalhistas": {
        "Backlog": "SOLICITAÇÕES",
        "Aprovação Diretoria": "DIRETORIA",
        "Aprovação Presidência": "PRESIDÊNCIA",
        "Aprovado": "APROVADO",
        "Finalizado": "FINALIZADO",
        "Rejeitado": "REJEITADO",
    },
    "movimentacoes_mc": {
        "Backlog": "SOLICITAÇÕES",
        "Aprovação Diretoria": "DIRETORIA",
        "Aprovação Presidência": "PRESIDÊNCIA",
        "Aprovado": "APROVADO",
        "Exames Gerais": "EXAMES",
        "Documentação": "DOCUMENTAÇÃO E CADASTRO",
        "Finalizado": "FINALIZADO",
        "Rejeitado": "REJEITADO",
    },
    "requisicao_vaga_rc": {
        "Backlog": "SOLICITAÇÕES DE VAGA",
        "Aprovação Diretoria": "DIRETORIA",
        "Aprovação Presidência": "PRESIDÊNCIA",
        "Triagem": "TRIAGEM",
        "Prospecção": "PROSPECÇÃO",
        "Entrevista RH": "ENTREVISTA RH",
        "Provas": "PROVAS",
        "Compliance": "COMPLIANCE",
        "Entrevista com Gestor": "ENTREVISTA COM GESTOR",
        "Aguardando Gestor": "AGUARDANDO GESTOR",
        "Carta Proposta": "CARTA PROPOSTA",
        "Documentos e Cadastro": "DOCUMENTOS",
        "Exames Admissão": "EXAMES",
        "Aguardando Integração": "AGUARDANDO INTEGRAÇÃO",
        "Finalizado": "FINALIZADO",
        "Rejeitado": "REJEITADO",
    },
}


def _normalize_text_for_match(value: Any) -> str:
    """Normaliza texto para comparação (ignora acentos e case)."""
    if value is None:
        return ""
    s = str(value).strip()
    if not s:
        return ""
    if s.lower() in {"none", "nan", "nat", "<na>"}:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"\s+", " ", s)
    return s


def _find_column(df: pd.DataFrame, candidates: List[str]) -> str:
    """Encontra a primeira coluna cuja normalização contém algum dos candidatos."""
    if df.empty:
        return ""
    cols = list(df.columns)
    normalized_cols = {c: _normalize_text_for_match(c) for c in cols}
    for cand in candidates:
        cand_norm = _normalize_text_for_match(cand)
        for col, col_norm in normalized_cols.items():
            if cand_norm and cand_norm in col_norm:
                return col
    return ""


@st.cache_data(ttl=600)
def load_quadro_rh_autorizacoes() -> pd.DataFrame:
    """Carrega a tabela planilhas.quadro_rh_autorizacoes para governança."""
    md_conn = get_md_connection()
    sql = "SELECT * FROM planilhas.quadro_rh_autorizacoes"
    try:
        return md_conn.run_query(sql)
    except Exception as e:
        st.error(f"Erro ao carregar `planilhas.quadro_rh_autorizacoes`: {str(e)}")
        return pd.DataFrame()


def get_allowed_supervisoes_for_current_user() -> List[str]:
    """Retorna lista de supervisões autorizadas para o usuário logado."""
    user_data = get_current_user()
    user_email = (user_data or {}).get("email") if user_data else None
    if not user_email:
        return []

    auth_df = load_quadro_rh_autorizacoes()
    if auth_df.empty:
        return []

    email_col = _find_column(auth_df, ["email", "e-mail", "mail"])
    supervisao_col = _find_column(auth_df, ["supervisao", "supervisão", "supervis"])

    if not email_col or not supervisao_col:
        return []

    user_email_norm = _normalize_text_for_match(user_email)
    auth_subset = auth_df[
        auth_df[email_col].astype(str).apply(_normalize_text_for_match) == user_email_norm
    ]

    allowed = (
        auth_subset[supervisao_col]
        .dropna()
        .astype(str)
        .map(lambda x: x.strip())
        .tolist()
    )
    allowed = [a for a in allowed if a and a.lower() not in {"none", "nan", "nat", "<na>"}]
    # normaliza para remover duplicatas por case/acento
    seen = set()
    deduped: List[str] = []
    for a in allowed:
        k = _normalize_text_for_match(a)
        if k and k not in seen:
            seen.add(k)
            deduped.append(a)
    return deduped


@st.cache_data(ttl=600)
def load_jira_dho_acompanhamento() -> pd.DataFrame:
    """Carrega dados da view Jira_projeto_dho_consolidado."""
    md_conn = get_md_connection()
    sql = "SELECT * FROM administracao.Jira_projeto_dho_consolidado"
    try:
        return md_conn.run_query(sql)
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        return pd.DataFrame()


def _filter_df_by_board(df: pd.DataFrame, board_key: str) -> pd.DataFrame:
    """Filtra o DataFrame para um quadro específico."""
    if df.empty:
        return df
    config = BOARD_FILTERS.get(board_key, {})
    col = config.get("col", "Motivo_da_Requisição")
    values = config.get("values", [])

    if col not in df.columns:
        col = "Motivo_da_Requisição" if "Motivo_da_Requisição" in df.columns else None
    if col is None:
        return df

    df_col = df[col].astype(str).str.strip()
    mask = df_col.isin(values)

    # Ajuste manual solicitado: "Triagem" deve sair de Movimentações (MC)
    # e passar para Requisições de Vagas (RC).
    # Como o dashboard filtra por "Motivo_da_Requisição", fazemos uma exceção por STATUS.
    triagem_norm_target = "triagem"
    status_col = _get_status_column(df)
    if status_col and status_col in df.columns:
        df_status_norm = (
            df[status_col]
            .astype(str)
            .str.strip()
            .apply(lambda x: unicodedata.normalize("NFKD", x))
            .apply(lambda x: "".join(c for c in x if not unicodedata.combining(c)))
            .str.lower()
        )
        triagem_mask = df_status_norm == triagem_norm_target

        if board_key == "movimentacoes_mc":
            mask = mask & ~triagem_mask
        elif board_key == "requisicao_vaga_rc":
            mask = mask | triagem_mask

    if not mask.any() and config.get("fallback_contains"):
        for term in config["fallback_contains"]:
            mask = mask | df_col.str.lower().str.contains(term, na=False, regex=False)
    return df[mask].copy()


def _get_status_display_name(board_key: str, status_val: str) -> str:
    """Retorna o nome de exibição do status, ou o original se não houver mapeamento."""
    mapping = STATUS_DISPLAY_NAMES.get(board_key, {})
    s_raw = str(status_val).strip()

    def _normalize_for_mapping(x: str) -> str:
        # Normaliza para comparar mesmo com variação de acentos/case do Jira.
        x_norm = unicodedata.normalize("NFKD", str(x).strip())
        x_norm = "".join(c for c in x_norm if not unicodedata.combining(c))
        x_norm = x_norm.lower()
        x_norm = re.sub(r"\s+", " ", x_norm)
        return x_norm

    if s_raw in mapping:
        return mapping[s_raw]

    s_norm = _normalize_for_mapping(s_raw)
    for k, v in mapping.items():
        if _normalize_for_mapping(k) == s_norm:
            return v

    return s_raw


def _get_status_column(df: pd.DataFrame) -> str:
    """Identifica a coluna de Status."""
    for c in ["Status", "status"]:
        if c in df.columns:
            return c
    for col in df.columns:
        if "status" in col.lower():
            return col
    return ""


def _normalize_jira_status_token(value: Any) -> str:
    """Normaliza valor de status do Jira para comparação (sem acentos, minúsculas)."""
    if value is None:
        return ""
    s_raw = str(value).strip()
    if not s_raw or s_raw.lower() in {"none", "nan", "nat", "<na>"}:
        return ""
    s_norm = unicodedata.normalize("NFKD", s_raw)
    s_norm = "".join(c for c in s_norm if not unicodedata.combining(c))
    s_norm = s_norm.lower()
    s_norm = re.sub(r"\s+", " ", s_norm)
    return s_norm


# Ordem de colunas da matriz de indicadores (quadro × situação)
SOLICITACOES_MATRIX_BUCKET_ORDER: Tuple[str, ...] = (
    "Aguardando atendimento",
    "Em andamento",
    "Concluídas",
    "Rejeitadas",
)


def classify_jira_status_bucket(status_val: Any) -> str:
    """
    Agrupa o status bruto do Jira em faixas para indicadores:
    - Aguardando atendimento: backlog (entrada / solicitações novas no quadro)
    - Em andamento: demais etapas do fluxo até conclusão ou rejeição
    - Concluídas: finalizado (ou equivalentes comuns)
    - Rejeitadas: rejeitado (ou equivalentes comuns)
    """
    n = _normalize_jira_status_token(status_val)
    if not n:
        return "Em andamento"

    # Concluídas
    if n == "finalizado" or n in ("done", "closed", "concluido", "concluído", "resolvido", "resolved"):
        return "Concluídas"

    # Rejeitadas
    if n == "rejeitado" or n == "rejected":
        return "Rejeitadas"

    # Aguardando atendimento (Backlog — primeira coluna do Kanban nos quadros DHO)
    if n == "backlog":
        return "Aguardando atendimento"

    return "Em andamento"


def compute_solicitacoes_matrix_by_quadro(df: pd.DataFrame) -> pd.DataFrame:
    """
    Conta solicitações por quadro (mesma regra de filtro do Kanban) e por faixa de status.

    Retorna DataFrame com colunas: Quadro, Aguardando atendimento, Em andamento, Concluídas, Rejeitadas, Total.
    Última linha: TOTAL GERAL (soma por coluna; total geral pode contar o mesmo card
    uma vez por quadro — cada linha de quadro já é disjunta porMotivo/Regra Triagem).
    """
    status_col = _get_status_column(df)
    if df.empty or not status_col:
        return pd.DataFrame()

    cols_order = list(SOLICITACOES_MATRIX_BUCKET_ORDER)
    rows: List[Dict[str, Any]] = []

    for board_key, cfg in BOARD_FILTERS.items():
        dfb = _filter_df_by_board(df, board_key)
        counts = {c: 0 for c in cols_order}
        if not dfb.empty and status_col in dfb.columns:
            buckets = dfb[status_col].apply(classify_jira_status_bucket)
            vc = buckets.value_counts()
            for c in cols_order:
                counts[c] = int(vc.get(c, 0) or 0)
        row: Dict[str, Any] = {"Quadro": cfg["label"], **counts}
        row["Total"] = sum(counts[c] for c in cols_order)
        rows.append(row)

    mat = pd.DataFrame(rows)
    if mat.empty:
        return mat

    totals = {c: int(mat[c].sum()) for c in cols_order}
    total_row: Dict[str, Any] = {
        "Quadro": "TOTAL GERAL",
        **totals,
        "Total": int(sum(totals[c] for c in cols_order)),
    }
    return pd.concat([mat, pd.DataFrame([total_row])], ignore_index=True)


def _find_dataframe_column_normalized(df: pd.DataFrame, desired: str) -> str:
    """
    Encontra coluna no DataFrame comparando rótulos normalizados
    (minúsculas, sem acentos, espaços como underscore).
    """
    if df is None or df.empty or not desired:
        return ""
    desired_norm = unicodedata.normalize("NFKD", desired.strip()).lower()
    desired_norm = "".join(c for c in desired_norm if not unicodedata.combining(c))
    desired_norm = re.sub(r"\s+", "_", desired_norm.strip())

    norm_to_col: Dict[str, str] = {}
    for c in df.columns:
        c_str = str(c).strip()
        c_norm = unicodedata.normalize("NFKD", c_str).lower()
        c_norm = "".join(ch for ch in c_norm if not unicodedata.combining(ch))
        c_norm = re.sub(r"\s+", "_", c_norm)
        norm_to_col[c_norm] = c_str
    return norm_to_col.get(desired_norm, "")


def _series_day_diff_days(start: pd.Series, end: pd.Series) -> pd.Series:
    """Diferença em dias corridos (normalizado ao calendário); inválido ou negativo vira NA."""
    s = pd.to_datetime(start, errors="coerce", dayfirst=True)
    e = pd.to_datetime(end, errors="coerce", dayfirst=True)
    s_norm = s.dt.normalize()
    e_norm = e.dt.normalize()
    delta = (e_norm - s_norm).dt.days
    out = delta.astype("Int64")
    out = out.where((out.notna()) & (out >= 0))
    return out


# Colunas de saída (tabela de tempos — requisição de vagas)
COL_TEMPO_FECHAMENTO_VAGA = "Tempo fechamento vaga (dias)"
COL_TEMPO_APROVACAO_VAGA = "Tempo aprovação vaga (dias)"
COL_TEMPO_TOTAL_CONTRATACAO = "Tempo total contratação (dias)"


def compute_requisicao_vaga_tempos_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Quadro **Requisição de vaga (RC)**, apenas registros com status em **Concluídas** (ex.: Finalizado).

    Métricas (dias corridos), sempre a partir do **início**:
    - **Início**: `Start_date` por linha; onde vazio, usa-se `Data_de_inicio`.
    - **Tempo fechamento vaga**: até **Data de aprovação** (aceite do candidato).
    - **Tempo aprovação vaga**: até **Data de fechamento** (aprovação presidência / fechamento da req.).
    - **Tempo total contratação**: até **Data finalização**.

    Colunas de data na view consolidada: `Data_de_aprovação`, `Data_de_fechamento`, `Data_de_finalizacao`.
    """
    if df.empty:
        return pd.DataFrame()

    base = _filter_df_by_board(df, "requisicao_vaga_rc")
    status_col = _get_status_column(base)
    if base.empty or not status_col:
        return pd.DataFrame()

    done_mask = base[status_col].apply(
        lambda s: classify_jira_status_bucket(s) == "Concluídas"
    )
    done = base.loc[done_mask].copy()
    if done.empty:
        return pd.DataFrame()

    col_start = _find_dataframe_column_normalized(done, "Start_date")
    col_data_inicio = _find_dataframe_column_normalized(done, "Data_de_inicio")
    if not col_start and not col_data_inicio:
        return pd.DataFrame()

    inicio = pd.Series(pd.NaT, index=done.index, dtype="datetime64[ns]")
    if col_start and col_start in done.columns:
        inicio = pd.to_datetime(done[col_start], errors="coerce", dayfirst=True)
    if col_data_inicio and col_data_inicio in done.columns:
        alt = pd.to_datetime(done[col_data_inicio], errors="coerce", dayfirst=True)
        inicio = inicio.fillna(alt)

    if inicio.isna().all():
        return pd.DataFrame()

    col_aprov = _find_dataframe_column_normalized(done, "Data_de_aprovacao")
    col_fech = _find_dataframe_column_normalized(done, "Data_de_fechamento")
    col_fin = _find_dataframe_column_normalized(done, "Data_de_finalizacao") or _find_dataframe_column_normalized(
        done, "Data_de_finalização"
    )

    chave_col = _find_dataframe_column_normalized(done, "Chave") or (
        "Chave" if "Chave" in done.columns else ""
    )
    if not chave_col:
        return pd.DataFrame()

    resumo_col = _find_dataframe_column_normalized(done, "Resumo")

    out = pd.DataFrame()
    out["Chave"] = done[chave_col].astype(str).str.strip()
    if resumo_col and resumo_col in done.columns:
        out["Resumo"] = done[resumo_col].apply(lambda x: str(x).strip() if pd.notna(x) else "")

    out["Início"] = inicio.dt.strftime("%Y-%m-%d")
    out.loc[inicio.isna(), "Início"] = ""

    if col_aprov and col_aprov in done.columns:
        d_ap = pd.to_datetime(done[col_aprov], errors="coerce", dayfirst=True)
        out["Data de aprovação"] = d_ap.dt.strftime("%Y-%m-%d")
        out.loc[d_ap.isna(), "Data de aprovação"] = ""
        out[COL_TEMPO_FECHAMENTO_VAGA] = _series_day_diff_days(inicio, d_ap)
    else:
        out["Data de aprovação"] = ""
        out[COL_TEMPO_FECHAMENTO_VAGA] = pd.Series(pd.NA, index=out.index, dtype="Int64")

    if col_fech and col_fech in done.columns:
        d_fe = pd.to_datetime(done[col_fech], errors="coerce", dayfirst=True)
        out["Data de fechamento"] = d_fe.dt.strftime("%Y-%m-%d")
        out.loc[d_fe.isna(), "Data de fechamento"] = ""
        out[COL_TEMPO_APROVACAO_VAGA] = _series_day_diff_days(inicio, d_fe)
    else:
        out["Data de fechamento"] = ""
        out[COL_TEMPO_APROVACAO_VAGA] = pd.Series(pd.NA, index=out.index, dtype="Int64")

    if col_fin and col_fin in done.columns:
        d_fi = pd.to_datetime(done[col_fin], errors="coerce", dayfirst=True)
        out["Data finalização"] = d_fi.dt.strftime("%Y-%m-%d")
        out.loc[d_fi.isna(), "Data finalização"] = ""
        out[COL_TEMPO_TOTAL_CONTRATACAO] = _series_day_diff_days(inicio, d_fi)
    else:
        out["Data finalização"] = ""
        out[COL_TEMPO_TOTAL_CONTRATACAO] = pd.Series(pd.NA, index=out.index, dtype="Int64")

    # Ordenar: maior tempo total primeiro (quando houver)
    if out[COL_TEMPO_TOTAL_CONTRATACAO].notna().any():
        out = out.sort_values(
            COL_TEMPO_TOTAL_CONTRATACAO, ascending=False, na_position="last"
        )
    else:
        out = out.sort_values("Chave")

    return out.reset_index(drop=True)


def _build_kanban_column_html(
    df: pd.DataFrame, status_col: str, status_val: str, chave_col: str, resumo_col: str, tipo_col: str
) -> str:
    """Monta o HTML de uma coluna do Kanban."""
    df_status = df[df[status_col] == status_val]
    cards_html = ""

    def _find_col_by_normalized(cols: List[str], desired: str) -> str:
        # Resolve nomes com/sem acentos e com variações de case
        desired_norm = unicodedata.normalize("NFKD", desired.strip()).lower()
        desired_norm = "".join(c for c in desired_norm if not unicodedata.combining(c))
        norm_to_col = {}
        for c in cols:
            c_norm = unicodedata.normalize("NFKD", str(c).strip()).lower()
            c_norm = "".join(ch for ch in c_norm if not unicodedata.combining(ch))
            norm_to_col[c_norm] = str(c)
        return norm_to_col.get(desired_norm, "")

    def _clean_text(value: Any) -> str:
        """Normaliza valores para exibição sem mostrar None/nan."""
        if value is None:
            return ""
        text = str(value).strip()
        if not text:
            return ""
        if text.lower() in {"none", "nan", "nat", "<na>"}:
            return ""
        return text

    def _to_display_case(value: str) -> str:
        """
        Normaliza textos muito gritados (CAIXA ALTA / caixa baixa)
        para um formato mais legível, preservando siglas comuns.
        """
        text = _clean_text(value)
        if not text:
            return ""

        has_lower = any(ch.islower() for ch in text)
        has_upper = any(ch.isupper() for ch in text)

        # Se já vier em formato misto, preserva como está.
        if has_lower and has_upper:
            return text

        acronyms = {
            "rh": "RH",
            "dho": "DHO",
            "rc": "RC",
            "mc": "MC",
            "ti": "TI",
            "ia": "IA",
            "t&d": "T&D",
            "cnpj": "CNPJ",
            "bim": "BIM",
        }
        small_words = {"de", "da", "do", "das", "dos", "e", "em", "com", "para"}
        roman = {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"}

        def repl(match: re.Match[str]) -> str:
            token = match.group(0)
            lower = token.lower()
            if lower in acronyms:
                return acronyms[lower]
            if lower in roman:
                return lower.upper()
            return token.capitalize()

        normalized = re.sub(r"[A-Za-zÀ-ÿ0-9&/().-]+", repl, text.lower())

        for word in small_words:
            normalized = re.sub(rf"\b{word.capitalize()}\b", word, normalized)

        # Primeira palavra sempre começa com maiúscula
        if normalized:
            normalized = normalized[0].upper() + normalized[1:]

        return normalized

    def _get_motivo_color(motivo: str) -> str:
        motivo_norm = unicodedata.normalize("NFKD", motivo.strip()).lower()
        motivo_norm = "".join(c for c in motivo_norm if not unicodedata.combining(c))

        if any(k in motivo_norm for k in ["demissao", "desligamento"]):
            return "#EF4444"
        if any(k in motivo_norm for k in ["promocao", "treinamento", "ferias"]):
            return "#10B981"
        if any(k in motivo_norm for k in ["movimentacao", "mudanca", "transferencia"]):
            return "#3B82F6"
        if any(k in motivo_norm for k in ["afastamento", "substituicao", "aumento de quadro"]):
            return "#F59E0B"
        return "#6366F1"

    def _get_life_badge(life_days: int) -> tuple[str, str]:
        if life_days <= 7:
            return "#DCFCE7", "#166534"
        if life_days <= 14:
            return "#FEF3C7", "#92400E"
        return "#FEE2E2", "#991B1B"

    supervisao_col = (
        "Supervisão"
        if "Supervisão" in df.columns
        else _find_col_by_normalized(list(df.columns), "Supervisao")
    )
    area_col = "Área" if "Área" in df.columns else _find_col_by_normalized(list(df.columns), "Area")
    cargo_col = "Cargo" if "Cargo" in df.columns else _find_col_by_normalized(list(df.columns), "Cargo")
    motivo_col = "Motivo_da_Requisição" if "Motivo_da_Requisição" in df.columns else _find_col_by_normalized(list(df.columns), "Motivo_da_Requisicao")
    start_date_col = "Start_date" if "Start_date" in df.columns else _find_col_by_normalized(list(df.columns), "Start_date")
    colaborador_col = (
        "Nome_do_colaborador"
        if "Nome_do_colaborador" in df.columns
        else _find_col_by_normalized(list(df.columns), "Nome_do_colaborador")
    )

    responsavel_col = (
        "Responsável"
        if "Responsável" in df.columns
        else (
            "Responsavel"
            if "Responsavel" in df.columns
            else _find_col_by_normalized(list(df.columns), "Responsável")
            or _find_col_by_normalized(list(df.columns), "Responsavel")
        )
    )

    # Para calcular tempo de vida:
    # - se houver "Data_de_finalização" (ou variações), usamos ela como data final
    # - caso contrário, usamos a data de hoje
    finalizacao_col = (
        _find_col_by_normalized(list(df.columns), "Data_de_finalização")
        or _find_col_by_normalized(list(df.columns), "Data_de_finalizacao")
        or _find_col_by_normalized(list(df.columns), "Data_de_fechamento")
    )

    for _, row in df_status.iterrows():
        chave = html.escape(_clean_text(row.get(chave_col, "")) if chave_col else "")
        resumo_raw = _to_display_case(row.get(resumo_col, "")) if resumo_col else ""
        resumo = html.escape(resumo_raw[:120] + ("..." if len(resumo_raw) > 120 else ""))
        cargo_raw = _to_display_case(row.get(cargo_col, "")) if cargo_col else ""
        cargo = html.escape(cargo_raw) if cargo_raw else ""
        supervisao_raw = _to_display_case(row.get(supervisao_col, "")) if supervisao_col else ""
        area_raw = _to_display_case(row.get(area_col, "")) if area_col else ""
        if supervisao_raw and supervisao_raw.strip():
            local_raw = f"Supervisão: {supervisao_raw.strip()}"
        else:
            local_raw = area_raw.strip()
        area = html.escape(local_raw)
        motivo_raw = _to_display_case(row.get(motivo_col, "")) if motivo_col else ""
        motivo_text = motivo_raw[:120] + ("..." if len(motivo_raw) > 120 else "")
        motivo = html.escape(motivo_text) if motivo_text else ""
        colaborador_raw = _to_display_case(row.get(colaborador_col, "")) if colaborador_col else ""
        colaborador = html.escape(colaborador_raw) if colaborador_raw else ""

        responsavel_raw = _to_display_case(row.get(responsavel_col, "")) if responsavel_col else ""
        responsavel = html.escape(responsavel_raw.strip())
        start_date_raw = row.get(start_date_col, None) if start_date_col else None
        start_dt = pd.to_datetime(start_date_raw, errors="coerce")
        if pd.notna(start_dt):
            end_dt_raw = row.get(finalizacao_col, None) if finalizacao_col else None
            end_dt = pd.to_datetime(end_dt_raw, errors="coerce")

            if pd.notna(end_dt):
                end_dt = end_dt.normalize()
            else:
                end_dt = pd.Timestamp.today().normalize()

            life_days = int((end_dt - start_dt.normalize()).days)
            if life_days < 0:
                life_days = 0
            life_text = f"{life_days} dias desde criação"
        else:
            life_text = ""
            life_days = 0

        resp_line = f"Resp: {responsavel}" if responsavel else ""
        motivo_color = _get_motivo_color(motivo_text)
        tempo_bg, tempo_fg = _get_life_badge(life_days)

        resumo_html = f'<div class="kanban-card-resumo">{resumo}</div>' if resumo else ""
        motivo_html = (
            f'<div class="kanban-card-badge kanban-card-badge-motivo" style="background:{motivo_color};">{motivo}</div>'
            if motivo else ""
        )
        tempo_html = (
            f'<div class="kanban-card-badge kanban-card-badge-tempo" style="background:{tempo_bg}; color:{tempo_fg};">⏱ {life_text}</div>'
            if life_text else ""
        )
        colaborador_html = f'<div class="kanban-card-colaborador">👤 {colaborador}</div>' if colaborador else ""
        cargo_html = f'<div class="kanban-card-cargo">📌 {cargo}</div>' if cargo else ""
        area_html = f'<div class="kanban-card-area">🏢 {area}</div>' if area else ""
        resp_html = f'<div class="kanban-card-resp">{resp_line}</div>' if resp_line else ""

        cards_html += f"""
        <div class="kanban-card" style="border-left: 4px solid {motivo_color};">
            <div class="kanban-card-chave">{chave}</div>
            {resumo_html}
            <div class="kanban-card-meta">
                {motivo_html}
                {tempo_html}
            </div>
            {colaborador_html}
            {cargo_html}
            {area_html}
            <div class="kanban-card-footer">
                {resp_html}
            </div>
        </div>
        """
    return cards_html if cards_html else '<div style="color: #888; font-style: italic; padding: 8px;">Nenhum item</div>'


def _render_kanban_board(df: pd.DataFrame, title: str, board_key: str = "") -> None:
    """Renderiza um quadro Kanban completo com colunas por status e scroll horizontal."""
    if df.empty:
        st.info(f"Nenhum item encontrado para **{title}**.")
        return

    status_col = _get_status_column(df)
    if not status_col:
        st.warning("Coluna de Status não encontrada nos dados.")
        st.dataframe(df.head(20), use_container_width=True, hide_index=True)
        return

    def _normalize_for_compare(x: str) -> str:
        x_norm = unicodedata.normalize("NFKD", str(x).strip())
        x_norm = "".join(c for c in x_norm if not unicodedata.combining(c))
        x_norm = x_norm.lower()
        x_norm = re.sub(r"\s+", " ", x_norm)
        return x_norm

    # Lista fixa de colunas por quadro (sempre exibidas, mesmo sem itens).
    # Status nos dados que não estiverem no catálogo entram ao final.
    desired_status_order: Optional[List[str]] = None
    if board_key == "rotinas_trabalhistas":
        desired_status_order = [
            "Backlog",
            "Aprovação Diretoria",
            "Aprovação Presidência",
            "Aprovado",
            "Finalizado",
            "Rejeitado",
        ]
    elif board_key == "movimentacoes_mc":
        desired_status_order = [
            "Backlog",
            "Aprovação Diretoria",
            "Aprovação Presidência",
            "Aprovado",
            "Exames Gerais",
            "Documentação",
            "Finalizado",
            "Rejeitado",
        ]
    elif board_key == "requisicao_vaga_rc":
        desired_status_order = [
            "Backlog",
            "Aprovação Diretoria",
            "Aprovação Presidência",
            "Triagem",
            "Prospecção",
            "Entrevista RH",
            "Provas",
            "Compliance",
            "Entrevista com Gestor",
            "Aguardando Gestor",
            "Carta Proposta",
            "Documentos e Cadastro",
            "Exames Admissão",
            "Aguardando Integração",
            "Finalizado",
            "Rejeitado",
        ]
    elif board_key == "treinamentos_td":
        desired_status_order = [
            "Backlog",
            "Aprovação Diretoria",
            "Aprovação Presidência",
            "Aprovado",
            "Finalizado",
            "Rejeitado",
        ]

    if desired_status_order is not None:
        statuses = list(desired_status_order)
        catalog_norms = {_normalize_for_compare(s) for s in statuses}
        extras: List[str] = []
        for s in df[status_col].dropna().unique().tolist():
            s_str = str(s).strip()
            if not s_str:
                continue
            n = _normalize_for_compare(s_str)
            if n not in catalog_norms:
                catalog_norms.add(n)
                extras.append(s_str)
        extras.sort(key=lambda x: (_normalize_for_compare(x), str(x).lower()))
        statuses = statuses + extras
    else:
        statuses = [s for s in df[status_col].dropna().unique().tolist() if str(s).strip()]

        def _sort_status_default(s: str) -> tuple[int, str]:
            s_str = str(s).strip()
            return (0, s_str) if _normalize_for_compare(s_str) == "backlog" else (1, _normalize_for_compare(s_str))

        statuses = sorted(statuses, key=_sort_status_default)
        if not statuses:
            st.info("Nenhum status encontrado.")
            return

    chave_col = "Chave" if "Chave" in df.columns else (df.columns[0] if len(df.columns) > 0 else "")
    resumo_col = "Resumo" if "Resumo" in df.columns else ""
    tipo_col = "Tipo_de_item" if "Tipo_de_item" in df.columns else ""

    # Altura automática baseada na coluna com maior volume de cards.
    # Objetivo: reduzir rolagem vertical e ampliar visão do quadro.
    max_cards_in_column = 0
    for status_val in statuses:
        max_cards_in_column = max(max_cards_in_column, len(df[df[status_col] == status_val]))

    base_height = 200
    estimated_card_height = 150
    board_height = base_height + (max_cards_in_column * estimated_card_height)
    board_height = max(520, min(1400, board_height))

    # Montar cabeçalhos e colunas de cards separadamente para permitir sticky no topo
    headers_html = ""
    cards_columns_html = ""
    for status_val in statuses:
        cards = _build_kanban_column_html(df, status_col, status_val, chave_col, resumo_col, tipo_col)
        outer_label = _get_status_display_name(board_key, status_val)
        n_items = int((df[status_col] == status_val).sum())
        headers_html += f"""
        <div class="kanban-column kanban-column-header-cell">
            <div class="kanban-column-title">{html.escape(outer_label)} <span class="kanban-column-count">({n_items})</span></div>
            <hr style="border: none; border-top: 1px solid #dee2e6; margin: 0;">
        </div>
        """
        cards_columns_html += f"""
        <div class="kanban-column kanban-column-cards">
            {cards}
        </div>
        """

    scroll_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">
    <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: inherit; background: transparent; color: #333; }}
    .kanban-sticky-top {{
        position: sticky;
        top: 0;
        z-index: 20;
        background: #0B1220;
        padding-bottom: 4px;
    }}
    .kanban-top-scroll {{
        overflow-x: auto;
        overflow-y: hidden;
        height: 14px;
        margin-bottom: 6px;
    }}
    .kanban-top-scroll-inner {{
        height: 1px;
    }}
    .kanban-scroll-container {{
        overflow-x: scroll;
        overflow-y: hidden;
        padding-bottom: 16px;
    }}
    /* Usa scrollbar nativa do navegador (mesma lógica da vertical) - adapta automaticamente ao tema */
    .kanban-board {{
        display: flex;
        flex-direction: row;
        width: max-content;
        min-width: 100%;
        padding: 8px 0;
    }}
    .kanban-headers-scroll {{
        overflow-x: auto;
        overflow-y: hidden;
        margin-bottom: 2px;
        scrollbar-width: none; /* Firefox */
        -ms-overflow-style: none; /* IE/Edge legado */
    }}
    .kanban-headers-scroll::-webkit-scrollbar {{
        display: none; /* Chrome/Safari/Edge */
    }}
    .kanban-board-headers {{
        display: flex;
        flex-direction: row;
        align-items: flex-start;
        width: max-content;
        min-width: 100%;
    }}
    .kanban-board-cards {{
        display: flex;
        flex-direction: row;
        align-items: flex-start;
        width: max-content;
        min-width: 100%;
        padding: 0;
    }}
    /* Largura fixa e igual em cabeçalho e cards: evita larguras diferentes por conteúdo e perde sincronia no scroll */
    .kanban-column {{
        flex: 0 0 260px;
        width: 260px;
        min-width: 260px;
        max-width: 260px;
        box-sizing: border-box;
        overflow-x: hidden;
        background: #f8f9fa;
        border-radius: 8px;
        padding: 12px;
        margin-right: 12px;
    }}
    .kanban-column-header-cell {{
        background: #f8f9fa;
        border-radius: 4px;
        /* mesmo padding da coluna de cards — antes 8px/10px deslocava o grid */
    }}
    .kanban-column-cards {{ background: #f8f9fa; }}
    .kanban-column-title {{
        font-weight: 600;
        margin-bottom: 6px;
        font-size: 0.82rem;
        line-height: 1.15;
        text-align: center;
        letter-spacing: 0.2px;
        word-break: break-word;
        overflow-wrap: anywhere;
    }}
    .kanban-column-count {{
        font-weight: 700;
        font-size: 0.78em;
        color: #374151;
        white-space: nowrap;
    }}
    .kanban-card {{
        background: #fff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        font-size: 0.88rem;
        width: 100%;
        max-width: 100%;
        box-sizing: border-box;
        word-break: break-word;
        overflow-wrap: anywhere;
    }}
    .kanban-card-chave {{
        font-weight: 600;
        color: #1a73e8;
        margin-bottom: 6px;
        font-size: 0.85rem;
    }}
    .kanban-card-resumo {{
        color: #1F2937;
        margin-bottom: 8px;
        word-wrap: break-word;
        overflow-wrap: anywhere;
        font-weight: 700;
        line-height: 1.2;
        font-size: 0.95rem;
    }}
    .kanban-card-meta {{
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        margin-bottom: 10px;
    }}
    .kanban-card-badge {{
        display: inline-flex;
        align-items: center;
        border-radius: 999px;
        padding: 4px 8px;
        font-size: 0.72rem;
        font-weight: 600;
        line-height: 1;
    }}
    .kanban-card-badge-motivo {{
        color: #fff;
    }}
    .kanban-card-area {{ font-size: 0.8rem; color: #4B5563; margin-bottom: 4px; word-wrap: break-word; }}
    .kanban-card-motivo {{ font-size: 0.8rem; color: #374151; word-wrap: break-word; }}
    .kanban-card-colaborador {{ font-size: 0.8rem; color: #374151; margin-bottom: 4px; word-wrap: break-word; }}
    .kanban-card-cargo {{ font-size: 0.8rem; color: #374151; margin-bottom: 4px; word-wrap: break-word; }}
    .kanban-card-footer {{
        display: flex;
        flex-direction: column;
        gap: 6px;
        margin-top: 10px;
    }}
    .kanban-card-resp {{
        font-size: 0.75rem;
        color: #374151;
    }}
    </style>
    </head>
    <body>
    <div class="kanban-sticky-top">
        <div id="kanbanTopScroll" class="kanban-top-scroll">
            <div id="kanbanTopScrollInner" class="kanban-top-scroll-inner"></div>
        </div>
        <div id="kanbanHeaderScroll" class="kanban-headers-scroll">
            <div id="kanbanHeaderBoard" class="kanban-board-headers">
                {headers_html}
            </div>
        </div>
    </div>
    <div id="kanbanBottomScroll" class="kanban-scroll-container">
        <div id="kanbanCardsBoard" class="kanban-board-cards">
            {cards_columns_html}
        </div>
    </div>
    <script>
    (function () {{
        const top = document.getElementById("kanbanTopScroll");
        const topInner = document.getElementById("kanbanTopScrollInner");
        const header = document.getElementById("kanbanHeaderScroll");
        const headerBoard = document.getElementById("kanbanHeaderBoard");
        const bottom = document.getElementById("kanbanBottomScroll");
        const cardsBoard = document.getElementById("kanbanCardsBoard");

        if (!top || !topInner || !header || !headerBoard || !bottom || !cardsBoard) return;

        const syncWidth = () => {{
            const width = Math.max(headerBoard.scrollWidth, cardsBoard.scrollWidth);
            topInner.style.width = `${{width}}px`;
        }};

        let syncingFromTop = false;
        let syncingFromHeader = false;
        let syncingFromBottom = false;

        top.addEventListener("scroll", () => {{
            if (syncingFromBottom || syncingFromHeader) return;
            syncingFromTop = true;
            bottom.scrollLeft = top.scrollLeft;
            header.scrollLeft = top.scrollLeft;
            requestAnimationFrame(() => {{ syncingFromTop = false; }});
        }});

        header.addEventListener("scroll", () => {{
            if (syncingFromTop || syncingFromBottom) return;
            syncingFromHeader = true;
            bottom.scrollLeft = header.scrollLeft;
            top.scrollLeft = header.scrollLeft;
            requestAnimationFrame(() => {{ syncingFromHeader = false; }});
        }});

        bottom.addEventListener("scroll", () => {{
            if (syncingFromTop || syncingFromHeader) return;
            syncingFromBottom = true;
            top.scrollLeft = bottom.scrollLeft;
            header.scrollLeft = bottom.scrollLeft;
            requestAnimationFrame(() => {{ syncingFromBottom = false; }});
        }});

        syncWidth();
        window.addEventListener("resize", syncWidth);
        window.addEventListener("load", syncWidth);
    }})();
    </script>
    </body>
    </html>
    """
    components.html(scroll_html, height=int(board_height), scrolling=True)


def render_acompanhamento_solicitacoes_dashboard() -> None:
    """Renderiza o dashboard completo de Acompanhamento de Solicitações."""
    st.subheader("📋 Acompanhamento de Solicitações")

    with st.spinner("Carregando dados do Jira DHO..."):
        df_raw = load_jira_dho_acompanhamento()

    if df_raw.empty:
        st.warning("⚠️ Nenhum dado encontrado na view Jira_projeto_dho_consolidado.")
        return

    # Governança: filtrar por supervisão autorizada do usuário logado.
    # Observação: para o(s) usuário(s) abaixo, ignoramos a lista de permissões
    # e liberamos a leitura total (mesmo sem estar na planilha).
    bypass_emails = {
        "odair2d@hotmail.com",
        "odair.santos@grupoprati.com",
        "joao.fantinel@grupoprati.com",
        "airton.silva@grupoprati.com",
        "gustavo.sordi@grupoprati.com",
    }
    user_data = get_current_user()
    user_email = (user_data or {}).get("email", "") if user_data else ""
    user_email_norm = _normalize_text_for_match(user_email)

    governanca_enabled = user_email_norm not in {_normalize_text_for_match(v) for v in bypass_emails if v}

    allowed_supervisoes_norm: Optional[set[str]] = None
    if governanca_enabled:
        allowed_supervisoes = get_allowed_supervisoes_for_current_user()
        allowed_supervisoes_norm = {
            _normalize_text_for_match(v) for v in allowed_supervisoes if v
        }
        if not allowed_supervisoes_norm:
            st.error(
                "Acesso negado: não foi possível encontrar supervisões autorizadas para seu usuário."
            )
            return

    supervisao_col_probe = _find_column(df_raw, ["supervisao", "supervisão", "supervis"])
    area_col_probe = _find_column(df_raw, ["area", "área"])
    if not (supervisao_col_probe or area_col_probe):
        st.error("Acesso negado: colunas de `Supervisão`/`Área` não foram encontradas para aplicar governança.")
        return

    st.markdown(
        """
        <div style="
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(128,128,128,0.25);
            border-radius: 8px;
            padding: 10px 12px;
            margin: 8px 0 14px 0;
            font-size: 0.85rem;
        ">
            <strong>Legenda:</strong>
            <span style="margin-left: 10px;">👤 Colaborador</span>
            <span style="margin-left: 10px;">📌 Cargo</span>
            <span style="margin-left: 10px;">🏢 Supervisão/Área</span>
            <span style="margin-left: 10px;">⏱ Tempo desde criação</span>
            <span style="margin-left: 10px;">Resp: Responsável</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Sidebar: filtro global de Cargo (aplica em todos os quadros)
    cargo_col_global = "Cargo" if "Cargo" in df_raw.columns else None
    if cargo_col_global is None:
        for c in df_raw.columns:
            c_norm = unicodedata.normalize("NFKD", str(c).strip()).lower()
            c_norm = "".join(ch for ch in c_norm if not unicodedata.combining(ch))
            if c_norm == "cargo":
                cargo_col_global = c
                break

    selected_cargos: List[str] = []
    selected_supervisoes: List[str] = []

    # Colunas usadas para o filtro de Supervisão (e fallback para Área)
    supervisao_col_global = "Supervisão" if "Supervisão" in df_raw.columns else None
    if supervisao_col_global is None:
        for c in df_raw.columns:
            c_norm = unicodedata.normalize("NFKD", str(c).strip()).lower()
            c_norm = "".join(ch for ch in c_norm if not unicodedata.combining(ch))
            if c_norm == "supervisao":
                supervisao_col_global = c
                break

    area_col_global = "Área" if "Área" in df_raw.columns else None
    if area_col_global is None:
        for c in df_raw.columns:
            c_norm = unicodedata.normalize("NFKD", str(c).strip()).lower()
            c_norm = "".join(ch for ch in c_norm if not unicodedata.combining(ch))
            if c_norm == "area":
                area_col_global = c
                break

    with st.sidebar:
        st.markdown("### 🔎 Filtros")
        if supervisao_col_global or area_col_global:
            # O filtro de Supervisão deve respeitar o filtro de Cargo
            df_for_supervisao_options = df_raw.copy()
            sup_series = (
                df_raw[supervisao_col_global].astype(str).str.strip()
                if supervisao_col_global
                else pd.Series("", index=df_raw.index)
            )
            area_series = (
                df_raw[area_col_global].astype(str).str.strip()
                if area_col_global
                else pd.Series("", index=df_raw.index)
            )
            supervisao_display = sup_series.where(
                sup_series.notna()
                & (sup_series != "")
                & (~sup_series.str.lower().isin(["none", "nan", "nat", "<na>"])),
                area_series,
            )
            supervisao_display_norm = supervisao_display.map(_normalize_text_for_match)

            # Respeitar governança (quando habilitada)
            if governanca_enabled and allowed_supervisoes_norm is not None:
                df_for_supervisao_options = df_for_supervisao_options[
                    supervisao_display_norm.isin(allowed_supervisoes_norm)
                ]

            if cargo_col_global and selected_cargos:
                df_for_supervisao_options = df_for_supervisao_options[
                    df_for_supervisao_options[cargo_col_global]
                    .astype(str)
                    .str.strip()
                    .isin(selected_cargos)
                ]

            supervisao_options = sorted(
                [
                    v
                    for v in supervisao_display.loc[df_for_supervisao_options.index]
                    .dropna()
                    .astype(str)
                    .str.strip()
                    .unique()
                    .tolist()
                    if v and v.lower() not in {"none", "nan", "nat", "<na>"}
                ]
            )

            supervisao_options_norm = {_normalize_text_for_match(v) for v in supervisao_options}

            selected_supervisoes = st.multiselect(
                "Supervisão",
                options=supervisao_options,
                default=[],
                key="filter_supervisoes",
                placeholder="Selecione uma ou mais supervisões",
            )
            selected_supervisoes = [
                v
                for v in selected_supervisoes
                if _normalize_text_for_match(v) in supervisao_options_norm
            ]
        else:
            st.caption("Colunas de Supervisão/Área não encontradas para filtro.")

        if cargo_col_global:
            # O filtro de Cargo deve respeitar o filtro de Supervisão
            supervisoes_prev = st.session_state.get("filter_supervisoes", [])
            supervisoes_prev_norm = {
                _normalize_text_for_match(v) for v in supervisoes_prev if v
            }

            df_for_cargo_options = df_raw.copy()
            if supervisao_col_global or area_col_global:
                sup_series = (
                    df_raw[supervisao_col_global].astype(str).str.strip()
                    if supervisao_col_global
                    else pd.Series("", index=df_raw.index)
                )
                area_series = (
                    df_raw[area_col_global].astype(str).str.strip()
                    if area_col_global
                    else pd.Series("", index=df_raw.index)
                )
                supervisao_display = sup_series.where(
                    sup_series.notna()
                    & (sup_series != "")
                    & (~sup_series.str.lower().isin(["none", "nan", "nat", "<na>"])),
                    area_series,
                )
                supervisao_display_norm = supervisao_display.map(_normalize_text_for_match)

                # Respeitar governança (quando habilitada)
                if governanca_enabled and allowed_supervisoes_norm is not None:
                    df_for_cargo_options = df_for_cargo_options[
                        supervisao_display_norm.isin(allowed_supervisoes_norm)
                    ]
                # Respeitar supervisões já selecionadas (pra atualizar a lista)
                if supervisoes_prev_norm:
                    df_for_cargo_options = df_for_cargo_options[
                        supervisao_display_norm.isin(supervisoes_prev_norm)
                    ]

            cargo_options = sorted(
                [
                    v
                    for v in df_for_cargo_options[cargo_col_global]
                    .dropna()
                    .astype(str)
                    .str.strip()
                    .unique()
                    .tolist()
                    if v and v.lower() not in {"none", "nan", "nat", "<na>"}
                ]
            )
            selected_cargos = st.multiselect(
                "Cargo",
                options=cargo_options,
                default=[],
                key="filter_cargos",
                placeholder="Selecione um ou mais cargos",
            )
            cargo_options_norm = {_normalize_text_for_match(v) for v in cargo_options}
            selected_cargos = [v for v in selected_cargos if _normalize_text_for_match(v) in cargo_options_norm]
        else:
            st.caption("Coluna de Cargo não encontrada para filtro.")

    df_global = df_raw.copy()
    if cargo_col_global and selected_cargos:
        df_global = df_global[
            df_global[cargo_col_global].astype(str).str.strip().isin(selected_cargos)
        ]

    # Aplicar governança ao conjunto de dados (quando habilitada)
    if supervisao_col_global or area_col_global:
        sup_series = (
            df_global[supervisao_col_global].astype(str).str.strip()
            if supervisao_col_global
            else pd.Series("", index=df_global.index)
        )
        area_series = (
            df_global[area_col_global].astype(str).str.strip()
            if area_col_global
            else pd.Series("", index=df_global.index)
        )
        supervisao_display = sup_series.where(
            sup_series.notna()
            & (sup_series != "")
            & (~sup_series.str.lower().isin(["none", "nan", "nat", "<na>"])),
            area_series,
        )

        supervisao_display_norm = supervisao_display.map(_normalize_text_for_match)
        if governanca_enabled and allowed_supervisoes_norm is not None:
            df_global = df_global[
                supervisao_display_norm.isin(allowed_supervisoes_norm)
            ]

        # Aplicar filtro do usuário, se ele selecionar
        if selected_supervisoes:
            selected_supervisoes_norm = {_normalize_text_for_match(v) for v in selected_supervisoes if v}
            df_global = df_global[supervisao_display_norm.isin(selected_supervisoes_norm)]

    # 4 abas lado a lado
    tab_keys = list(BOARD_FILTERS.keys())
    tabs = st.tabs([BOARD_FILTERS[k]["label"] for k in tab_keys])

    for i, (tab, board_key) in enumerate(zip(tabs, tab_keys)):
        with tab:
            df_board = _filter_df_by_board(df_global, board_key)
            if df_board.empty and i == 0 and not df_global.empty:
                # Não exibimos mensagem adicional aqui: o próprio board renderiza o estado vazio.
                pass
            _render_kanban_board(df_board, BOARD_FILTERS[board_key]["label"], board_key)
