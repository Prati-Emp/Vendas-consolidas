#!/usr/bin/env python3
"""
Integração com API do CV - Repasses
Endpoint: https://prati.cvcrm.com.br/api/v1/cvdw/repasses
Credenciais: mesmas de CV Vendas (email, token)

Adaptação do M do Power BI:
- Paginação por 'pagina'
- Filtros de data (a_partir_data_referencia, ate_data_referencia) podem ser passados como query se necessário
- Seleção de colunas conforme M e transformação de tipos
- Junção de-para por 'situacao' para coluna derivada "Para"
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd
import duckdb
import os

from scripts.orchestrator import make_api_request
from scripts.config import get_api_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


MAPEAMENTO_SITUACAO_PADRAO = {
    "Contrato Registrado": "Contrato Registrado",
    "Conformidade Aprovada": "Em Assinatura Caixa",
    "Assinado Caixa": "Em Assinatura Caixa",
    "Recolhimento de Custas": "Em Assinatura Caixa",
    "Confecção de Contrato Caixa": "Em Assinatura Caixa",
    "Enviado ao correspondente": "Em Conformidade",
    "Aguardando projeto e Alvará": "Em Conformidade",
    "Aguardando Assinatura Formulários": "Em Conformidade",
    "Aguardando Assinatura Formulario": "Em Conformidade",
    "Aguardando Assinatura Formularios": "Em Conformidade",  # Adicionado para cobrir variação
    "Análise de Conformidade": "Em Conformidade",
    "Inconforme": "Em Conformidade",
    "Validação Cohapar": "Em Conformidade",
    "Vistoria da Engenharia": "Em Conformidade",
    "Autorização Cohapar": "Em Conformidade",
    "Em Espera": "Em Espera",
    "Espera - Análise Aprovada": "Em Espera",
    "Prazo de contrato - sem análise": "Em Espera",
    "Espera - Demanda Mínima": "Em Espera",
    "Espera - Demanda Minima": "Em Espera",
    "Espera - Analisando Credito": "Em Espera",
    "Espera -  Analisando Credito": "Em Espera",  # Adicionado para cobrir espaço extra
    "Espera - Analisando Crédito": "Em Espera",
    "Espera - Sem Análise": "Em Espera",
    "Espera - Análise Reprovada": "Em Espera",
    "Renegociação": "Em Espera",
    "Aprovação de Aditivo": "Em Espera",
    "Elaboração de Aditivo": "Em Espera",
    "Em assinatura Aditivo": "Em Espera",
    "Prazo de contrato - com análise": "Em Espera",
    "Entrada no Registro": "Entrada no registro",
    "Venda a Investidor": "Venda a Investidor",
    # Adicionando situações que estavam sem mapeamento
    "Distrato": "Distrato",
    "Cancelado": "Cancelado",
}


class CVRepassesAPIClient:
    def __init__(self):
        self.config = get_api_config('cv_repasses')
        if not self.config:
            raise ValueError("Configuração da API CV Repasses não encontrada")

    async def get_pagina(self, pagina: int = 1, a_partir: str = '2020-01-01', ate: Optional[str] = None) -> Dict[str, Any]:
        endpoint = ""
        if not ate:
            ate = datetime.now().strftime('%Y-%m-%d')
        params = {
            'pagina': pagina,
            'a_partir_data_referencia': a_partir,
            'ate_data_referencia': ate,
            'registros_por_pagina': 100,
        }
        logger.info(f"Buscando CV Repasses - Página {pagina}")
        return await make_api_request('cv_repasses', endpoint, params)

    async def get_all(self, a_partir: str = '2020-01-01', ate: Optional[str] = None) -> List[Dict[str, Any]]:
        pagina = 1
        todos: List[Dict[str, Any]] = []
        vazias = 0
        max_vazias = 3
        while True:
            result = await self.get_pagina(pagina, a_partir, ate)
            if not result.get('success'):
                logger.error(f"Erro na página {pagina}: {result.get('error')}")
                break
            dados = result.get('data', {}).get('dados', [])
            if not dados:
                vazias += 1
                if vazias >= max_vazias:
                    break
            else:
                vazias = 0
                todos.extend(dados)
            pagina += 1
            await asyncio.sleep(0.2)
        logger.info(f"Total repasses: {len(todos)}")
        return todos


def _montar_mapa_de_para(df_de_para: Optional[pd.DataFrame]) -> Dict[str, str]:
    mapping = {k.strip(): v for k, v in MAPEAMENTO_SITUACAO_PADRAO.items()}
    if df_de_para is not None and not df_de_para.empty:
        df_local = df_de_para.rename(columns={df_de_para.columns[0]: 'De', df_de_para.columns[1]: 'Para'})
        for _, row in df_local.iterrows():
            de = str(row['De']).strip()
            para = str(row['Para']).strip()
            if de:
                mapping[de] = para
    return mapping


def processar_cv_repasses(dados: List[Dict[str, Any]], df_de_para: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    if not dados:
        return pd.DataFrame()

    df = pd.DataFrame(dados)

    # Normalização de campos principais
    if 'data_cad' in df.columns:
        df['data_cad'] = pd.to_datetime(df['data_cad'], errors='coerce')
    if 'codigointerno_empreendimento' in df.columns:
        df['codigointerno_empreendimento'] = pd.to_numeric(
            df['codigointerno_empreendimento'], errors='coerce'
        ).astype('Int64')
    # CORREÇÃO: Normalização otimizada de valores monetários
    def normalizar_valor_monetario_otimizado(valor):
        """
        Normalização otimizada de valores monetários
        - Se tem vírgula: já está no formato brasileiro correto
        - Se tem pontos: substitui apenas o ÚLTIMO ponto por vírgula
        - Se não tem nem pontos nem vírgulas: número simples
        """
        if pd.isna(valor) or valor is None:
            return 0.0
        
        valor_str = str(valor).replace('R$', '').replace('$', '').strip()
        
        # Se já tem vírgula, está no formato brasileiro correto
        if ',' in valor_str:
            return float(valor_str.replace(',', '.'))
        
        # Se tem pontos, substituir apenas o ÚLTIMO ponto por vírgula
        if '.' in valor_str:
            ultimo_ponto = valor_str.rfind('.')
            valor_corrigido = valor_str[:ultimo_ponto] + ',' + valor_str[ultimo_ponto+1:]
            return float(valor_corrigido.replace(',', '.'))
        
        # Número simples sem formatação
        try:
            return float(valor_str)
        except ValueError:
            return 0.0

    # Aplicar normalização otimizada em todas as colunas de valor
    colunas_valor = [
        'valor_previsto', 'valor_divida', 'valor_subsidio', 
        'valor_fgts', 'valor_registro', 'valor_financiado', 'valor_contrato'
    ]
    
    for col in colunas_valor:
        if col in df.columns:
            df[col] = df[col].apply(normalizar_valor_monetario_otimizado)

    # Construção da coluna "Para" baseada em situacao
    if 'situacao' in df.columns:
        df['situacao'] = df['situacao'].astype(str).str.strip()
        mapping = _montar_mapa_de_para(df_de_para)
        df['Para'] = df['situacao'].map(mapping).fillna('Sem Mapeamento')
    else:
        df['Para'] = 'Sem Mapeamento'

    # Filtrar "Venda a Investidor", "Distrato" e "Cancelado"
    df = df[~df['Para'].isin(['Venda a Investidor', 'Distrato', 'Cancelado'])]

    df['fonte'] = 'cv_repasses'
    df['processado_em'] = datetime.now()
    return df


def carregar_de_para_motherduck() -> Optional[pd.DataFrame]:
    try:
        token = os.environ.get('MOTHERDUCK_TOKEN', '').strip()
        if not token:
            return None
        os.environ['motherduck_token'] = token
        con = duckdb.connect('md:reservas')
        q = """
        SELECT TRIM("De ") AS De, TRIM(Para) AS Para
        FROM reservas.main.de_para_repasse
        """
        df = con.sql(q).df()
        con.close()
        return df
    except Exception:
        return None


async def obter_dados_cv_repasses() -> pd.DataFrame:
    client = CVRepassesAPIClient()
    dados = await client.get_all()
    de_para = carregar_de_para_motherduck()
    return processar_cv_repasses(dados, de_para)


if __name__ == '__main__':
    async def _test():
        df = await obter_dados_cv_repasses()
        print('Registros:', len(df))
        if not df.empty:
            print(df.head())
    asyncio.run(_test())


