from unittest.mock import patch

from src.notificar_falha import notificar_falha
from src.telegram import FalhaExternaTelegram


@patch("src.notificar_falha.enviar_mensagem")
def test_notificar_falha_envia_mensagem_formatada(mock_enviar_mensagem):
    notificar_falha("busca de detalhes da Ata 270", RuntimeError("instável"))

    mensagem = mock_enviar_mensagem.call_args.args[0]
    assert "busca de detalhes da Ata 270" in mensagem
    assert "instável" in mensagem


@patch("src.notificar_falha.enviar_mensagem")
def test_notificar_falha_nao_relanca_quando_o_proprio_telegram_falha(mock_enviar_mensagem):
    mock_enviar_mensagem.side_effect = FalhaExternaTelegram("Telegram indisponível")

    notificar_falha("busca de detalhes do Comunicado 270", RuntimeError("instável"))  # não deve levantar

    mock_enviar_mensagem.assert_called_once()
