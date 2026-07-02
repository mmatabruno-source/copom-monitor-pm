# Data Model: Robustez e Resiliência Operacional do Monitor

Esta feature não introduz nenhuma entidade persistida (nenhuma mudança no schema de
`estado.json` ou de `historico/*.json` — Princípio II). A única estrutura nova é
efêmera, existente apenas durante uma execução, para atender FR-007.

## Resumo de Execução

Representa o resultado consolidado de uma execução do robô. Vive apenas em memória
durante `main()` e é registrado como uma linha de log estruturada ao final — **não é
gravado em arquivo nem enviado por Telegram**.

Cada fluxo (Comunicado, Ata) sempre é verificado na API do BCB a cada execução (Princípio
V) — não há um estado intermediário "não verificado" a registrar. O resumo, portanto,
só precisa distinguir três resultados possíveis por fluxo:

| Campo | Tipo | Descrição |
|---|---|---|
| `comunicado.processado` | bool | Se um novo Comunicado foi encontrado, notificado e persistido |
| `comunicado.falhou` | bool | Se houve uma falha inesperada (não tratada dentro do próprio fluxo) no processamento do Comunicado |
| `ata.processado` | bool | Se uma nova Ata foi encontrada, notificada e persistida |
| `ata.falhou` | bool | Se houve uma falha inesperada no processamento da Ata |
| `duracao_segundos` | float | Duração total da execução, do início ao fim de `main()` |

### Regras

- `processado=True` implica `falhou=False` para o mesmo fluxo (mutuamente exclusivos).
- `processado=False` e `falhou=False` juntos significam "verificado, sem novidade" —
  incluindo os casos em que uma falha já esperada (`FalhaExterna*`) foi tratada e
  notificada dentro do próprio fluxo (esses casos já geram seu próprio aviso via
  `notificar_falha`; o resumo não precisa duplicá-los como "falha" para não confundir
  falha transitória já avisada com bug inesperado).
- `falhou=True` é reservado para exceções verdadeiramente inesperadas, isoladas por
  `_executar_isolado` em `main.py` (FR-001).
- Uma falha em um fluxo nunca altera os campos do outro fluxo (FR-001) — cada fluxo
  reporta seu próprio resultado de forma independente.
- Este resumo é complementar aos logs detalhados já existentes (`logger.error`/`logger.info`
  por etapa) — ele não os substitui, apenas oferece uma visão consolidada no final.
