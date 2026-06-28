# Contrato: API da Anthropic

**Modelo**: `claude-sonnet-4-6`

**Autenticação**: `ANTHROPIC_API_KEY` via GitHub Secrets (nunca em código).

## Chamada para Comunicado

**Entrada**: texto bruto do Comunicado (decisão, votação, justificativa resumida).

**Saída esperada** (texto estruturado, 2 itens, nesta ordem):
1. Decisão objetiva — Selic resultante, variação em p.p., votação
2. Sinalização (forward guidance) — tom hawkish/dovish/neutro

## Chamada para Ata

**Entrada**:
- Texto completo estruturado da Ata atual (seções A/B/C/D)
- Texto da análise/Ata anterior já processada no histórico (`historico/atas/`), se
  existir — usado apenas para a comparação de tom (item 4); se não existir (primeira
  Ata processada), o prompt omite a instrução de comparação.

**Saída esperada** (texto estruturado, 6 itens, nesta ordem, conforme FR-005):
1. Decisão objetiva — Selic, variação, votação
2. Diagnóstico do Copom — atividade, inflação, expectativas Focus, fiscal, externo
3. Balanço de riscos
4. Sinalização (forward guidance) e o que mudou desde a Ata anterior
5. Leitura por classe de ativo — renda fixa, câmbio, bolsa, crédito privado
6. Sugestão de mensagem ao cliente (2-3 frases)

## Tratamento de erro

Qualquer falha (timeout, rate limit, erro 5xx, resposta vazia) é tratada como falha
externa (FR-011): aborta o processamento daquela publicação sem marcar como
processada; tenta notificar a falha via Telegram (FR-012).
