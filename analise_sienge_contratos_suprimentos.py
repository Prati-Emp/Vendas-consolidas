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
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Configurar matplotlib para português
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False

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
    
    def explorar_estrutura_tabela(self):
        """Explora a estrutura da tabela sienge_contratos_suprimentos"""
        print("\n" + "="*60)
        print("EXPLORAÇÃO DA ESTRUTURA DA TABELA")
        print("="*60)
        
        try:
            # Verificar se a tabela existe
            tables = self.conn.execute("SHOW TABLES").fetchall()
            table_names = [t[0] for t in tables]
            
            if 'sienge_contratos_suprimentos' not in table_names:
                print("ERRO: Tabela 'sienge_contratos_suprimentos' não encontrada!")
                print(f"Tabelas disponíveis: {table_names}")
                return False
            
            # Obter estrutura da tabela
            print("\n1. ESTRUTURA DA TABELA:")
            schema = self.conn.execute("DESCRIBE sienge_contratos_suprimentos").fetchall()
            
            for col in schema:
                print(f"   {col[0]:<30} {col[1]:<20} {col[2] if len(col) > 2 else ''}")
            
            # Contar registros
            print(f"\n2. TOTAL DE REGISTROS: {self.conn.execute('SELECT COUNT(*) FROM sienge_contratos_suprimentos').fetchone()[0]:,}")
            
            # Verificar se existe coluna data_contrato
            columns = [col[0] for col in schema]
            if 'data_contrato' not in columns:
                print("AVISO: Coluna 'data_contrato' não encontrada!")
                print("Colunas disponíveis:", columns)
                return False
            
            return True
            
        except Exception as e:
            print(f"ERRO ao explorar estrutura: {e}")
            return False
    
    def carregar_dados(self):
        """Carrega os dados da tabela"""
        print("\n" + "="*60)
        print("CARREGANDO DADOS")
        print("="*60)
        
        try:
            # Carregar dados completos
            query = """
            SELECT *
            FROM sienge_contratos_suprimentos
            ORDER BY data_contrato DESC
            """
            
            print("Executando consulta...")
            self.df = self.conn.execute(query).df()
            
            print(f"Dados carregados: {len(self.df):,} registros")
            print(f"Colunas: {list(self.df.columns)}")
            
            # Converter data_contrato para datetime
            if 'data_contrato' in self.df.columns:
                self.df['data_contrato'] = pd.to_datetime(self.df['data_contrato'], errors='coerce')
                print(f"Período dos dados: {self.df['data_contrato'].min()} a {self.df['data_contrato'].max()}")
            
            return True
            
        except Exception as e:
            print(f"ERRO ao carregar dados: {e}")
            return False
    
    def analise_temporal(self):
        """Análise temporal baseada na coluna data_contrato"""
        print("\n" + "="*60)
        print("ANÁLISE TEMPORAL")
        print("="*60)
        
        if self.df is None or 'data_contrato' not in self.df.columns:
            print("ERRO: Dados não carregados ou coluna data_contrato não encontrada!")
            return
        
        # Remover registros sem data
        df_temp = self.df.dropna(subset=['data_contrato']).copy()
        print(f"Registros com data válida: {len(df_temp):,}")
        
        # Análise por ano
        print("\n1. DISTRIBUIÇÃO POR ANO:")
        df_temp['ano'] = df_temp['data_contrato'].dt.year
        contratos_por_ano = df_temp['ano'].value_counts().sort_index()
        for ano, count in contratos_por_ano.items():
            print(f"   {ano}: {count:,} contratos")
        
        # Análise por mês (últimos 12 meses)
        print("\n2. ÚLTIMOS 12 MESES:")
        data_limite = df_temp['data_contrato'].max() - timedelta(days=365)
        df_ultimo_ano = df_temp[df_temp['data_contrato'] >= data_limite].copy()
        df_ultimo_ano['mes_ano'] = df_ultimo_ano['data_contrato'].dt.to_period('M')
        
        contratos_por_mes = df_ultimo_ano['mes_ano'].value_counts().sort_index()
        for mes, count in contratos_por_mes.items():
            print(f"   {mes}: {count:,} contratos")
        
        # Análise por trimestre
        print("\n3. DISTRIBUIÇÃO POR TRIMESTRE (último ano):")
        df_ultimo_ano['trimestre'] = df_ultimo_ano['data_contrato'].dt.quarter
        df_ultimo_ano['ano_trimestre'] = df_ultimo_ano['data_contrato'].dt.year.astype(str) + '-Q' + df_ultimo_ano['trimestre'].astype(str)
        
        contratos_por_trimestre = df_ultimo_ano['ano_trimestre'].value_counts().sort_index()
        for trim, count in contratos_por_trimestre.items():
            print(f"   {trim}: {count:,} contratos")
        
        # Tendência mensal
        print("\n4. TENDÊNCIA MENSAL:")
        df_ultimo_ano['mes'] = df_ultimo_ano['data_contrato'].dt.month
        tendencia_mensal = df_ultimo_ano.groupby('mes').size()
        for mes, count in tendencia_mensal.items():
            nome_mes = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 
                       'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'][mes-1]
            print(f"   {nome_mes}: {count:,} contratos")
    
    def explorar_colunas(self):
        """Explora todas as colunas da tabela"""
        print("\n" + "="*60)
        print("EXPLORAÇÃO DAS COLUNAS")
        print("="*60)
        
        if self.df is None:
            print("ERRO: Dados não carregados!")
            return
        
        for col in self.df.columns:
            print(f"\nCOLUNA: {col}")
            print("-" * 40)
            
            # Informações básicas
            print(f"Tipo: {self.df[col].dtype}")
            print(f"Valores únicos: {self.df[col].nunique():,}")
            print(f"Valores nulos: {self.df[col].isnull().sum():,} ({self.df[col].isnull().sum()/len(self.df)*100:.1f}%)")
            
            # Para colunas numéricas
            if self.df[col].dtype in ['int64', 'float64']:
                print(f"Mínimo: {self.df[col].min():,}")
                print(f"Máximo: {self.df[col].max():,}")
                print(f"Média: {self.df[col].mean():.2f}")
                print(f"Mediana: {self.df[col].median():.2f}")
            
            # Para colunas categóricas
            elif self.df[col].dtype == 'object':
                print("Top 5 valores mais frequentes:")
                top_values = self.df[col].value_counts().head()
                for valor, count in top_values.items():
                    print(f"   {valor}: {count:,} ({count/len(self.df)*100:.1f}%)")
            
            # Para colunas de data
            elif 'datetime' in str(self.df[col].dtype):
                print(f"Período: {self.df[col].min()} a {self.df[col].max()}")
    
    def analise_valores_monetarios(self):
        """Analisa colunas com valores monetários"""
        print("\n" + "="*60)
        print("ANÁLISE DE VALORES MONETÁRIOS")
        print("="*60)
        
        if self.df is None:
            print("ERRO: Dados não carregados!")
            return
        
        # Identificar colunas que podem conter valores monetários
        colunas_valores = []
        for col in self.df.columns:
            if any(palavra in col.lower() for palavra in ['valor', 'preco', 'total', 'custo', 'montante']):
                if self.df[col].dtype in ['int64', 'float64']:
                    colunas_valores.append(col)
        
        if not colunas_valores:
            print("Nenhuma coluna de valores monetários identificada.")
            return
        
        for col in colunas_valores:
            print(f"\nCOLUNA: {col}")
            print("-" * 30)
            
            # Remover valores nulos para análise
            valores = self.df[col].dropna()
            if len(valores) == 0:
                print("Todos os valores são nulos.")
                continue
            
            print(f"Registros com valor: {len(valores):,}")
            print(f"Valor total: R$ {valores.sum():,.2f}")
            print(f"Valor médio: R$ {valores.mean():,.2f}")
            print(f"Valor mediano: R$ {valores.median():,.2f}")
            print(f"Valor mínimo: R$ {valores.min():,.2f}")
            print(f"Valor máximo: R$ {valores.max():,.2f}")
            
            # Distribuição por faixas
            print("\nDistribuição por faixas de valor:")
            faixas = pd.cut(valores, bins=5, precision=0)
            distribuicao = faixas.value_counts().sort_index()
            for faixa, count in distribuicao.items():
                print(f"   {faixa}: {count:,} contratos")
    
    def analise_fornecedores(self):
        """Analisa dados relacionados a fornecedores"""
        print("\n" + "="*60)
        print("ANÁLISE DE FORNECEDORES")
        print("="*60)
        
        if self.df is None:
            print("ERRO: Dados não carregados!")
            return
        
        # Identificar colunas relacionadas a fornecedores
        colunas_fornecedor = []
        for col in self.df.columns:
            if any(palavra in col.lower() for palavra in ['fornecedor', 'empresa', 'razao', 'nome']):
                colunas_fornecedor.append(col)
        
        if not colunas_fornecedor:
            print("Nenhuma coluna de fornecedor identificada.")
            return
        
        for col in colunas_fornecedor:
            print(f"\nCOLUNA: {col}")
            print("-" * 30)
            
            valores_unicos = self.df[col].nunique()
            print(f"Fornecedores únicos: {valores_unicos:,}")
            
            if valores_unicos > 0:
                print("\nTop 10 fornecedores por volume de contratos:")
                top_fornecedores = self.df[col].value_counts().head(10)
                for fornecedor, count in top_fornecedores.items():
                    print(f"   {fornecedor}: {count:,} contratos")
    
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
        insights.append(f"📊 VOLUME TOTAL: {total_contratos:,} contratos de suprimentos")
        
        # 2. Análise temporal
        if 'data_contrato' in self.df.columns:
            df_temp = self.df.dropna(subset=['data_contrato'])
            if len(df_temp) > 0:
                periodo_inicio = df_temp['data_contrato'].min()
                periodo_fim = df_temp['data_contrato'].max()
                insights.append(f"📅 PERÍODO: {periodo_inicio.strftime('%d/%m/%Y')} a {periodo_fim.strftime('%d/%m/%Y')}")
                
                # Contratos do último ano
                data_limite = df_temp['data_contrato'].max() - timedelta(days=365)
                contratos_ultimo_ano = len(df_temp[df_temp['data_contrato'] >= data_limite])
                insights.append(f"📈 ÚLTIMO ANO: {contratos_ultimo_ano:,} contratos")
        
        # 3. Análise de valores (se houver colunas monetárias)
        colunas_valores = [col for col in self.df.columns 
                          if any(palavra in col.lower() for palavra in ['valor', 'preco', 'total', 'custo', 'montante'])
                          and self.df[col].dtype in ['int64', 'float64']]
        
        if colunas_valores:
            for col in colunas_valores:
                valores = self.df[col].dropna()
                if len(valores) > 0:
                    insights.append(f"💰 {col.upper()}: Total R$ {valores.sum():,.2f} | Média R$ {valores.mean():,.2f}")
        
        # 4. Análise de fornecedores
        colunas_fornecedor = [col for col in self.df.columns 
                             if any(palavra in col.lower() for palavra in ['fornecedor', 'empresa', 'razao', 'nome'])]
        
        if colunas_fornecedor:
            for col in colunas_fornecedor:
                fornecedores_unicos = self.df[col].nunique()
                insights.append(f"🏢 {col.upper()}: {fornecedores_unicos:,} fornecedores únicos")
        
        # 5. Qualidade dos dados
        colunas_nulas = []
        for col in self.df.columns:
            pct_nulos = self.df[col].isnull().sum() / len(self.df) * 100
            if pct_nulos > 50:
                colunas_nulas.append(f"{col} ({pct_nulos:.1f}% nulos)")
        
        if colunas_nulas:
            insights.append(f"⚠️ ATENÇÃO: Colunas com muitos dados faltantes: {', '.join(colunas_nulas)}")
        
        # Exibir insights
        for insight in insights:
            print(insight)
        
        # Recomendações
        print("\n" + "="*60)
        print("RECOMENDAÇÕES PARA O TIME DE SUPRIMENTOS")
        print("="*60)
        
        recomendacoes = [
            "🔍 Implementar dashboard de acompanhamento mensal dos contratos",
            "📊 Criar relatórios de performance por fornecedor",
            "📈 Estabelecer metas de volume mensal de contratos",
            "💰 Monitorar valores médios por tipo de contrato",
            "📅 Implementar alertas para contratos próximos do vencimento",
            "🏢 Análise de concentração de fornecedores (risco de dependência)",
            "📋 Padronizar campos obrigatórios para melhor qualidade dos dados"
        ]
        
        for i, rec in enumerate(recomendacoes, 1):
            print(f"{i}. {rec}")
    
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
        # 1. Explorar estrutura
        if not analise.explorar_estrutura_tabela():
            return
        
        # 2. Carregar dados
        if not analise.carregar_dados():
            return
        
        # 3. Análise temporal
        analise.analise_temporal()
        
        # 4. Explorar colunas
        analise.explorar_colunas()
        
        # 5. Análise de valores monetários
        analise.analise_valores_monetarios()
        
        # 6. Análise de fornecedores
        analise.analise_fornecedores()
        
        # 7. Gerar insights
        analise.gerar_insights_suprimentos()
        
    except Exception as e:
        print(f"ERRO durante a análise: {e}")
    
    finally:
        # Fechar conexão
        analise.fechar_conexao()

if __name__ == "__main__":
    main()


