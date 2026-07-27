---
name: revisar-contrato
description: >
  Use esta skill para revisar, analisar ou auditar qualquer tipo de contrato ou documento jurídico.
  Ative sempre que o usuário enviar ou mencionar: contrato, acordo, termo, aditivo, distrato, NDA,
  confidencialidade, compra e venda, prestação de serviço, locação, parceria, ou pedir para verificar
  cláusulas, riscos, obrigações, multas ou condições de qualquer documento legal. Mesmo expressões
  informais como "olha esse contrato pra mim" ou "tem algum problema nesse acordo?" devem acionar
  esta skill.
---

# Skill: Revisar Contrato

Use quando precisar analisar contratos do ponto de vista jurídico.

## Quando usar

- Usuário envia contrato para revisão
- Pede análise de cláusulas específicas
- Quer identificar riscos
- Precisa comparar com modelo padrão

## Processo

1. **Leia o contrato completo**: Use read_file no .md convertido
2. **Identifique estrutura**:
   - Partes (contratante/contratado)
   - Objeto do contrato
   - Obrigações de cada parte
   - Prazo e condições
   - Cláusulas especiais
3. **Analise riscos**: Identifique pontos de atenção
4. **Compare com padrões**: Use RAG para buscar contratos similares
5. **Recomende alterações**: Seja específico e fundamente

## REGRAS CRÍTICAS

- ⚠️ NUNCA invente jurisprudência ou leis
- ⚠️ Sempre cite trechos literais do contrato
- ⚠️ Identifique claramente RISCOS vs RECOMENDAÇÕES
- ⚠️ Se algo está fora da sua competência, informe

## Exemplo de output

## Revisão de Contrato: [Tipo]

### Identificação
- **Contratante:** [Nome/CNPJ]
- **Contratado:** [Nome/CNPJ]
- **Objeto:** [Descrição]
- **Valor:** R$ X
- **Prazo:** [Datas]

### Cláusulas Principais

#### 1. Objeto (Cláusula X)
> "..."

**Análise:** Clara e específica. Sem problemas identificados.

#### 2. Pagamento (Cláusula Y)
> "..."

**Análise:**
- ⚠️ **ATENÇÃO:** Prazo de 90 dias é longo. Recomendar 30 dias.
- ✅ Multa por atraso bem definida (2% + juros)

### Riscos Identificados

🔴 **ALTO RISCO**
1. **Cláusula Z** - Foro exclusivo em cidade distante
   - **Risco:** Dificuldade para ações judiciais
   - **Recomendação:** Alterar para foro da comarca do contratante

🟡 **MÉDIO RISCO**
2. **Cláusula W** - Renovação automática sem aviso prévio
   - **Risco:** Dificulta rescisão
   - **Recomendação:** Incluir aviso prévio de 60 dias

### Recomendações Finais

1. **Obrigatório:** Alterar cláusulas de alto risco
2. **Recomendado:** Revisar prazos de pagamento
3. **Opcional:** Incluir cláusula de confidencialidade
