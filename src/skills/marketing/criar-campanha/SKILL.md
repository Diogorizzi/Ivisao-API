---
name: criar-campanha
description: >
  Use esta skill para criar, planejar ou estruturar campanhas, estratégias e ações de marketing.
  Ative sempre que o usuário mencionar: campanha, lançamento, divulgação, promoção, marketing,
  publicidade, anúncio, estratégia de vendas, plano de comunicação, mídia social, email marketing,
  ou pedir ideias para promover um produto, serviço ou evento. Expressões informais como
  "como faço para divulgar X" ou "quero promover meu negócio" também devem acionar esta skill.
---

# Skill: Criar Campanha de Marketing

Use esta skill quando o usuário pedir para criar, planejar ou estruturar uma campanha de marketing.

## Quando usar

- Usuário pede "crie uma campanha para produto X"
- Quer estratégia de lançamento de produto/serviço
- Precisa de plano de marketing para evento/promoção
- Solicita ideias criativas para divulgação

## Processo

1. **Entenda o objetivo**: Pergunte sobre meta (vendas, awareness, engajamento)
2. **Defina o público-alvo**: Idade, localização, interesses, comportamento
3. **Analise dados disponíveis**: Use o RAG para buscar campanhas anteriores similares
4. **Estruture a campanha**:
   - Mensagem principal (copywriting)
   - Canais (social media, email, ads, etc)
   - Cronograma sugerido
   - Budget estimado (se aplicável)
   - KPIs para medir sucesso
5. **Use web_search** se precisar de referências atuais do mercado
6. **Documente tudo** em formato estruturado (markdown tables)

## Informações que você deve coletar

- Qual produto/serviço?
- Objetivo principal? (ex: aumentar vendas 20%, gerar leads)
- Público-alvo?
- Budget disponível?
- Prazo/duração da campanha?
- Canais preferidos?

## Exemplo de output

### Campanha: [Nome]
**Objetivo:** [Meta clara]
**Público:** [Descrição do target]
**Duração:** [Período]

#### Estratégia
1. Fase 1 - Awareness (semana 1-2)
2. Fase 2 - Consideração (semana 3-4)
3. Fase 3 - Conversão (semana 5-6)

#### Canais e Táticas
| Canal | Ação | Frequência |
|-------|------|------------|
| Instagram | Posts + Stories | 3x/semana |
| Email | Newsletter | 1x/semana |
| Ads | Google + Meta | Diário |

#### KPIs
- Impressões: X
- CTR: Y%
- Conversões: Z

## Best Practices

- Sempre baseie sugestões em dados do RAG quando disponível
- Use exemplos reais de mercado (web search) para validar ideias
- Seja específico em cronogramas e métricas
- Adapte a linguagem ao tom da empresa
