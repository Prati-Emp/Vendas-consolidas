## Ingestão de planilhas do SharePoint para o MotherDuck

### Visão geral
- Lê todas as planilhas (`.xlsx`, `.xls`, `.xlsm`, `.csv`) presentes na pasta sincronizada do SharePoint/OneDrive.
- Cada arquivo vira uma tabela no database `planilhas` do MotherDuck, com o nome derivado do arquivo (ex.: `Acompanhamento Vendas.xlsx` → tabela `acompanhamento_vendas`).
- Mantém um log (`__planilhas_ingest_log`) com caminho, timestamp e quantidade de linhas para evitar reprocessar arquivos que não mudaram.
- Sempre que uma planilha nova é adicionada ou um arquivo existente é alterado, o script recria a tabela correspondente.

### Pré-requisitos
- Pasta sincronizada localmente (via OneDrive/Microsoft Auth). Se ainda não tiver certeza do caminho local, abra o OneDrive, clique com o botão direito na pasta desejada e copie o caminho.
- Defina as variáveis no `.env` ou no ambiente:
  - `MOTHERDUCK_TOKEN`: token já usado pelas outras rotinas.
  - `SHAREPOINT_PLANILHAS_DIR`: caminho completo da pasta com as planilhas (ex.: `C:/Users/SeuUsuario/PratiEmp/Materialatualizaodiria`).
  - (Opcional) `PLANILHAS_DATABASE`: nome do database no MotherDuck (default `planilhas`).
  - (Opcional) `PLANILHAS_CSV_SEPARATOR`: separador padrão para arquivos `.csv` (default `,`).

### Execução manual
```bash
python scripts/planilhas_sharepoint_ingest.py \
  --root "C:/Users/.../SharePoint/Pasta" \
  --include-subdirs \
  --force
```

- Se `--root` não for informado, o script usa `SHAREPOINT_PLANILHAS_DIR`.
- Use `--force` apenas quando quiser reprocessar todos os arquivos.
- Se os arquivos estiverem em subpastas, passe `--include-subdirs`.
- Para CSVs com `;` ou `\t`, configure `PLANILHAS_CSV_SEPARATOR` ou use `--csv-separator`.

### Saída esperada
- Para cada arquivo atualizado é exibido: `Atualizada tabela nome_tabela com X linhas`.
- Ao final, é mostrado o resumo com quantos arquivos foram atualizados, ignorados (sem alteração) e quantos apresentaram erro.
- Em caso de erro, o script retorna código `1`, permitindo que o GitHub Actions marque a execução como falha.

### Agendamento no GitHub Actions
1. No workflow existente (ex.: `update_motherduck_daily.yml`), adicione um novo passo:
   ```yaml
   - name: Ingestão planilhas SharePoint
     run: python scripts/planilhas_sharepoint_ingest.py --include-subdirs
     env:
       MOTHERDUCK_TOKEN: ${{ secrets.MOTHERDUCK_TOKEN }}
       SHAREPOINT_PLANILHAS_DIR: ${{ secrets.SHAREPOINT_PLANILHAS_DIR }}
   ```
2. Ajuste o cron do workflow para rodar duas vezes ao dia (por exemplo `0 6,18 * * *`) ou crie um workflow dedicado.
3. Se preferir rodar apenas essa rotina, basta criar um arquivo `.github/workflows/planilhas_sharepoint.yml` e apontar para o mesmo comando.

### Dicas adicionais
- Mantenha todos os arquivos dentro de uma única pasta; fica mais simples garantir que tudo será processado.
- Use nomes de arquivo únicos – se dois arquivos tiverem nomes iguais (até a extensão), o script acrescenta `_2`, `_3`, etc. ao nome da tabela.
- Para reinicializar o controle de mudanças, delete a tabela `__planilhas_ingest_log` no MotherDuck ou execute o script com `--force`.


