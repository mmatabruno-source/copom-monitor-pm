# Contrato: API do GitHub Actions (consumida pelo watchdog)

## Listar execuções do workflow `monitor-copom.yml`

```
GET https://api.github.com/repos/{owner}/{repo}/actions/workflows/monitor-copom.yml/runs?per_page=5
Authorization: Bearer {GITHUB_TOKEN}
Accept: application/vnd.github+json
```

`{owner}/{repo}` é lido de `GITHUB_REPOSITORY` (variável de ambiente padrão do runner).
`{GITHUB_TOKEN}` é o token padrão injetado automaticamente pelo GitHub Actions no
workflow do watchdog — requer `permissions: { actions: read }` no `watchdog.yml`.

**Resposta relevante** (campos usados por `src/watchdog.py`; resposta real tem mais
campos, ignorados):

```json
{
  "workflow_runs": [
    {
      "created_at": "2026-07-01T21:15:03Z",
      "conclusion": "success"
    },
    {
      "created_at": "2026-07-01T18:00:11Z",
      "conclusion": "failure"
    }
  ]
}
```

- `workflow_runs`: lista ordenada da mais recente para a mais antiga (comportamento
  padrão da API, não é necessário reordenar).
- `created_at`: timestamp ISO 8601 UTC de início da execução.
- `conclusion`: `"success"`, `"failure"`, `"cancelled"`, ou `null` se a execução ainda
  estiver em andamento — execuções em andamento (`conclusion: null`) devem ser
  ignoradas na contagem de falhas repetidas (D2, research.md), mas não impedem a
  avaliação de `created_at` da execução mais recente concluída.
- Lista vazia (`workflow_runs: []`): tratado como cold start — nenhum alerta (FR
  correspondente ao Edge Case de `spec.md`).

**Erros**: qualquer resposta HTTP diferente de 200 (ex.: rate limit, token sem
permissão) é tratada como falha de consulta do watchdog — não deve gerar um alerta
falso de "monitoramento parado"; deve apenas logar e encerrar sem alertar nesta
execução (o watchdog roda novamente no dia seguinte).
