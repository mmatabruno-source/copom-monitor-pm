---

description: "Task list for feature implementation"
---

# Tasks: Robustez e Resiliência Operacional do Monitor

**Input**: Design documents from `/specs/002-robustez-resiliencia-monitor/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Explicitamente exigidos pela spec (US5, FR-008, FR-009) — incluídos.

**Organization**: Tarefas agrupadas por user story (spec.md), em ordem de prioridade.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de tarefa incompleta)
- **[Story]**: A qual user story a tarefa pertence

## Path Conventions

Projeto único Python: `src/`, `tests/unit/`, `tests/integration/` na raiz do repositório
(inalterado do feature 001).

---

## Phase 1: Setup

Nenhuma tarefa de setup necessária — esta feature não adiciona dependências nem
infraestrutura nova; todas as mudanças são cirúrgicas em módulos já existentes.

---

## Phase 2: Foundational

Nenhuma tarefa foundational bloqueante — as seis user stories tocam arquivos
majoritariamente distintos (`bcb_client.py`, `analise.py`, `telegram.py`, `main.py`,
`requirements.txt`, testes novos) e podem ser implementadas na ordem de prioridade sem
uma etapa comum prévia.

---

## Phase 3: User Story 1 - Nenhuma notificação duplicada mesmo com falha parcial (Priority: P1) 🎯 MVP

**Goal**: Uma falha inesperada no processamento de uma publicação não impede a
persistência do resultado já concluído com sucesso da outra, nem deixa de avisar o
usuário se a persistência durável falhar mesmo assim.

**Independent Test**: Ver quickstart.md, passo 2 — forçar `verificar_ata` a lançar uma
exceção inesperada depois de `verificar_comunicado` ter tido sucesso e confirmar que
`main()` não propaga a exceção.

### Tests for User Story 1

- [X] T001 [P] [US1] Adicionar cenário em `tests/integration/test_main_fluxo_completo.py`: `verificar_comunicado` bem-sucedido seguido de `verificar_ata` lançando uma exceção inesperada (não `FalhaExterna*`) dentro de `main()` — o estado do Comunicado permanece salvo e `main()` não propaga a exceção (FR-001, FR-009, SC-001)

### Implementation for User Story 1

- [X] T002 [US1] Em `src/main.py`, envolver cada chamada a `verificar_comunicado()` e `verificar_ata()` dentro de `main()` em `try/except Exception`, registrando a exceção inesperada em log e chamando `notificar_falha` com um contexto genérico, sem relançar (FR-001, D5) — depende de T001 estar escrito e falhando antes da mudança
- [X] T003 [US1] Em `.github/workflows/monitor-copom.yml`, envolver `git pull --rebase --autostash` + `git push` do step "Commitar histórico atualizado" em um laço de até 3 tentativas com espera entre elas; ao esgotar as tentativas, invocar `notificar_falha` (via `python -c` ou script auxiliar) com os secrets do Telegram já disponíveis nesse step, avisando sobre o risco de notificação duplicada na próxima execução (FR-011, D6) — validação manual via quickstart.md, não é testável por `pytest`

**Checkpoint**: A garantia mais crítica do projeto (idempotência sob falha parcial) está
protegida e testada. Este é o MVP desta feature.

---

## Phase 4: User Story 2 - Recuperação automática de falhas passageiras nos serviços externos (Priority: P2)

**Goal**: Falhas transitórias no BCB, na Anthropic ou no Telegram são resolvidas
automaticamente dentro da mesma execução; falhas permanentes não desperdiçam tentativas;
o reenvio de uma mensagem longa após falha parcial nunca duplica blocos já entregues.

**Independent Test**: Ver quickstart.md, passo 1 (`pytest -q`) — casos de
`test_bcb_client.py` e `test_telegram.py` cobrindo retry seletivo e não duplicação.

### Tests for User Story 2

- [X] T004 [P] [US2] Criar `tests/unit/test_bcb_client.py`: erro de conexão e status `5xx`/`429` disparam nova tentativa (respeitando `Retry-After` quando presente); status `4xx` permanente (ex.: `404`) não gera nova tentativa (FR-004, D2)
- [ ] T005 [P] [US2] Criar `tests/unit/test_analise.py`: `_cliente()` constrói o `anthropic.Anthropic` com `max_retries=3` (retry nativo do SDK, FR-003); `extrair_selic_resultante` e `extrair_secoes_ata` cobertos com casos de sucesso e de formato inesperado/texto vazio (FR-008)
- [ ] T006 [P] [US2] Estender `tests/unit/test_telegram.py`: ao falhar um bloco no meio de um envio de múltiplos blocos e a tentativa seguinte ter sucesso, os blocos já entregues não são reenviados (FR-005); esgotar tentativas de um bloco propaga `FalhaExternaTelegram` (FR-003)

### Implementation for User Story 2

- [X] T007 [P] [US2] Em `src/bcb_client.py`, alterar `_get` para distinguir falha permanente (`4xx` exceto `429`) de transitória (erro de conexão, `5xx`, `429`), abortando sem novas tentativas no caso permanente e respeitando o cabeçalho `Retry-After` em `429` quando presente (FR-004, D2)
- [ ] T008 [P] [US2] Em `src/analise.py`, passar `max_retries=3` na construção do cliente `anthropic.Anthropic` em `_cliente()`, usando o retry nativo do SDK para falhas tipicamente transitórias da API da Anthropic (FR-003, D1)
- [ ] T009 [P] [US2] Em `src/telegram.py`, adicionar retry/backoff por bloco na chamada a `_enviar_bloco` dentro do laço de `enviar_mensagem`, garantindo que blocos já entregues nunca sejam reenviados (FR-003, FR-005, D1, D3)

**Checkpoint**: O robô se recupera sozinho de instabilidades momentâneas nas três
integrações externas, sem esperar o próximo ciclo do cron.

---

## Phase 5: User Story 3 - Nenhum segredo exposto em logs ou mensagens (Priority: P3)

**Goal**: O token do bot do Telegram nunca aparece em texto legível em logs ou em
mensagens de aviso de falha devolvidas ao usuário.

**Independent Test**: Ver quickstart.md, passo 3.

### Tests for User Story 3

- [ ] T010 [US3] Estender `tests/unit/test_telegram.py`: forçar uma `requests.RequestException` cujo texto contenha o token e verificar que o texto da `FalhaExternaTelegram` levantada não contém o token (FR-006, SC-003) — depende de T006/T009 já terem ajustado a estrutura de retry em `_enviar_bloco`

### Implementation for User Story 3

- [ ] T011 [US3] Em `src/telegram.py`, adicionar uma função de sanitização que substitui qualquer ocorrência do token por `***` no texto de qualquer `FalhaExternaTelegram` levantada a partir de `_enviar_bloco`, cobrindo tanto os logs quanto as mensagens de `notificar_falha` que reaproveitam essa exceção (FR-006, D4) — depende de T009

**Checkpoint**: Nenhum caminho de erro do Telegram expõe o token, nem em log nem em
mensagem enviada de volta ao usuário.

---

## Phase 6: User Story 4 - Resumo objetivo de cada execução (Priority: P4)

**Goal**: Ao final de cada execução, existe um resumo legível do que foi verificado,
processado e do que falhou, sem precisar abrir os logs detalhados.

**Independent Test**: Ver quickstart.md, passo 4.

### Tests for User Story 4

- [ ] T012 [US4] Em `tests/integration/test_main_fluxo_completo.py`, adicionar um teste que roda `main()` com um cenário misto (um fluxo processado, outro sem novidade) e verifica, via `caplog`, que a última linha de log é um resumo estruturado contendo o resultado dos dois fluxos (FR-007, SC-004)

### Implementation for User Story 4

- [ ] T013 [US4] Em `src/main.py`, acumular um resumo de execução (campos descritos em `data-model.md`: verificado/processado/falhou por fluxo, duração) durante `main()` e registrá-lo como uma única linha de log estruturada ao final (FR-007, D7) — depende de T002 (mesma função `main()`, mesmo arquivo)

**Checkpoint**: Qualquer execução pode ser diagnosticada lendo apenas a última linha de
log, sem vasculhar o log bruto inteiro.

---

## Phase 7: User Story 5 - Cobertura de testes para os módulos críticos ainda sem testes (Priority: P5)

**Goal**: Os módulos `historico.py` e `notificar_falha.py` — os dois que continuam sem
nenhum teste automatizado mesmo após as fases anteriores — passam a ter testes cobrindo
sucesso e falha.

**Independent Test**: `pytest tests/unit/test_historico.py tests/unit/test_notificar_falha.py -q`

### Tests for User Story 5

- [ ] T014 [P] [US5] Criar `tests/unit/test_historico.py`: `carregar_publicacao_anterior` retorna a publicação de maior número anterior ao número atual, retorna `None` quando o diretório não existe ou está vazio, e ignora arquivos `.json` com nome não numérico; `salvar_publicacao` grava `.json` e `.md` de forma atômica (FR-008)
- [ ] T015 [P] [US5] Criar `tests/unit/test_notificar_falha.py`: caminho de sucesso (envia mensagem de aviso formatada) e caminho de falha dupla (o próprio Telegram falha ao tentar avisar — `notificar_falha` não relança nem tenta de novo) (FR-008)

**Checkpoint**: Todos os módulos listados na spec como hoje sem testes (`bcb_client`,
`analise`, `historico`, `notificar_falha`) têm cobertura de sucesso e falha.

---

## Phase 8: User Story 6 - Dependências com versão travada (Priority: P6)

**Goal**: Nenhuma dependência externa do projeto tem versão em aberto.

**Independent Test**: `grep -E "==" requirements.txt` retorna as três linhas.

### Implementation for User Story 6

- [ ] T016 [P] [US6] Em `requirements.txt`, fixar `requests==2.34.2`, `anthropic==0.115.1`, `pytest==9.1.1` (FR-010, D8)

**Checkpoint**: Uma atualização externa de biblioteca não pode mais alterar o
comportamento de uma execução agendada sem ser uma decisão explícita.

---

## Phase 9: Polish & Cross-Cutting Concerns

- [ ] T017 Rodar `pytest -q` completo e os passos manuais de `quickstart.md` (isolamento de falha, ausência do token nos logs, resumo de execução) e confirmar que todos os critérios de sucesso (SC-001 a SC-006) passam
- [ ] T018 Atualizar `specs/001-monitor-decisoes-copom/plan.md` ou `CLAUDE.md` apenas se a implementação revelar necessidade de novos módulos/arquivos além dos já mapeados no Project Structure de `plan.md` (não antecipar — só se necessário)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup / Foundational**: Não aplicável — sem tarefas bloqueantes.
- **US1 (Phase 3)**: Sem dependência de outras stories — pode começar imediatamente. É o MVP.
- **US2 (Phase 4)**: Sem dependência de US1 (arquivos diferentes: `bcb_client.py`, `analise.py`, `telegram.py` vs. `main.py`/workflow) — pode ser feita em paralelo a US1 por outra pessoa, ou em sequência.
- **US3 (Phase 5)**: Depende de US2 (T009) ter ajustado `_enviar_bloco`/`enviar_mensagem`, já que a sanitização é aplicada no mesmo ponto do código.
- **US4 (Phase 6)**: Depende de US1 (T002) — mesma função `main()`.
- **US5 (Phase 7)**: Sem dependência de nenhuma story anterior — `historico.py` e `notificar_falha.py` não são alterados por nenhuma outra story, apenas testados.
- **US6 (Phase 8)**: Totalmente independente — arquivo isolado (`requirements.txt`).
- **Polish (Phase 9)**: Depende de todas as stories desejadas estarem completas.

### Parallel Opportunities

- T004, T005, T006 (testes de US2) podem ser escritos em paralelo — arquivos diferentes.
- T007, T008, T009 (implementação de US2) podem ser feitas em paralelo — arquivos diferentes.
- T014, T015 (US5) podem ser feitas em paralelo entre si e em paralelo com qualquer outra story — não tocam nenhum arquivo alterado pelas demais.
- T016 (US6) pode ser feita a qualquer momento, em paralelo com qualquer outra story.

---

## Parallel Example: User Story 2

```bash
# Testes de US2 em paralelo (arquivos diferentes):
Task: "tests/unit/test_bcb_client.py"
Task: "tests/unit/test_analise.py"
Task: "tests/unit/test_telegram.py (extensão)"

