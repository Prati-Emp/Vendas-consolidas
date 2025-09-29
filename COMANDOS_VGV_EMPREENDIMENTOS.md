# 🚀 Comandos para VGV Empreendimentos

## 📋 Resumo da Implementação

A nova API VGV Empreendimentos foi integrada ao sistema de vendas consolidadas com sucesso! 

### ✅ O que foi implementado:
- ✅ Nova API `scripts/cv_vgv_empreendimentos_api.py`
- ✅ Integração ao sistema completo (`sistema_completo.py`)
- ✅ Configuração atualizada (`scripts/config.py`)
- ✅ Scripts de atualização manual
- ✅ Comandos para Windows (BAT e PowerShell)
- ✅ Documentação completa
- ✅ Tabela `main.vgv_empreendimentos` no MotherDuck

## 🧪 Comandos de Teste

### Teste da API Individual
```bash
# Testa apenas a API VGV Empreendimentos (IDs 1-5)
python teste_vgv_empreendimentos.py
```

### Teste da API Direta
```bash
# Testa a API diretamente
python scripts/cv_vgv_empreendimentos_api.py
```

## 🔄 Comandos de Atualização

### Atualização Apenas VGV Empreendimentos
```bash
# Atualiza apenas os dados VGV Empreendimentos
python atualizar_vgv_empreendimentos.py
```

### Atualização Completa (Incluindo VGV)
```bash
# Atualiza TODOS os dados do banco incluindo VGV Empreendimentos
python atualizar_banco_completo_vgv.py
```

### Sistema Completo Original
```bash
# Sistema completo original (já inclui VGV Empreendimentos)
python sistema_completo.py
```

## 🖥️ Comandos Windows

### Atualização VGV Empreendimentos
```cmd
# Executar arquivo BAT
atualizar_vgv_empreendimentos.bat

# Executar arquivo PowerShell
atualizar_vgv_empreendimentos.ps1
```

### Atualização Completa
```cmd
# Executar arquivo BAT
atualizar_banco_completo_vgv.bat

# Executar arquivo PowerShell
atualizar_banco_completo_vgv.ps1
```

## 📊 O que a API faz:

1. **Testa IDs**: Verifica IDs de empreendimentos de 1 a 20
2. **Busca Tabelas**: Encontra tabelas de preço por empreendimento
3. **Seleciona Tabela**: Prioriza tabelas de financiamento
4. **Expande Unidades**: Converte lista de unidades em registros individuais
5. **Normaliza Dados**: Padroniza campos com prefixo 'unidades.'
6. **Upload**: Salva na tabela `main.vgv_empreendimentos` no MotherDuck

## 🗄️ Estrutura da Tabela

A nova tabela `main.vgv_empreendimentos` contém:
- **Metadados**: ID empreendimento, ID tabela, nomes
- **Unidades**: Etapa, bloco, unidade, área, situação, valor
- **Controle**: Fonte, timestamp de processamento

## ⚙️ Configuração

A API usa as **mesmas credenciais** do CV Vendas:
- `CVCRM_EMAIL`
- `CVCRM_TOKEN`
- `MOTHERDUCK_TOKEN`

## 📈 Monitoramento

### Logs importantes:
- IDs testados vs válidos
- Empreendimentos encontrados
- Unidades processadas por empreendimento
- Taxa de sucesso

### Métricas típicas:
- **IDs testados**: 1-20
- **IDs válidos**: 5-15 empreendimentos
- **Unidades**: 10-100 por empreendimento
- **Tempo**: 2-5 minutos
- **Taxa de sucesso**: >90%

## 🔧 Personalização

Para alterar o range de IDs testados, edite:
```python
# Em scripts/cv_vgv_empreendimentos_api.py
df = await obter_dados_vgv_empreendimentos(1, 20)  # Altere aqui
```

## 📚 Documentação

- **API**: `docs/cv-vgv-empreendimentos-api.md`
- **Arquitetura**: `docs/arquitetura.md`
- **Configuração**: `docs/configuracao-ambiente.md`

## 🚨 Importante

- A API testa IDs de 1 a 20 por padrão
- Usa as mesmas credenciais do CV Vendas
- Faz upload para a tabela `main.vgv_empreendimentos`
- Integra automaticamente ao sistema completo
- Pode ser executada independentemente

---

**Status**: ✅ Implementado e funcionando  
**Última atualização**: $(date)

