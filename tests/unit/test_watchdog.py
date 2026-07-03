from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from src.watchdog import avaliar_execucoes


def _execucao(horas_atras, conclusion):
    momento = datetime.now(timezone.utc) - timedelta(hours=horas_atras)
    return {
        "created_at": momento.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "conclusion": conclusion,
    }


def test_execucao_recente_e_saudavel_nao_alerta():
    execucoes = [_execucao(1, "success"), _execucao(4, "success")]
    resultado = avaliar_execucoes(execucoes)
    assert resultado["deve_alertar"] is False
    assert resultado["motivo"] is None


def test_nenhuma_execucao_nao_alerta():
    resultado = avaliar_execucoes([])
    assert resultado["deve_alertar"] is False
    assert resultado["motivo"] is None
    assert resultado["ultima_execucao_em"] is None


def test_execucao_muito_antiga_alerta_ausencia():
    execucoes = [_execucao(31, "success")]
    resultado = avaliar_execucoes(execucoes)
    assert resultado["deve_alertar"] is True
    assert resultado["motivo"] == "sem_execucao_recente"


def test_ultimas_tres_falhas_alertam_falhas_repetidas():
    execucoes = [_execucao(1, "failure"), _execucao(4, "failure"), _execucao(7, "failure")]
    resultado = avaliar_execucoes(execucoes)
    assert resultado["deve_alertar"] is True
    assert resultado["motivo"] == "falhas_repetidas"


def test_execucao_em_andamento_e_ignorada_na_contagem_de_falhas():
    execucoes = [
        _execucao(1, None),
        _execucao(4, "failure"),
        _execucao(7, "failure"),
        _execucao(10, "failure"),
    ]
    resultado = avaliar_execucoes(execucoes)
    assert resultado["deve_alertar"] is True
    assert resultado["motivo"] == "falhas_repetidas"


@patch("src.watchdog.requests.get")
def test_resposta_de_erro_da_api_nao_gera_alerta_falso(mock_get):
    mock_get.return_value.status_code = 500

    from src.watchdog import consultar_execucoes

    resultado = consultar_execucoes("owner/repo", "token-teste")

    assert resultado is None


@patch("src.watchdog.requests.get")
def test_consultar_execucoes_retorna_lista_do_campo_workflow_runs(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        "workflow_runs": [{"created_at": "2026-07-01T00:00:00Z", "conclusion": "success"}]
    }

    from src.watchdog import consultar_execucoes

    resultado = consultar_execucoes("owner/repo", "token-teste")

    assert resultado == [{"created_at": "2026-07-01T00:00:00Z", "conclusion": "success"}]
