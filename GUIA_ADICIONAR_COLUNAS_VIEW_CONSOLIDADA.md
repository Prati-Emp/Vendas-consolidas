# Guia: Como Adicionar Novas Colunas à View Consolidada de Vendas

## Visão Geral

Este documento descreve o processo completo para adicionar novas colunas da tabela `reservas_abril` à **view consolidada de vendas** `informacoes_consolidadas.sienge_vendas_consolidadas`.

## Estrutura da View Consolidada de Vendas

A **view consolidada de vendas** é composta por 3 seções unidas com `UNION ALL`:

1. **Seção 1:** Vendas Realizadas Sienge (`reservas.sienge_vendas_realizadas`)
2. **Seção 2:** Vendas Canceladas Sienge (`reservas.sienge_vendas_canceladas`)  
3. **Seção 3:** Reservas Vera Cruz (`reservas.cv_vendas_consolidadas_vera_cruz`)

## Relacionamentos Principais

### Chaves de Relacionamento
- **Sienge → Reservas:** `s.id` (Sienge) ↔ `codigointerno` (Reservas)
- **Empreendimento:** `s.enterpriseId` (Sienge) ↔ `codigointerno_empreendimento` (Reservas)
- **Corretor:** `s.brokers[1].id` (Sienge) ↔ `idcorretor` (Reservas)

### Estratégias de Busca
1. **Busca Direta:** `WHERE codigointerno = s.id`
2. **Busca por Corretor:** `WHERE idcorretor = s.brokers[1].id`
3. **Busca por Imobiliaria:** `WHERE idimobiliaria = s.brokers[1].id`

## Processo Passo a Passo

### 1. Investigar a Nova Coluna

```python
# Verificar se a coluna existe na tabela reservas_abril
result = conn.execute("DESCRIBE reservas.reservas_abril").fetchall()
print("Colunas disponíveis:")
for col in columns:
    if 'nome_da_coluna' in col[0].lower():
        print(f"- {col[0]} ({col[1]})")

# Verificar dados da nova coluna
result = conn.execute("""
    SELECT nome_da_coluna, COUNT(*) as total
    FROM reservas.reservas_abril
    WHERE nome_da_coluna IS NOT NULL
    GROUP BY nome_da_coluna
    ORDER BY total DESC
    LIMIT 10
""").fetchall()
```

### 2. Testar Relacionamentos

```python
# Testar busca por codigointerno
result = conn.execute("""
    SELECT 
        s.id,
        s.brokers[1].id as idcorretor,
        (SELECT nome_da_coluna FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as valor_por_codigointerno
    FROM reservas.sienge_vendas_realizadas s
    WHERE s.brokers[1].id IS NOT NULL
    LIMIT 5
""").fetchall()

# Testar busca por idcorretor
result = conn.execute("""
    SELECT 
        s.id,
        s.brokers[1].id as idcorretor,
        (SELECT nome_da_coluna FROM reservas.reservas_abril WHERE idcorretor = s.brokers[1].id LIMIT 1) as valor_por_idcorretor
    FROM reservas.sienge_vendas_realizadas s
    WHERE s.brokers[1].id IS NOT NULL
    LIMIT 5
""").fetchall()
```

### 3. Atualizar a View

#### Para Seções Sienge (1 e 2)

Adicionar a nova coluna usando `COALESCE` para múltiplas estratégias:

```sql
-- NOVA COLUNA ADICIONADA
COALESCE(
    (SELECT nome_da_coluna FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1),
    (SELECT nome_da_coluna FROM reservas.reservas_abril WHERE idcorretor = s.brokers[1].id LIMIT 1),
    (SELECT nome_da_coluna FROM reservas.reservas_abril WHERE idimobiliaria = s.brokers[1].id LIMIT 1)
) as nome_da_coluna
```

#### Para Seção Reservas (3)

Se a coluna já existe na view `cv_vendas_consolidadas_vera_cruz`, apenas referenciar:

```sql
r.nome_da_coluna
```

