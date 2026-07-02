import time

import requests

BASE_URL = "https://www.bcb.gov.br/api/servico/sitebcb/copom"
TIMEOUT_SEGUNDOS = 30
TENTATIVAS = 3
ESPERA_INICIAL_SEGUNDOS = 2


class FalhaExternaBCB(Exception):
    pass


def _retentavel(status_code):
    # 429 (limite de taxa) e 5xx (indisponibilidade momentânea) são tipicamente
    # transitórios; qualquer outro 4xx (ex.: 404) é permanente — insistir não ajuda.
    return status_code == 429 or status_code >= 500


def _espera_para_tentativa(resposta, tentativa):
    if resposta is not None and resposta.status_code == 429:
        retry_after = resposta.headers.get("Retry-After")
        if retry_after is not None:
            try:
                return float(retry_after)
            except ValueError:
                pass
    return ESPERA_INICIAL_SEGUNDOS * tentativa  # 2s, depois 4s


def _get(url, params):
    ultimo_erro = None
    for tentativa in range(1, TENTATIVAS + 1):
        resposta = None
        try:
            resposta = requests.get(url, params=params, timeout=TIMEOUT_SEGUNDOS)
        except requests.RequestException as exc:
            ultimo_erro = FalhaExternaBCB(f"Falha de conexão com a API do BCB: {exc}")
        else:
            if resposta.status_code < 400:
                return resposta.json()
            ultimo_erro = FalhaExternaBCB(
                f"API do BCB retornou status {resposta.status_code} para {url}"
            )
            if not _retentavel(resposta.status_code):
                raise ultimo_erro

        if tentativa < TENTATIVAS:
            time.sleep(_espera_para_tentativa(resposta, tentativa))

    raise ultimo_erro


def listar_atas(quantidade=1):
    # Confirmado em 28/06/2026 (contracts/bcb-api.md): resposta envelopada em "conteudo",
    # mesmo padrão de Comunicados. Identificador "nroReuniao" (camelCase, confirmado).
    resposta = _get(f"{BASE_URL}/atas", {"quantidade": quantidade})
    return resposta.get("conteudo", [])


def detalhes_ata(nro_reuniao):
    # Confirmado em 28/06/2026: também envelopado em "conteudo", como lista de um único
    # item. Campo de texto: "textoAta" (HTML, seções A/B/C/D).
    resposta = _get(f"{BASE_URL}/atas_detalhes", {"nro_reuniao": nro_reuniao})
    itens = resposta.get("conteudo", [])
    return itens[0] if itens else {}


def listar_comunicados(quantidade=1):
    # Confirmado em 28/06/2026 (contracts/bcb-api.md): a resposta vem envelopada em
    # "conteudo" e o identificador é "nro_reuniao" (snake_case) — diferente de Atas.
    resposta = _get(f"{BASE_URL}/comunicados", {"quantidade": quantidade})
    return resposta.get("conteudo", [])


def detalhes_comunicado(nro_reuniao):
    # Confirmado em 28/06/2026 (contracts/bcb-api.md): resposta também envelopada em
    # "conteudo", como lista de um único item (mesmo padrão da listagem). Campo de
    # texto: "textoComunicado" (HTML). Sem campos estruturados de Selic/variação/votação.
    resposta = _get(f"{BASE_URL}/comunicados_detalhes", {"nro_reuniao": nro_reuniao})
    itens = resposta.get("conteudo", [])
    return itens[0] if itens else {}
