from unittest.mock import patch

import pytest

from src.analise import (
    TENTATIVAS_ANTHROPIC,
    _cliente,
    extrair_secoes_ata,
    extrair_selic_resultante,
)


@patch("src.analise.anthropic.Anthropic")
def test_cliente_usa_retry_nativo_do_sdk(mock_anthropic_cls):
    _cliente()

    _, kwargs = mock_anthropic_cls.call_args
    assert kwargs["max_retries"] == TENTATIVAS_ANTHROPIC


def test_extrair_selic_resultante_encontra_valor():
    mensagem = "▪️ *Antes:* 10,50% a.a.\n▪️ *Depois:* 10,75% a.a."
    assert extrair_selic_resultante(mensagem) == "10,75"


def test_extrair_selic_resultante_retorna_none_em_formato_inesperado():
    assert extrair_selic_resultante("texto sem o rótulo esperado") is None


def test_extrair_secoes_ata_retorna_texto_quando_preenchido():
    html = "<p>Seção A: diagnóstico.</p>"
    assert extrair_secoes_ata(html) == html


def test_extrair_secoes_ata_levanta_erro_quando_vazio():
    with pytest.raises(ValueError):
        extrair_secoes_ata("")

    with pytest.raises(ValueError):
        extrair_secoes_ata("   ")
