#!/usr/bin/env python3
"""
Processador de Dados Unificado
Padroniza e processa dados de todas as fontes (Reservas, Sienge, CV)
"""

import pandas as pd
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import numpy as np

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataProcessor:
    """Processador unificado de dados de todas as fontes"""
    
    def __init__(self):
        self.schema_padrao = self._definir_schema_padrao()
    
    def _definir_schema_padrao(self) -> Dict[str, str]:
        """Define o schema padrão para todos os dados"""
        return {
            # Identificadores
            'id': 'string',
            'id_contrato': 'string',
            'id_cliente': 'string',
            'id_venda': 'string',
            
            # Datas
            'data_venda': 'datetime64[ns]',
            'data_contrato': 'datetime64[ns]',
            'data_cancelamento': 'datetime64[ns]',
            'data_emissao': 'datetime64[ns]',
            'data_viagem': 'datetime64[ns]',
            
            # Valores monetários
            'valor_venda': 'float64',
            'valor_contrato': 'float64',
            'valor_cancelamento': 'float64',
            'valor_comissao': 'float64',
            'valor_imposto': 'float64',
            
            # Informações do cliente
            'nome_cliente': 'string',
            'email_cliente': 'string',
            'telefone_cliente': 'string',
            'cpf_cliente': 'string',
            
            # Informações do produto/serviço
            'produto': 'string',
            'destino': 'string',
            'origem': 'string',
            'categoria': 'string',
            
            # Status e tipo
            'status': 'string',
            'tipo_venda': 'string',
            'fonte': 'string',
            
            # Metadados
            'processado_em': 'datetime64[ns]',
            'referencia_data': 'datetime64[ns]'
        }
    
    def processar_reservas(self, df: pd.DataFrame) -> pd.DataFrame:
        """Processa dados de reservas (API existente)"""
        if df.empty:
            return df
        
        logger.info(f"Processando {len(df)} registros de reservas")
        
        # Mapear colunas existentes para schema padrão
        mapeamento = {
            'referencia_data': 'data_venda',
            'valor_contrato': 'valor_contrato',
            'nome_cliente': 'nome_cliente',
            'email_cliente': 'email_cliente',
            'telefone_cliente': 'telefone_cliente',
            'cpf_cliente': 'cpf_cliente',
            'produto': 'produto',
            'destino': 'destino',
            'origem': 'origem',
            'status': 'status'
        }
        
        # Renomear colunas
        df_processed = df.rename(columns=mapeamento)
        
        # Adicionar colunas padrão
        df_processed['fonte'] = 'reservas'
        df_processed['tipo_venda'] = 'reserva'
        df_processed['processado_em'] = datetime.now()
        
        # Converter tipos
        df_processed = self._converter_tipos(df_processed)
        
        return df_processed
    
    def processar_workflow(self, df: pd.DataFrame) -> pd.DataFrame:
        """Processa dados de workflow (API existente)"""
        if df.empty:
            return df
        
        logger.info(f"Processando {len(df)} registros de workflow")
        
        # Mapear colunas existentes para schema padrão
        mapeamento = {
            'referencia_data': 'data_venda',
            'tempo_processamento': 'tempo_processamento',
            'status_workflow': 'status',
            'etapa_atual': 'etapa_atual'
        }
        
        # Renomear colunas
        df_processed = df.rename(columns=mapeamento)
        
        # Adicionar colunas padrão
        df_processed['fonte'] = 'workflow'
        df_processed['tipo_venda'] = 'workflow'
        df_processed['processado_em'] = datetime.now()
        
        # Converter tipos
        df_processed = self._converter_tipos(df_processed)
        
        return df_processed
    
    def processar_sienge_vendas(self, df: pd.DataFrame, tipo: str) -> pd.DataFrame:
        """Processa dados do Sienge (vendas realizadas ou canceladas)"""
        if df.empty:
            return df
        
        logger.info(f"Processando {len(df)} registros do Sienge - {tipo}")
        
        # Mapear colunas do Sienge para schema padrão
        mapeamento = {
            'id_venda': 'id_venda',
            'data_venda': 'data_venda',
            'data_contrato': 'data_contrato',
            'data_cancelamento': 'data_cancelamento',
            'valor_venda': 'valor_venda',
            'valor_contrato': 'valor_contrato',
            'valor_cancelamento': 'valor_cancelamento',
            'nome_cliente': 'nome_cliente',
            'email_cliente': 'email_cliente',
            'telefone_cliente': 'telefone_cliente',
            'cpf_cliente': 'cpf_cliente',
            'produto': 'produto',
            'destino': 'destino',
            'origem': 'origem',
            'categoria': 'categoria',
            'status': 'status'
        }
        
        # Renomear colunas
        df_processed = df.rename(columns=mapeamento)
        
        # Adicionar colunas padrão
        df_processed['fonte'] = f'sienge_{tipo}'
        df_processed['tipo_venda'] = tipo
        df_processed['processado_em'] = datetime.now()
        
        # Converter tipos
        df_processed = self._converter_tipos(df_processed)
        
        return df_processed
    
    def processar_cv_vendas(self, df: pd.DataFrame) -> pd.DataFrame:
        """Processa dados do relatório de vendas do CV"""
        if df.empty:
            return df
        
        logger.info(f"Processando {len(df)} registros do CV Vendas")
        
        # Mapear colunas do CV para schema padrão
        mapeamento = {
            'id_venda': 'id_venda',
            'data_venda': 'data_venda',
            'data_contrato': 'data_contrato',
            'data_emissao': 'data_emissao',
            'data_viagem': 'data_viagem',
            'valor_venda': 'valor_venda',
            'valor_contrato': 'valor_contrato',
            'valor_comissao': 'valor_comissao',
            'valor_imposto': 'valor_imposto',
            'nome_cliente': 'nome_cliente',
            'email_cliente': 'email_cliente',
            'telefone_cliente': 'telefone_cliente',
            'cpf_cliente': 'cpf_cliente',
            'produto': 'produto',
            'destino': 'destino',
            'origem': 'origem',
            'categoria': 'categoria',
            'status': 'status'
        }
        
        # Renomear colunas
        df_processed = df.rename(columns=mapeamento)
        
        # Adicionar colunas padrão
        df_processed['fonte'] = 'cv_vendas'
        df_processed['tipo_venda'] = 'venda'
        df_processed['processado_em'] = datetime.now()
        
        # Converter tipos
        df_processed = self._converter_tipos(df_processed)
        
        return df_processed
    
    def _converter_tipos(self, df: pd.DataFrame) -> pd.DataFrame:
        """Converte tipos de dados conforme schema padrão"""
        for coluna, tipo in self.schema_padrao.items():
            if coluna in df.columns:
                try:
                    if tipo == 'datetime64[ns]':
                        df[coluna] = pd.to_datetime(df[coluna], errors='coerce')
                    elif tipo == 'float64':
                        df[coluna] = pd.to_numeric(df[coluna], errors='coerce')
                    elif tipo == 'string':
                        df[coluna] = df[coluna].astype(str)
                except Exception as e:
                    logger.warning(f"Erro ao converter coluna {coluna} para {tipo}: {str(e)}")
        
        return df
    
    def consolidar_dados(self, dados: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Consolida dados de todas as fontes em um único DataFrame
        
        Args:
            dados: Dicionário com DataFrames de cada fonte
        """
        logger.info("Consolidando dados de todas as fontes")
        
        dataframes = []
        
        # Processar cada fonte
        if 'reservas' in dados and not dados['reservas'].empty:
            df_reservas = self.processar_reservas(dados['reservas'])
            dataframes.append(df_reservas)
        
        if 'workflow' in dados and not dados['workflow'].empty:
            df_workflow = self.processar_workflow(dados['workflow'])
            dataframes.append(df_workflow)
        
        if 'sienge_vendas_realizadas' in dados and not dados['sienge_vendas_realizadas'].empty:
            df_sienge_realizadas = self.processar_sienge_vendas(dados['sienge_vendas_realizadas'], 'realizadas')
            dataframes.append(df_sienge_realizadas)
        
        if 'sienge_vendas_canceladas' in dados and not dados['sienge_vendas_canceladas'].empty:
            df_sienge_canceladas = self.processar_sienge_vendas(dados['sienge_vendas_canceladas'], 'canceladas')
            dataframes.append(df_sienge_canceladas)
        
        if 'cv_vendas' in dados and not dados['cv_vendas'].empty:
            df_cv_vendas = self.processar_cv_vendas(dados['cv_vendas'])
            dataframes.append(df_cv_vendas)
        
        if not dataframes:
            logger.warning("Nenhum dado para consolidar")
            return pd.DataFrame()
        
        # Concatenar todos os DataFrames
        df_consolidado = pd.concat(dataframes, ignore_index=True, sort=False)
        
        # Adicionar colunas que podem estar faltando
        for coluna in self.schema_padrao.keys():
            if coluna not in df_consolidado.columns:
                if self.schema_padrao[coluna] == 'string':
                    df_consolidado[coluna] = ''
                elif self.schema_padrao[coluna] == 'float64':
                    df_consolidado[coluna] = 0.0
                elif self.schema_padrao[coluna] == 'datetime64[ns]':
                    df_consolidado[coluna] = pd.NaT
        
        # Ordenar por data de venda
        if 'data_venda' in df_consolidado.columns:
            df_consolidado = df_consolidado.sort_values('data_venda', ascending=False)
        
        logger.info(f"Dados consolidados: {len(df_consolidado)} registros de {len(dataframes)} fontes")
        
        return df_consolidado
    
    def gerar_relatorio_consolidacao(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Gera relatório da consolidação de dados"""
        if df.empty:
            return {'total_registros': 0}
        
        relatorio = {
            'total_registros': len(df),
            'por_fonte': df['fonte'].value_counts().to_dict() if 'fonte' in df.columns else {},
            'por_tipo': df['tipo_venda'].value_counts().to_dict() if 'tipo_venda' in df.columns else {},
            'periodo': {
                'inicio': df['data_venda'].min() if 'data_venda' in df.columns else None,
                'fim': df['data_venda'].max() if 'data_venda' in df.columns else None
            },
            'valores': {
                'total_vendas': df['valor_venda'].sum() if 'valor_venda' in df.columns else 0,
                'total_contratos': df['valor_contrato'].sum() if 'valor_contrato' in df.columns else 0,
                'media_venda': df['valor_venda'].mean() if 'valor_venda' in df.columns else 0
            }
        }
        
        return relatorio

# Instância global do processador
data_processor = DataProcessor()

if __name__ == "__main__":
    # Teste do processador
    print("=== Testando Data Processor ===")
    
    # Criar dados de teste
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
    
    df_consolidado = data_processor.consolidar_dados(dados_teste)
    relatorio = data_processor.gerar_relatorio_consolidacao(df_consolidado)
    
    print(f"Registros consolidados: {relatorio['total_registros']}")
    print(f"Por fonte: {relatorio['por_fonte']}")
    print(f"Por tipo: {relatorio['por_tipo']}")
