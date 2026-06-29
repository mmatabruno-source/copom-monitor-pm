"""Script avulso para testar gerar_mensagens_comunicado contra um Comunicado real do
BCB, sem afetar estado.json nem historico/. Uso: python -m src.teste_comunicado <nro_reuniao>
[--selic-anterior X] [--data-publicacao DD/MM/AAAA]
"""

import argparse
import logging

from src import bcb_client
from src.analise import gerar_mensagens_comunicado
from src.telegram import enviar_mensagem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("nro_reuniao", type=int)
    parser.add_argument("--selic-anterior", default=None)
    parser.add_argument("--data-publicacao", default=None)
    args = parser.parse_args()

    detalhes = bcb_client.detalhes_comunicado(args.nro_reuniao)
    texto_bruto = detalhes.get("textoComunicado", "")
    data_publicacao = args.data_publicacao or detalhes.get("dataReferencia", "")

    mensagem1, mensagem2 = gerar_mensagens_comunicado(
        texto_bruto, args.nro_reuniao, data_publicacao, args.selic_anterior
    )

    enviar_mensagem(f"🧪 *TESTE — não afeta estado/histórico*\n\n{mensagem1}")
    enviar_mensagem(mensagem2)
    logger.info("Teste do Comunicado %s enviado com sucesso", args.nro_reuniao)


if __name__ == "__main__":
    main()
