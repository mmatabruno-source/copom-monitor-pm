# Implementation Plan: Robustez e Resiliência Operacional do Monitor

**Branch**: `002-robustez-resiliencia-monitor` | **Date**: 2026-07-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/002-robustez-resiliencia-monitor/spec.md`

## Summary

Reforçar a resiliência operacional do monitor já existente sem alterar sua arquitetura:
isolar falhas inesperadas entre os fluxos de Comunicado e Ata para que uma não impeça a
persistência da outra; adicionar retry/backoff criterioso (distinguindo falha
transitória de permanente) nas três integrações externas (BCB, Anthropic, Telegram);
evitar duplicação de blocos de mensagem no Telegram; eliminar vazamento do token em
logs/erros; tornar o push do estado ao Git resiliente a falhas transitórias, com aviso
ao usuário se falhar mesmo assim; registrar um resumo estruturado por execução; cobrir
com testes os módulos hoje sem testes; e fixar as versões das dependências.

## Technical Context

**Language/Version**: Python 3.12 (inalterado)

**Primary Dependencies**: `requests==2.34.2`, `anthropic==0.115.1` (SDK oficial, já em
uso) — versões fixas em vez de sem pin (D8, research.md). Nenhuma dependência nova.

**Storage**: Inalterado — arquivos em `historico/` + `estado.json` no próprio
repositório Git (Princípio II).

**Testing**: `pytest==9.1.1` com `unittest.mock` (stdlib) para simular `requests` e o
cliente `anthropic`, seguindo o padrão já usado em `tests/unit/test_telegram.py` (D9).

**Target Platform**: GitHub Actions runner (`ubuntu-latest`), inalterado.

**Project Type**: Script/CLI único, sem interface — inalterado.

**Performance Goals**: Não aplicável — mesma natureza de baixo volume do feature 001.
O requisito relevante é a recuperação automática de falhas transitórias dentro da mesma
execução (SC-002), não throughput.

**Constraints**: Nenhuma dependência nova (Princípio VII); nenhuma mudança de
infraestrutura ou custo (Princípio I); o comportamento de idempotência existente
(Princípio IV) não pode regredir — esta feature o reforça, não o substitui.

**Scale/Scope**: Mesmo volume do feature 001 (~16 publicações novas/ano, ~1300
execuções/ano do workflow). Escopo desta feature é inteiramente dentro dos módulos
`src/` já existentes, do workflow `monitor-copom.yml` e de `requirements.txt` — nenhum
módulo novo é criado, exceto os arquivos de teste que faltam.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio/Restrição | Avaliação |
|---|---|
| I. Stack Mínimo e Custo Zero | PASS — nenhuma dependência ou serviço novo; retry/backoff implementado com código próprio, sem biblioteca adicional |
| II. Armazenamento em Arquivos | PASS — resumo de execução (FR-007) é só log, não é persistido; nenhuma mudança em `historico/`/`estado.json` |
| III. Segredos Nunca em Texto Plano | PASS — FR-006 reforça esse princípio (elimina vazamento do token em logs/erros), não o enfraquece |
| IV. Idempotência e Resiliência | PASS — esta feature existe justamente para fechar as lacunas que ainda permitiam violação deste princípio (FR-001, FR-002, FR-011) |
| V. Fonte de Verdade é a API | PASS — nenhuma mudança na lógica de detecção de novidade |
| VI. Comunicação em Português | PASS — mensagens de aviso continuam em português; resumo de execução (FR-007) fica em log, não é mensagem ao usuário |
| VII. Simplicidade | PASS — todas as decisões em `research.md` rejeitaram explicitamente abstrações/bibliotecas adicionais em favor de reaproveitar o padrão já existente em `bcb_client._get` |
| Restrição técnica: limite de mensagem do Telegram | PASS — divisão em blocos existente é preservada; retry por bloco (D3) não altera o limite de 4096 caracteres |

Nenhuma violação identificada. Nenhuma entrada necessária em Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/002-robustez-resiliencia-monitor/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
└── tasks.md              # Phase 2 output (/speckit-tasks — ainda não criado)
```

Sem `contracts/`: esta feature não expõe nem consome nenhuma interface externa nova —
os contratos de BCB/Anthropic/Telegram documentados em `specs/001-monitor-decisoes-copom/contracts/`
continuam válidos e inalterados.

### Source Code (repository root)

```text
src/
├── bcb_client.py         # ALTERADO — retry criterioso (D2): distingue erro permanente
│                          # de transitório, respeita Retry-After em 429
├── analise.py             # ALTERADO — retry/backoff em _chamar_claude (D1)
├── telegram.py             # ALTERADO — retry por bloco (D1+D3), sanitização do token
│                          # antes de logar/lançar exceção (D4)
├── notificar_falha.py      # INALTERADO — reaproveitado por main.py e pelo step de push
├── historico.py            # INALTERADO — só ganha testes (D9)
├── estado.py               # INALTERADO
└── main.py                 # ALTERADO — isolamento de falha por fluxo (D5), resumo de
                             # execução estruturado em log (D7)

tests/
├── unit/
│   ├── test_bcb_client.py        # NOVO (D9) — retry, distinção retentável/permanente
│   ├── test_analise.py           # NOVO (D9) — parsing/regex de extração
│   ├── test_historico.py         # NOVO (D9) — carregar_publicacao_anterior
│   ├── test_notificar_falha.py   # NOVO (D9) — falha dupla (Telegram também falha)
│   └── test_telegram.py          # ALTERADO — casos de retry por bloco e sanitização
└── integration/
    └── test_main_fluxo_completo.py  # ALTERADO — cenário de falha inesperada em um
                                       # fluxo depois do outro ter sido concluído (FR-009)

.github/workflows/
└── monitor-copom.yml     # ALTERADO — retry no pull/push do step de commit (D6),
                           # aviso via Telegram se persistência falhar mesmo assim

requirements.txt          # ALTERADO — versões fixas (D8)
```

**Structure Decision**: Mesma estrutura de projeto único do feature 001 (`src/` +
`tests/unit` + `tests/integration`, sem camadas de API/web). Todas as mudanças desta
feature são alterações cirúrgicas nos módulos já existentes — nenhum diretório novo é
necessário além dos novos arquivos de teste.

## Complexity Tracking

Nenhuma violação da constituição identificada — seção não aplicável.
