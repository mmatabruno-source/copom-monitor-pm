"""Script avulso para testar gerar_mensagens_comunicado contra um Comunicado real do
BCB, sem afetar estado.json nem historico/. Uso: python -m src.teste_comunicado <nro_reuniao>
[--selic-anterior X] [--data-publicacao DD/MM/AAAA] [--mensagens 1,2]
"""

import argparse
import logging

from src import bcb_client, historico
from src.analise import extrair_selic_resultante, gerar_mensagens_comunicado
from src.telegram import enviar_mensagem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _buscar_selic_anterior_na_api(nro_reuniao):
    """Fallback para quando não há histórico local: gera a mensagem do Comunicado
    anterior diretamente a partir da API do BCB só para extrair a Selic resultante.
    """
    nro_anterior = nro_reuniao - 1
    detalhes_anterior = bcb_client.detalhes_comunicado(nro_anterior)
    texto_anterior = detalhes_anterior.get("textoComunicado", "")
    if not texto_anterior:
        return None

    data_anterior = detalhes_anterior.get("dataReferencia", "")
    mensagem1_anterior, _ = gerar_mensagens_comunicado(
        texto_anterior, nro_anterior, data_anterior, None
    )
    return extrair_selic_resultante(mensagem1_anterior)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("nro_reuniao", type=int)
    parser.add_argument("--selic-anterior", default=None)
    parser.add_argument("--data-publicacao", default=None)
    parser.add_argument(
        "--mensagens",
        default="1,2",
        help="Quais mensagens enviar, separadas por vírgula (ex.: 2 ou 1,2). Padrão: 1,2.",
    )
    args = parser.parse_args()
    mensagens_a_enviar = {int(m) for m in args.mensagens.split(",")}

    selic_anterior = args.selic_anterior
    if selic_anterior is None:
        comunicado_anterior = historico.carregar_publicacao_anterior(
            "comunicado", args.nro_reuniao
        )
        if comunicado_anterior:
            selic_anterior = comunicado_anterior.get("selic_resultante")
    if selic_anterior is None:
        logger.info(
            "Sem histórico local — buscando Selic anterior via Comunicado da reunião %s na API do BCB",
            args.nro_reuniao - 1,
        )
        selic_anterior = _buscar_selic_anterior_na_api(args.nro_reuniao)

    detalhes = bcb_client.detalhes_comunicado(args.nro_reuniao)
    texto_bruto = detalhes.get("textoComunicado", "")
    data_publicacao = args.data_publicacao or detalhes.get("dataReferencia", "")

    mensagem1, mensagem2 = gerar_mensagens_comunicado(
        texto_bruto, args.nro_reuniao, data_publicacao, selic_anterior
    )

    prefixo = "🧪 *TESTE — não afeta estado/histórico*\n\n"
    if 1 in mensagens_a_enviar:
        enviar_mensagem(f"{prefixo}{mensagem1}")
        prefixo = ""
    if 2 in mensagens_a_enviar:
        enviar_mensagem(f"{prefixo}{mensagem2}" if prefixo else mensagem2)
    logger.info("Teste do Comunicado %s enviado com sucesso", args.nro_reuniao)


if __name__ == "__main__":
    main()