# Implementação de US2 em paralelo (arquivos diferentes):
Task: "src/bcb_client.py"
Task: "src/analise.py"
Task: "src/telegram.py"
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. T001 → T002 → T003 (US1 completa)
2. **PARAR e VALIDAR**: rodar `pytest tests/integration/test_main_fluxo_completo.py -q` e o passo 2 do quickstart.md
3. Este é o MVP: a garantia de idempotência sob falha parcial já está protegida mesmo sem as demais stories.

### Entrega Incremental

1. US1 (P1) → validar → é o MVP
2. US2 (P2) → validar → robô se recupera sozinho de falhas transitórias
3. US3 (P3) → validar → nenhum vazamento de token
4. US4 (P4) → validar → resumo de execução
5. US5 (P5) → validar → cobertura de testes completa
6. US6 (P6) → validar → dependências travadas
7. Polish (T017-T018)

Cada tarefa concluída deve gerar um commit próprio referenciando seu ID (ex.:
`T002: isola falha inesperada entre Comunicado e Ata em main()`), conforme o fluxo de
SDD descrito em `CLAUDE.md`.

---

## Notes

- [P] tasks = arquivos diferentes, sem dependência entre si
- [Story] mapeia a tarefa à user story correspondente para rastreabilidade
- Tarefas de teste (quando presentes numa story) devem ser escritas e falhar antes da
  implementação correspondente
- Commit após cada tarefa concluída, referenciando o ID da tarefa
- Evitar: tarefas vagas, conflito no mesmo arquivo entre tarefas paralelas, dependências
  entre stories que quebrem a independência
