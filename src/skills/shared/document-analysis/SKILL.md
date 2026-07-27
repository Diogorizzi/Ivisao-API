---
name: document-analysis
description: >
  Use esta skill para analisar, resumir ou extrair informações de documentos enviados pelo usuário.
  Ative sempre que o usuário enviar ou mencionar um arquivo como PDF, Word, apresentação, relatório,
  ou pedir para: ler o documento, resumir, extrair informações específicas, comparar documentos,
  ou responder perguntas sobre o conteúdo de um arquivo. Expressões como "o que diz nesse arquivo",
  "me explica esse relatório", "tem algo importante aqui?" também devem acionar esta skill.
  Diferente de revisar-contrato (que é específico para documentos jurídicos) — esta skill cobre
  qualquer tipo de documento.
---

# Skill: Document Analysis

Use quando precisar analisar documentos complexos.

## Quando usar

- Usuário envia PDF, Word, contrato
- Pede resumo ou análise de documento
- Quer extrair informações específicas
- Precisa comparar documentos

## Processo

1. **Leia o documento**: Use `read_file` no caminho .md fornecido
2. **Entenda a estrutura**: Identifique seções, tópicos principais
3. **Extraia informações**: Foque no que foi pedido
4. **Organize resposta**: Use estrutura clara (markdown)
5. **Cite trechos**: Referencie partes específicas quando relevante

## REGRAS CRÍTICAS

- ⚠️ Para documentos .docx, use o caminho .md convertido
- ⚠️ Sempre cite trechos literais com aspas
- ⚠️ Se documento está incompleto/ilegível, informe
- ⚠️ Não invente informações que não estão no documento

## Exemplo de output

**Documento:** contrato-fornecedor.docx

**Análise:**

### Partes
- Contratante: [Nome]
- Contratado: [Nome]

### Objeto
[Descrição do que está sendo contratado]

### Valor
- Total: R$ X
- Forma de pagamento: [...]

### Prazo
- Início: [data]
- Término: [data]

### Cláusulas Importantes
1. [Cláusula X]: "..." (página Y)
2. [Cláusula Z]: "..." (página W)
