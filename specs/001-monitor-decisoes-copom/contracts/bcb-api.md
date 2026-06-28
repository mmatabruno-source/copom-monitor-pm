# Contrato: API do BCB

## Listar Atas (confirmado em 28/06/2026, via navegador)

```
GET https://www.bcb.gov.br/api/servico/sitebcb/copom/atas?quantidade=N
```

Resposta real (mesmo padrão de envelope `"conteudo"` de Comunicados — diferente da
hipótese original, que assumia array na raiz):

```json
{
  "conteudo": [
    {
      "nroReuniao": 279,
      "dataReferencia": "2026-06-17",
      "dataPublicacao": "2026-06-23",
      "titulo": "279ª Reunião - 16-17 junho, 2026"
    }
  ]
}
```

Identificador `nroReuniao` (camelCase) confirmado — diferente de Comunicados
(`nro_reuniao`, snake_case). Não assumir consistência de naming entre os endpoints.

## Detalhes da Ata (confirmado em 28/06/2026, via navegador)

```
GET https://www.bcb.gov.br/api/servico/sitebcb/copom/atas_detalhes?nro_reuniao=N
```

Resposta real (mesmo padrão de envelope — lista de um único item):

```json
{
  "conteudo": [
    {
      "nroReuniao": 279,
      "dataReferencia": "2026-06-17",
      "dataPublicacao": "2026-06-23",
      "titulo": "279ª Reunião - 16-17 junho, 2026",
      "urlPdfAta": "https://www.bcb.gov.br/.../Copom279-not20260617279.pdf",
      "textoAta": "<html estruturado em seções A/B/C/D>"
    }
  ]
}
```

## Listar Comunicados (confirmado em 28/06/2026, via navegador — endpoint bloqueado para
## chamadas automatizadas no ambiente de desenvolvimento)

```
GET https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados?quantidade=N
```

Resposta real (formato **diferente** da hipótese original — atenção às duas diferenças):

```json
{
  "conteudo": [
    {
      "nro_reuniao": 279,
      "dataReferencia": "2026-06-17",
      "titulo": "279ª reunião - Copom reduz a taxa Selic para 14,25% a.a."
    }
  ]
}
```

Diferenças confirmadas em relação à hipótese:
1. A lista vem dentro de uma chave `"conteudo"`, não como array na raiz.
2. O identificador da reunião é `nro_reuniao` (snake_case), e não `nroReuniao`
   (camelCase, como em Atas). **Não assumir consistência de naming entre os dois
   endpoints.**
3. Não há `dataPublicacao` nem campos numéricos de Selic/variação/votação na listagem —
   só `titulo` (texto livre) e `dataReferencia`. Os dados objetivos (Selic resultante,
   variação em p.p., votação) precisam vir do endpoint de detalhes ou ser extraídos do
   `titulo`/texto completo pela análise da Anthropic.

## Detalhes do Comunicado (confirmado em 28/06/2026, via navegador)

```
GET https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao=N
```

Resposta real (mesmo padrão de envelope da listagem — lista dentro de `"conteudo"`):

```json
{
  "conteudo": [
    {
      "nro_reuniao": 279,
      "dataReferencia": "2026-06-17",
      "titulo": "Copom reduz a taxa Selic para 14,25% a.a.",
      "textoComunicado": "<html com texto completo do Comunicado>"
    }
  ]
}
```

Confirmado:
1. Mesmo envelope `"conteudo"` da listagem, também como lista de um único item.
2. Campo de texto completo: `textoComunicado` (HTML), análogo a `textoAta` em Atas.
3. **Não há campos estruturados** de Selic resultante/variação/votação em nenhum dos dois
   endpoints de Comunicado — esses dados existem só como texto livre dentro de
   `textoComunicado`. A extração (decisão objetiva + sinalização) é responsabilidade da
   análise da Anthropic (`gerar_analise_comunicado`), conforme já desenhado em
   `contracts/anthropic-api.md` — nenhuma mudança de arquitetura necessária.

**Nota de risco (resolvida em 28/06/2026)**: confirmado que `atas` e `atas_detalhes`
também usam o envelope `"conteudo"` (não payload bruto, como assumido originalmente).
`src/bcb_client.py` (`listar_atas`, `detalhes_ata`) ajustado para desembrulhar.

## Tratamento de erro (ambos endpoints)

- Timeout ou status HTTP ≥ 500: tratar como falha externa (FR-011) — abortar a
  verificação daquela publicação, sem marcar como processada.
- Status HTTP 4xx: tratar como falha externa também (não assumir formato de payload
  diferente sem validação manual prévia).
