#!/usr/bin/env python3
"""
Integração com API do CV - Leads
Endpoint: https://prati.cvcrm.com.br/api/v1/cvdw/leads
Credenciais: mesmas de CV Vendas (email, token)

Baseado no código fornecido pelo usuário:
- Paginação por 'pagina' e 'registros_por_pagina'
- Filtro por imobiliária: manter "Prati" OU vazio/nulo
- Sem filtro de data (busca dados mais atualizados)
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd

from scripts.orchestrator import make_api_request
from scripts.config import get_api_config

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CVLeadsAPIClient:
    """Cliente para API de leads do CV"""
    
    def __init__(self):
        self.config = get_api_config('cv_leads')
        
        if not self.config:
            raise ValueError("Configuração da API CV Leads não encontrada")
    
    async def get_pagina(self, pagina: int = 1, registros_por_pagina: int = 500) -> Dict[str, Any]:
        """
        Busca uma página dos leads do CV.
        """
        endpoint = ""  # base_url já aponta direto para /cvdw/leads
        params = {
            'pagina': pagina,
            'registros_por_pagina': registros_por_pagina
        }

        logger.info(f"Buscando CV Leads - Página {pagina}")
        return await make_api_request('cv_leads', endpoint, params)
    
    async def get_all_leads(self, 
                           registros_por_pagina: int = 500,
                           imobiliaria_match: str = "Prati",
                           include_empty_imobiliaria: bool = True,
                           max_paginas: int = 5000,
                           sleep_between_calls: float = 0.0) -> List[Dict[str, Any]]:
        """
        Busca todos os leads com paginação automática e filtros.
        
        Args:
            registros_por_pagina: Número de registros por página
            imobiliaria_match: Filtro para imobiliária (padrão: "Prati")
            include_empty_imobiliaria: Incluir registros com imobiliária vazia
            max_paginas: Limite máximo de páginas
            sleep_between_calls: Delay entre chamadas (segundos)
        """
        pagina = 1
        results: List[Dict[str, Any]] = []
        total_processed = 0
        total_filtered = 0
        paginas_vazias = 0
        max_paginas_vazias = 3

        logger.info("=== BUSCANDO LEADS SEM FILTRO DE DATA ===")
        logger.info(f"Filtro imobiliária: '{imobiliaria_match}' (incluir vazias: {include_empty_imobiliaria})")

        while pagina <= max_paginas:
            try:
                result = await self.get_pagina(pagina, registros_por_pagina)
                
                if not result['success']:
                    error_msg = result.get('error', 'Erro desconhecido')
                    logger.error(f"Erro na página {pagina}: {error_msg}")
                    
                    # Se for erro 404, pode ser fim dos dados
                    if '404' in str(error_msg) or 'not found' in str(error_msg).lower():
                        logger.info("Fim dos dados detectado (erro 404)")
                        break
                    break

                data = result['data']
                dados = data.get("dados", [])
                total_pages = data.get("total_de_paginas")
                registros = data.get("registros", len(dados))
                
                logger.info(f"Dados recebidos: {len(dados) if isinstance(dados, list) else 'não é uma lista'}")
                logger.info(f"Total de páginas: {total_pages}, Registros nesta página: {registros}")
                
                if not isinstance(dados, list) or len(dados) == 0:
                    paginas_vazias += 1
                    logger.info(f"Página {pagina} vazia ({paginas_vazias}/{max_paginas_vazias})")
                    
                    if paginas_vazias >= max_paginas_vazias:
                        logger.info(f"Fim da paginação: {paginas_vazias} páginas vazias consecutivas")
                        break
                else:
                    paginas_vazias = 0  # Reset contador de páginas vazias
                    
                    # Processar cada item com filtros
                    for item in dados:
                        total_processed += 1
                        imob = (item.get("imobiliaria") or "").strip()

                        # Filtro: manter "Prati" OU vazio/nulo
                        is_prati = imobiliaria_match.lower() in imob.lower() if imob else False
                        is_empty = (imob == "")
                        
                        # Debug: mostrar alguns exemplos de imobiliárias
                        if len(results) < 5:  # Mostrar apenas os primeiros 5 para debug
                            logger.info(f"Debug - Imobiliaria: '{imob}', is_prati: {is_prati}, is_empty: {is_empty}")
                        
                        if not (is_prati or (include_empty_imobiliaria and is_empty)):
                            continue

                        total_filtered += 1
                        
                        # Extrair campos adicionais expansíveis
                        campos_adicionais = item.get("campos_adicionais", [])
                        idcampo_values = []
                        nome_values = []
                        valor_values = []
                        
                        if isinstance(campos_adicionais, list):
                            for campo in campos_adicionais:
                                if isinstance(campo, dict):
                                    idcampo_values.append(campo.get("idcampo"))
                                    nome_values.append(campo.get("nome"))
                                    valor_values.append(campo.get("valor"))
                        
                        row = {
                            "Idlead": item.get("idlead"),
                            "Data_cad": item.get("data_cad"),
                            "Situacao": item.get("situacao"),
                            "Imobiliaria": item.get("imobiliaria"),
                            "nome_situacao_anterior_lead": item.get("nome_situacao_anterior_lead"),
                            "gestor": item.get("gestor"),
                            "empreendimento_ultimo": item.get("empreendimento_ultimo"),
                            "empreendimento_primeiro": item.get("empreendimento_primeiro"),
                            "referencia_data": item.get("referencia_data"),
                            "data_reativacao": item.get("data_reativacao"),
            "corretor": item.get("corretor"),
            "corretor_ultimo": item.get("corretor_ultimo"),
            "tags": item.get("tags"),
            "midia_original": item.get("midia_original"),
            "midia_ultimo": item.get("midia_ultimo"),
                            "motivo_cancelamento": item.get("motivo_cancelamento"),
                            "data_cancelamento": item.get("data_cancelamento"),
                            "ultima_data_conversao": item.get("ultima_data_conversao"),
                            "descricao_motivo_cancelamento": item.get("descricao_motivo_cancelamento"),
                            "possibilidade_venda": item.get("possibilidade_venda"),
                            "score": item.get("score"),
                            "novo": item.get("novo"),
                            "retorno": item.get("retorno"),
                            "data_ultima_alteracao": item.get("data_ultima_alteracao"),
                            "campos_adicionais_idcampo": idcampo_values,
                            "campos_adicionais_nome": nome_values,
                            "campos_adicionais_valor": valor_values,
                        }
                        results.append(row)

                    # Condições de parada
                    if len(dados) < registros_por_pagina:
                        logger.info("Página com menos registros que o tamanho da página, parando.")
                        break
                    
                    if total_pages and pagina >= total_pages:
                        logger.info(f"Alcançou o total de páginas ({total_pages}), parando.")
                        break

                pagina += 1
                if sleep_between_calls > 0:
                    await asyncio.sleep(sleep_between_calls)

            except Exception as e:
                logger.error(f"Erro na página {pagina}: {str(e)}")
                break

        logger.info(f"\n=== RESUMO ===")
        logger.info(f"Total de registros processados: {total_processed}")
        logger.info(f"Total de registros filtrados (Prati + vazias): {total_filtered}")
        logger.info(f"Registros finais salvos: {len(results)}")
        
        return results

def processar_dados_cv_leads(dados: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Processa e padroniza dados dos leads do CV
    
    Args:
        dados: Lista de dados brutos
    """
    if not dados:
        logger.warning("Nenhum dado para processar - CV Leads")
        return pd.DataFrame()
    
    df = pd.DataFrame(dados)
    
    # Padronizar colunas de data
    if 'Data_cad' in df.columns:
        df['Data_cad'] = pd.to_datetime(df['Data_cad'], errors='coerce')
    
    if 'referencia_data' in df.columns:
        df['referencia_data'] = pd.to_datetime(df['referencia_data'], errors='coerce')
    
    # Nova coluna: data_reativacao
    if 'data_reativacao' in df.columns:
        df['data_reativacao'] = pd.to_datetime(df['data_reativacao'], errors='coerce')
    
    # Tratar campos de data adicionais
    for col_data in [
        'data_cancelamento',
        'ultima_data_conversao',
        'data_ultima_alteracao'
    ]:
        if col_data in df.columns:
            df[col_data] = pd.to_datetime(df[col_data], errors='coerce')

    # Adicionar coluna de fonte
    df['fonte'] = 'cv_leads'
    
    # Adicionar timestamp de processamento
    df['processado_em'] = datetime.now()
    
    # Processar campos expansíveis e criar colunas dinâmicas
    if 'campos_adicionais_nome' in df.columns and 'campos_adicionais_valor' in df.columns:
        # Criar colunas dinâmicas baseadas nos nomes únicos
        logger.info("Processando campos adicionais para criar colunas dinâmicas...")
        
        # Coletar todos os nomes únicos
        todos_nomes = set()
        for idx, row in df.iterrows():
            if isinstance(row['campos_adicionais_nome'], list) and isinstance(row['campos_adicionais_valor'], list):
                for nome in row['campos_adicionais_nome']:
                    if nome:  # Ignorar valores vazios
                        todos_nomes.add(str(nome).strip())
        
        logger.info(f"Nomes únicos encontrados: {sorted(todos_nomes)}")
        
        # Criar colunas dinâmicas
        for nome in todos_nomes:
            coluna_nome = f"campo_{nome.replace(' ', '_').replace('-', '_').replace('.', '_').lower()}"
            df[coluna_nome] = None
        
        # Mapear valores para as colunas corretas
        for idx, row in df.iterrows():
            if isinstance(row['campos_adicionais_nome'], list) and isinstance(row['campos_adicionais_valor'], list):
                for nome, valor in zip(row['campos_adicionais_nome'], row['campos_adicionais_valor']):
                    if nome and valor:  # Ignorar valores vazios
                        coluna_nome = f"campo_{str(nome).replace(' ', '_').replace('-', '_').replace('.', '_').lower()}"
                        if coluna_nome in df.columns:
                            df.at[idx, coluna_nome] = valor
        
        # Remover as colunas originais dos campos adicionais
        df = df.drop(columns=['campos_adicionais_idcampo', 'campos_adicionais_nome', 'campos_adicionais_valor'], errors='ignore')
        
        logger.info(f"Colunas dinâmicas criadas: {[col for col in df.columns if col.startswith('campo_')]}")
    
    # Processar 'tags' em colunas dinâmicas tag1..tagN
    if 'tags' in df.columns:
        logger.info("Processando coluna 'tags' em colunas tag1..tagN")
        # Garantir string e dividir por vírgula
        tags_split = df['tags'].fillna('').astype(str).apply(lambda x: [t.strip() for t in x.split(',') if t.strip()])
        # Descobrir o número máximo de tags
        max_tags = tags_split.apply(len).max() if not tags_split.empty else 0
        # Criar colunas tag1..tagN
        for i in range(1, max_tags + 1):
            col_name = f"tag{i}"
            df[col_name] = tags_split.apply(lambda lst, idx=i-1: lst[idx] if len(lst) > idx else None)
        logger.info(f"Colunas de tags criadas: {[f'tag{i}' for i in range(1, max_tags + 1)]}")
        # Remover coluna original 'tags' se desejado manter apenas tags normalizadas
        # df = df.drop(columns=['tags'])

    # Criar colunas consolidadas
    logger.info("Criando colunas consolidadas...")
    
    # corretor_consolidado: corretor ou corretor_ultimo se corretor estiver vazio
    if 'corretor' in df.columns and 'corretor_ultimo' in df.columns:
        df['corretor_consolidado'] = df['corretor'].fillna('').astype(str)
        # Aplicar fallback para corretor_ultimo quando corretor estiver vazio
        mask_vazio = (df['corretor_consolidado'] == '') | (df['corretor_consolidado'] == 'nan') | (df['corretor_consolidado'].isna())
        df.loc[mask_vazio, 'corretor_consolidado'] = df.loc[mask_vazio, 'corretor_ultimo'].fillna('')
        logger.info("Coluna 'corretor_consolidado' criada com fallback para corretor_ultimo")
    
    # midia_consolidada: midia_ultimo ou midia_original se midia_ultimo estiver vazio
    if 'midia_ultimo' in df.columns and 'midia_original' in df.columns:
        df['midia_consolidada'] = df['midia_ultimo'].fillna('').astype(str)
        # Aplicar fallback para midia_original quando midia_ultimo estiver vazio
        mask_vazio = (df['midia_consolidada'] == '') | (df['midia_consolidada'] == 'nan') | (df['midia_consolidada'].isna())
        df.loc[mask_vazio, 'midia_consolidada'] = df.loc[mask_vazio, 'midia_original'].fillna('')
        logger.info("Coluna 'midia_consolidada' criada com fallback para midia_original")

    # Criar colunas de status baseadas em tags com lógica hierárquica
    logger.info("Criando colunas de status baseadas em tags...")
    
    # Definir status e suas variações (incluindo palavras concatenadas)
    status_definitions = {
        'status_venda_realizada': ['venda realizada', 'vendarealizada', 'vendarealizada'],
        'status_reserva': ['reserva'],
        'status_visita_realizada': ['visita realizada', 'visitarealizada', 'visitarealizada'],
        'status_em_atendimento': ['em atendimento'],  # Apenas "em atendimento", não "em atendimento corretor"
        'status_descoberta': ['descoberta'],
        'status_qualificacao': ['qualificação', 'qualificacao', 'qualificaçao']
    }
    
    # Inicializar todas as colunas de status como 'Não'
    for status_col in status_definitions.keys():
        df[status_col] = 'Não'
    
    # Percorrer todas as colunas de tags dinamicamente
    tag_columns = [col for col in df.columns if col.startswith('tag') and col[3:].isdigit()]
    logger.info(f"Colunas de tags encontradas: {tag_columns}")
    
    for idx, row in df.iterrows():
        # Coletar todas as tags da linha
        all_tags = []
        for tag_col in tag_columns:
            tag_value = row[tag_col]
            if pd.notna(tag_value) and str(tag_value).strip() != '':
                all_tags.append(str(tag_value).strip().lower())
        
        # Verificar cada status nas tags
        status_found = {}
        for status_col, variations in status_definitions.items():
            for tag in all_tags:
                for variation in variations:
                    if variation.lower() in tag:
                        status_found[status_col] = True
                        break
        
        # Aplicar lógica hierárquica
        # Hierarquia: venda realizada > reserva > visita realizada > em atendimento > descoberta > qualificação
        if status_found.get('status_venda_realizada', False):
            # Se venda realizada, todos os status são 'Sim'
            df.at[idx, 'status_venda_realizada'] = 'Sim'
            df.at[idx, 'status_reserva'] = 'Sim'
            df.at[idx, 'status_visita_realizada'] = 'Sim'
            df.at[idx, 'status_em_atendimento'] = 'Sim'
            df.at[idx, 'status_descoberta'] = 'Sim'
            df.at[idx, 'status_qualificacao'] = 'Sim'
        elif status_found.get('status_reserva', False):
            # Se reserva, todos os anteriores são 'Sim'
            df.at[idx, 'status_reserva'] = 'Sim'
            df.at[idx, 'status_visita_realizada'] = 'Sim'
            df.at[idx, 'status_em_atendimento'] = 'Sim'
            df.at[idx, 'status_descoberta'] = 'Sim'
            df.at[idx, 'status_qualificacao'] = 'Sim'
        elif status_found.get('status_visita_realizada', False):
            # Se visita realizada, todos os anteriores são 'Sim'
            df.at[idx, 'status_visita_realizada'] = 'Sim'
            df.at[idx, 'status_em_atendimento'] = 'Sim'
            df.at[idx, 'status_descoberta'] = 'Sim'
            df.at[idx, 'status_qualificacao'] = 'Sim'
        elif status_found.get('status_em_atendimento', False):
            # Se em atendimento, descoberta e qualificação são 'Sim'
            df.at[idx, 'status_em_atendimento'] = 'Sim'
            df.at[idx, 'status_descoberta'] = 'Sim'
            df.at[idx, 'status_qualificacao'] = 'Sim'
        elif status_found.get('status_descoberta', False):
            # Se descoberta, qualificação é 'Sim'
            df.at[idx, 'status_descoberta'] = 'Sim'
            df.at[idx, 'status_qualificacao'] = 'Sim'
        elif status_found.get('status_qualificacao', False):
            # Se apenas qualificação
            df.at[idx, 'status_qualificacao'] = 'Sim'
    
    logger.info("Colunas de status criadas com lógica hierárquica aplicada")

    # Criar coluna data_consolidada com fallback
    logger.info("Criando coluna 'data_consolidada' com fallback...")
    
    if 'data_reativacao' in df.columns and 'Data_cad' in df.columns:
        # Inicializar com data_reativacao
        df['data_consolidada'] = df['data_reativacao']
        
        # Aplicar fallback para Data_cad quando data_reativacao estiver vazio
        mask_vazio = (df['data_reativacao'].isna()) | (df['data_reativacao'] == '') | (df['data_reativacao'] == 'NaT')
        df.loc[mask_vazio, 'data_consolidada'] = df.loc[mask_vazio, 'Data_cad']
        
        # Converter para datetime se necessário
        df['data_consolidada'] = pd.to_datetime(df['data_consolidada'], errors='coerce')
        
        logger.info("Coluna 'data_consolidada' criada com fallback para Data_cad")
    else:
        logger.warning("Colunas 'data_reativacao' ou 'Data_cad' não encontradas para criar data_consolidada")

    # Processar outros campos expansíveis se existirem
    campos_expansiveis = []  # Removido campos_adicionais pois já foram processados
    for campo in campos_expansiveis:
        if campo in df.columns:
            # Converter listas para strings separadas por vírgula para armazenamento
            df[campo] = df[campo].apply(lambda x: ', '.join(map(str, x)) if isinstance(x, list) and x else '')
    
    # Log das colunas disponíveis para debug
    logger.info(f"Colunas disponíveis no DataFrame: {list(df.columns)}")
    
    # Log de exemplo das colunas dinâmicas
    colunas_dinamicas = [col for col in df.columns if col.startswith('campo_')]
    if colunas_dinamicas and not df.empty:
        logger.info(f"Exemplos de colunas dinâmicas criadas: {colunas_dinamicas[:5]}")  # Mostrar apenas as primeiras 5
        for col in colunas_dinamicas[:3]:  # Mostrar exemplos das primeiras 3 colunas
            valores_nao_nulos = df[df[col].notna()][col].head(3)
            if not valores_nao_nulos.empty:
                logger.info(f"Exemplos de valores em {col}: {list(valores_nao_nulos)}")
    
    logger.info(f"Dados processados - CV Leads: {len(df)} registros")
    return df

async def obter_dados_cv_leads() -> pd.DataFrame:
    """Obtém todos os dados de leads do CV com paginação automática."""
    logger.info("Buscando dados do CV Leads (todas as páginas)")

    client = CVLeadsAPIClient()
    dados = await client.get_all_leads(
        registros_por_pagina=500,
        imobiliaria_match="Prati",
        include_empty_imobiliaria=True,
        max_paginas=5000,
        sleep_between_calls=0.0
    )

    return processar_dados_cv_leads(dados)

if __name__ == "__main__":
    # Teste da API do CV Leads
    async def test_cv_leads():
        print("=== Testando API CV Leads ===")
        
        try:
            df = await obter_dados_cv_leads()
            
            print(f"Registros encontrados: {len(df)}")
            
            if not df.empty:
                print("\nColunas:", list(df.columns))
                print(df.head())
            
        except Exception as e:
            print(f"Erro no teste: {str(e)}")
    
    asyncio.run(test_cv_leads())



