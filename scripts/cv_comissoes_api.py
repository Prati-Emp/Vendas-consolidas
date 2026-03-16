#!/usr/bin/env python3
"""
Integração com API do CV CRM - Comissões
Endpoint: https://prati.cvcrm.com.br/api/v1/cv/comissoes
Credenciais: CVCRM_EMAIL e CVCRM_TOKEN

Baseado no código fornecido pelo usuário.
"""

import logging
import os
import sys
import time
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
import pandas as pd
import requests

# Garante import do projeto quando rodar via Actions
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from scripts.config import get_api_config

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComissoesAPIClient:
    """
    Cliente para API de Comissões do CV CRM
    """
    
    def __init__(self):
        self.config = get_api_config('cv_comissoes')
        
        if not self.config:
            raise ValueError("Configuração da API CV Comissões não encontrada")
        
        self.base_url = self.config.base_url
        self.headers = self.config.headers
    
    def _fazer_requisicao_com_retry(
        self, payload: dict, page: int, max_retries: int = 3
    ) -> requests.Response:
        """Faz requisição com retry em caso de HTTP 500/502/503 (erros transientes)."""
        delays = [2, 5, 10]  # segundos entre tentativas
        last_error = None
        for attempt in range(max_retries):
            resp = requests.get(
                self.base_url, headers=self.headers, params=payload, timeout=90
            )
            if resp.status_code in (500, 502, 503):
                last_error = resp
                if attempt < max_retries - 1:
                    wait = delays[attempt]
                    logger.warning(
                        f"HTTP {resp.status_code} na página {page}, tentativa {attempt + 1}/{max_retries}. "
                        f"Aguardando {wait}s antes de tentar novamente..."
                    )
                    time.sleep(wait)
                else:
                    raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")
            else:
                return resp
        raise RuntimeError(f"HTTP {last_error.status_code}: {last_error.text}")

    def buscar_comissoes(self, 
                        a_partir_de: str = None,
                        ate: str = None,
                        page_size: int = 50,  # 50 reduz carga por página e evita erro 500 em offsets altos
                        max_pages: int = 5000,
                        sleep_between_calls: float = 1.5) -> List[Dict]:
        """
        Busca comissões paginando e retorna todos os dados detalhados.
        Explode a estrutura: Comissão -> Beneficiários -> Programação
        Usa retry em HTTP 500/502/503 e page_size menor para mitigar instabilidade da API.
        """
        # Se não fornecidas, usa datas padrão
        hoje = date.today()
        
        if a_partir_de is None:
            a_partir_de = "01/01/2025"
            
        if ate is None:
            # Data final: ontem (dinâmico) para evitar erro 500 com dados do dia atual
            ontem = hoje - timedelta(days=1)
            ate = ontem.strftime("%d/%m/%Y")
        
        page = 1
        results: List[Dict] = []
        total_processed = 0

        while page <= max_pages:
            offset = (page - 1) * page_size
            
            payload = {
                "a_partir_de": a_partir_de,
                "ate": ate,
                "limit": page_size,
                "offset": offset
            }

            logger.info(f"Fazendo requisição para página {page} (offset={offset})...")
            logger.info(f"Parâmetros: a_partir_de={a_partir_de}, ate={ate}")
            
            resp = self._fazer_requisicao_com_retry(payload, page)
            logger.info(f"Status da resposta: {resp.status_code}")

            data = resp.json()
            
            dados = data.get("comissoes", [])
            total = data.get("total", 0)
            limit = data.get("limit", page_size)
            offset_returned = data.get("offset", 0)
            
            logger.info(f"Dados recebidos: {len(dados)}")
            logger.info(f"Total de registros: {total}, Limit: {limit}, Offset: {offset_returned}")
            
            if not isinstance(dados, list) or len(dados) == 0:
                logger.info("Nenhum dado encontrado, parando paginação.")
                break

            # Processa cada comissão
            for item in dados:
                total_processed += 1
                
                # Dados base da comissão
                base_row = {
                    "idcomissao_cv": item.get("idcomissao_cv"),
                    "idcomissao_int": item.get("idcomissao_int"),
                    "data_cad_comissao": item.get("data_cad"),
                    "idsituacao_comissao": item.get("idsituacao"),
                    "idreserva_cv": item.get("idreserva_cv"),
                    "numero_venda": item.get("numero_venda"),
                    "empreendimento": item.get("empreendimento"),
                    "etapa": item.get("etapa"),
                    "bloco": item.get("bloco"),
                    "unidade": item.get("unidade"),
                    "valor_comissao_total": item.get("valor_comissao"),
                    "pagador_nome": item.get("pagador", {}).get("nome") if item.get("pagador") else None,
                    "pagador_doc": item.get("pagador", {}).get("documento") if item.get("pagador") else None,
                }
                
                beneficiarios = item.get("beneficiarios", [])
                
                if beneficiarios:
                    for ben in beneficiarios:
                        ben_row = base_row.copy()
                        ben_row.update({
                            "beneficiario_nome": ben.get("nome"),
                            "beneficiario_doc": ben.get("documento"),
                            "beneficiario_tipo": ben.get("para"),
                            "beneficiario_valor_total": ben.get("valor"),
                        })
                        
                        programacao = ben.get("programacao", [])
                        
                        if programacao:
                            for prog in programacao:
                                row = ben_row.copy()
                                row.update({
                                    "idpagamento": prog.get("idpagamento"),
                                    "situacao_pagamento": prog.get("situacao"),
                                    "valor_parcela": prog.get("valor"),
                                    "data_pagamento": prog.get("vencimento"),  # Renomeia vencimento para data_pagamento
                                    "vencimento": prog.get("vencimento"),  # Mantém também o original
                                    "data_medicao": prog.get("data_medicao"),
                                    "observacoes_pagamento": prog.get("observacoes")
                                })
                                results.append(row)
                        else:
                            # Beneficiário sem programação
                            row = ben_row.copy()
                            row.update({
                                "idpagamento": None,
                                "situacao_pagamento": None,
                                "valor_parcela": None,
                                "data_pagamento": None,  # Renomeia vencimento para data_pagamento
                                "vencimento": None,
                                "data_medicao": None,
                                "observacoes_pagamento": None
                            })
                            results.append(row)
                else:
                    # Comissão sem beneficiários
                    row = base_row.copy()
                    # Preenche campos de beneficiário e pagamento com None
                    for key in ["beneficiario_nome", "beneficiario_doc", "beneficiario_tipo", 
                               "beneficiario_valor_total", "idpagamento", "situacao_pagamento", 
                               "valor_parcela", "data_pagamento", "vencimento", "data_medicao", "observacoes_pagamento"]:
                        row[key] = None
                    results.append(row)

            if len(dados) < page_size:
                logger.info("Página com menos registros que o tamanho da página, parando.")
                break
            
            if total_processed >= total:
                logger.info(f"Coletou todos os {total} registros, parando.")
                break
            
            if offset + len(dados) >= total:
                logger.info(f"Alcançou o total de registros ({total}), parando.")
                break

            page += 1
            if sleep_between_calls > 0:
                time.sleep(sleep_between_calls)

        logger.info(f"\n=== RESUMO ===")
        logger.info(f"Total de comissões processadas: {total_processed}")
        logger.info(f"Total de linhas geradas (detalhadas): {len(results)}")
        
        return results
    
    def processar_dados(self, dados: List[Dict]) -> pd.DataFrame:
        """
        Processa os dados brutos em DataFrame
        """
        if not dados:
            logger.warning("Nenhum dado recebido para processar")
            return pd.DataFrame()
        
        df = pd.DataFrame(dados)
        
        # Ordenação sugerida das colunas (data_pagamento primeiro)
        cols_order = [
            "data_pagamento", "vencimento", "valor_parcela", "situacao_pagamento", "data_medicao",
            "beneficiario_nome", "beneficiario_tipo", "beneficiario_valor_total",
            "empreendimento", "unidade", "pagador_nome", 
            "idcomissao_cv", "data_cad_comissao", "valor_comissao_total"
        ]
        
        # Mantém apenas colunas existentes e adiciona o resto no final
        cols_to_use = [c for c in cols_order if c in df.columns]
        remaining_cols = [c for c in df.columns if c not in cols_to_use]
        final_cols = cols_to_use + remaining_cols
        
        df = df[final_cols]
        
        return df

