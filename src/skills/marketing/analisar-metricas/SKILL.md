---
name: analisar-metricas
description: >
  Use esta skill para analisar métricas, KPIs e resultados de campanhas ou ações de marketing.
  Ative sempre que o usuário enviar dados de campanha ou mencionar: ROI, CTR, CPC, CPM, conversão,
  taxa de clique, impressões, engajamento, alcance, ROAS, custo por lead, performance de anúncio,
  resultados de Google Ads, Meta Ads, ou pedir para avaliar se uma campanha foi bem ou o que melhorar.
  Mesmo perguntas vagas como "minha campanha tá boa?" ou "por que meu ROI está baixo?" devem usar
  esta skill.
---

# Skill: Analisar Métricas de Marketing

Use quando precisar analisar performance de campanhas ou ações de marketing.

## Quando usar

- Usuário envia planilha com métricas
- Pede análise de campanha
- Quer entender ROI/performance
- Precisa de insights sobre o que melhorar

## Processo

1. **Carregue os dados**: Use SmartPandasTools
2. **Identifique KPIs principais**:
   - Impressões, Alcance, Engajamento
   - CTR, CPC, CPM
   - Conversões, ROI
3. **Analise tendências**: Compare períodos, identifique padrões
4. **Calcule métricas derivadas**: CAC, LTV, ROAS
5. **Apresente insights**: Use gráficos (em texto) e tabelas
6. **Recomende ações**: Baseado nos dados

## REGRAS CRÍTICAS

- ⚠️ SEMPRE use SmartPandasTools para cálculos precisos
- ⚠️ Compare com benchmarks do setor quando possível (via web_search)
- ⚠️ Apresente números formatados (%, R$, etc)
- ⚠️ Seja específico nas recomendações

## Exemplo de output

## Análise de Campanha: [Nome]

### Resumo Executivo
- **Investimento Total:** R$ X
- **ROI:** Y%
- **Conversões:** Z

### Métricas por Canal

| Canal | Impressões | CTR | CPC | Conversões | ROI |
|-------|-----------|-----|-----|------------|-----|
| Google Ads | X | Y% | R$ Z | W | A% |
| Meta Ads | X | Y% | R$ Z | W | A% |

### Insights
1. ✅ **Google Ads** teve melhor ROI (X%) vs Meta (Y%)
2. ⚠️ **CTR baixo** em Meta - testar novos criativos
3. ✅ **Conversões** aumentaram 30% vs mês anterior

### Recomendações
1. **Aumentar budget** em Google Ads (+20%)
2. **A/B test** criativos no Meta
3. **Otimizar landing page** (conversão atual: X%, benchmark: Y%)
