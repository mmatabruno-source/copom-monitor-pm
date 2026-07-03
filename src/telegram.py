import os
import time

import requests

LIMITE_CARACTERES = 4096
TIMEOUT_SEGUNDOS = 30
TENTATIVAS = 3
ESPERA_INICIAL_SEGUNDOS = 2


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


def _sanitizar(texto, token):
    """Remove o token do bot de uma string antes que ela vire mensagem de erro/log —
    o token entra na própria URL da requisição, então qualquer exceção de rede ou corpo
    de resposta pode reproduzi-lo literalmente (FR-006).
    """
    if not token:
        return texto
    return texto.replace(token, "***")


def _erro_de_formatacao(resposta):
    return resposta is not None and resposta.status_code == 400 and (
        "can't parse entities" in resposta.text.lower()
    )


def _postar(texto, token, chat_id, com_formatacao):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": texto}
    if com_formatacao:
        payload["parse_mode"] = "Markdown"
    try:
        return requests.post(url, json=payload, timeout=TIMEOUT_SEGUNDOS)
    except requests.RequestException as exc:
        raise FalhaExternaTelegram(
            f"Falha de conexão com o Telegram: {_sanitizar(str(exc), token)}"
        ) from exc


def _verificar_sucesso(resposta, token):
    if resposta.status_code != 200 or not resposta.json().get("ok"):
        raise FalhaExternaTelegram(
            _sanitizar(
                f"Telegram retornou falha (status {resposta.status_code}): {resposta.text}",
                token,
            )
        )


def _enviar_bloco(texto, token, chat_id):
    resposta = _postar(texto, token, chat_id, com_formatacao=True)

    if _erro_de_formatacao(resposta):
        # O Telegram rejeitou a formatação Markdown do texto gerado pela LLM — em vez
        # de perder a notificação, reenviamos o mesmo bloco sem formatação especial.
        resposta = _postar(texto, token, chat_id, com_formatacao=False)

    _verificar_sucesso(resposta, token)


def _enviar_bloco_com_retry(bloco, token, chat_id):
    """Tenta enviar um único bloco até TENTATIVAS vezes. O retry é por bloco (não
    reinicia do primeiro bloco da mensagem), então um bloco já entregue com sucesso
    nunca é reenviado, mesmo que um bloco seguinte precise de novas tentativas.
    """
    ultimo_erro = None
    for tentativa in range(1, TENTATIVAS + 1):
        try:
            _enviar_bloco(bloco, token, chat_id)
            return
        except FalhaExternaTelegram as exc:
            ultimo_erro = exc
            if tentativa < TENTATIVAS:
                time.sleep(ESPERA_INICIAL_SEGUNDOS * tentativa)
    raise ultimo_erro


def enviar_mensagem(texto, token=None, chat_id=None):
    token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")

    blocos = _dividir_em_blocos(texto)
    for indice, bloco in enumerate(blocos, start=1):
        try:
            _enviar_bloco_com_retry(bloco, token, chat_id)
        except FalhaExternaTelegram as exc:
            raise FalhaExternaTelegram(
                f"Falha ao enviar bloco {indice}/{len(blocos)}: {exc}"
            ) from exc
