from unittest.mock import patch

from src.telegram import _dividir_em_blocos, enviar_mensagem


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
