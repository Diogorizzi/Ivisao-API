---
name: pesquisar-jurisprudencia
description: >
  Use esta skill para pesquisar jurisprudência, legislação, leis, normas e precedentes judiciais.
  Ative sempre que o usuário mencionar: buscar lei, encontrar jurisprudência, base legal, fundamentação
  jurídica, STJ, STF, tribunal, processo, acórdão, decisão judicial, artigo de lei, norma, regulamentação,
  ou pedir respaldo legal para qualquer situação. Mesmo que o usuário não use termos jurídicos formais —
  se ele está pedindo "que lei diz sobre X" ou "já houve decisão sobre Y", use esta skill.
---

# Skill: Pesquisar Jurisprudência

Use quando precisar de fundamentação legal para análises.

## Quando usar

- Precisa embasar argumento jurídico
- Quer encontrar precedentes
- Usuário pede base legal para situação
- Precisa citar legislação específica

## Processo

1. **Identifique o tema**: Qual área do direito?
2. **Busque no RAG**: Documentos jurídicos internos primeiro
3. **Use web_search**: Para jurisprudência atualizada
4. **Filtre resultados**: Tribunais superiores > inferiores
5. **Cite corretamente**: Número do processo, tribunal, data

## REGRAS CRÍTICAS

- ⚠️ NUNCA invente jurisprudência ou números de processo
- ⚠️ Sempre cite fonte completa (tribunal, processo, data)
- ⚠️ Prefira decisões recentes e de tribunais superiores
- ⚠️ Se não encontrar, seja honesto: "Não localizei precedentes"

## Exemplo de output

## Pesquisa: [Tema]

### Legislação Aplicável

- **Lei nº X, de Y** - Art. Z
  > "..."

  **Aplicação:** [Como se aplica ao caso]

### Jurisprudência

#### STJ - Superior Tribunal de Justiça

**1. REsp XXXXXX/SP - Data**
- **Ementa resumida:** [...]
- **Relevância:** Trata especificamente de [...]
- **Conclusão:** Tribunal entendeu que [...]

**2. AgInt no AREsp YYYYYY/RJ - Data**
- **Ementa resumida:** [...]
- **Relevância:** Caso similar em contexto [...]

#### TJ-SP - Tribunal de Justiça de São Paulo

**1. Apelação ZZZZZZ - Data**
- **Ementa resumida:** [...]

### Síntese

Com base na legislação e jurisprudência consultadas:

1. **Entendimento predominante:** [...]
2. **Exceções identificadas:** [...]
3. **Aplicação ao caso:** [...]

### Fontes
- [Links ou referências completas]
