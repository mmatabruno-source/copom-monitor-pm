import json
from unittest.mock import patch

import pytest

from src import estado, main


@pytest.fixture
def estado_arquivo(tmp_path, monkeypatch):
    arquivo = tmp_path / "estado.json"
    arquivo.write_text(json.dumps({"ultima_ata": None, "ultimo_comunicado": None}))
    monkeypatch.setattr(estado, "ESTADO_PATH", str(arquivo))
    return arquivo


@pytest.fixture
def historico_dir(tmp_path, monkeypatch):
    from src import historico

    base = tmp_path / "historico"
    monkeypatch.setattr(historico, "HISTORICO_DIR", str(base))
    monkeypatch.setattr(
        historico,
        "DIRETORIO_POR_TIPO",
        {
            "comunicado": str(base / "comunicados"),
            "ata": str(base / "atas"),
        },
    )
    return base


COMUNICADO_LISTA = [{"nroReuniao": 270, "dataReferencia": "2026-06-24", "dataPublicacao": "2026-06-24T18:30:00"}]
COMUNICADO_DETALHES = {"texto_bruto": "Selic mantida em 10%, decisão unânime."}


def test_sem_novidade_nao_altera_estado_nem_notifica(estado_arquivo, historico_dir):
    estado.salvar_estado(ultimo_comunicado=270)

    with patch("src.bcb_client.listar_comunicados", return_value=COMUNICADO_LISTA), \
         patch("src.bcb_client.listar_atas", return_value=[]), \
         patch("src.main.enviar_mensagem") as mock_enviar:
        main.verificar_comunicado()

    mock_enviar.assert_not_called()
    assert estado.carregar_estado()["ultimo_comunicado"] == 270


def test_novidade_notifica_salva_historico_e_atualiza_estado(estado_arquivo, historico_dir):
    with patch("src.bcb_client.listar_comunicados", return_value=COMUNICADO_LISTA), \
         patch("src.bcb_client.detalhes_comunicado", return_value=COMUNICADO_DETALHES), \
         patch("src.main.gerar_analise_comunicado", return_value="1. Decisão: Selic 10%\n2. Tom: neutro"), \
         patch("src.main.enviar_mensagem") as mock_enviar:
        processado = main.verificar_comunicado()

    assert processado is True
    mock_enviar.assert_called_once()
    assert estado.carregar_estado()["ultimo_comunicado"] == 270
    assert (historico_dir / "comunicados" / "270.json").exists()
    assert (historico_dir / "comunicados" / "270.md").exists()


def test_idempotencia_segunda_execucao_nao_notifica(estado_arquivo, historico_dir):
    with patch("src.bcb_client.listar_comunicados", return_value=COMUNICADO_LISTA), \
         patch("src.bcb_client.detalhes_comunicado", return_value=COMUNICADO_DETALHES), \
         patch("src.main.gerar_analise_comunicado", return_value="análise"), \
         patch("src.main.enviar_mensagem"):
        main.verificar_comunicado()

    with patch("src.bcb_client.listar_comunicados", return_value=COMUNICADO_LISTA), \
         patch("src.main.enviar_mensagem") as mock_enviar_2:
        processado = main.verificar_comunicado()

    assert processado is False
    mock_enviar_2.assert_not_called()


def test_falha_externa_aborta_sem_marcar_processado(estado_arquivo, historico_dir):
    from src.analise import FalhaExternaAnthropic

    with patch("src.bcb_client.listar_comunicados", return_value=COMUNICADO_LISTA), \
         patch("src.bcb_client.detalhes_comunicado", return_value=COMUNICADO_DETALHES), \
         patch("src.main.gerar_analise_comunicado", side_effect=FalhaExternaAnthropic("chave inválida")), \
         patch("src.main.notificar_falha") as mock_notificar:
        processado = main.verificar_comunicado()

    assert processado is False
    assert estado.carregar_estado()["ultimo_comunicado"] is None
    mock_notificar.assert_called_once()


def test_reprocessa_apos_falha_quando_chamada_externa_volta_a_funcionar(estado_arquivo, historico_dir):
    from src.analise import FalhaExternaAnthropic

    with patch("src.bcb_client.listar_comunicados", return_value=COMUNICADO_LISTA), \
         patch("src.bcb_client.detalhes_comunicado", return_value=COMUNICADO_DETALHES), \
         patch("src.main.gerar_analise_comunicado", side_effect=FalhaExternaAnthropic("chave inválida")), \
         patch("src.main.notificar_falha"):
        main.verificar_comunicado()

    assert estado.carregar_estado()["ultimo_comunicado"] is None

    with patch("src.bcb_client.listar_comunicados", return_value=COMUNICADO_LISTA), \
         patch("src.bcb_client.detalhes_comunicado", return_value=COMUNICADO_DETALHES), \
         patch("src.main.gerar_analise_comunicado", return_value="análise ok"), \
         patch("src.main.enviar_mensagem") as mock_enviar:
        processado = main.verificar_comunicado()

    assert processado is True
    mock_enviar.assert_called_once()
    assert estado.carregar_estado()["ultimo_comunicado"] == 270
