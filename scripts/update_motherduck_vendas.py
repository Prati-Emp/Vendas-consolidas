#!/usr/bin/env python3
"""
Atualização do MotherDuck com todas as fontes de dados
Integra: Reservas, Workflow, Sienge (vendas realizadas/canceladas), CV Vendas
"""

import asyncio
import os
import pandas as pd
import duckdb
import logging
from datetime import datetime
from typing import Dict, Any

from dotenv import load_dotenv
from config import config_manager
from orchestrator import orchestrator
from data_processor import data_processor

# Importar novas APIs
from sienge_apis import obter_dados_sienge_completos
from cv_vendas_api import obter_dados_cv_vendas

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_motherduck_connection():
    """Cria conexão com MotherDuck"""
    token = os.environ.get('MOTHERDUCK_TOKEN', '').strip()
    
    if not token:
        raise ValueError("MOTHERDUCK_TOKEN não encontrado nas variáveis de ambiente")
    
    # Configurar DuckDB
    duckdb.sql("INSTALL motherduck")
    duckdb.sql("LOAD motherduck")
    
    # Configurar token
    os.environ['motherduck_token'] = token
    
    try:
        conn = duckdb.connect('md:vendas_consolidadas')
        logger.info("Conexão estabelecida com MotherDuck")
        return conn
    except Exception as e:
        logger.error(f"Erro na conexão com MotherDuck: {str(e)}")
        raise

async def obter_todos_dados():
    """Obtém dados somente das novas APIs (Sienge e CV Vendas)"""
    logger.info("Iniciando coleta de dados das novas APIs (Sienge e CV Vendas)")

    dados = {}

    try:
        # Novas APIs (assíncronas)
        logger.info("Coletando dados do Sienge...")
        dados_sienge = await obter_dados_sienge_completos()
        dados.update(dados_sienge)

        logger.info("Coletando dados do CV Vendas...")
        dados_cv = await obter_dados_cv_vendas()
        dados['cv_vendas'] = dados_cv

        # Estatísticas
        for fonte, df in dados.items():
            if isinstance(df, pd.DataFrame):
                logger.info(f"{fonte}: {len(df)} registros")
            else:
                logger.info(f"{fonte}: {len(df)} registros")

        return dados

    except Exception as e:
        logger.error(f"Erro ao coletar dados: {str(e)}")
        raise

def criar_tabelas_motherduck(conn, df_consolidado: pd.DataFrame):
    """Cria/atualiza tabelas no MotherDuck"""
    logger.info("Criando/atualizando tabelas no MotherDuck")
    
    try:
        # Criar schema se não existir
        conn.sql("CREATE SCHEMA IF NOT EXISTS vendas_consolidadas.main")

        # Remover tabelas antigas
        logger.info("Removendo tabelas antigas (apenas novas fontes)...")
        conn.sql("DROP TABLE IF EXISTS vendas_consolidadas.main.vendas_consolidadas")
        conn.sql("DROP TABLE IF EXISTS vendas_consolidadas.main.sienge_vendas_realizadas")
        conn.sql("DROP TABLE IF EXISTS vendas_consolidadas.main.sienge_vendas_canceladas")
        conn.sql("DROP TABLE IF EXISTS vendas_consolidadas.main.cv_vendas")

        # Criar tabela consolidada principal
        logger.info("Criando tabela consolidada...")
        conn.execute("CREATE TABLE vendas_consolidadas.main.vendas_consolidadas AS SELECT * FROM df_consolidado")

        # Criar tabelas individuais por fonte (apenas novas fontes)
        logger.info("Criando tabelas individuais (Sienge e CV Vendas)...")

        # Tabelas do Sienge
        if 'sienge_realizadas' in df_consolidado['fonte'].values:
            df_sienge_realizadas = df_consolidado[df_consolidado['fonte'] == 'sienge_realizadas']
            conn.execute("CREATE TABLE vendas_consolidadas.main.sienge_vendas_realizadas AS SELECT * FROM df_sienge_realizadas")

        if 'sienge_canceladas' in df_consolidado['fonte'].values:
            df_sienge_canceladas = df_consolidado[df_consolidado['fonte'] == 'sienge_canceladas']
            conn.execute("CREATE TABLE vendas_consolidadas.main.sienge_vendas_canceladas AS SELECT * FROM df_sienge_canceladas")

        # Tabela CV Vendas
        if 'cv_vendas' in df_consolidado['fonte'].values:
            df_cv_vendas = df_consolidado[df_consolidado['fonte'] == 'cv_vendas']
            conn.execute("CREATE TABLE vendas_consolidadas.main.cv_vendas AS SELECT * FROM df_cv_vendas")

        # Validar tabelas criadas
        logger.info("Validando tabelas criadas...")
        tabelas = [
            'vendas_consolidadas',
            'sienge_vendas_realizadas',
            'sienge_vendas_canceladas',
            'cv_vendas'
        ]
        
        for tabela in tabelas:
            try:
                count = conn.sql(f"SELECT COUNT(*) as count FROM vendas_consolidadas.main.{tabela}").fetchone()[0]
                logger.info(f"Tabela {tabela}: {count} registros")
            except:
                logger.info(f"Tabela {tabela}: não criada (sem dados)")
        
        logger.info("Tabelas criadas/atualizadas com sucesso!")
        
    except Exception as e:
        logger.error(f"Erro ao criar tabelas: {str(e)}")
        raise

