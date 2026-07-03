# Implementation Plan: Melhorias Operacionais e de Confiabilidade do Monitor

**Branch**: `003-melhorias-operacionais-confiabilidade` | **Date**: 2026-07-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/003-melhorias-operacionais-confiabilidade/spec.md`

## Summary

Quatro melhorias pontuais e independentes no monitor já existente, sem alterar sua
arquitetura: (1) garantir que uma notificação nunca seja perdida por erro de
formatação Markdown do Telegram, reenviando o bloco rejeitado em texto simples; (2)
criar um watchdog diário, via novo workflow do GitHub Actions, que consulta o
histórico de execuções do workflow principal e alerta via Telegram se o monitoramento
parar de rodar ou falhar repetidamente; (3) incluir um link oficial do BCB ao final da
mensagem 1 de Comunicado e de Ata; (4) corrigir o `CLAUDE.md` para remover a pendência
já resolvida sobre o endpoint de Comunicados.

## Technical Context

**Language/Version**: Python 3.12 (inalterado)

**Primary Dependencies**: `requests==2.34.2` (já em uso, reaproveitado pelo watchdog
para consultar a API do GitHub). Nenhuma dependência nova.

**Storage**: Inalterado — arquivos em `historico/` + `estado.json` no próprio
repositório Git (Princípio II). O watchdog não persiste estado próprio: consulta o
histórico de execuções diretamente na API do GitHub Actions a cada checagem, evitando
qualquer novo arquivo de estado.

**Testing**: `pytest==9.1.1` com `unittest.mock`, seguindo o padrão já usado em
`tests/unit/test_telegram.py` e `tests/unit/test_bcb_client.py`.

**Target Platform**: GitHub Actions runner (`ubuntu-latest`), inalterado. O watchdog
roda como um segundo workflow agendado no mesmo repositório.

**Project Type**: Script/CLI único, sem interface — inalterado.

**Performance Goals**: Não aplicável — mesma natureza de baixo volume dos features
001/002.

**Constraints**: Nenhuma dependência nova (Princípio VII); nenhuma mudança de custo
(Princípio I — a API de execuções do GitHub Actions é gratuita e já usada pelo próprio
runner via `GITHUB_TOKEN` padrão); o comportamento de idempotência existente
(Princípio IV) não pode regredir.

**Scale/Scope**: Escopo inteiramente dentro dos módulos `src/` já existentes, mais um
módulo novo pequeno (`src/watchdog.py`) e um workflow novo (`watchdog.yml`).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio/Restrição | Avaliação |
|---|---|
| I. Stack Mínimo e Custo Zero | PASS — nenhuma dependência nova; watchdog usa `requests` (já em uso) e a API do GitHub Actions, gratuita via `GITHUB_TOKEN` padrão do runner |
| II. Armazenamento em Arquivos | PASS — nenhum novo arquivo de estado; o watchdog consulta a API do GitHub em vez de manter estado próprio, e não altera `historico/`/`estado.json` |
| III. Segredos Nunca em Texto Plano | PASS — nenhuma mudança; `GITHUB_TOKEN` do watchdog é o token padrão injetado pelo próprio Actions, nunca versionado |
| IV. Idempotência e Resiliência | PASS — o fallback de texto simples (US1) e o watchdog (US2) reforçam a garantia central (nenhuma decisão perdida), sem alterar a lógica de detecção/idempotência de publicações |
| V. Fonte de Verdade é a API | PASS — nenhuma mudança na lógica de detecção de novidade de Comunicado/Ata; o watchdog é ortogonal, só observa o histórico de execuções do próprio workflow |
| VI. Comunicação em Português | PASS — todos os alertas novos (fallback de formatação, watchdog) seguem em português via `notificar_falha` |
| VII. Simplicidade | PASS — fallback de formatação é um `if` adicional em `_enviar_bloco`; watchdog é um script simples de consulta+decisão, sem infraestrutura nova |
| Restrição técnica: limite de mensagem do Telegram | PASS — inalterado |

Nenhuma violação identificada. Nenhuma entrada necessária em Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/003-melhorias-operacionais-confiabilidade/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (contrato da API do GitHub Actions usada pelo watchdog)
└── tasks.md             # Phase 2 output (/speckit-tasks — ainda não criado)
```

### Source Code (repository root)

```text
src/
├── telegram.py           # ALTERADO — fallback para texto simples quando o Telegram
│                          # rejeitar formatação (US1)
├── watchdog.py            # NOVO (US2) — consulta a API do GitHub Actions e decide se
│                          # alerta via notificar_falha
├── notificar_falha.py      # INALTERADO — reaproveitado pelo watchdog
├── analise.py              # INALTERADO
├── main.py                 # ALTERADO — concatena o link oficial ao final da mensagem 1
│                          # de Comunicado e de Ata (US3)
├── bcb_client.py           # INALTERADO
└── estado.py               # INALTERADO

tests/
├── unit/
│   ├── test_telegram.py    # ALTERADO — caso de fallback para texto simples (US1)
│   └── test_watchdog.py    # NOVO (US2) — execução recente/saudável, atrasada, com
│                          # falhas repetidas, e cold start (sem execuções ainda)
└── integration/
    └── test_main_fluxo_completo.py  # ALTERADO — mensagem 1 de Comunicado/Ata contém
                                       # o link oficial correspondente (US3)

.github/workflows/
└── watchdog.yml            # NOVO (US2) — agendamento diário, chama `python -m src.watchdog`

CLAUDE.md                   # ALTERADO — remove a pendência já resolvida sobre o
                             # endpoint de Comunicados (US4)
```

**Structure Decision**: Mesma estrutura de projeto único dos features 001/002 (`src/` +
`tests/unit` + `tests/integration`). Único módulo novo é `src/watchdog.py`, justificado
por ser uma responsabilidade distinta (observar a saúde do próprio agendamento) dos
módulos existentes, que tratam do conteúdo das publicações.

## Complexity Tracking

Nenhuma violação da constituição identificada — seção não aplicável.
