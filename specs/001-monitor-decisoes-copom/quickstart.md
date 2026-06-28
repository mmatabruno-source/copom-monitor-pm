# Quickstart: Monitor de Decisões do Copom

## Pré-requisitos

- Python 3.12+
- Bot do Telegram criado (token + chat_id) — ver playbook do projeto
- Chave de API da Anthropic
- Repositório com GitHub Secrets configurados: `ANTHROPIC_API_KEY`,
  `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`

## Setup local (desenvolvimento)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...
export TELEGRAM_BOT_TOKEN=...
export TELEGRAM_CHAT_ID=...
```

## Validar o endpoint de Comunicados (pendência técnica, fazer antes de tudo)

```bash
curl -s "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados?quantidade=1"
```

Confirmar manualmente os nomes de campo retornados e ajustar `contracts/bcb-api.md` e
`src/bcb_client.py` de acordo, antes de prosseguir com a implementação do fluxo de
Comunicado.

## Rodar uma verificação manual (sem esperar o cron)

```bash
python -m src.main
```

Comportamento esperado:
- Sem novidade na API: encerra sem alterar `estado.json` nem enviar mensagem.
- Com novidade: gera os arquivos em `historico/`, envia mensagem(ns) ao Telegram e só
  então atualiza `estado.json`.

## Cenário de validação 1 — Primeira execução (sem histórico)

1. Garantir que `estado.json` não existe ou tem ambos os campos `null`.
2. Rodar `python -m src.main`.
3. **Esperado**: a publicação mais recente disponível na API é processada como nova; a
   análise da Ata (se for o caso) omite a comparação com Ata anterior, pois não há base
   de comparação (edge case do spec.md).

## Cenário de validação 2 — Idempotência

1. Rodar `python -m src.main` com uma publicação nova disponível — confirmar que a
   notificação chega ao Telegram e `estado.json` é atualizado.
2. Rodar `python -m src.main` novamente, sem nenhuma publicação nova na API.
3. **Esperado**: nenhuma segunda notificação é enviada (FR-010, SC-003).

## Cenário de validação 3 — Falha simulada

1. Simular falha na chamada à Anthropic (ex.: chave inválida temporária).
2. Rodar `python -m src.main`.
3. **Esperado**: execução aborta sem atualizar `estado.json`; uma mensagem de falha é
   enviada ao Telegram (FR-012); rodar novamente com a chave correta deve reprocessar a
   mesma publicação do zero (FR-011, SC-004).

## Workflow do GitHub Actions

Arquivo: `.github/workflows/monitor-copom.yml` — três `schedule:` (baseline 3h,
densa terça, densa quarta), `concurrency` para execução serializada (FR-014),
`permissions: contents: write` para o commit automático do histórico.
