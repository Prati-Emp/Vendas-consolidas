#!/usr/bin/env python3
"""
Teste direto da API de Repasses Workflow
"""

import requests
import os
from dotenv import load_dotenv

def main():
    load_dotenv()
    
    email = os.environ.get('CVCRM_EMAIL')
    token = os.environ.get('CVCRM_TOKEN')
    
    print('=== TESTANDO API DIRETAMENTE ===')
    print(f'Email: {email}')
    print(f'Token: {token[:10]}...' if token else 'Token não encontrado')
    
    headers = {
        'accept': 'application/json',
        'content-type': 'application/json',
        'email': email,
        'token': token
    }
    
    url = 'https://prati.cvcrm.com.br/api/v1/cvdw/repasses/workflow/tempo'
    
    try:
        print(f'\nFazendo requisição para: {url}')
        response = requests.get(url, headers=headers, timeout=30)
        print(f'Status: {response.status_code}')
        
        if response.status_code == 200:
            data = response.json()
            print(f'\nTipo de resposta: {type(data)}')
            
            if isinstance(data, dict):
                print(f'Chaves principais: {list(data.keys())}')
                
                # Verificar se há paginação
                if 'total_paginas' in data or 'pagina' in data:
                    print('⚠️ API TEM PAGINAÇÃO - precisamos implementar coleta completa')
                else:
                    print('✅ API SEM PAGINAÇÃO - coletando todos os dados')
                
                # Verificar estrutura dos dados
                if 'dados' in data:
                    dados = data['dados']
                    print(f'Dados encontrados: {len(dados)} registros')
                    if dados:
                        print(f'Primeiro registro: {dados[0]}')
                else:
                    print(f'Dados diretos: {data}')
                    
            elif isinstance(data, list):
                print(f'Lista com {len(data)} registros')
                if data:
                    print(f'Primeiro registro: {data[0]}')
            else:
                print(f'Formato inesperado: {type(data)}')
                
        else:
            print(f'Erro HTTP {response.status_code}: {response.text}')
            
    except Exception as e:
        print(f'Erro na requisição: {e}')

if __name__ == "__main__":
    main()





