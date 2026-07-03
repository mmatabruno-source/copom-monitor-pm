# Quickstart: Validação da feature 003

Pré-requisito: `pip install -r requirements.txt` já executado.

## 1. Suíte de testes automatizada

```bash
python -m pytest -q
```

Deve cobrir: fallback de texto simples no Telegram (US1), decisão do watchdog em
todos os cenários (US2 — saudável, atrasado, falhas repetidas, cold start), presença
do link oficial na mensagem 1 de Comunicado e de Ata (US3).

## 2. Validação manual — fallback de formatação (US1)

Simular localmente uma resposta 400 do Telegram com
`"can't parse entities"` no corpo (via mock em teste, não é necessário chamar o
Telegram real) e confirmar que a segunda chamada HTTP no payload não contém a chave
`parse_mode` — ver `tests/unit/test_telegram.py`.

## 3. Validação manual — watchdog (US2)

```bash
GITHUB_REPOSITORY="<owner>/<repo>" GITHUB_TOKEN="<token de teste>" python -m src.watchdog
```

Não é possível validar end-to-end sem esperar o cron real; validar a lógica de decisão
via os testes unitários com resposta mockada da API do GitHub (`tests/unit/test_watchdog.py`),
cobrindo os 4 cenários descritos em `data-model.md`.

## 4. Validação manual — link oficial (US3)

Revisar a `mensagem1` renderizada de um Comunicado e de uma Ata (via teste de
integração ou execução manual local com credenciais de teste) e conferir:
- Termina com `🔗 *Leia na íntegra*: <url>` correta para o tipo.
- O mesmo texto aparece no arquivo `.md` salvo em `historico/`.

## 5. Validação manual — documentação (US4)

```bash
grep -n "Pendências conhecidas" CLAUDE.md
```

Não deve haver ocorrência.

## Critérios de sucesso (spec.md)

- SC-001 a SC-005 confirmados pelos passos acima.
