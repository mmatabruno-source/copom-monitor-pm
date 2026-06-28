# Contrato: Telegram Bot API

**Autenticação**: `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID` via GitHub Secrets.

## Envio de notificação

```
POST https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/sendMessage
Content-Type: application/json

{
  "chat_id": "<TELEGRAM_CHAT_ID>",
  "text": "<bloco de até 4096 caracteres>",
  "parse_mode": "Markdown"
}
```

## Regra de divisão de mensagens (FR-009)

Se o texto da análise exceder 4096 caracteres, dividir em N blocos sequenciais, cada um
enviado como uma chamada `sendMessage` separada, na ordem correta. Preferir quebrar em
limites de parágrafo (linha em branco) mais próximos do limite de 4096 caracteres, para
não cortar uma frase no meio.

## Resposta de sucesso

HTTP 200 com `{"ok": true, ...}`. Só após receber `ok: true` para **todos** os blocos de
uma publicação o sistema considera a notificação enviada com sucesso e atualiza
`estado.json` (ver data-model.md).

## Tratamento de erro

Qualquer falha (timeout, `ok: false`, erro 4xx/5xx) em qualquer bloco da sequência:
- A publicação NÃO é marcada como processada (mesmo que blocos anteriores tenham sido
  enviados com sucesso — para evitar uma notificação parcial silenciosa, o sistema
  trata a falha de qualquer bloco como falha de toda a notificação e tentará reenviar a
  sequência completa na próxima execução).
- Tentar notificar a falha via Telegram (FR-012) é, por definição, impossível se o
  próprio Telegram for o componente falho — nesse caso a falha é apenas registrada no
  log da execução do GitHub Actions, sem retry adicional dentro da mesma execução.
