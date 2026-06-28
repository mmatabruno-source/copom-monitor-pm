import requests

BASE_URL = "https://www.bcb.gov.br/api/servico/sitebcb/copom"
TIMEOUT_SEGUNDOS = 30


class FalhaExternaBCB(Exception):
    pass


def _get(url, params):
    try:
        resposta = requests.get(url, params=params, timeout=TIMEOUT_SEGUNDOS)
    except requests.RequestException as exc:
        raise FalhaExternaBCB(f"Falha de conexão com a API do BCB: {exc}") from exc

    if resposta.status_code >= 400:
        raise FalhaExternaBCB(
            f"API do BCB retornou status {resposta.status_code} para {url}"
        )

    return resposta.json()


def listar_atas(quantidade=1):
    return _get(f"{BASE_URL}/atas", {"quantidade": quantidade})


def detalhes_ata(nro_reuniao):
    return _get(f"{BASE_URL}/atas_detalhes", {"nro_reuniao": nro_reuniao})


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
