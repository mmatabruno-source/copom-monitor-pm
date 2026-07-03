---

description: "Task list for feature implementation"
---

# Tasks: Melhorias Operacionais e de Confiabilidade do Monitor

**Input**: Design documents from `/specs/003-melhorias-operacionais-confiabilidade/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Incluídos — mesmo padrão de cobertura já estabelecido pelo feature 002
(todo módulo novo/alterado ganha teste unitário; fluxo ponta a ponta coberto por
`tests/integration/test_main_fluxo_completo.py`).

**Organization**: Tarefas agrupadas por user story (spec.md), em ordem de prioridade.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de tarefa incompleta)
- **[Story]**: A qual user story a tarefa pertence

## Path Conventions

Projeto único Python: `src/`, `tests/unit/`, `tests/integration/` na raiz do repositório
(inalterado dos features 001/002).

---

## Phase 1: Setup

Nenhuma tarefa de setup necessária — nenhuma dependência nova, nenhuma infraestrutura
além de um novo workflow do GitHub Actions (criado na própria US2).

---

## Phase 2: Foundational

Nenhuma tarefa foundational bloqueante — as quatro user stories tocam arquivos
majoritariamente distintos (`telegram.py`, `watchdog.py`+`watchdog.yml`, `main.py`,
`CLAUDE.md`) e podem ser implementadas na ordem de prioridade sem uma etapa comum
prévia.

---

## Phase 3: User Story 1 - Notificação nunca perdida por erro de formatação (Priority: P1) 🎯 MVP

**Goal**: Um bloco de mensagem rejeitado pelo Telegram por erro de formatação é
reenviado automaticamente em texto simples, sem perder a notificação e sem duplicar
blocos já entregues.

**Independent Test**: Ver quickstart.md, passo 2 — mockar uma resposta 400 do
Telegram contendo "can't parse entities", confirmar reenvio sem `parse_mode` e entrega
bem-sucedida.

### Tests for User Story 1

- [X] T001 [P] [US1] Em `tests/unit/test_telegram.py`, adicionar caso: `_enviar_bloco` recebe 400 com `"can't parse entities"` no corpo, reenvia o mesmo bloco sem a chave `parse_mode` no payload, e a chamada seguinte tem sucesso — `enviar_mensagem` não lança exceção (FR-001, FR-003)
- [X] T002 [P] [US1] Em `tests/unit/test_telegram.py`, adicionar caso: erro de formatação seguido de nova falha (não relacionada a formatação) na tentativa em texto simples — `FalhaExternaTelegram` é levantada normalmente, não fica silenciosa (FR-001, Edge Case de spec.md)
- [X] T003 [P] [US1] Em `tests/unit/test_telegram.py`, adicionar caso: envio de múltiplos blocos onde um bloco anterior já foi entregue com sucesso e um bloco seguinte aciona o fallback de texto simples — o bloco já entregue não é reenviado (FR-003)

### Implementation for User Story 1

- [X] T004 [US1] Em `src/telegram.py`, em `_enviar_bloco`, detectar erro de formatação (status 400 com `"can't parse entities"` no corpo da resposta, case-insensitive) e, quando detectado, fazer uma tentativa extra imediata do mesmo bloco com payload sem `parse_mode`, antes de propagar `FalhaExternaTelegram` (FR-001, FR-002, D1 de research.md) — depende de T001-T003 estarem escritos e falhando antes da mudança

**Checkpoint**: Nenhuma notificação é perdida por formatação inválida. Este é o MVP
desta feature.

---

## Phase 4: User Story 2 - Alerta quando o monitoramento parar de rodar (Priority: P2)

**Goal**: Uma checagem diária e independente detecta ausência prolongada de execuções
ou falhas repetidas do workflow principal, alertando o usuário via Telegram sem gerar
alertas falsos em operação normal ou no cold start.

**Independent Test**: Ver quickstart.md, passo 3 — `tests/unit/test_watchdog.py` com
resposta mockada da API do GitHub Actions cobrindo os 4 cenários de `data-model.md`.

### Tests for User Story 2

- [X] T005 [P] [US2] Criar `tests/unit/test_watchdog.py`: execução mais recente dentro do intervalo esperado e sem falhas recentes → `deve_alertar=False` (FR-007, data-model.md)
- [X] T006 [P] [US2] Em `tests/unit/test_watchdog.py`: nenhuma execução retornada pela API (cold start) → `deve_alertar=False`, sem exceção (Edge Case de spec.md, SC-003)
- [X] T007 [P] [US2] Em `tests/unit/test_watchdog.py`: execução mais recente com `created_at` há mais de 30h → `deve_alertar=True`, `motivo="sem_execucao_recente"` (FR-004, FR-005)
- [X] T008 [P] [US2] Em `tests/unit/test_watchdog.py`: últimas 3 execuções com `conclusion="failure"` → `deve_alertar=True`, `motivo="falhas_repetidas"`, mesmo com execução recente (FR-006)
- [X] T009 [P] [US2] Em `tests/unit/test_watchdog.py`: resposta HTTP de erro (≠ 200) da API do GitHub Actions → não gera alerta falso, apenas loga e encerra (contracts/github-actions-api.md, seção "Erros")

### Implementation for User Story 2

- [X] T010 [US2] Criar `src/watchdog.py`: função de consulta à API do GitHub Actions (`GET .../actions/workflows/monitor-copom.yml/runs?per_page=5`, autenticada com `GITHUB_TOKEN` do ambiente, repositório de `GITHUB_REPOSITORY`) e função pura de decisão (`deve_alertar`, `motivo`, `ultima_execucao_em`) conforme regras de `data-model.md` e `contracts/github-actions-api.md` (FR-004 a FR-007, D2 de research.md) — depende de T005-T009 estarem escritos e falhando antes da implementação
- [X] T011 [US2] Em `src/watchdog.py`, no ponto de entrada (`if __name__ == "__main__"` ou função `main()`), chamar `notificar_falha` de `src/notificar_falha.py` com mensagem específica por `motivo` quando `deve_alertar=True`, em português (FR-005, FR-006, Princípio VI) — depende de T010
- [X] T012 [US2] Criar `.github/workflows/watchdog.yml`: agendamento diário (`cron: "0 12 * * *"`), `permissions: { contents: read, actions: read }`, step que roda `python -m src.watchdog` com `GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}` e os secrets do Telegram já usados por `notificar_falha` (D3 de research.md) — depende de T010-T011, validação manual via quickstart.md, não é testável por `pytest`

**Checkpoint**: Uma ausência ou degradação prolongada do monitoramento automático é
detectada e comunicada ao usuário em até 24h, sem falsos positivos.

---

## Phase 5: User Story 3 - Link oficial na notificação (Priority: P3)

**Goal**: A mensagem principal de cada notificação (Comunicado e Ata) inclui o link
oficial correspondente do BCB, formatado de forma consistente com o restante da
mensagem, e o mesmo link é preservado no histórico salvo.

**Independent Test**: Ver quickstart.md, passo 4 — revisar `mensagem1` renderizada de
Comunicado e de Ata, e o `.md` salvo em `historico/`.

### Tests for User Story 3

- [ ] T013 [P] [US3] Em `tests/integration/test_main_fluxo_completo.py`, adicionar cenário: `verificar_comunicado` processa uma nova publicação e a mensagem 1 enviada ao Telegram termina com `🔗 *Leia na íntegra*: https://www.bcb.gov.br/controleinflacao/comunicadoscopom/cronologicos` (FR-008, FR-010)
- [ ] T014 [P] [US3] Em `tests/integration/test_main_fluxo_completo.py`, adicionar cenário: `verificar_ata` processa uma nova publicação e a mensagem 1 enviada ao Telegram termina com `🔗 *Leia na íntegra*: https://www.bcb.gov.br/publicacoes/atascopom/cronologicos` (FR-009, FR-010)
- [ ] T015 [P] [US3] Em `tests/integration/test_main_fluxo_completo.py`, adicionar verificação: o markdown salvo em `historico/comunicados/*.md` e `historico/atas/*.md` contém o mesmo link presente na mensagem enviada (FR-011)

