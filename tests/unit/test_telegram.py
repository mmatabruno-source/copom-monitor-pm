from unittest.mock import patch

import pytest
import requests

from src.telegram import (
    TENTATIVAS,
    FalhaExternaTelegram,
    _dividir_em_blocos,
    _enviar_bloco,
    enviar_mensagem,
)


def test_texto_curto_gera_um_unico_bloco():
    texto = "decisão objetiva\n\nsinalização"
    assert _dividir_em_blocos(texto) == [texto]


def test_texto_longo_e_dividido_em_blocos_por_paragrafo():
    paragrafo = "x" * 2000
    texto = "\n\n".join([paragrafo] * 3)
    blocos = _dividir_em_blocos(texto)

    assert len(blocos) > 1
    for bloco in blocos:
        assert len(bloco) <= 4096
    assert "".join(blocos).replace("\n\n", "") == texto.replace("\n\n", "")


@patch("src.telegram._enviar_bloco")
def test_enviar_mensagem_envia_todos_os_blocos_na_ordem(mock_enviar_bloco):
    paragrafo = "y" * 2000
    texto = "\n\n".join([paragrafo] * 3)

    enviar_mensagem(texto, token="tok", chat_id="123")

    blocos_enviados = [chamada.args[0] for chamada in mock_enviar_bloco.call_args_list]
    assert blocos_enviados == _dividir_em_blocos(texto)


@patch("src.telegram.time.sleep")
@patch("src.telegram._enviar_bloco")
def test_falha_transitoria_em_um_bloco_tenta_novamente_sem_reenviar_blocos_anteriores(
    mock_enviar_bloco, mock_sleep
):
    texto = "\n\n".join(letra * 4090 for letra in "abc")  # 3 blocos distintos e próximos do limite
    blocos = _dividir_em_blocos(texto)

    # bloco 1: sucesso de primeira. bloco 2: falha e depois sucesso. bloco 3: sucesso de primeira.
    mock_enviar_bloco.side_effect = [
        None,
        FalhaExternaTelegram("instável"),
        None,
        None,
    ]

    enviar_mensagem(texto, token="tok", chat_id="123")

    chamadas = [chamada.args[0] for chamada in mock_enviar_bloco.call_args_list]
    assert chamadas == [blocos[0], blocos[1], blocos[1], blocos[2]]
    assert chamadas.count(blocos[0]) == 1  # bloco já entregue nunca é reenviado


@patch("src.telegram.time.sleep")
@patch("src.telegram._enviar_bloco")
def test_falha_persistente_em_um_bloco_propaga_apos_tentativas(mock_enviar_bloco, mock_sleep):
    mock_enviar_bloco.side_effect = FalhaExternaTelegram("indisponível")

    with pytest.raises(FalhaExternaTelegram):
        enviar_mensagem("texto curto", token="tok", chat_id="123")

    assert mock_enviar_bloco.call_count == TENTATIVAS


@patch("src.telegram.requests.post")
def test_falha_de_conexao_nao_expoe_o_token_na_excecao(mock_post):
    token = "123456:SEGREDO-DO-BOT"
    mock_post.side_effect = requests.ConnectionError(
        f"Max retries exceeded with url: /bot{token}/sendMessage"
    )

    with pytest.raises(FalhaExternaTelegram) as excinfo:
        _enviar_bloco("texto", token, "123")

    assert token not in str(excinfo.value)


@patch("src.telegram.requests.post")
def test_falha_de_status_nao_expoe_o_token_na_excecao(mock_post):
    token = "123456:SEGREDO-DO-BOT"
    resposta = mock_post.return_value
    resposta.status_code = 401
    resposta.json.return_value = {"ok": False}
    resposta.text = f"Unauthorized: bot{token} não existe"

    with pytest.raises(FalhaExternaTelegram) as excinfo:
        _enviar_bloco("texto", token, "123")

    assert token not in str(excinfo.value)


def _resposta(status_code, texto):
    resposta = type("Resposta", (), {})()
    resposta.status_code = status_code
    resposta.text = texto
    resposta.json = lambda: {"ok": status_code == 200, "description": texto}
    return resposta


@patch("src.telegram.requests.post")
def test_erro_de_formatacao_reenvia_o_mesmo_bloco_em_texto_simples(mock_post):
    mock_post.side_effect = [
        _resposta(400, "Bad Request: can't parse entities: character '_' is reserved"),
        _resposta(200, "ok"),
    ]

    _enviar_bloco("texto *mal* formatado", "tok", "123")

    assert mock_post.call_count == 2
    primeira_chamada, segunda_chamada = mock_post.call_args_list
    assert "parse_mode" in primeira_chamada.kwargs["json"]
    assert "parse_mode" not in segunda_chamada.kwargs["json"]


@patch("src.telegram.requests.post")
def test_erro_de_formatacao_com_nova_falha_em_texto_simples_propaga_erro(mock_post):
    mock_post.side_effect = [
        _resposta(400, "Bad Request: can't parse entities: character '_' is reserved"),
        _resposta(500, "Internal Server Error"),
    ]

    with pytest.raises(FalhaExternaTelegram):
        _enviar_bloco("texto *mal* formatado", "tok", "123")


@patch("src.telegram.requests.post")
def test_erro_de_formatacao_em_bloco_posterior_nao_reenvia_bloco_ja_entregue(mock_post):
    paragrafo = "z" * 3000
    texto = "\n\n".join([paragrafo] * 2)
    blocos = _dividir_em_blocos(texto)

    mock_post.side_effect = [
        _resposta(200, "ok"),  # bloco 1: sucesso de primeira
        _resposta(400, "Bad Request: can't parse entities"),  # bloco 2: erro de formatação
        _resposta(200, "ok"),  # bloco 2: sucesso em texto simples
    ]

    enviar_mensagem(texto, token="tok", chat_id="123")

    assert mock_post.call_count == 3
    textos_enviados = [chamada.kwargs["json"]["text"] for chamada in mock_post.call_args_list]
    assert textos_enviados == [blocos[0], blocos[1], blocos[1]]
