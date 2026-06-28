import logging

from src import bcb_client, estado, historico
from src.analise import (
    FalhaExternaAnthropic,
    extrair_secoes_ata,
    gerar_analise_ata,
    gerar_analise_comunicado,
)
from src.bcb_client import FalhaExternaBCB
from src.notificar_falha import notificar_falha
from src.telegram import FalhaExternaTelegram, enviar_mensagem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _renderizar_md_comunicado(comunicado, analise):
    return (
        f"# Comunicado — Reunião {comunicado['nro_reuniao']}\n\n"
        f"## Análise\n\n{analise}\n\n"
        f"## Dados\n\n"
        f"- Título: {comunicado.get('titulo')}\n"
        f"- Data de referência: {comunicado.get('dataReferencia')}\n"
        f"- Data de publicação: {comunicado.get('dataPublicacao')}\n\n"
        f"## Texto bruto\n\n{comunicado.get('texto_bruto', '')}\n"
    )


def _renderizar_md_ata(ata, analise):
    return (
        f"# Ata — Reunião {ata['nroReuniao']}\n\n"
        f"## Análise\n\n{analise}\n\n"
        f"## Dados\n\n"
        f"- Data de referência: {ata.get('dataReferencia')}\n"
        f"- Data de publicação: {ata.get('dataPublicacao')}\n"
        f"- PDF oficial: {ata.get('urlPdfAta')}\n\n"
        f"## Texto estruturado\n\n{ata.get('texto_estruturado', '')}\n"
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
    # Comunicado usa "nro_reuniao" (snake_case) — diferente de "nroReuniao" em Atas
    # (contracts/bcb-api.md, confirmado em 28/06/2026). Não assumir naming consistente.
    nro_reuniao = comunicado_recente["nro_reuniao"]

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


def verificar_ata():
    """Processa uma nova Ata, se houver. Retorna True se algo foi processado."""
    try:
        lista = bcb_client.listar_atas(quantidade=1)
    except FalhaExternaBCB as exc:
        logger.error("Falha ao listar Atas: %s", exc)
        notificar_falha("busca de Ata na API do BCB", exc)
        return False

    if not lista:
        return False

    ata_recente = lista[0]
    nro_reuniao = ata_recente["nroReuniao"]

    estado_atual = estado.carregar_estado()
    if estado_atual.get("ultima_ata") == nro_reuniao:
        return False  # já processado — idempotência (FR-010)

    try:
        detalhes = bcb_client.detalhes_ata(nro_reuniao)
    except FalhaExternaBCB as exc:
        logger.error("Falha ao buscar detalhes da Ata %s: %s", nro_reuniao, exc)
        notificar_falha(f"busca de detalhes da Ata {nro_reuniao}", exc)
        return False

    ata = {**ata_recente, **detalhes}
    try:
        texto_estruturado = extrair_secoes_ata(detalhes.get("textoAta", ""))
    except ValueError as exc:
        logger.error("Ata %s sem texto: %s", nro_reuniao, exc)
        notificar_falha(f"extração de seções da Ata {nro_reuniao}", exc)
        return False
    ata["texto_estruturado"] = texto_estruturado

    ata_anterior = historico.carregar_publicacao_anterior("ata", nro_reuniao)
    analise_ata_anterior = ata_anterior.get("analise") if ata_anterior else None

    try:
        analise = gerar_analise_ata(texto_estruturado, analise_ata_anterior)
    except FalhaExternaAnthropic as exc:
        logger.error("Falha ao gerar análise da Ata %s: %s", nro_reuniao, exc)
        notificar_falha(f"geração de análise da Ata {nro_reuniao}", exc)
        return False

    mensagem = f"📄 Nova Ata do Copom (Reunião {nro_reuniao})\n\n{analise}"
    try:
        enviar_mensagem(mensagem)
    except FalhaExternaTelegram as exc:
        logger.error("Falha ao notificar Ata %s via Telegram: %s", nro_reuniao, exc)
        return False

    ata["analise"] = analise
    md = _renderizar_md_ata(ata, analise)
    historico.salvar_publicacao("ata", nro_reuniao, ata, md)

    estado.salvar_estado(ultima_ata=nro_reuniao)
    return True


def main():
    # Comunicado e Ata são verificados de forma independente na mesma execução:
    # falha/sucesso em um não afeta o processamento do outro (spec.md, clarificação).
    verificar_comunicado()
    verificar_ata()


if __name__ == "__main__":
    main()