### Implementation for User Story 3

- [ ] T016 [US3] Em `src/main.py`, em `verificar_comunicado`, após `gerar_mensagens_comunicado` retornar, concatenar a `mensagem1` com `\n\n🔗 *Leia na íntegra*: https://www.bcb.gov.br/controleinflacao/comunicadoscopom/cronologicos` antes do envio e do registro em `comunicado["analise"]` (FR-008, FR-010, FR-011, D4 de research.md) — depende de T013-T015 estarem escritos e falhando antes da mudança
- [ ] T017 [US3] Em `src/main.py`, em `verificar_ata`, após `gerar_analise_ata` retornar, concatenar a `mensagem1` com `\n\n🔗 *Leia na íntegra*: https://www.bcb.gov.br/publicacoes/atascopom/cronologicos` antes do envio e do registro em `ata["analise"]` (FR-009, FR-010, FR-011, D4 de research.md) — depende de T013-T015 estarem escritos e falhando antes da mudança

**Checkpoint**: 100% das notificações principais de Comunicado e de Ata contêm o link
oficial, na mensagem entregue e no histórico salvo.

---

## Phase 6: User Story 4 - Documentação do projeto sem pendência resolvida (Priority: P4)

**Goal**: `CLAUDE.md` não lista mais como pendente o endpoint de Comunicados, já
confirmado e em produção.

