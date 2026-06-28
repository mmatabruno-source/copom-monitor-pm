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
    # PENDÊNCIA TÉCNICA (T005, contracts/bcb-api.md): URL e payload ainda não confirmados
    # manualmente — hipótese análoga ao endpoint de Atas. Validar com curl antes de usar
    # contra a API real.
    return _get(f"{BASE_URL}/comunicados", {"quantidade": quantidade})


def detalhes_comunicado(nro_reuniao):
    # PENDÊNCIA TÉCNICA (T005, contracts/bcb-api.md): mesma ressalva de listar_comunicados.
    return _get(f"{BASE_URL}/comunicados_detalhes", {"nro_reuniao": nro_reuniao})
