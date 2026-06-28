import logging

from src.telegram import FalhaExternaTelegram, enviar_mensagem

logger = logging.getLogger(__name__)


def notificar_falha(contexto, erro):
    mensagem = f"⚠️ Falha em {contexto}: {erro}\nTentando novamente na próxima execução."
    logger.error(mensagem)
    try:
        enviar_mensagem(mensagem)
    except FalhaExternaTelegram as exc:
        logger.error("Falha ao notificar via Telegram (sem retry adicional): %s", exc)
