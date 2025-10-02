#!/usr/bin/env python3
"""
Análise da tabela sienge_contratos_suprimentos
Análise temporal e exploratória para o time de suprimentos
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dotenv import load_dotenv
import duckdb

class AnaliseSiengeContratosSuprimentos:
    def __init__(self):
        """Inicializa a análise com conexão ao MotherDuck"""
        self.conn = None
        self.df = None
        self.setup_connection()
    
    def setup_connection(self):
        """Configura conexão com MotherDuck"""
        try:
            # Carregar variáveis de ambiente
            load_dotenv('motherduck_config.env')
            
            # Obter token do MotherDuck
            token = os.getenv('MOTHERDUCK_TOKEN')
            if not token:
                print("ERRO: Token do MotherDuck não encontrado!")
                return False
            
            print("Conectando ao MotherDuck...")
            self.conn = duckdb.connect(f'md:?motherduck_token={token}')
            print("Conexão estabelecida com sucesso!")
            return True
            
        except Exception as e:
            print(f"ERRO na conexão: {e}")
            return False
    
    def carregar_dados(self):
        """Carrega os dados da tabela sienge_contratos_suprimentos"""
        print("\n" + "="*60)
        print("CARREGANDO DADOS DA TABELA SIENGE_CONTRATOS_SUPRIMENTOS")
        print("="*60)
        
        try:
            # Usar o database correto
            self.conn.execute("USE reservas")
            
            # Carregar dados completos
            query = """
            SELECT *
            FROM sienge_contratos_suprimentos
            ORDER BY Data_Contrato DESC
            """
            
            print("Executando consulta...")
            self.df = self.conn.execute(query).df()
            
            print(f"Dados carregados: {len(self.df):,} registros")
            print(f"Colunas: {list(self.df.columns)}")
            
            # Converter Data_Contrato para datetime
            if 'Data_Contrato' in self.df.columns:
                self.df['Data_Contrato'] = pd.to_datetime(self.df['Data_Contrato'], errors='coerce')
                print(f"Período dos dados: {self.df['Data_Contrato'].min()} a {self.df['Data_Contrato'].max()}")
            
            return True
            
        except Exception as e:
            print(f"ERRO ao carregar dados: {e}")
            return False
    
    def analise_temporal(self):
        """Análise temporal baseada na coluna Data_Contrato"""
        print("\n" + "="*60)
        print("ANÁLISE TEMPORAL - CONTRATOS DE SUPRIMENTOS")
        print("="*60)
        
        if self.df is None or 'Data_Contrato' not in self.df.columns:
            print("ERRO: Dados não carregados ou coluna Data_Contrato não encontrada!")
            return
        
        # Remover registros sem data
        df_temp = self.df.dropna(subset=['Data_Contrato']).copy()
        print(f"Registros com data válida: {len(df_temp):,}")
        
        # Análise por ano
        print("\n1. DISTRIBUIÇÃO POR ANO:")
        df_temp['ano'] = df_temp['Data_Contrato'].dt.year
        contratos_por_ano = df_temp['ano'].value_counts().sort_index()
        for ano, count in contratos_por_ano.items():
            print(f"   {ano}: {count:,} contratos")
        
        # Análise por mês (últimos 12 meses)
        print("\n2. ÚLTIMOS 12 MESES:")
        data_limite = df_temp['Data_Contrato'].max() - timedelta(days=365)
        df_ultimo_ano = df_temp[df_temp['Data_Contrato'] >= data_limite].copy()
        df_ultimo_ano['mes_ano'] = df_ultimo_ano['Data_Contrato'].dt.to_period('M')
        
        contratos_por_mes = df_ultimo_ano['mes_ano'].value_counts().sort_index()
        for mes, count in contratos_por_mes.items():
            print(f"   {mes}: {count:,} contratos")
        
        # Análise por trimestre
        print("\n3. DISTRIBUIÇÃO POR TRIMESTRE (último ano):")
        df_ultimo_ano['trimestre'] = df_ultimo_ano['Data_Contrato'].dt.quarter
        df_ultimo_ano['ano_trimestre'] = df_ultimo_ano['Data_Contrato'].dt.year.astype(str) + '-Q' + df_ultimo_ano['trimestre'].astype(str)
        
        contratos_por_trimestre = df_ultimo_ano['ano_trimestre'].value_counts().sort_index()
        for trim, count in contratos_por_trimestre.items():
            print(f"   {trim}: {count:,} contratos")
        
        # Tendência mensal
        print("\n4. TENDÊNCIA MENSAL:")
        df_ultimo_ano['mes'] = df_ultimo_ano['Data_Contrato'].dt.month
        tendencia_mensal = df_ultimo_ano.groupby('mes').size()
        for mes, count in tendencia_mensal.items():
            nome_mes = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 
                       'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'][mes-1]
            print(f"   {nome_mes}: {count:,} contratos")
    
    def analise_valores_contratos(self):
        """Analisa valores dos contratos de suprimentos"""
        print("\n" + "="*60)
        print("ANÁLISE DE VALORES DOS CONTRATOS DE SUPRIMENTOS")
        print("="*60)
        
        if self.df is None:
            print("ERRO: Dados não carregados!")
            return
        
        # Analisar coluna Total_MaoObra
        if 'Total_MaoObra' in self.df.columns:
            valores_mao_obra = self.df['Total_MaoObra'].dropna()
            if len(valores_mao_obra) > 0:
                print(f"\n1. ANÁLISE DA COLUNA 'Total_MaoObra':")
                print(f"   Registros com valor: {len(valores_mao_obra):,}")
                print(f"   Valor total: R$ {valores_mao_obra.sum():,.2f}")
                print(f"   Valor médio: R$ {valores_mao_obra.mean():,.2f}")
                print(f"   Valor mediano: R$ {valores_mao_obra.median():,.2f}")
                print(f"   Valor mínimo: R$ {valores_mao_obra.min():,.2f}")
                print(f"   Valor máximo: R$ {valores_mao_obra.max():,.2f}")
        
        # Analisar coluna Total_Material
        if 'Total_Material' in self.df.columns:
            valores_material = self.df['Total_Material'].dropna()
            if len(valores_material) > 0:
                print(f"\n2. ANÁLISE DA COLUNA 'Total_Material':")
                print(f"   Registros com valor: {len(valores_material):,}")
                print(f"   Valor total: R$ {valores_material.sum():,.2f}")
                print(f"   Valor médio: R$ {valores_material.mean():,.2f}")
                print(f"   Valor mediano: R$ {valores_material.median():,.2f}")
                print(f"   Valor mínimo: R$ {valores_material.min():,.2f}")
                print(f"   Valor máximo: R$ {valores_material.max():,.2f}")
        
        # Calcular valor total do contrato
        if 'Total_MaoObra' in self.df.columns and 'Total_Material' in self.df.columns:
            df_valores = self.df.dropna(subset=['Total_MaoObra', 'Total_Material']).copy()
            if len(df_valores) > 0:
                df_valores['Valor_Total_Contrato'] = df_valores['Total_MaoObra'] + df_valores['Total_Material']
                
                print(f"\n3. ANÁLISE DO VALOR TOTAL DOS CONTRATOS:")
                print(f"   Registros com valores completos: {len(df_valores):,}")
                print(f"   Valor total: R$ {df_valores['Valor_Total_Contrato'].sum():,.2f}")
                print(f"   Valor médio: R$ {df_valores['Valor_Total_Contrato'].mean():,.2f}")
                print(f"   Valor mediano: R$ {df_valores['Valor_Total_Contrato'].median():,.2f}")
                print(f"   Valor mínimo: R$ {df_valores['Valor_Total_Contrato'].min():,.2f}")
                print(f"   Valor máximo: R$ {df_valores['Valor_Total_Contrato'].max():,.2f}")
        
        # Análise temporal de valores
        if 'Data_Contrato' in self.df.columns and 'Total_MaoObra' in self.df.columns:
            df_temp = self.df.dropna(subset=['Data_Contrato', 'Total_MaoObra']).copy()
            if len(df_temp) > 0:
                print(f"\n4. EVOLUÇÃO TEMPORAL DOS VALORES (Mão de Obra):")
                df_temp['ano'] = df_temp['Data_Contrato'].dt.year
                valores_por_ano = df_temp.groupby('ano')['Total_MaoObra'].agg(['count', 'sum', 'mean']).round(2)
                
                for ano, row in valores_por_ano.iterrows():
                    print(f"   {ano}: {row['count']:,} contratos | Total: R$ {row['sum']:,.2f} | Média: R$ {row['mean']:,.2f}")
    
    def analise_fornecedores(self):
        """Analisa dados relacionados a fornecedores"""
        print("\n" + "="*60)
        print("ANÁLISE DE FORNECEDORES")
        print("="*60)
        
        if self.df is None:
            print("ERRO: Dados não carregados!")
            return
        
        # Análise por fornecedor
        if 'Fornecedor' in self.df.columns:
            print("\n1. DISTRIBUIÇÃO POR FORNECEDOR:")
            fornecedores = self.df['Fornecedor'].value_counts()
            print(f"   Total de fornecedores únicos: {len(fornecedores)}")
            
            print("\n   Top 10 fornecedores por volume de contratos:")
            for i, (forn, count) in enumerate(fornecedores.head(10).items(), 1):
                print(f"   {i:2d}. {forn}: {count:,} contratos")
        
        # Análise por empresa
        if 'Empresa' in self.df.columns:
            print(f"\n2. DISTRIBUIÇÃO POR EMPRESA:")
            empresas = self.df['Empresa'].value_counts()
            print(f"   Total de empresas únicas: {len(empresas)}")
            
            print("\n   Top 10 empresas por volume de contratos:")
            for i, (emp, count) in enumerate(empresas.head(10).items(), 1):
                print(f"   {i:2d}. {emp}: {count:,} contratos")
        
        # Análise por responsável
        if 'Responsavel' in self.df.columns:
            print(f"\n3. DISTRIBUIÇÃO POR RESPONSÁVEL:")
            responsaveis = self.df['Responsavel'].value_counts()
            print(f"   Total de responsáveis únicos: {len(responsaveis)}")
            
            print("\n   Top 10 responsáveis por volume de contratos:")
            for i, (resp, count) in enumerate(responsaveis.head(10).items(), 1):
                print(f"   {i:2d}. {resp}: {count:,} contratos")
    
    def analise_status_contratos(self):
        """Analisa status e aprovação dos contratos"""
        print("\n" + "="*60)
        print("ANÁLISE DE STATUS E APROVAÇÃO DOS CONTRATOS")
        print("="*60)
        
        if self.df is None:
            print("ERRO: Dados não carregados!")
            return
        
        # Análise por status
        if 'Status' in self.df.columns:
            print("\n1. DISTRIBUIÇÃO POR STATUS:")
            status = self.df['Status'].value_counts()
            for stat, count in status.items():
                pct = count / len(self.df) * 100
                print(f"   {stat}: {count:,} contratos ({pct:.1f}%)")
        
        # Análise por aprovação
        if 'Aprovacao' in self.df.columns:
            print(f"\n2. DISTRIBUIÇÃO POR APROVAÇÃO:")
            aprovacoes = self.df['Aprovacao'].value_counts()
            for aprov, count in aprovacoes.items():
                pct = count / len(self.df) * 100
                print(f"   {aprov}: {count:,} contratos ({pct:.1f}%)")
        
        # Análise por autorização
        if 'Autorizacao' in self.df.columns:
            print(f"\n3. DISTRIBUIÇÃO POR AUTORIZAÇÃO:")
            autorizacoes = self.df['Autorizacao'].value_counts()
            for aut, count in autorizacoes.items():
                pct = count / len(self.df) * 100
                print(f"   {aut}: {count:,} contratos ({pct:.1f}%)")
    
    def analise_objetos_contratos(self):
        """Analisa objetos dos contratos"""
        print("\n" + "="*60)
        print("ANÁLISE DOS OBJETOS DOS CONTRATOS")
        print("="*60)
        
        if self.df is None:
            print("ERRO: Dados não carregados!")
            return
        
        if 'Objeto' in self.df.columns:
            print("\n1. DISTRIBUIÇÃO POR OBJETO:")
            objetos = self.df['Objeto'].value_counts()
            print(f"   Total de objetos únicos: {len(objetos)}")
            
            print("\n   Top 10 objetos por volume de contratos:")
            for i, (obj, count) in enumerate(objetos.head(10).items(), 1):
                print(f"   {i:2d}. {obj}: {count:,} contratos")
    
    def gerar_insights_suprimentos(self):
        """Gera insights específicos para o time de suprimentos"""
        print("\n" + "="*60)
        print("INSIGHTS PARA O TIME DE SUPRIMENTOS")
        print("="*60)
        
        if self.df is None:
            print("ERRO: Dados não carregados!")
            return
        
        insights = []
        
        # 1. Volume de contratos
        total_contratos = len(self.df)
        insights.append(f"VOLUME TOTAL: {total_contratos:,} contratos de suprimentos")
        
        # 2. Análise temporal
        if 'Data_Contrato' in self.df.columns:
            df_temp = self.df.dropna(subset=['Data_Contrato'])
            if len(df_temp) > 0:
                periodo_inicio = df_temp['Data_Contrato'].min()
                periodo_fim = df_temp['Data_Contrato'].max()
                insights.append(f"PERÍODO: {periodo_inicio.strftime('%d/%m/%Y')} a {periodo_fim.strftime('%d/%m/%Y')}")
                
                # Contratos do último ano
                data_limite = df_temp['Data_Contrato'].max() - timedelta(days=365)
                contratos_ultimo_ano = len(df_temp[df_temp['Data_Contrato'] >= data_limite])
                insights.append(f"ÚLTIMO ANO: {contratos_ultimo_ano:,} contratos")
        
        # 3. Análise de valores
        if 'Total_MaoObra' in self.df.columns and 'Total_Material' in self.df.columns:
            df_valores = self.df.dropna(subset=['Total_MaoObra', 'Total_Material']).copy()
            if len(df_valores) > 0:
                df_valores['Valor_Total'] = df_valores['Total_MaoObra'] + df_valores['Total_Material']
                insights.append(f"VALOR TOTAL CONTRATOS: R$ {df_valores['Valor_Total'].sum():,.2f}")
                insights.append(f"VALOR MÉDIO POR CONTRATO: R$ {df_valores['Valor_Total'].mean():,.2f}")
        
        # 4. Análise de fornecedores
        if 'Fornecedor' in self.df.columns:
            fornecedores_unicos = self.df['Fornecedor'].nunique()
            insights.append(f"FORNECEDORES: {fornecedores_unicos:,} únicos")
        
        # 5. Análise de empresas
        if 'Empresa' in self.df.columns:
            empresas_unicas = self.df['Empresa'].nunique()
            insights.append(f"EMPRESAS: {empresas_unicas:,} únicas")
        
        # 6. Qualidade dos dados
        colunas_importantes = ['Data_Contrato', 'Total_MaoObra', 'Total_Material', 'Fornecedor', 'Status']
        colunas_nulas = []
        for col in colunas_importantes:
            if col in self.df.columns:
                pct_nulos = self.df[col].isnull().sum() / len(self.df) * 100
                if pct_nulos > 20:
                    colunas_nulas.append(f"{col} ({pct_nulos:.1f}% nulos)")
        
        if colunas_nulas:
            insights.append(f"ATENÇÃO: Colunas com dados faltantes: {', '.join(colunas_nulas)}")
        
        # Exibir insights
        for insight in insights:
            print(insight)
        
        # Recomendações
        print("\n" + "="*60)
        print("RECOMENDAÇÕES PARA O TIME DE SUPRIMENTOS")
        print("="*60)
        
        recomendacoes = [
            "Implementar dashboard de acompanhamento mensal dos contratos de suprimentos",
            "Criar relatórios de performance por fornecedor e empresa",
            "Estabelecer metas de volume mensal de contratos",
            "Monitorar valores médios por tipo de contrato e fornecedor",
            "Implementar alertas para contratos próximos do vencimento",
            "Análise de concentração de fornecedores (risco de dependência)",
            "Padronizar campos obrigatórios para melhor qualidade dos dados",
            "Focar em fornecedores com maior potencial de negócios",
            "Análise sazonal para planejamento de compras",
            "Desenvolver estratégias específicas por tipo de objeto",
            "Implementar controle de aprovação e autorização",
            "Criar indicadores de performance por responsável"
        ]
        
        for i, rec in enumerate(recomendacoes, 1):
            print(f"{i:2d}. {rec}")
    
    def fechar_conexao(self):
        """Fecha a conexão com o banco"""
        if self.conn:
            self.conn.close()
            print("\nConexão fechada.")

def main():
    """Função principal"""
    print("ANÁLISE DA TABELA SIENGE_CONTRATOS_SUPRIMENTOS")
    print("Análise temporal e exploratória para o time de suprimentos")
    print("="*80)
    
    # Inicializar análise
    analise = AnaliseSiengeContratosSuprimentos()
    
    if not analise.conn:
        print("ERRO: Não foi possível conectar ao banco de dados!")
        return
    
    try:
        # 1. Carregar dados
        if not analise.carregar_dados():
            return
        
        # 2. Análise temporal
        analise.analise_temporal()
        
        # 3. Análise de valores
        analise.analise_valores_contratos()
        
        # 4. Análise de fornecedores
        analise.analise_fornecedores()
        
        # 5. Análise de status
        analise.analise_status_contratos()
        
        # 6. Análise de objetos
        analise.analise_objetos_contratos()
        
        # 7. Gerar insights
        analise.gerar_insights_suprimentos()
        
    except Exception as e:
        print(f"ERRO durante a análise: {e}")
    
    finally:
        # Fechar conexão
        analise.fechar_conexao()

if __name__ == "__main__":
    main()

