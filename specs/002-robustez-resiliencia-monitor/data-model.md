# Data Model: Robustez e Resiliência Operacional do Monitor

Esta feature não introduz nenhuma entidade persistida (nenhuma mudança no schema de
`estado.json` ou de `historico/*.json` — Princípio II). A única estrutura nova é
efêmera, existente apenas durante uma execução, para atender FR-007.

## Resumo de Execução

Representa o resultado consolidado de uma execução do robô. Vive apenas em memória
durante `main()` e é registrado como uma linha de log estruturada ao final — **não é
gravado em arquivo nem enviado por Telegram**.

| Campo | Tipo | Descrição |
|---|---|---|
| `comunicado.verificado` | bool | Se a listagem de Comunicados foi consultada com sucesso na API do BCB |
| `comunicado.processado` | bool | Se um novo Comunicado foi encontrado, notificado e persistido |
| `comunicado.falhou` | bool | Se houve falha (esperada ou inesperada) no processamento do Comunicado |
| `ata.verificado` | bool | Se a listagem de Atas foi consultada com sucesso na API do BCB |
| `ata.processado` | bool | Se uma nova Ata foi encontrada, notificada e persistida |
| `ata.falhou` | bool | Se houve falha (esperada ou inesperada) no processamento da Ata |
| `duracao_segundos` | float | Duração total da execução, do início ao fim de `main()` |

### Regras

- `processado=True` implica `falhou=False` para o mesmo fluxo (mutuamente exclusivos).
- Uma falha em um fluxo nunca altera os campos do outro fluxo (FR-001) — cada fluxo
  reporta seu próprio resultado de forma independente.
- Este resumo é complementar aos logs detalhados já existentes (`logger.error`/`logger.info`
  por etapa) — ele não os substitui, apenas oferece uma visão consolidada no final.
