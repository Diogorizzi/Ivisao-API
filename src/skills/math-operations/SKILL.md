---
name: math-operations
description: >
  Use esta skill para realizar cálculos matemáticos que exigem precisão absoluta. Ative sempre que
  o usuário pedir: juros compostos, simulações financeiras, amortizações, cálculos de física ou
  engenharia, estatísticas complexas, equações algébricas, probabilidades, conversões de unidades
  com múltiplas etapas, ou qualquer cálculo onde um erro seria inaceitável. Também ative quando
  o resultado precisar ser verificável — se o usuário disser "quero ter certeza do resultado" ou
  "precisa ser exato", use esta skill em vez de calcular diretamente.
---

# Math Operations Skill

Use esta skill quando precisar resolver equações complexas, fazer matemática financeira, rodar simulações exatas ou fazer cálculos de planilhas.

## Quando usar

- Usuário pede juros compostos com dezenas de iterações.
- Usuário envia cálculos de física, estatística ou engenharia.
- Quando o cálculo não pode ter margem de erro ou alucinação da LLM.

## Processo

1. Leia o problema matemático.
2. Formule as equações.
3. Se for muito complexo, CRIE um script Python usando PythonTools para rodar as variáveis do problema.
4. Execute o código para encontrar a resposta absoluta e precisa.

## Best Practices
- Sempre responda usando PythonTools para obter o resultado. Falhas matemáticas desapontam os usuários.