Se não existe, adicionar à view `cv_vendas_consolidadas_vera_cruz` primeiro.

### 4. Script de Atualização Completo

```python
#!/usr/bin/env python3
"""
Script para adicionar nova coluna à view consolidada
"""

import os
import duckdb
from dotenv import load_dotenv

def conectar_motherduck():
    """Conecta ao MotherDuck"""
    try:
        load_dotenv('.env')
        token = os.getenv('MOTHERDUCK_TOKEN')
        if not token:
            print("ERRO: Token do MotherDuck nao encontrado!")
            return None
        
        print("Conectando ao MotherDuck...")
        conn = duckdb.connect(f'md:?motherduck_token={token}')
        print("Conexao estabelecida com sucesso!")
        return conn
        
    except Exception as e:
        print(f"ERRO na conexao: {e}")
        return None

def adicionar_nova_coluna(conn, nome_coluna):
    """Adiciona nova coluna à view consolidada"""
    print(f"\nAdicionando coluna: {nome_coluna}")
    
    try:
        # 1. Usar o banco informacoes_consolidadas
        conn.execute("USE informacoes_consolidadas")
        
        # 2. Remover view existente
        conn.execute("DROP VIEW IF EXISTS sienge_vendas_consolidadas")
        
        # 3. Criar view com nova coluna
        sql_view = f"""
        CREATE VIEW sienge_vendas_consolidadas AS
        -- Seção 1: Vendas Realizadas Sienge
        SELECT
            CAST(s.enterpriseId AS INTEGER) as enterpriseId,
            COALESCE(
                (SELECT empreendimento FROM reservas.reservas_abril 
                 WHERE codigointerno_empreendimento = CAST(s.enterpriseId AS INTEGER) 
                 LIMIT 1),
                CASE WHEN s.enterpriseId = '19' THEN 'Ondina II' ELSE 'Sienge Realizada' END
            ) as nome_empreendimento,
            s.value,
            CAST(s.issueDate AS DATE) as issueDate,
            CAST(s.contractDate AS DATE) as contractDate,
            'Sienge Realizada' as origem,
            s.brokers[1].name as corretor,
            COALESCE(
                (SELECT imobiliaria FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1),
                (SELECT imobiliaria FROM reservas.reservas_abril WHERE idcorretor = s.brokers[1].id LIMIT 1),
                (SELECT imobiliaria FROM reservas.reservas_abril WHERE idimobiliaria = s.brokers[1].id LIMIT 1)
            ) as imobiliaria,
            s.customers[1].name as cliente,
            s.customers[1].email as email,
            s.customers[1].addresses[1].city as cidade,
            s.customers[1].addresses[1].zipCode as cep_cliente,
            s.customers[1].profession as profissao,
            s.customers[1].cpf as documento_cliente,
            s.customers[1].id as idcliente,
            s.brokers[1].id as idcorretor,
            (SELECT idimobiliaria FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as idimobiliaria,
            s.customers[1].sex as sexo,
            s.customers[1].civilStatus as estado_civil,
            NULL as idade,
            NULL as renda,
            NULL as situacao_original,
            NULL as data_venda,
            NULL as valor_contrato_com_juros,
            NULL as vencimento,
            NULL as campanha,
            NULL as midia,
            NULL as tipovenda,
            NULL as grupo,
            NULL as regiao,
            NULL as bloco,
            NULL as unidade,
            NULL as etapa,
            -- COLUNAS EXISTENTES
            (SELECT vpl_reserva FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as vpl_reserva,
            (SELECT vpl_tabela FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as vpl_tabela,
            (SELECT idreserva FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as idreserva,
            -- NOVA COLUNA ADICIONADA
            COALESCE(
                (SELECT {nome_coluna} FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1),
                (SELECT {nome_coluna} FROM reservas.reservas_abril WHERE idcorretor = s.brokers[1].id LIMIT 1),
                (SELECT {nome_coluna} FROM reservas.reservas_abril WHERE idimobiliaria = s.brokers[1].id LIMIT 1)
            ) as {nome_coluna}
        FROM reservas.sienge_vendas_realizadas s

        UNION ALL

        -- Seção 2: Vendas Canceladas Sienge
        SELECT
            CAST(s.enterpriseId AS INTEGER) as enterpriseId,
            COALESCE(
                (SELECT empreendimento FROM reservas.reservas_abril 
                 WHERE codigointerno_empreendimento = CAST(s.enterpriseId AS INTEGER) 
                 LIMIT 1),
                CASE WHEN s.enterpriseId = '19' THEN 'Ondina II' ELSE 'Sienge Cancelada' END
            ) as nome_empreendimento,
            s.value,
            CAST(s.issueDate AS DATE) as issueDate,
            CAST(s.contractDate AS DATE) as contractDate,
            'Sienge Cancelada' as origem,
            s.brokers[1].name as corretor,
            COALESCE(
                (SELECT imobiliaria FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1),
                (SELECT imobiliaria FROM reservas.reservas_abril WHERE idcorretor = s.brokers[1].id LIMIT 1),
                (SELECT imobiliaria FROM reservas.reservas_abril WHERE idimobiliaria = s.brokers[1].id LIMIT 1)
            ) as imobiliaria,
            s.customers[1].name as cliente,
            s.customers[1].email as email,
            s.customers[1].addresses[1].city as cidade,
            s.customers[1].addresses[1].zipCode as cep_cliente,
            s.customers[1].profession as profissao,
            s.customers[1].cpf as documento_cliente,
            s.customers[1].id as idcliente,
            s.brokers[1].id as idcorretor,
            (SELECT idimobiliaria FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as idimobiliaria,
            s.customers[1].sex as sexo,
            s.customers[1].civilStatus as estado_civil,
            NULL as idade,
            NULL as renda,
            NULL as situacao_original,
            NULL as data_venda,
            NULL as valor_contrato_com_juros,
            NULL as vencimento,
            NULL as campanha,
            NULL as midia,
            NULL as tipovenda,
            NULL as grupo,
            NULL as regiao,
            NULL as bloco,
            NULL as unidade,
            NULL as etapa,
            -- COLUNAS EXISTENTES
            (SELECT vpl_reserva FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as vpl_reserva,
            (SELECT vpl_tabela FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as vpl_tabela,
            (SELECT idreserva FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1) as idreserva,
            -- NOVA COLUNA ADICIONADA
            COALESCE(
                (SELECT {nome_coluna} FROM reservas.reservas_abril WHERE codigointerno = s.id LIMIT 1),
                (SELECT {nome_coluna} FROM reservas.reservas_abril WHERE idcorretor = s.brokers[1].id LIMIT 1),
                (SELECT {nome_coluna} FROM reservas.reservas_abril WHERE idimobiliaria = s.brokers[1].id LIMIT 1)
            ) as {nome_coluna}
        FROM reservas.sienge_vendas_canceladas s

        UNION ALL

        -- Seção 3: Reservas Vera Cruz
        SELECT
            r.enterpriseId,
            r.nome_empreendimento,
            r.value,
            r.issueDate,
            r.contractDate,
            r.origem,
            r.corretor,
            r.imobiliaria,
            r.cliente,
            r.email,
            r.cidade,
            r.cep_cliente,
            r.renda as profissao,
            r.documento_cliente,
            r.idcliente,
            r.idcorretor,
            r.idimobiliaria,
            r.sexo,
            r.estado_civil,
            r.idade,
            r.renda,
            r.situacao_original,
            r.data_venda,
            r.valor_contrato_com_juros,
            r.vencimento,
            r.campanha,
            r.midia,
            r.tipovenda,
            r.grupo,
            r.regiao,
            r.bloco,
            r.unidade,
            r.etapa,
            -- COLUNAS EXISTENTES
            r.vpl_reserva,
            r.vpl_tabela,
            r.idreserva,
            -- NOVA COLUNA (se existir na view cv_vendas_consolidadas_vera_cruz)
            r.{nome_coluna}
        FROM reservas.cv_vendas_consolidadas_vera_cruz r
        """
        
        conn.execute(sql_view)
        print(f"   View atualizada com coluna {nome_coluna}!")
        
        # 4. Verificar resultado
        result = conn.execute("SELECT COUNT(*) FROM sienge_vendas_consolidadas").fetchone()
        print(f"   Total de registros: {result[0]:,}")
        
        # 5. Verificar nova coluna
        result = conn.execute(f"""
            SELECT 
                COUNT(*) as total,
                COUNT({nome_coluna}) as com_dados
            FROM sienge_vendas_consolidadas
        """).fetchone()
        
        print(f"   Registros com {nome_coluna}: {result[1]:,} de {result[0]:,}")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao adicionar coluna: {e}")
        return False

def main():
    """Funcao principal"""
    print("ADICIONANDO NOVA COLUNA À VIEW CONSOLIDADA")
    print("="*60)
    
    # Substituir pelo nome da nova coluna
    nova_coluna = "nome_da_nova_coluna"
    
    conn = conectar_motherduck()
    if not conn:
        return False
    
    try:
        if not adicionar_nova_coluna(conn, nova_coluna):
            return False
        
        print("\n" + "="*60)
        print("COLUNA ADICIONADA COM SUCESSO!")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"ERRO na execucao: {e}")
        return False
    
    finally:
        if conn:
            conn.close()
            print("\nConexao com MotherDuck encerrada.")

if __name__ == "__main__":
    main()
```

