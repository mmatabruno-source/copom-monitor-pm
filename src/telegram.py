import os

import requests

LIMITE_CARACTERES = 4096
TIMEOUT_SEGUNDOS = 30


class FalhaExternaTelegram(Exception):
    pass


def _dividir_em_blocos(texto, limite=LIMITE_CARACTERES):
    if len(texto) <= limite:
        return [texto]

    blocos = []
    restante = texto
    while len(restante) > limite:
        corte = restante.rfind("\n\n", 0, limite)
        if corte == -1:
            corte = limite
        blocos.append(restante[:corte].rstrip("\n"))
        restante = restante[corte:].lstrip("\n")
    if restante:
        blocos.append(restante)
    return blocos


def _enviar_bloco(texto, token, chat_id):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": texto, "parse_mode": "Markdown"}
    try:
        resposta = requests.post(url, json=payload, timeout=TIMEOUT_SEGUNDOS)
    except requests.RequestException as exc:
        raise FalhaExternaTelegram(f"Falha de conexão com o Telegram: {exc}") from exc

    if resposta.status_code != 200 or not resposta.json().get("ok"):
        raise FalhaExternaTelegram(
            f"Telegram retornou falha (status {resposta.status_code}): {resposta.text}"
        )


def enviar_mensagem(texto, token=None, chat_id=None):
    token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")

    blocos = _dividir_em_blocos(texto)
    for indice, bloco in enumerate(blocos, start=1):
        try:
            _enviar_bloco(bloco, token, chat_id)
        except FalhaExternaTelegram as exc:
            # Se a mensagem foi dividida em vários blocos e falhar no meio, os blocos
            # anteriores já foram entregues — uma nova tentativa reenvia a mensagem
            # inteira, podendo duplicar o início. Risco aceito (raro e de baixo impacto),
            # mas registrado explicitamente para facilitar diagnóstico se ocorrer.
            raise FalhaExternaTelegram(
                f"Falha ao enviar bloco {indice}/{len(blocos)}: {exc}"
            ) from exc
