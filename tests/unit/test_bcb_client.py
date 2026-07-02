from unittest.mock import Mock, patch

import pytest
import requests

from src.bcb_client import FalhaExternaBCB, _get


def _resposta(status_code, json_data=None, headers=None):
    resposta = Mock()
    resposta.status_code = status_code
    resposta.json.return_value = json_data or {}
    resposta.headers = headers or {}
    return resposta


@patch("src.bcb_client.time.sleep")
@patch("src.bcb_client.requests.get")
def test_erro_de_conexao_tenta_novamente_e_ao_final_levanta(mock_get, mock_sleep):
    mock_get.side_effect = requests.ConnectionError("instável")

    with pytest.raises(FalhaExternaBCB):
        _get("https://exemplo.com/atas", {})

    assert mock_get.call_count == 3
    assert mock_sleep.call_count == 2


@patch("src.bcb_client.time.sleep")
@patch("src.bcb_client.requests.get")
def test_status_5xx_tenta_novamente(mock_get, mock_sleep):
    mock_get.side_effect = [_resposta(503), _resposta(503), _resposta(200, {"conteudo": []})]

    resultado = _get("https://exemplo.com/atas", {})

    assert resultado == {"conteudo": []}
    assert mock_get.call_count == 3


@patch("src.bcb_client.time.sleep")
@patch("src.bcb_client.requests.get")
def test_status_404_e_permanente_nao_tenta_novamente(mock_get, mock_sleep):
    mock_get.return_value = _resposta(404)

    with pytest.raises(FalhaExternaBCB):
        _get("https://exemplo.com/atas_detalhes", {"nro_reuniao": 999})

    assert mock_get.call_count == 1
    mock_sleep.assert_not_called()


@patch("src.bcb_client.time.sleep")
@patch("src.bcb_client.requests.get")
def test_status_429_respeita_retry_after(mock_get, mock_sleep):
    mock_get.side_effect = [
        _resposta(429, headers={"Retry-After": "7"}),
        _resposta(200, {"conteudo": [{"nroReuniao": 1}]}),
    ]

    resultado = _get("https://exemplo.com/atas", {})

    assert resultado == {"conteudo": [{"nroReuniao": 1}]}
    mock_sleep.assert_called_once_with(7)


@patch("src.bcb_client.time.sleep")
@patch("src.bcb_client.requests.get")
def test_status_429_sem_retry_after_usa_backoff_padrao(mock_get, mock_sleep):
    mock_get.side_effect = [
        _resposta(429),
        _resposta(200, {"conteudo": []}),
    ]

    _get("https://exemplo.com/atas", {})

    mock_sleep.assert_called_once_with(2)
