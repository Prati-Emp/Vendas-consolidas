#!/usr/bin/env python3
"""
Análise da tabela sienge_vendas_consolidadas
Análise temporal e exploratória para o time de suprimentos
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dotenv import load_dotenv
import duckdb

class AnaliseSiengeVendasConsolidadas:
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
        """Carrega os dados da tabela sienge_vendas_consolidadas"""
        print("\n" + "="*60)
        print("CARREGANDO DADOS DA TABELA SIENGE_VENDAS_CONSOLIDADAS")
        print("="*60)
        
        try:
            # Usar o database correto
            self.conn.execute("USE informacoes_consolidadas")
            
            # Carregar dados completos
            query = """
            SELECT *
            FROM sienge_vendas_consolidadas
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
        print("ANÁLISE TEMPORAL - CONTRATOS DE VENDAS")
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
    
    def analise_valores_contratos(self):
        """Analisa valores dos contratos"""
        print("\n" + "="*60)
        print("ANÁLISE DE VALORES DOS CONTRATOS")
        print("="*60)
        
        if self.df is None:
            print("ERRO: Dados não carregados!")
            return
        
        # Analisar coluna value
        if 'value' in self.df.columns:
            valores = self.df['value'].dropna()
            if len(valores) > 0:
                print(f"\n1. ANÁLISE DA COLUNA 'value':")
                print(f"   Registros com valor: {len(valores):,}")
                print(f"   Valor total: R$ {valores.sum():,.2f}")
                print(f"   Valor médio: R$ {valores.mean():,.2f}")
                print(f"   Valor mediano: R$ {valores.median():,.2f}")
                print(f"   Valor mínimo: R$ {valores.min():,.2f}")
                print(f"   Valor máximo: R$ {valores.max():,.2f}")
        
        # Analisar coluna valor_contrato_com_juros
        if 'valor_contrato_com_juros' in self.df.columns:
            valores_juros = self.df['valor_contrato_com_juros'].dropna()
            if len(valores_juros) > 0:
                print(f"\n2. ANÁLISE DA COLUNA 'valor_contrato_com_juros':")
                print(f"   Registros com valor: {len(valores_juros):,}")
                print(f"   Valor total: R$ {valores_juros.sum():,.2f}")
                print(f"   Valor médio: R$ {valores_juros.mean():,.2f}")
                print(f"   Valor mediano: R$ {valores_juros.median():,.2f}")
                print(f"   Valor mínimo: R$ {valores_juros.min():,.2f}")
                print(f"   Valor máximo: R$ {valores_juros.max():,.2f}")
        
        # Análise temporal de valores
        if 'data_contrato' in self.df.columns and 'value' in self.df.columns:
            df_temp = self.df.dropna(subset=['data_contrato', 'value']).copy()
            if len(df_temp) > 0:
                print(f"\n3. EVOLUÇÃO TEMPORAL DOS VALORES:")
                df_temp['ano'] = df_temp['data_contrato'].dt.year
                valores_por_ano = df_temp.groupby('ano')['value'].agg(['count', 'sum', 'mean']).round(2)
                
                for ano, row in valores_por_ano.iterrows():
                    print(f"   {ano}: {row['count']:,} contratos | Total: R$ {row['sum']:,.2f} | Média: R$ {row['mean']:,.2f}")
    
    def analise_empreendimentos(self):
        """Analisa dados por empreendimento"""
        print("\n" + "="*60)
        print("ANÁLISE POR EMPREENDIMENTO")
        print("="*60)
        
        if self.df is None:
            print("ERRO: Dados não carregados!")
            return
        
        if 'nome_empreendimento' in self.df.columns:
            print("\n1. DISTRIBUIÇÃO POR EMPREENDIMENTO:")
            empreendimentos = self.df['nome_empreendimento'].value_counts()
            print(f"   Total de empreendimentos únicos: {len(empreendimentos)}")
            
            print("\n   Top 10 empreendimentos por volume de contratos:")
            for i, (emp, count) in enumerate(empreendimentos.head(10).items(), 1):
                print(f"   {i:2d}. {emp}: {count:,} contratos")
        
        # Análise por região
        if 'regiao' in self.df.columns:
            print(f"\n2. DISTRIBUIÇÃO POR REGIÃO:")
            regioes = self.df['regiao'].value_counts()
            for regiao, count in regioes.items():
                print(f"   {regiao}: {count:,} contratos")
    
    def analise_imobiliarias(self):
        """Analisa dados por imobiliária"""
        print("\n" + "="*60)
        print("ANÁLISE POR IMOBILIÁRIA")
        print("="*60)
        
        if self.df is None:
            print("ERRO: Dados não carregados!")
            return
        
        if 'imobiliaria' in self.df.columns:
            print("\n1. DISTRIBUIÇÃO POR IMOBILIÁRIA:")
            imobiliarias = self.df['imobiliaria'].value_counts()
            print(f"   Total de imobiliárias únicas: {len(imobiliarias)}")
            
            print("\n   Top 10 imobiliárias por volume de contratos:")
            for i, (imob, count) in enumerate(imobiliarias.head(10).items(), 1):
                print(f"   {i:2d}. {imob}: {count:,} contratos")
        
        # Análise por corretor
        if 'corretor' in self.df.columns:
            print(f"\n2. DISTRIBUIÇÃO POR CORRETOR:")
            corretores = self.df['corretor'].value_counts()
            print(f"   Total de corretores únicos: {len(corretores)}")
            
            print("\n   Top 10 corretores por volume de contratos:")
            for i, (corr, count) in enumerate(corretores.head(10).items(), 1):
                print(f"   {i:2d}. {corr}: {count:,} contratos")
    
    def analise_situacao_contratos(self):
        """Analisa situação dos contratos"""
        print("\n" + "="*60)
        print("ANÁLISE DA SITUAÇÃO DOS CONTRATOS")
        print("="*60)
        
        if self.df is None:
            print("ERRO: Dados não carregados!")
            return
        
        if 'situacao' in self.df.columns:
            print("\n1. DISTRIBUIÇÃO POR SITUAÇÃO:")
            situacoes = self.df['situacao'].value_counts()
            for situacao, count in situacoes.items():
                pct = count / len(self.df) * 100
                print(f"   {situacao}: {count:,} contratos ({pct:.1f}%)")
        
        # Análise por tipo de venda
        if 'tipovenda' in self.df.columns:
            print(f"\n2. DISTRIBUIÇÃO POR TIPO DE VENDA:")
            tipos_venda = self.df['tipovenda'].value_counts()
            for tipo, count in tipos_venda.items():
                pct = count / len(self.df) * 100
                print(f"   {tipo}: {count:,} contratos ({pct:.1f}%)")
    
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
        insights.append(f"VOLUME TOTAL: {total_contratos:,} contratos de vendas")
        
        # 2. Análise temporal
        if 'data_contrato' in self.df.columns:
            df_temp = self.df.dropna(subset=['data_contrato'])
            if len(df_temp) > 0:
                periodo_inicio = df_temp['data_contrato'].min()
                periodo_fim = df_temp['data_contrato'].max()
                insights.append(f"PERÍODO: {periodo_inicio.strftime('%d/%m/%Y')} a {periodo_fim.strftime('%d/%m/%Y')}")
                
                # Contratos do último ano
                data_limite = df_temp['data_contrato'].max() - timedelta(days=365)
                contratos_ultimo_ano = len(df_temp[df_temp['data_contrato'] >= data_limite])
                insights.append(f"ÚLTIMO ANO: {contratos_ultimo_ano:,} contratos")
        
        # 3. Análise de valores
        if 'value' in self.df.columns:
            valores = self.df['value'].dropna()
            if len(valores) > 0:
                insights.append(f"VALOR TOTAL: R$ {valores.sum():,.2f}")
                insights.append(f"VALOR MÉDIO: R$ {valores.mean():,.2f}")
        
        # 4. Análise de empreendimentos
        if 'nome_empreendimento' in self.df.columns:
            empreendimentos_unicos = self.df['nome_empreendimento'].nunique()
            insights.append(f"EMPREENDIMENTOS: {empreendimentos_unicos:,} únicos")
        
        # 5. Análise de imobiliárias
        if 'imobiliaria' in self.df.columns:
            imobiliarias_unicas = self.df['imobiliaria'].nunique()
            insights.append(f"IMOBILIÁRIAS: {imobiliarias_unicas:,} únicas")
        
        # 6. Qualidade dos dados
        colunas_importantes = ['data_contrato', 'value', 'nome_empreendimento', 'imobiliaria', 'situacao']
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
            "Implementar dashboard de acompanhamento mensal dos contratos de vendas",
            "Criar relatórios de performance por empreendimento e imobiliária",
            "Estabelecer metas de volume mensal de contratos",
            "Monitorar valores médios por empreendimento e região",
            "Implementar alertas para contratos próximos do vencimento",
            "Análise de concentração de vendas por imobiliária (risco de dependência)",
            "Padronizar campos obrigatórios para melhor qualidade dos dados",
            "Focar em empreendimentos com maior potencial de vendas",
            "Análise sazonal para planejamento de campanhas",
            "Desenvolver estratégias específicas por região"
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
    print("ANÁLISE DA TABELA SIENGE_VENDAS_CONSOLIDADAS")
    print("Análise temporal e exploratória para o time de suprimentos")
    print("="*80)
    
    # Inicializar análise
    analise = AnaliseSiengeVendasConsolidadas()
    
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
        
        # 4. Análise por empreendimento
        analise.analise_empreendimentos()
        
        # 5. Análise por imobiliária
        analise.analise_imobiliarias()
        
        # 6. Análise de situação
        analise.analise_situacao_contratos()
        
        # 7. Gerar insights
        analise.gerar_insights_suprimentos()
        
    except Exception as e:
        print(f"ERRO durante a análise: {e}")
    
    finally:
        # Fechar conexão
        analise.fechar_conexao()

if __name__ == "__main__":
    main()
