#!/usr/bin/env python3
"""
Integração com API do CV - VGV Empreendimentos
Endpoint: https://prati.cvcrm.com.br/api/v1/cv/tabelasdepreco
Credenciais: mesmas de CV Vendas (email, token)

Baseado no código fornecido pelo usuário:
- Testa IDs de empreendimentos de 1 a 20
- Busca tabelas de preço por empreendimento
- Seleciona tabela de financiamento (ou primeira disponível)
- Expande unidades e normaliza dados
- Remove saída em Excel (integração com MotherDuck)
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd
import requests

from scripts.orchestrator import make_api_request
from scripts.config import get_api_config

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CVVGVEmpreendimentosAPIClient:
    """Cliente para API de VGV Empreendimentos do CV"""
    
    def __init__(self):
        # Usar configuração do CV Vendas (mesmas credenciais)
        self.config = get_api_config('cv_vendas')
        
        if not self.config:
            raise ValueError("Configuração da API CV Vendas não encontrada")
        
        # URL específica para tabelas de preço
        self.base_url = "https://prati.cvcrm.com.br/api/v1/cv/tabelasdepreco"
        self.headers = self.config.headers
    
    async def testar_ids_empreendimentos(self, inicio: int = 1, fim: int = 20) -> List[int]:
        """
        Testa IDs de empreendimentos e retorna lista de IDs válidos
        """
        logger.info(f"=== TESTANDO IDs DE {inicio} A {fim} ===")
        ids_validos = []
        
        for id_empreendimento in range(inicio, fim + 1):
            try:
                params = {"idempreendimento": id_empreendimento}
                resp = requests.get(self.base_url, headers=self.headers, params=params, timeout=10)
                
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list) and len(data) > 0:
                        nome_empreendimento = data[0].get('empreendimento', 'N/A')
                        qtd_tabelas = len(data)
                        logger.info(f"✅ ID {id_empreendimento}: {qtd_tabelas} tabelas - {nome_empreendimento}")
                        ids_validos.append(id_empreendimento)
                    else:
                        logger.info(f"❌ ID {id_empreendimento}: 0 tabelas")
                else:
                    logger.info(f"❌ ID {id_empreendimento}: Erro {resp.status_code}")
                    
            except Exception as e:
                logger.info(f"❌ ID {id_empreendimento}: Erro - {e}")
            
            time.sleep(0.3)  # Pausa entre requisições
        
        logger.info(f"=== RESUMO ===")
        logger.info(f"IDs válidos encontrados: {ids_validos}")
        return ids_validos

    async def processar_empreendimento(self, id_empreendimento: int) -> Optional[Dict]:
        """
        Processa um empreendimento completo
        """
        logger.info(f"\n=== PROCESSANDO ID {id_empreendimento} ===")
        
        try:
            # 1. Buscar tabelas
            params = {"idempreendimento": id_empreendimento}
            resp = requests.get(self.base_url, headers=self.headers, params=params, timeout=30)
            
            if resp.status_code != 200:
                logger.error(f"  ❌ Erro ao buscar tabelas: {resp.status_code}")
                return None
            
            tabelas = resp.json()
            if not tabelas:
                logger.error(f"  ❌ Nenhuma tabela encontrada")
                return None
            
            logger.info(f"  ✅ {len(tabelas)} tabelas encontradas")
            
            # 2. Selecionar tabela de financiamento
            tabelas_financiamento = [
                t for t in tabelas 
                if t.get('tabela', '').lower().find('financiamento') != -1
            ]
            
            if tabelas_financiamento:
                tabela_selecionada = max(tabelas_financiamento, key=lambda x: int(x.get('idtabela', 0)))
                logger.info(f"  ✅ Tabela de financiamento: ID {tabela_selecionada.get('idtabela')} - {tabela_selecionada.get('tabela')}")
            else:
                tabela_selecionada = tabelas[0]
                logger.info(f"  ⚠️  Nenhuma tabela de financiamento. Usando: ID {tabela_selecionada.get('idtabela')} - {tabela_selecionada.get('tabela')}")
            
            # 3. Buscar dados completos
            id_tabela = tabela_selecionada.get('idtabela')
            params_completos = {
                "idempreendimento": id_empreendimento,
                "idtabela": id_tabela
            }
            
            resp_completos = requests.get(self.base_url, headers=self.headers, params=params_completos, timeout=30)
            
            if resp_completos.status_code != 200:
                logger.error(f"  ❌ Erro ao buscar dados completos: {resp_completos.status_code}")
                return None
            
            dados_completos = resp_completos.json()
            logger.info(f"  ✅ Dados completos encontrados")
            
            # 4. Expandir unidades
            df = pd.DataFrame(dados_completos)
            
            if 'unidades' in df.columns:
                # Expandir lista de unidades
                df_expandido = df.explode('unidades')
                
                # Expandir campos das unidades (que são records/dicts)
                if not df_expandido.empty and df_expandido['unidades'].notna().any():
                    # Normalizar as unidades (assumindo que são dicionários)
                    unidades_normalizadas = []
                    for idx, row in df_expandido.iterrows():
                        if isinstance(row['unidades'], dict):
                            unidade_data = row['unidades'].copy()
                            # Adicionar prefixo 'unidades.' para evitar conflitos
                            for key in ['etapa', 'bloco', 'unidade', 'idunidade', 'area_privativa', 'situacao', 'valor_total']:
                                if key in unidade_data:
                                    unidade_data[f'unidades.{key}'] = unidade_data.pop(key)
                            # Excluir series se existir
                            if 'series' in unidade_data:
                                del unidade_data['series']
                            unidades_normalizadas.append(unidade_data)
                        else:
                            unidades_normalizadas.append({})
                    
                    if unidades_normalizadas:
                        df_unidades = pd.DataFrame(unidades_normalizadas)
                        # Resetar índices para evitar problemas de concatenação
                        df_expandido_reset = df_expandido.drop('unidades', axis=1).reset_index(drop=True)
                        df_unidades_reset = df_unidades.reset_index(drop=True)
                        df_final = pd.concat([df_expandido_reset, df_unidades_reset], axis=1)
                        
                        # Excluir colunas series e referencia se existirem
                        colunas_para_excluir = ['series', 'referencia']
                        for col in colunas_para_excluir:
                            if col in df_final.columns:
                                df_final = df_final.drop(col, axis=1)
                        
                        logger.info(f"  ✅ {len(df_final)} unidades expandidas com campos normalizados")
                        
                        resultado = {
                            'id_empreendimento': id_empreendimento,
                            'id_tabela': id_tabela,
                            'nome_tabela': tabela_selecionada.get('tabela'),
                            'nome_empreendimento': tabela_selecionada.get('empreendimento'),
                            'total_unidades': len(df_final),
                            'df_expandido': df_final
                        }
                        
                        return resultado
                    else:
                        logger.error(f"  ❌ Erro ao normalizar unidades")
                        return None
                else:
                    logger.error(f"  ❌ Nenhuma unidade válida encontrada")
                    return None
            else:
                logger.error(f"  ❌ Coluna 'unidades' não encontrada")
                return None
                
        except Exception as e:
            logger.error(f"  ❌ Erro: {e}")
            return None

    async def get_all_empreendimentos(self, inicio: int = 1, fim: int = 20) -> List[Dict]:
        """
        Busca todos os empreendimentos válidos e processa seus dados
        """
        logger.info("=== VGV EMPREENDIMENTOS - VERSÃO FINAL ===")
        
        # 1. Testar IDs
        ids_validos = await self.testar_ids_empreendimentos(inicio, fim)
        
        if not ids_validos:
            logger.warning("Nenhum ID válido encontrado. Encerrando.")
            return []
        
        # 2. Processar empreendimentos
        logger.info(f"\n=== PROCESSANDO {len(ids_validos)} EMPREENDIMENTOS ===")
        resultados = []
        
        for id_empreendimento in ids_validos:
            resultado = await self.processar_empreendimento(id_empreendimento)
            if resultado:
                resultados.append(resultado)
            time.sleep(1)  # Pausa entre requisições
        
        logger.info(f"\n=== RESUMO FINAL ===")
        logger.info(f"IDs testados: {ids_validos}")
        logger.info(f"IDs processados com sucesso: {len(resultados)}")
        logger.info(f"Taxa de sucesso: {len(resultados)/len(ids_validos)*100:.1f}%")
        
        return resultados

def processar_dados_vgv_empreendimentos(resultados: List[Dict]) -> pd.DataFrame:
    """
    Processa e padroniza dados dos empreendimentos VGV
    
    Args:
        resultados: Lista de resultados de empreendimentos processados
    """
    if not resultados:
        logger.warning("Nenhum resultado para processar - VGV Empreendimentos")
        return pd.DataFrame()
    
    # Consolidar todos os DataFrames
    todos_dfs = []
    
    for resultado in resultados:
        df_empreendimento = resultado['df_expandido'].copy()
        
        # Adicionar metadados do empreendimento
        df_empreendimento['id_empreendimento'] = resultado['id_empreendimento']
        df_empreendimento['id_tabela'] = resultado['id_tabela']
        df_empreendimento['nome_tabela'] = resultado['nome_tabela']
        df_empreendimento['nome_empreendimento'] = resultado['nome_empreendimento']
        
        todos_dfs.append(df_empreendimento)
    
    if not todos_dfs:
        return pd.DataFrame()
    
    # Concatenar todos os DataFrames
    df_final = pd.concat(todos_dfs, ignore_index=True)
    
    # Adicionar coluna de fonte
    df_final['fonte'] = 'vgv_empreendimentos'
    
    # Adicionar timestamp de processamento
    df_final['processado_em'] = datetime.now()
    
    logger.info(f"Dados processados - VGV Empreendimentos: {len(df_final)} registros")
    return df_final

async def obter_dados_vgv_empreendimentos(inicio: int = 1, fim: int = 20) -> pd.DataFrame:
    """Obtém todos os dados de empreendimentos VGV com processamento completo."""
    logger.info("Buscando dados do VGV Empreendimentos")

    client = CVVGVEmpreendimentosAPIClient()
    resultados = await client.get_all_empreendimentos(inicio, fim)

    return processar_dados_vgv_empreendimentos(resultados)

if __name__ == "__main__":
    # Teste da API do VGV Empreendimentos
    async def test_vgv_empreendimentos():
        print("=== Testando API VGV Empreendimentos ===")
        
        try:
            df = await obter_dados_vgv_empreendimentos(1, 5)  # Testar apenas IDs 1-5
            
            print(f"Registros encontrados: {len(df)}")
            
            if not df.empty:
                print("\nColunas:", list(df.columns))
                print(df.head())
            
        except Exception as e:
            print(f"Erro no teste: {str(e)}")
    
    asyncio.run(test_vgv_empreendimentos())

