# Data Model: Melhorias Operacionais e de Confiabilidade do Monitor

Esta feature não introduz nenhuma nova entidade persistida (nenhum arquivo novo em
`historico/` ou campo novo em `estado.json` — ver D2 em `research.md`). As únicas
estruturas de dados relevantes são efêmeras (em memória, durante uma única execução).

## Resultado da checagem de saúde do watchdog (`src/watchdog.py`)

Estrutura interna (não persistida) retornada pela função de decisão do watchdog a
partir da resposta da API do GitHub Actions:

| Campo | Tipo | Descrição |
|---|---|---|
| `deve_alertar` | bool | Se um alerta deve ser enviado nesta checagem |
| `motivo` | str \| None | `"sem_execucao_recente"`, `"falhas_repetidas"` ou `None` |
| `ultima_execucao_em` | str \| None | Timestamp ISO 8601 da execução mais recente, ou `None` se não houver nenhuma (cold start) |

Regras de transição (determinístico, sem estado entre chamadas — ver D2):
- Nenhuma execução retornada pela API → `deve_alertar=False`, `motivo=None`.
- `ultima_execucao_em` com mais de 30h → `deve_alertar=True`, `motivo="sem_execucao_recente"`.
- As últimas 3 execuções todas com `conclusion="failure"` → `deve_alertar=True`,
  `motivo="falhas_repetidas"` (avaliado mesmo se `ultima_execucao_em` estiver dentro do
  prazo).
- Caso contrário → `deve_alertar=False`, `motivo=None`.

## Mensagem 1 (Comunicado e Ata) — campo adicional

Nenhuma nova entidade: a mudança é um sufixo textual fixo, determinado pelo tipo de
publicação (`comunicado` ou `ata`), concatenado ao texto de `mensagem1` já existente
antes do envio e do registro no histórico (ver D4 em `research.md`). Não há novo campo
estruturado em `historico/*/*.json` — o link passa a fazer parte do texto livre já
armazenado em `analise`.
