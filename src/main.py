import logging

from src import bcb_client, estado, historico
from src.analise import FalhaExternaAnthropic, gerar_analise_comunicado
from src.bcb_client import FalhaExternaBCB
from src.notificar_falha import notificar_falha
from src.telegram import FalhaExternaTelegram, enviar_mensagem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _renderizar_md_comunicado(comunicado, analise):
    return (
        f"# Comunicado — Reunião {comunicado['nroReuniao']}\n\n"
        f"## Análise\n\n{analise}\n\n"
        f"## Dados\n\n"
        f"- Data de referência: {comunicado.get('dataReferencia')}\n"
        f"- Data de publicação: {comunicado.get('dataPublicacao')}\n\n"
        f"## Texto bruto\n\n{comunicado.get('texto_bruto', '')}\n"
    )


def verificar_comunicado():
    """Processa um novo Comunicado, se houver. Retorna True se algo foi processado."""
    try:
        lista = bcb_client.listar_comunicados(quantidade=1)
    except FalhaExternaBCB as exc:
        logger.error("Falha ao listar Comunicados: %s", exc)
        notificar_falha("busca de Comunicado na API do BCB", exc)
        return False

    if not lista:
        return False

    comunicado_recente = lista[0]
    nro_reuniao = comunicado_recente["nroReuniao"]

    estado_atual = estado.carregar_estado()
    if estado_atual.get("ultimo_comunicado") == nro_reuniao:
        return False  # já processado — idempotência (FR-010)

    try:
        detalhes = bcb_client.detalhes_comunicado(nro_reuniao)
    except FalhaExternaBCB as exc:
        logger.error("Falha ao buscar detalhes do Comunicado %s: %s", nro_reuniao, exc)
        notificar_falha(f"busca de detalhes do Comunicado {nro_reuniao}", exc)
        return False

    comunicado = {**comunicado_recente, **detalhes}
    texto_bruto = comunicado.get("texto_bruto") or comunicado.get("textoComunicado", "")

    try:
        analise = gerar_analise_comunicado(texto_bruto)
    except FalhaExternaAnthropic as exc:
        logger.error("Falha ao gerar análise do Comunicado %s: %s", nro_reuniao, exc)
        notificar_falha(f"geração de análise do Comunicado {nro_reuniao}", exc)
        return False

    mensagem = f"📢 Novo Comunicado do Copom (Reunião {nro_reuniao})\n\n{analise}"
    try:
        enviar_mensagem(mensagem)
    except FalhaExternaTelegram as exc:
        logger.error("Falha ao notificar Comunicado %s via Telegram: %s", nro_reuniao, exc)
        return False

    comunicado["analise"] = analise
    md = _renderizar_md_comunicado(comunicado, analise)
    historico.salvar_publicacao("comunicado", nro_reuniao, comunicado, md)

    estado.salvar_estado(ultimo_comunicado=nro_reuniao)
    return True


def main():
    verificar_comunicado()


if __name__ == "__main__":
    main()