def _gerar_meses_entre_datas(a_partir_de: str, ate: str) -> List[tuple]:
    """Gera lista de (inicio_mes, fim_mes) no formato DD/MM/YYYY para cada mês no intervalo."""
    def parse_ddmmyyyy(s: str) -> date:
        d, m, y = map(int, s.split("/"))
        return date(y, m, d)

    def fmt(d: date) -> str:
        return d.strftime("%d/%m/%Y")

    def ultimo_dia_mes(ano: int, mes: int) -> date:
        if mes == 12:
            return date(ano, 12, 31)
        return date(ano, mes + 1, 1) - timedelta(days=1)

    inicio = parse_ddmmyyyy(a_partir_de)
    fim = parse_ddmmyyyy(ate)
    meses = []
    ano, mes = inicio.year, inicio.month
    while date(ano, mes, 1) <= fim:
        primeiro = date(ano, mes, 1)
        ultimo = ultimo_dia_mes(ano, mes)
        de = max(inicio, primeiro)
        ate_d = min(fim, ultimo)
        meses.append((fmt(de), fmt(ate_d)))
        if mes == 12:
            ano, mes = ano + 1, 1
        else:
            mes += 1
    return meses


def obter_dados_cv_comissoes(
    a_partir_de: str = None,
    ate: str = None,
    chunk_por_mes: bool = True,
) -> pd.DataFrame:
    """
    Função principal para obter dados de comissões do CV CRM.

    Args:
        a_partir_de: Data inicial no formato DD/MM/YYYY (padrão: 01/01/2025)
        ate: Data final no formato DD/MM/YYYY (padrão: ontem)
        chunk_por_mes: Se True (padrão), busca mês a mês para reduzir carga por requisição
                       e mitigar HTTP 500 em offsets altos.
    """
    try:
        client = ComissoesAPIClient()
        hoje = date.today()
        if a_partir_de is None:
            a_partir_de = "01/01/2025"
        if ate is None:
            ate = (hoje - timedelta(days=1)).strftime("%d/%m/%Y")

        if chunk_por_mes:
            meses = _gerar_meses_entre_datas(a_partir_de, ate)
            logger.info(f"Buscando comissões em {len(meses)} blocos mensais (mitigação HTTP 500)")
            todos_dados = []
            for i, (de, ate_mes) in enumerate(meses, 1):
                try:
                    logger.info(f"[{i}/{len(meses)}] Período: {de} a {ate_mes}")
                    dados = client.buscar_comissoes(a_partir_de=de, ate=ate_mes)
                    todos_dados.extend(dados)
                    logger.info(f"  -> {len(dados)} registros obtidos")
                except Exception as e:
                    logger.error(f"  -> Erro no período {de}-{ate_mes}: {e}. Continuando...")
            dados = todos_dados
        else:
            dados = client.buscar_comissoes(a_partir_de=a_partir_de, ate=ate)

        if not dados:
            return pd.DataFrame()

        df = client.processar_dados(dados)

        if not df.empty:
            df["fonte"] = "cv_comissoes"
            df["processado_em"] = datetime.now()
            df["Data_Snapshot"] = pd.to_datetime(date.today())

        return df
    except Exception as e:
        logger.error(f"Erro ao obter dados: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Obtém dados de comissões do CV CRM'
    )
    parser.add_argument(
        '--a_partir_de',
        type=str,
        default=None,
        help='Data inicial no formato DD/MM/YYYY (padrão: 01/01/2025)'
    )
    parser.add_argument(
        '--ate',
        type=str,
        default=None,
        help='Data final no formato DD/MM/YYYY (padrão: ontem)'
    )
    
    args = parser.parse_args()
    
    df = obter_dados_cv_comissoes(
        a_partir_de=args.a_partir_de,
        ate=args.ate
    )
    
    print(f"Registros obtidos: {len(df)}")
    if not df.empty:
        print(f"Colunas: {list(df.columns)}")
