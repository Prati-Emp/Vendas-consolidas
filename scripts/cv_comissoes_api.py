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
    
    def buscar_comissoes(self, 
                        a_partir_de: str = None,
                        ate: str = None,
                        page_size: int = 300,  # Aumentado de 100 para 300 diferente do código de referência
                        max_pages: int = 5000,
                        sleep_between_calls: float = 0.0) -> List[Dict]:
        """
        Busca comissões paginando e retorna todos os dados detalhados.
        Explode a estrutura: Comissão -> Beneficiários -> Programação
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
        total_pages = None
        total_processed = 0

        while page <= max_pages:
            offset = (page - 1) * page_size
            
            payload = {
                "a_partir_de": a_partir_de,
                "ate": ate,
                "limit": page_size,
                "offset": offset
            }

            logger.info(f"Fazendo requisição para página {page}...")
            logger.info(f"Parâmetros: a_partir_de={a_partir_de}, ate={ate}")
            
            resp = requests.get(self.base_url, headers=self.headers, params=payload, timeout=60)
            logger.info(f"Status da resposta: {resp.status_code}")
            
            if resp.status_code != 200:
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")

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

def obter_dados_cv_comissoes(a_partir_de: str = None, ate: str = None) -> pd.DataFrame:
    """
    Função principal para obter dados de comissões do CV CRM
    
    Args:
        a_partir_de: Data inicial no formato DD/MM/YYYY (padrão: 01/01/2025)
        ate: Data final no formato DD/MM/YYYY (padrão: ontem)
    """
    try:
        client = ComissoesAPIClient()
        dados = client.buscar_comissoes(a_partir_de=a_partir_de, ate=ate)
        
        if not dados:
            return pd.DataFrame()
        
        df = client.processar_dados(dados)
        
        if not df.empty:
            # Adiciona colunas padrão do sistema
            df['fonte'] = 'cv_comissoes'
            df['processado_em'] = datetime.now()
            df['Data_Snapshot'] = pd.to_datetime(date.today())
            
        return df
    except Exception as e:
        logger.error(f"Erro ao obter dados: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()

if __name__ == "__main__":
    df = obter_dados_cv_comissoes()
    print(f"Registros obtidos: {len(df)}")
    if not df.empty:
        print(f"Colunas: {list(df.columns)}")
