# Contrato: API do BCB

## Listar Atas (confirmado)

```
GET https://www.bcb.gov.br/api/servico/sitebcb/copom/atas?quantidade=N
```

Resposta esperada (lista, mais recente primeiro ou último — **validar ordenação na
implementação**, não assumir):

```json
[
  {
    "nroReuniao": 268,
    "dataReferencia": "2026-06-17",
    "dataPublicacao": "2026-06-23T08:00:00",
    "titulo": "Ata da 268ª Reunião do Copom"
  }
]
```

## Detalhes da Ata (confirmado)

```
GET https://www.bcb.gov.br/api/servico/sitebcb/copom/atas_detalhes?nro_reuniao=N
```

Resposta esperada:

```json
{
  "nroReuniao": 268,
  "textoAta": "<html estruturado em seções A/B/C/D>",
  "urlPdfAta": "https://www.bcb.gov.br/.../ata268.pdf"
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

**Nota de risco (ainda não resolvida)**: como a listagem e os detalhes de Comunicados
tiveram formato de envelope (`conteudo`) diferente do assumido para Atas, vale também
confirmar se `atas_detalhes` e a listagem de Atas realmente retornam payload bruto (sem
envelope) como documentado acima — essa suposição nunca foi testada de fato contra a API
real, apenas copiada da especificação original do usuário.

## Tratamento de erro (ambos endpoints)

- Timeout ou status HTTP ≥ 500: tratar como falha externa (FR-011) — abortar a
  verificação daquela publicação, sem marcar como processada.
- Status HTTP 4xx: tratar como falha externa também (não assumir formato de payload
  diferente sem validação manual prévia).
