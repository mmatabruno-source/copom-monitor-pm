# Implementation Plan: Monitor de Decisões do Copom

**Branch**: `001-monitor-decisoes-copom` | **Date**: 2026-06-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-monitor-decisoes-copom/spec.md`

## Summary

Robô em Python, executado via GitHub Actions (sem servidor dedicado), que consulta
periodicamente a API pública do BCB para detectar novo Comunicado ou nova Ata do
Copom, gera uma análise crítica via API da Anthropic (Claude Sonnet), notifica o
usuário via Telegram e persiste todo o histórico (dados brutos + análise) como
arquivos JSON/Markdown no próprio repositório, commitados automaticamente pela Action.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: `requests` (HTTP para API do BCB, Anthropic e Telegram —
biblioteca padrão de mercado, evita SDKs adicionais para um projeto pequeno).
Alternativa avaliada: SDK oficial `anthropic` — adotado apenas para a chamada à
Anthropic (mensagens estruturadas, contagem de tokens), mantendo `requests` para BCB e
Telegram (APIs REST simples, sem necessidade de SDK dedicado).

**Storage**: Arquivos no próprio repositório Git — `historico/comunicados/*.json|.md`,
`historico/atas/*.json|.md`, `estado.json`. Sem banco de dados externo (Princípio II da
constituição).

**Testing**: `pytest`, com testes de unidade para parsing/extração e testes de
integração com chamadas externas mockadas (sem custo de chamadas reais durante CI).

**Target Platform**: GitHub Actions runner (`ubuntu-latest`), sem servidor dedicado.

**Project Type**: Script/CLI único, sem interface — execução agendada não-interativa.

**Performance Goals**: Não aplicável no sentido tradicional (sem usuários concorrentes);
o requisito relevante é de latência de detecção, já coberto pelo desenho do cron
(SC-001/SC-002 do spec.md), não pela implementação em si.

**Constraints**: Custo de infraestrutura zero (Princípio I); execução serializada — uma
verificação por vez, via `concurrency` do GitHub Actions (FR-014); falha em chamada
externa não pode corromper histórico nem marcar publicação como processada (FR-011,
FR-013); segredos apenas via GitHub Secrets (Princípio III).

**Scale/Scope**: Volume baixíssimo — no máximo ~16 publicações novas por ano (8
Comunicados + 8 Atas), e até ~1300 execuções/ano do workflow (baseline + janelas
densas), todas dentro do tier gratuito do GitHub Actions.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio/Restrição | Avaliação |
|---|---|
| I. Stack Mínimo e Custo Zero | PASS — Python + GitHub Actions + APIs públicas, sem serviço pago |
| II. Armazenamento em Arquivos | PASS — `historico/` + `estado.json`, sem banco externo |
| III. Segredos Nunca em Texto Plano | PASS — `ANTHROPIC_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` via GitHub Secrets |
| IV. Idempotência e Resiliência | PASS — `estado.json` só atualizado após notificação bem-sucedida (FR-010, FR-011) |
| V. Fonte de Verdade é a API | PASS — detecção sempre via comparação de `nroReuniao`; cron usa calendário só como heurística de frequência, nunca gatilho |
| VI. Comunicação em Português | PASS — todas as mensagens do Telegram em português |
| VII. Simplicidade | PASS — sem filas, workers ou frameworks; um único script orquestrado pelo cron |
| Restrição técnica: modelo Claude Sonnet | PASS |
| Restrição técnica: cron de 3 camadas | PASS — implementado como 3 entradas `schedule:` no workflow |
| Restrição técnica: limite de mensagem Telegram | PASS — função de divisão de mensagem em blocos ≤4096 caracteres |

Nenhuma violação identificada. Nenhuma entrada necessária em Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/001-monitor-decisoes-copom/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks — ainda não criado)
```

### Source Code (repository root)

```text
src/
├── bcb_client.py         # Consulta à API do BCB (atas, comunicados) e parsing do payload
├── estado.py             # Leitura/escrita idempotente de estado.json
├── historico.py          # Persistência de .json/.md em historico/comunicados e historico/atas
├── analise.py            # Chamadas à API da Anthropic (resumo de Comunicado, análise de Ata)
├── telegram.py           # Envio de mensagens ao Telegram, incl. divisão por limite de caracteres
├── notificar_falha.py    # Wrapper de notificação de erro via Telegram
└── main.py               # Orquestração: verifica Comunicado e Ata, decide o que processar

tests/
├── unit/
│   ├── test_bcb_client.py
│   ├── test_estado.py
│   ├── test_historico.py
│   └── test_telegram.py
└── integration/
    └── test_main_fluxo_completo.py   # chamadas externas mockadas

.github/workflows/
└── monitor-copom.yml     # 3 entradas de schedule + concurrency + permissions: contents: write

historico/
├── comunicados/
└── atas/

estado.json
```

**Structure Decision**: Projeto Python simples (Option 1 — single project), sem
camadas de API/web. Cada módulo em `src/` tem responsabilidade única e é testável
isoladamente (alinhado ao Princípio VII de simplicidade). `main.py` é o único ponto de
entrada, invocado pelo workflow do GitHub Actions.

## Complexity Tracking

Nenhuma violação da constituição identificada — seção não aplicável.
