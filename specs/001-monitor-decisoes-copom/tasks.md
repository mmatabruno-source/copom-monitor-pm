---

description: "Task list for Monitor de Decisões do Copom"
---

# Tasks: Monitor de Decisões do Copom

**Input**: Design documents from `/specs/001-monitor-decisoes-copom/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: plan.md define pytest como ferramenta de teste. Tasks de teste estão incluídas
para os módulos com lógica crítica (idempotência, divisão de mensagem, parsing de API),
mas mantidas mínimas, alinhadas ao princípio VII (simplicidade) da constituição.

**Organization**: Tarefas agrupadas por user story (US1 = Comunicado/P1, US2 = Ata/P2,
US3 = Histórico navegável/P3), conforme spec.md.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência)
- **[Story]**: US1, US2 ou US3
- Caminhos de arquivo exatos em cada descrição

## Path Conventions

Projeto single (script/CLI), conforme plan.md: `src/`, `tests/unit/`, `tests/integration/`
na raiz do repositório.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Inicialização do projeto e estrutura básica

- [ ] T001 Criar estrutura de diretórios do projeto (`src/`, `tests/unit/`, `tests/integration/`,
  `historico/comunicados/`, `historico/atas/`) com arquivos `.gitkeep` onde necessário
- [ ] T002 Criar `requirements.txt` na raiz com `requests`, `anthropic`, `pytest`
- [ ] T003 [P] Criar `estado.json` inicial na raiz com `{"ultima_ata": null, "ultimo_comunicado": null}`
- [ ] T004 [P] Criar `.gitignore` cobrindo `.venv/`, `__pycache__/`, `*.pyc`

**Checkpoint**: Estrutura do projeto pronta para receber código

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infraestrutura central que TODAS as user stories dependem

**⚠️ CRITICAL**: Nenhuma user story pode começar antes desta fase estar completa

- [ ] T005 Validar manualmente o endpoint de Comunicados da API do BCB via
  `curl -s "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados?quantidade=1"`
  (e seu `_detalhes`), documentando achados em `specs/001-monitor-decisoes-copom/contracts/bcb-api.md`
  — bloqueante para T011/T012 (ver quickstart.md, pendência técnica)
- [ ] T006 Implementar `src/estado.py`: funções `carregar_estado()` e `salvar_estado(ultima_ata, ultimo_comunicado)`
  lendo/escrevendo `estado.json` (data-model.md, Registro de Processamento)
- [ ] T007 [P] Implementar `src/historico.py`: funções `salvar_publicacao(tipo, nro_reuniao, dados, analise)`
  gerando `historico/{comunicados|atas}/{nro_reuniao}.json` e `.md`, e
  `carregar_publicacao_anterior(tipo, nro_reuniao_atual)` para buscar a publicação anterior no histórico
  (data-model.md)
- [ ] T008 [P] Implementar `src/bcb_client.py` com `listar_atas(quantidade)` e `detalhes_ata(nro_reuniao)`
  contra os endpoints confirmados (`contracts/bcb-api.md`), tratando timeout/4xx/5xx como falha externa (FR-011)
- [ ] T009 [P] Implementar `src/telegram.py`: função `enviar_mensagem(texto)` que divide texto >4096
  caracteres em blocos por limite de parágrafo e envia sequencialmente via `sendMessage`, retornando
  sucesso só se todos os blocos retornarem `ok: true` (`contracts/telegram-api.md`, FR-009)
- [ ] T010 [P] Implementar `src/notificar_falha.py`: função `notificar_falha(contexto, erro)` que envia
  mensagem de falha ao Telegram (FR-012), registrando no log da execução se o próprio Telegram falhar

**Checkpoint**: Fundação pronta — implementação das user stories pode começar

---

## Phase 3: User Story 1 - Alerta imediato da decisão de juros (Priority: P1) 🎯 MVP

**Goal**: Detectar novo Comunicado via API do BCB e notificar o usuário via Telegram com
decisão objetiva + sinalização/tom, salvando o histórico, de forma idempotente.

**Independent Test**: Rodar `python -m src.main` com um Comunicado novo disponível na API
(ou mockado) e confirmar que a notificação chega ao Telegram, `historico/comunicados/{nro}.json|.md`
são criados e `estado.json.ultimo_comunicado` é atualizado só após sucesso; rodar novamente sem
novidade não deve gerar segunda notificação (quickstart.md, Cenário 2).

### Tests for User Story 1

- [ ] T011 [P] [US1] Teste unitário de divisão de mensagem >4096 caracteres em
  `tests/unit/test_telegram.py` (cobre T009)
- [ ] T012 [P] [US1] Teste unitário de idempotência de `src/estado.py` (não regressão de
  `ultimo_comunicado` ao salvar `ultima_ata` e vice-versa) em `tests/unit/test_estado.py`

### Implementation for User Story 1

- [ ] T013 [US1] Implementar `listar_comunicados(quantidade)` e `detalhes_comunicado(nro_reuniao)`
  em `src/bcb_client.py`, usando o payload confirmado em T005
- [ ] T014 [US1] Implementar `gerar_analise_comunicado(texto_bruto)` em `src/analise.py`, chamando a
  API da Anthropic (modelo `claude-sonnet-4-6`) com o prompt de 2 itens (decisão objetiva + sinalização)
  conforme `contracts/anthropic-api.md`, tratando falha como FR-011
- [ ] T015 [US1] Implementar fluxo de verificação do Comunicado em `src/main.py`: comparar
  `nro_reuniao` mais recente da API com `estado.ultimo_comunicado`, processar se novo
  (extrair → analisar → notificar → salvar histórico → atualizar estado, nesta ordem, FR-010)
- [ ] T016 [US1] Integrar tratamento de falha em `src/main.py` para o fluxo de Comunicado:
  qualquer falha externa aborta sem marcar como processado e chama `notificar_falha` (FR-011/FR-012)
- [ ] T017 [US1] Tratar edge case de primeira execução (sem histórico) no fluxo de Comunicado
  em `src/main.py` (spec.md, edge cases)

**Checkpoint**: User Story 1 completa e testável de forma independente

---

## Phase 4: User Story 2 - Análise crítica completa da Ata (Priority: P2)

**Goal**: Detectar nova Ata via API do BCB e notificar o usuário com a análise crítica completa
de 6 itens (incluindo comparação de tom com a Ata anterior), salvando o histórico de forma idempotente.

**Independent Test**: Rodar `python -m src.main` com uma Ata nova disponível e confirmar que a
notificação contém os 6 itens na ordem de FR-005, que a comparação de tom é omitida quando não há
Ata anterior no histórico (edge case), e que `estado.json.ultima_ata` só é atualizado após sucesso.

### Implementation for User Story 2

- [ ] T018 [US2] Implementar `extrair_secoes_ata(texto_ata_html)` em `src/analise.py` para estruturar
  o HTML retornado por `detalhes_ata` nas seções A/B/C/D (data-model.md, `texto_estruturado`)
- [ ] T019 [US2] Implementar `gerar_analise_ata(texto_estruturado, analise_ata_anterior=None)` em
  `src/analise.py`, chamando a API da Anthropic com o prompt de 6 itens (FR-005), omitindo a instrução
  de comparação de tom quando `analise_ata_anterior` for `None` (contracts/anthropic-api.md)
- [ ] T020 [US2] Implementar fluxo de verificação da Ata em `src/main.py`: comparar `nro_reuniao` mais
  recente da API com `estado.ultima_ata`, buscar Ata anterior via `historico.carregar_publicacao_anterior`,
  processar se novo (extrair → analisar → notificar → salvar histórico → atualizar estado, FR-010)
- [ ] T021 [US2] Integrar tratamento de falha em `src/main.py` para o fluxo de Ata (FR-011/FR-012),
  igual ao padrão de T016
- [ ] T022 [US2] Implementar processamento simultâneo de Comunicado e Ata na mesma execução de
  `src/main.py`, de forma independente (cada falha/sucesso não afeta o outro fluxo), conforme
  clarificação registrada em spec.md

**Checkpoint**: User Stories 1 e 2 funcionam de forma independente

---

## Phase 5: User Story 3 - Histórico navegável de publicações e análises (Priority: P3)

**Goal**: Garantir que todo conteúdo bruto e toda análise gerada fiquem permanentemente
acessíveis e legíveis no histórico do repositório (JSON para dados, Markdown para leitura humana).

**Independent Test**: Inspecionar `historico/comunicados/{nro}.md` e `historico/atas/{nro}.md`
gerados pelas Stories 1 e 2 e confirmar que contêm a análise em destaque e todos os campos de
data-model.md, em formato legível.

### Implementation for User Story 3

- [ ] T023 [US3] Implementar geração do `.md` legível em `src/historico.py` para Comunicado,
  destacando a análise (decisão + sinalização) no topo do arquivo
- [ ] T024 [US3] Implementar geração do `.md` legível em `src/historico.py` para Ata, com os 6 itens
  da análise organizados em seções correspondentes, seguidos do texto estruturado da Ata

**Checkpoint**: Todas as user stories funcionam de forma independente

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Integração final, automação e validação de ponta a ponta

- [ ] T025 Implementar `src/main.py` como ponto de entrada único (`python -m src.main`),
  orquestrando os fluxos de Comunicado (T015) e Ata (T020) em uma única execução
- [ ] T026 [P] Criar `.github/workflows/monitor-copom.yml` com os três `schedule:` (baseline 3h,
  janela densa terça 10:45–13:00 UTC, janela densa quarta 21:15–23:45 UTC), `concurrency` com
  `cancel-in-progress: false` (FR-014) e `permissions: contents: write`
- [ ] T027 Adicionar passo de commit automático do histórico (`historico/`, `estado.json`) ao
  workflow `.github/workflows/monitor-copom.yml`, executado apenas quando houver alterações
- [ ] T028 [P] Teste de integração do fluxo completo (sem novidade → sem alteração de estado/sem
  notificação) em `tests/integration/test_main_fluxo_completo.py`, com chamadas externas mockadas
- [ ] T029 [P] Teste de integração de idempotência (rodar duas vezes, segunda sem notificação) em
  `tests/integration/test_main_fluxo_completo.py`, conforme quickstart.md Cenário 2
- [ ] T030 [P] Teste de integração de falha simulada (abortar sem atualizar estado, reprocessar do
  zero na próxima execução) em `tests/integration/test_main_fluxo_completo.py`, conforme
  quickstart.md Cenário 3
- [ ] T031 Executar manualmente os 3 cenários de validação de quickstart.md contra a API real do
  BCB (ou o mais próximo possível) antes de considerar a feature concluída

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências — pode iniciar imediatamente
- **Foundational (Phase 2)**: depende do Setup; T005 bloqueia T013 (Comunicado real); BLOQUEIA
  todas as user stories
- **User Story 1 (Phase 3)**: depende da Foundational completa
- **User Story 2 (Phase 4)**: depende da Foundational completa; T022 depende de T015 e T020
  existirem (orquestração) — não depende de US1 estar "completa", mas a integração final (T025)
  depende de ambos
- **User Story 3 (Phase 5)**: depende da Foundational completa (T007); pode rodar em paralelo
  com US1/US2, mas conteúdo real só é validável após T015/T020 existirem
- **Polish (Phase 6)**: depende de US1 e US2 completos (T025 orquestra ambos); T026/T027
  podem ser feitos em paralelo com as user stories

### Parallel Opportunities

- T003, T004 (Setup) em paralelo
- T007, T008, T009, T010 (Foundational) em paralelo entre si, após T006
- T011, T012 (testes US1) em paralelo
- T026 (workflow) pode ser feito em paralelo com qualquer user story
- T028, T029, T030 (testes de integração) em paralelo entre si, após T025

---

## Implementation Strategy

### MVP First (User Story 1)

1. Completar Phase 1: Setup
2. Completar Phase 2: Foundational (T005 é bloqueante e deve ser feito o quanto antes)
3. Completar Phase 3: User Story 1 (fluxo completo de Comunicado)
4. **PARAR e VALIDAR**: testar Comunicado isoladamente (Cenário 1/2 de quickstart.md)

### Incremental Delivery

1. Setup + Foundational → fundação pronta
2. User Story 1 → validar isoladamente → MVP funcional para Comunicado
3. User Story 2 → validar isoladamente → Ata incluída
4. User Story 3 → validar isoladamente → histórico legível garantido
5. Polish → workflow do GitHub Actions, testes de integração, validação final de quickstart.md

---

## Notes

- [P] = arquivos diferentes, sem dependência entre as tarefas
- Cada tarefa deve corresponder a um commit, conforme CLAUDE.md e constitution.md
  ("Fluxo de Desenvolvimento (SDD)")
- T005 é a pendência técnica mais crítica: nenhuma tarefa de Comunicado real (T013+) deve
  assumir o formato do payload sem essa validação manual prévia
- Ordem decisão→análise→notificação→histórico→estado (nesta sequência) é obrigatória em
  T015 e T020 para preservar idempotência (FR-010, data-model.md)