## Checklist para Adicionar Nova Coluna

### ✅ Pré-requisitos
- [ ] Verificar se a coluna existe na tabela `reservas.reservas_abril`
- [ ] Testar relacionamentos (codigointerno, idcorretor, idimobiliaria)
- [ ] Verificar se a coluna já existe na view `cv_vendas_consolidadas_vera_cruz`

### ✅ Implementação
- [ ] Adicionar coluna nas seções 1 e 2 (Sienge) com `COALESCE`
- [ ] Adicionar coluna na seção 3 (Reservas) se necessário
- [ ] Manter ordem das colunas consistente
- [ ] Testar contagem de registros

### ✅ Validação
- [ ] Verificar total de colunas (deve ser 36 + novas colunas)
- [ ] Verificar contagem de registros (deve ser ~1,149)
- [ ] Verificar taxa de preenchimento da nova coluna
- [ ] Testar consultas com a nova coluna

## Estrutura Atual da View (36 colunas)

1. enterpriseId
2. nome_empreendimento
3. value
4. issueDate
5. contractDate
6. origem
7. corretor
8. imobiliaria
9. cliente
10. email
11. cidade
12. cep_cliente
13. profissao
14. documento_cliente
15. idcliente
16. idcorretor
17. idimobiliaria
18. sexo
19. estado_civil
20. idade
21. renda
22. situacao_original
23. data_venda
24. valor_contrato_com_juros
25. vencimento
26. campanha
27. midia
28. tipovenda
29. grupo
30. regiao
31. bloco
32. unidade
33. etapa
34. vpl_reserva
35. vpl_tabela
36. idreserva

## Notas Importantes

- **Sempre usar `COALESCE`** para múltiplas estratégias de busca
- **Manter ordem das colunas** consistente entre as 3 seções
- **Testar relacionamentos** antes de implementar
- **Verificar taxa de preenchimento** após implementação
- **Documentar mudanças** no changelog do projeto

## Troubleshooting

### Problema: "Set operations can only apply to expressions with the same number of result columns"
**Solução:** Verificar se todas as 3 seções têm o mesmo número de colunas na mesma ordem.

### Problema: Coluna retorna NULL para muitos registros
**Solução:** Verificar se o relacionamento está correto e testar outras estratégias de busca.

### Problema: View não é criada no banco correto
**Solução:** Usar `USE informacoes_consolidadas` antes de criar a view.

---

**Última atualização:** Janeiro 2025  
**Versão:** 1.0  
**Autor:** Sistema de Vendas Consolidadas
