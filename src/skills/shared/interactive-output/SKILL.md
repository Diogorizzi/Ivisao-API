---
name: interactive-output
description: Quando usar formulários interativos (HITL) e blocos de documento exportável
---

# Skill: Interactive Output

Você tem dois mecanismos distintos. Eles nunca se substituem. Nunca se misturam.

---

## Mecanismo 1 — HITL (Formulário Interativo)

**O que é:** uma chamada à ferramenta `emit_interactive_state` que pausa a conversa e exibe um formulário visual interativo para o usuário preencher. As respostas voltam no `session_state` do próximo run.

**Quando usar:** sempre que você precisar coletar variáveis antes de gerar algo.

**Gatilhos obrigatórios:**
- Usuário pede para criar conteúdo sem dar contexto suficiente: roteiro, campanha, proposta, estratégia, plano, email, script, copy, apresentação, análise personalizada
- Usuário pede para "fazer perguntas", "me entrevistar", "coletar informações", "me guiar"
- Você percebe que, sem mais dados, o output seria genérico

**Regra absoluta:** se o usuário pediu perguntas → use `emit_interactive_state`. NUNCA escreva perguntas como texto de chat. NUNCA use `\`\`\`document` para listar perguntas.

**Quando NÃO usar:**
- O usuário já forneceu contexto suficiente
- É uma pergunta direta com resposta objetiva
- É conversa ou explicação

### Fluxo HITL — passo a passo

**Run 1 — sem session_state ou `answers` vazio:**
Chame `emit_interactive_state` com suas perguntas. Não gere nenhum conteúdo. Apenas o formulário.

**Run 2+ — session_state contém `answers`:**
O sistema injeta no seu contexto:
```
<session_state>
{'interactive': True, 'answers': {'1': 'Resposta 1', '2': 'Resposta 2', ...}}
</session_state>
```
Leia as respostas. Se precisar de mais dados → novo `emit_interactive_state` com as respostas acumuladas no campo `answers`. Se já tem tudo → gere o output final.

**NUNCA repita perguntas já respondidas.**
**NUNCA gere conteúdo final antes de ter as respostas necessárias.**

### Estrutura da chamada

```
emit_interactive_state(
    type="form",           # "form" para 5+ perguntas, "single_step" para 1-2
    batch=1,               # número do batch atual
    total_batches=2,       # total de batches planejados
    steps=[
        {
            "step": 1,
            "title": "Texto da pergunta",
            "type": "single_choice",          # ou "multiple_choice" ou "text_input"
            "options": ["Opção A", "Opção B"]  # null para text_input
        },
        {
            "step": 2,
            "title": "Outra pergunta",
            "type": "text_input",
            "options": null,
            "placeholder": "Digite aqui..."
        }
    ],
    answers={}             # {} no primeiro batch; acumulado nos seguintes
)
```

Regras dos steps:
- Máximo 5 steps por chamada
- `single_choice`: usuário escolhe 1 — forneça `options`
- `multiple_choice`: usuário escolhe N — forneça `options` e opcionalmente `max_selections`
- `text_input`: usuário digita — `options` deve ser `null`, use `placeholder`

---

## Mecanismo 2 — Documento Exportável

**O que é:** um bloco de código com a linguagem `document`. O frontend detecta e exibe com botões de exportar (DOCX, PDF).

**Quando usar:** quando o output final é um documento formal que o usuário pode querer exportar.

**Gatilhos:**
- Usuário pede: "gera um documento", "relatório", "roteiro", "proposta comercial", "contrato", "apresentação", "exportar", "PDF", "DOCX"
- O output tem mais de 3 seções e é um entregável final — não uma resposta de chat

**Quando NÃO usar:**
- Para fazer perguntas ao usuário → use HITL
- Para respostas conversacionais, listas simples, explicações
- Enquanto ainda está coletando informações

### Formato

    ```document
    # Título do Documento

    ## Seção 1
    Conteúdo completo e pronto para publicação.

    ## Seção 2
    ...
    ```

Escreva o conteúdo completo e final — nunca um esqueleto ou resumo.

---

## Regra de ouro — nunca confunda os dois

| Situação | Ação correta |
|---|---|
| Usuário quer criar algo mas não deu contexto | `emit_interactive_state` |
| Usuário pediu para fazer perguntas | `emit_interactive_state` |
| Usuário respondeu o formulário, quer o resultado | Gere o output — use `\`\`\`document` se for exportável |
| Usuário quer um relatório/proposta diretamente | `\`\`\`document` |
| Conversa normal, pergunta direta | Resposta de texto simples |

**Perguntas nunca vão em `\`\`\`document`. Documentos nunca são formulários interativos.**
