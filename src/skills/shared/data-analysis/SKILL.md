---
name: data-analysis
description: >
  Use esta skill para analisar planilhas, tabelas, arquivos CSV, Excel ou qualquer conjunto de dados.
  Ative sempre que o usuário enviar um arquivo de dados ou mencionar: planilha, Excel, CSV, dados,
  tabela, análise, estatística, média, total, soma, correlação, tendência, relatório numérico, ou
  pedir para calcular, comparar, filtrar ou visualizar informações de dados. Também ative para
  perguntas como "o que esses números mostram", "quais são os maiores valores" ou qualquer cálculo
  que exija precisão matemática sobre um conjunto de dados.
---

# Skill: Data Analysis

Use quando precisar analisar planilhas, CSVs, ou fazer cálculos complexos com dados.

## Quando usar

- Usuário envia planilha Excel/CSV
- Pede estatísticas, médias, correlações
- Quer visualizar tendências ou padrões
- Precisa de cálculos financeiros/matemáticos precisos

## Processo

1. **Carregue os dados**:
   - Excel: `create_pandas_dataframe` com `read_excel`
   - CSV: `create_pandas_dataframe` com `read_csv`

2. **Explore os dados**:
   ```python
   df.head()
   df.info()
   df.describe()
   ```

3. **Análise específica**: Use `run_dataframe_operation` ou crie scripts Python

4. **Apresente insights**: Tabelas markdown + explicações claras

## REGRAS CRÍTICAS

- ⚠️ NUNCA use `read_file` para planilhas Excel
- ⚠️ SEMPRE use `engine='openpyxl'` para .xlsx
- ⚠️ Para cálculos complexos, CRIE um script Python (mais confiável que LLM)

## Exemplo de uso

```python
# 1. Carregar Excel
create_pandas_dataframe(
    dataframe_name="vendas",
    create_using_function="read_excel",
    function_parameters={"io": "data.xlsx", "engine": "openpyxl"}
)

# 2. Analisar
run_dataframe_operation(
    dataframe_name="vendas",
    operation="groupby",
    operation_parameters={"by": "regiao"}
)
```
