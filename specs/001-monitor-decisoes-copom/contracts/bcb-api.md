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

## Comunicados (NÃO confirmado — pendência técnica)

Hipótese a validar antes de implementar (seguindo o padrão análogo ao de Atas):

```
GET https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados?quantidade=N
GET https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao=N
```

**Ação obrigatória antes de codar `bcb_client.py` para Comunicado**: confirmar via
inspeção manual (ex.: `curl`) a URL exata, o nome dos campos retornados (Selic
resultante, variação, votação podem vir em campos com nomes diferentes do suposto) e o
comportamento em caso de lista vazia ou erro.

## Tratamento de erro (ambos endpoints)

- Timeout ou status HTTP ≥ 500: tratar como falha externa (FR-011) — abortar a
  verificação daquela publicação, sem marcar como processada.
- Status HTTP 4xx: tratar como falha externa também (não assumir formato de payload
  diferente sem validação manual prévia).
