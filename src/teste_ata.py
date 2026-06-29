"""Script avulso para testar gerar_analise_ata contra uma Ata real do BCB, sem afetar
estado.json nem historico/. Uso: python -m src.teste_ata <nro_reuniao>
[--analise-anterior-de NRO_REUNIAO_ANTERIOR]
"""

import argparse
import json
import logging
from pathlib import Path

from src import bcb_client
from src.analise import extrair_secoes_ata, gerar_analise_ata
from src.telegram import enviar_mensagem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("nro_reuniao", type=int)
    parser.add_argument("--analise-anterior-de", type=int, default=None)
    args = parser.parse_args()

    analise_ata_anterior = None
    if args.analise_anterior_de is not None:
        caminho = Path(f"historico/atas/{args.analise_anterior_de}.json")
        if caminho.exists():
            analise_ata_anterior = json.loads(caminho.read_text()).get("analise")

    detalhes = bcb_client.detalhes_ata(args.nro_reuniao)
    texto_estruturado = extrair_secoes_ata(detalhes.get("textoAta", ""))
    data_publicacao = detalhes.get("dataPublicacao", "")

    mensagem1, mensagem2, mensagem3, mensagem4 = gerar_analise_ata(
        texto_estruturado, args.nro_reuniao, data_publicacao, analise_ata_anterior
    )

    enviar_mensagem(f"🧪 *TESTE — não afeta estado/histórico*\n\n{mensagem1}")
    enviar_mensagem(mensagem2)
    enviar_mensagem(mensagem3)
    enviar_mensagem(mensagem4)
    logger.info("Teste da Ata %s enviado com sucesso", args.nro_reuniao)


if __name__ == "__main__":
    main()