**Independent Test**: Ver quickstart.md, passo 5 — `grep -n "Pendências conhecidas" CLAUDE.md` não retorna ocorrência.

### Implementation for User Story 4

- [ ] T018 [P] [US4] Em `CLAUDE.md`, remover a seção "Pendências conhecidas a validar com `/speckit-clarify` antes de implementar" (FR-012, D5 de research.md)

**Checkpoint**: Nenhuma referência desatualizada ao status do endpoint de Comunicados
permanece na documentação do projeto.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T019 Rodar `pytest -q` completo e os passos manuais de `quickstart.md` (fallback de formatação, watchdog em todos os cenários, link oficial nas duas mensagens, ausência da pendência no CLAUDE.md) e confirmar que todos os critérios de sucesso (SC-001 a SC-005) passam
- [ ] T020 Revisar se `CLAUDE.md`/`plan.md` precisam de atualização adicional além do já previsto no Project Structure de `plan.md` (003) — só se a implementação revelar necessidade de módulo/arquivo não mapeado

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup / Foundational**: Não aplicável — sem tarefas bloqueantes.
- **US1 (Phase 3)**: Sem dependência de outras stories — pode começar imediatamente. É o MVP.
- **US2 (Phase 4)**: Sem dependência de US1 (arquivos diferentes: `telegram.py` vs. `watchdog.py`/`watchdog.yml`) — pode ser feita em paralelo a US1.
- **US3 (Phase 5)**: Sem dependência de US1/US2 (arquivo `main.py`, não tocado por nenhuma delas) — pode ser feita em paralelo.
- **US4 (Phase 6)**: Totalmente independente — arquivo isolado (`CLAUDE.md`).
- **Polish (Phase 7)**: Depende de todas as stories desejadas estarem completas.

### Parallel Opportunities

- T001, T002, T003 (testes de US1) podem ser escritos em paralelo — mesmo arquivo (`test_telegram.py`), mas casos independentes; ao editar em paralelo, consolidar antes de rodar.
- T005-T009 (testes de US2) podem ser escritos em paralelo entre si.
- T013, T014, T015 (testes de US3) podem ser escritos em paralelo entre si.
- US1, US2, US3, US4 podem ser implementadas em paralelo por pessoas diferentes — arquivos praticamente disjuntos (`telegram.py`; `watchdog.py`+`watchdog.yml`; `main.py`; `CLAUDE.md`).

---

## Implementation Strategy

### MVP First (User Story 1)

1. T001 → T002 → T003 → T004 (US1 completa)
2. **PARAR e VALIDAR**: rodar `pytest tests/unit/test_telegram.py -q` e o passo 2 do quickstart.md
3. Este é o MVP: nenhuma notificação é mais perdida por erro de formatação, mesmo sem as demais stories.

### Entrega Incremental

1. US1 (P1) → validar → é o MVP
2. US2 (P2) → validar → watchdog protege contra ausência silenciosa de execução
3. US3 (P3) → validar → link oficial presente em toda notificação
4. US4 (P4) → validar → documentação sem pendência desatualizada
5. Polish (T019-T020)

Cada tarefa concluída deve gerar um commit próprio referenciando seu ID (ex.:
`T004: adiciona fallback de texto simples ao enviar bloco Telegram`), conforme o fluxo
de SDD descrito em `CLAUDE.md`.

---

## Notes

- [P] tasks = arquivos diferentes (ou casos independentes no mesmo arquivo de teste), sem dependência entre si
- [Story] mapeia a tarefa à user story correspondente para rastreabilidade
- Tarefas de teste devem ser escritas e falhar antes da implementação correspondente
- Commit após cada tarefa concluída, referenciando o ID da tarefa
- Evitar: tarefas vagas, conflito no mesmo arquivo entre tarefas paralelas, dependências entre stories que quebrem a independência
