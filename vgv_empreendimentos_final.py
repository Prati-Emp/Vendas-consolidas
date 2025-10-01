import requests
import pandas as pd
import time
from typing import Optional, List, Dict

# ===================== CONFIG =====================
BASE_URL_TABELAS = "https://prati.cvcrm.com.br/api/v1/cv/tabelasdepreco"
EMAIL = "odair.santos@grupoprati.com"
TOKEN = "487cd121c6c470d9bdcf66ea63a6797e7a7067e4"

HEADERS = {
    "accept": "application/json",
    "email": EMAIL,
    "token": TOKEN,
}

def testar_ids_empreendimentos(inicio: int = 1, fim: int = 20) -> List[int]:
    """
    Testa IDs de empreendimentos e retorna lista de IDs válidos
    """
    print(f"=== TESTANDO IDs DE {inicio} A {fim} ===")
    ids_validos = []
    
    for id_empreendimento in range(inicio, fim + 1):
        try:
            params = {"idempreendimento": id_empreendimento}
            resp = requests.get(BASE_URL_TABELAS, headers=HEADERS, params=params, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    nome_empreendimento = data[0].get('empreendimento', 'N/A')
                    qtd_tabelas = len(data)
                    print(f"OK ID {id_empreendimento}: {qtd_tabelas} tabelas - {nome_empreendimento}")
                    ids_validos.append(id_empreendimento)
                else:
                    print(f"X ID {id_empreendimento}: 0 tabelas")
            else:
                print(f"X ID {id_empreendimento}: Erro {resp.status_code}")
                
        except Exception as e:
            print(f"X ID {id_empreendimento}: Erro - {e}")
        
        time.sleep(0.3)  # Pausa entre requisições
    
    print(f"\n=== RESUMO ===")
    print(f"IDs válidos encontrados: {ids_validos}")
    return ids_validos

def processar_empreendimento(id_empreendimento: int) -> Optional[Dict]:
    """
    Processa um empreendimento completo
    """
    print(f"\n=== PROCESSANDO ID {id_empreendimento} ===")
    
    try:
        # 1. Buscar tabelas
        params = {"idempreendimento": id_empreendimento}
        resp = requests.get(BASE_URL_TABELAS, headers=HEADERS, params=params, timeout=30)
        
        if resp.status_code != 200:
            print(f"  X Erro ao buscar tabelas: {resp.status_code}")
            return None
        
        tabelas = resp.json()
        if not tabelas:
            print(f"  X Nenhuma tabela encontrada")
            return None
        
        print(f"  OK {len(tabelas)} tabelas encontradas")
        
        # 2. Selecionar tabela de financiamento
        tabelas_financiamento = [
            t for t in tabelas 
            if t.get('tabela', '').lower().find('financiamento') != -1
        ]
        
        if tabelas_financiamento:
            tabela_selecionada = max(tabelas_financiamento, key=lambda x: int(x.get('idtabela', 0)))
            print(f"  OK Tabela de financiamento: ID {tabela_selecionada.get('idtabela')} - {tabela_selecionada.get('tabela')}")
        else:
            tabela_selecionada = tabelas[0]
            print(f"  WARN Nenhuma tabela de financiamento. Usando: ID {tabela_selecionada.get('idtabela')} - {tabela_selecionada.get('tabela')}")
        
        # 3. Buscar dados completos
        id_tabela = tabela_selecionada.get('idtabela')
        params_completos = {
            "idempreendimento": id_empreendimento,
            "idtabela": id_tabela
        }
        
        resp_completos = requests.get(BASE_URL_TABELAS, headers=HEADERS, params=params_completos, timeout=30)
        
        if resp_completos.status_code != 200:
            print(f"  X Erro ao buscar dados completos: {resp_completos.status_code}")
            return None
        
        dados_completos = resp_completos.json()
        print(f"  OK Dados completos encontrados")
        
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
                    
                    print(f"  OK {len(df_final)} unidades expandidas com campos normalizados")
                    
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
                    print(f"  X Erro ao normalizar unidades")
                    return None
            else:
                print(f"  X Nenhuma unidade válida encontrada")
                return None
        else:
            print(f"  X Coluna 'unidades' não encontrada")
            return None
            
    except Exception as e:
        print(f"  X Erro: {e}")
        return None

def salvar_resultados(resultados: List[Dict], nome_arquivo: str = "vgv_empreendimentos_final.xlsx"):
    """
    Salva resultados em Excel
    """
    if not resultados:
        print("Nenhum resultado para salvar")
        return
    
    print(f"\n=== SALVANDO RESULTADOS ===")
    
    with pd.ExcelWriter(nome_arquivo, engine='openpyxl') as writer:
        # Resumo
        df_resumo = pd.DataFrame([
            {
                'ID_Empreendimento': r['id_empreendimento'],
                'Nome_Empreendimento': r['nome_empreendimento'],
                'ID_Tabela': r['id_tabela'],
                'Nome_Tabela': r['nome_tabela'],
                'Total_Unidades': r['total_unidades']
            }
            for r in resultados
        ])
        df_resumo.to_excel(writer, sheet_name='Resumo', index=False)
        
        # Dados de cada empreendimento
        for resultado in resultados:
            sheet_name = f"ID_{resultado['id_empreendimento']}"
            resultado['df_expandido'].to_excel(writer, sheet_name=sheet_name, index=False)
    
    print(f"OK Arquivo salvo: {nome_arquivo}")
    print(f"INFO {len(resultados)} empreendimentos processados")
    
    # Mostrar resumo
    total_unidades = sum(r['total_unidades'] for r in resultados)
    print(f"INFO Total de unidades: {total_unidades}")

def main():
    print("=== VGV EMPREENDIMENTOS - VERSÃO FINAL ===")
    
    # 1. Testar IDs
    ids_validos = testar_ids_empreendimentos(1, 20)
    
    if not ids_validos:
        print("Nenhum ID válido encontrado. Encerrando.")
        return
    
    # 2. Processar empreendimentos
    print(f"\n=== PROCESSANDO {len(ids_validos)} EMPREENDIMENTOS ===")
    resultados = []
    
    for id_empreendimento in ids_validos:
        resultado = processar_empreendimento(id_empreendimento)
        if resultado:
            resultados.append(resultado)
        time.sleep(1)  # Pausa entre requisições
    
    # 3. Salvar resultados
    if resultados:
        salvar_resultados(resultados)
        
        print(f"\n=== RESUMO FINAL ===")
        print(f"IDs testados: {ids_validos}")
        print(f"IDs processados com sucesso: {len(resultados)}")
        print(f"Taxa de sucesso: {len(resultados)/len(ids_validos)*100:.1f}%")
    else:
        print("Nenhum resultado obtido.")

if __name__ == "__main__":
    main()
