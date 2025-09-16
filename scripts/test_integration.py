#!/usr/bin/env python3
"""
Script de teste para validar toda a integração
Testa configurações, APIs e processamento de dados
"""

import asyncio
import logging
from datetime import datetime

from config import config_manager, get_all_rate_limits
from orchestrator import orchestrator
from data_processor import data_processor
from sienge_apis import SiengeAPIClient
from cv_vendas_api import CVVendasAPIClient

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_configurations():
    """Testa configurações das APIs"""
    logger.info("=== TESTE DE CONFIGURAÇÕES ===")
    
    configs = config_manager.get_all_configs()
    rate_limits = get_all_rate_limits()
    
    print(f"APIs configuradas: {len(configs)}")
    print(f"Limites de taxa: {rate_limits}")
    
    for api_name, config in configs.items():
        if config:
            print(f"✅ {config.name}: OK")
            print(f"   URL: {config.base_url}")
            print(f"   Rate Limit: {config.rate_limit} req/min")
        else:
            print(f"❌ {api_name}: Configuração inválida")
    
    return len([c for c in configs.values() if c]) == len(configs)

async def test_orchestrator():
    """Testa o orquestrador"""
    logger.info("=== TESTE DO ORQUESTRADOR ===")
    
    try:
        # Teste com API de reservas (se configurada)
        config = config_manager.get_config('reservas')
        if config:
            from orchestrator import make_api_request
            result = await make_api_request('reservas', '', {'pagina': 1, 'registros_por_pagina': 5})
            print(f"Teste API Reservas: {'✅ Sucesso' if result['success'] else '❌ Falha'}")
            if not result['success']:
                print(f"   Erro: {result.get('error', 'Desconhecido')}")
        
        # Imprimir estatísticas
        orchestrator.print_stats()
        return True
        
    except Exception as e:
        logger.error(f"Erro no teste do orquestrador: {str(e)}")
        return False

async def test_sienge_apis():
    """Testa APIs do Sienge"""
    logger.info("=== TESTE DAS APIs DO SIENGE ===")
    
    try:
        client = SiengeAPIClient()
        
        # Teste de vendas realizadas
        result_realizadas = await client.get_vendas_realizadas("2024-01-01", "2024-01-31", 1, 10)
        print(f"Vendas Realizadas: {'✅ Sucesso' if result_realizadas['success'] else '❌ Falha'}")
        
        # Teste de vendas canceladas
        result_canceladas = await client.get_vendas_canceladas("2024-01-01", "2024-01-31", 1, 10)
        print(f"Vendas Canceladas: {'✅ Sucesso' if result_canceladas['success'] else '❌ Falha'}")
        
        return result_realizadas['success'] and result_canceladas['success']
        
    except Exception as e:
        logger.error(f"Erro no teste das APIs do Sienge: {str(e)}")
        return False

async def test_cv_vendas_api():
    """Testa API do CV Vendas"""
    logger.info("=== TESTE DA API CV VENDAS ===")
    
    try:
        client = CVVendasAPIClient()
        
        result = await client.get_relatorio_vendas("2024-01-01", "2024-01-31", 1, 10)
        print(f"CV Vendas: {'✅ Sucesso' if result['success'] else '❌ Falha'}")
        
        return result['success']
        
    except Exception as e:
        logger.error(f"Erro no teste da API CV Vendas: {str(e)}")
        return False

def test_data_processor():
    """Testa o processador de dados"""
    logger.info("=== TESTE DO PROCESSADOR DE DADOS ===")
    
    try:
        import pandas as pd
        
        # Dados de teste
        dados_teste = {
            'reservas': pd.DataFrame({
                'referencia_data': ['2024-01-15', '2024-01-16'],
                'valor_contrato': ['R$ 1.000,00', 'R$ 2.000,00'],
                'nome_cliente': ['João Silva', 'Maria Santos']
            }),
            'sienge_vendas_realizadas': pd.DataFrame({
                'data_venda': ['2024-01-15', '2024-01-16'],
                'valor_venda': [1000.0, 2000.0],
                'nome_cliente': ['João Silva', 'Maria Santos']
            })
        }
        
        # Testar consolidação
        df_consolidado = data_processor.consolidar_dados(dados_teste)
        relatorio = data_processor.gerar_relatorio_consolidacao(df_consolidado)
        
        print(f"Consolidação: {'✅ Sucesso' if not df_consolidado.empty else '❌ Falha'}")
        print(f"Registros consolidados: {relatorio['total_registros']}")
        print(f"Por fonte: {relatorio['por_fonte']}")
        
        return not df_consolidado.empty
        
    except Exception as e:
        logger.error(f"Erro no teste do processador: {str(e)}")
        return False

async def run_all_tests():
    """Executa todos os testes"""
    logger.info("Iniciando testes de integração...")
    
    results = {}
    
    # Teste de configurações
    results['configurations'] = await test_configurations()
    
    # Teste do orquestrador
    results['orchestrator'] = await test_orchestrator()
    
    # Teste das APIs do Sienge
    results['sienge_apis'] = await test_sienge_apis()
    
    # Teste da API CV Vendas
    results['cv_vendas_api'] = await test_cv_vendas_api()
    
    # Teste do processador de dados
    results['data_processor'] = test_data_processor()
    
    # Resumo dos resultados
    logger.info("=== RESUMO DOS TESTES ===")
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    for test_name, result in results.items():
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{test_name}: {status}")
    
    print(f"\nResultado: {passed_tests}/{total_tests} testes passaram")
    
    if passed_tests == total_tests:
        print("🎉 Todos os testes passaram! Sistema pronto para uso.")
    else:
        print("⚠️ Alguns testes falharam. Verifique as configurações.")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    asyncio.run(run_all_tests())