def gerar_relatorio_final(relatorio: Dict[str, Any]):
    """Gera relatório final da atualização"""
    logger.info("=== RELATÓRIO FINAL ===")
    logger.info(f"Total de registros processados: {relatorio['total_registros']}")
    
    if relatorio['por_fonte']:
        logger.info("Registros por fonte:")
        for fonte, count in relatorio['por_fonte'].items():
            logger.info(f"  {fonte}: {count}")
    
    if relatorio['por_tipo']:
        logger.info("Registros por tipo:")
        for tipo, count in relatorio['por_tipo'].items():
            logger.info(f"  {tipo}: {count}")
    
    if relatorio['periodo']['inicio'] and relatorio['periodo']['fim']:
        logger.info(f"Período: {relatorio['periodo']['inicio']} a {relatorio['periodo']['fim']}")
    
    if relatorio['valores']['total_vendas'] > 0:
        logger.info(f"Valor total de vendas: R$ {relatorio['valores']['total_vendas']:,.2f}")
        logger.info(f"Valor médio por venda: R$ {relatorio['valores']['media_venda']:,.2f}")

async def update_motherduck_vendas():
    """Função principal de atualização"""
    start_time = datetime.now()
    logger.info(f"Iniciando atualização do MotherDuck - {start_time}")
    
    try:
        # Carregar variáveis de ambiente
        load_dotenv()
        
        # Verificar configurações
        logger.info("Verificando configurações das APIs...")
        for api_name in config_manager.get_all_configs().keys():
            config = config_manager.get_config(api_name)
            if config:
                logger.info(f"✅ {config.name}: Configurada")
            else:
                logger.warning(f"⚠️ {api_name}: Configuração inválida")
        
        # Obter dados de todas as APIs
        dados = await obter_todos_dados()
        
        # Consolidar dados
        logger.info("Consolidando dados...")
        df_consolidado = data_processor.consolidar_dados(dados)
        
        if df_consolidado.empty:
            logger.warning("Nenhum dado para processar")
            return
        
        # Gerar relatório
        relatorio = data_processor.gerar_relatorio_consolidacao(df_consolidado)
        
        # Conectar ao MotherDuck
        logger.info("Conectando ao MotherDuck...")
        conn = get_motherduck_connection()
        
        # Criar/atualizar tabelas
        criar_tabelas_motherduck(conn, df_consolidado)
        
        # Fechar conexão
        conn.close()
        
        # Imprimir estatísticas do orquestrador
        orchestrator.print_stats()
        
        # Gerar relatório final
        gerar_relatorio_final(relatorio)
        
        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"Atualização concluída com sucesso! Duração: {duration}")
        
    except Exception as e:
        logger.error(f"Erro durante a atualização: {str(e)}")
        raise
    finally:
        try:
            conn.close()
        except:
            pass

if __name__ == "__main__":
    asyncio.run(update_motherduck_vendas())
