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


COMUNICADO_LISTA = [{"nro_reuniao": 270, "dataReferencia": "2026-06-24", "titulo": "270ª reunião"}]
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
         patch(
             "src.main.gerar_mensagens_comunicado",
             return_value=("📢 Decisão: Selic 10%", "ℹ️ Explicações: tom neutro"),
         ), \
         patch("src.main.enviar_mensagem") as mock_enviar:
        processado = main.verificar_comunicado()

    assert processado is True
    assert mock_enviar.call_count == 2
    assert estado.carregar_estado()["ultimo_comunicado"] == 270
    assert (historico_dir / "comunicados" / "270.json").exists()
    assert (historico_dir / "comunicados" / "270.md").exists()


def test_idempotencia_segunda_execucao_nao_notifica(estado_arquivo, historico_dir):
    with patch("src.bcb_client.listar_comunicados", return_value=COMUNICADO_LISTA), \
         patch("src.bcb_client.detalhes_comunicado", return_value=COMUNICADO_DETALHES), \
         patch("src.main.gerar_mensagens_comunicado", return_value=("decisão", "explicação")), \
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
         patch(
             "src.main.gerar_mensagens_comunicado",
             side_effect=FalhaExternaAnthropic("chave inválida"),
         ), \
         patch("src.main.notificar_falha") as mock_notificar:
        processado = main.verificar_comunicado()

    assert processado is False
    assert estado.carregar_estado()["ultimo_comunicado"] is None
    mock_notificar.assert_called_once()


def test_selic_anterior_usa_historico_local_quando_disponivel(estado_arquivo, historico_dir):
    from src import historico

    historico.salvar_publicacao(
        "comunicado", 269, {"selic_resultante": "10,50"}, "# Comunicado 269"
    )

    with patch("src.bcb_client.listar_comunicados", return_value=COMUNICADO_LISTA), \
         patch("src.bcb_client.detalhes_comunicado", return_value=COMUNICADO_DETALHES), \
         patch("src.main.buscar_selic_anterior_via_api") as mock_fallback_api, \
         patch(
             "src.main.gerar_mensagens_comunicado", return_value=("decisão", "explicação")
         ) as mock_gerar, \
         patch("src.main.enviar_mensagem"):
        main.verificar_comunicado()

    mock_fallback_api.assert_not_called()  # histórico local existe — não precisa da API
    assert mock_gerar.call_args.args[3] == "10,50"


def test_selic_anterior_busca_via_api_quando_nao_ha_historico_local(estado_arquivo, historico_dir):
    with patch("src.bcb_client.listar_comunicados", return_value=COMUNICADO_LISTA), \
         patch("src.bcb_client.detalhes_comunicado", return_value=COMUNICADO_DETALHES), \
         patch("src.main.buscar_selic_anterior_via_api", return_value="10,75") as mock_fallback_api, \
         patch(
             "src.main.gerar_mensagens_comunicado", return_value=("decisão", "explicação")
         ) as mock_gerar, \
         patch("src.main.enviar_mensagem"):
        main.verificar_comunicado()

    mock_fallback_api.assert_called_once_with(270)  # cold start — busca na API do BCB
    assert mock_gerar.call_args.args[3] == "10,75"


def test_selic_anterior_segue_sem_falha_quando_fallback_via_api_quebra(estado_arquivo, historico_dir):
    from src.bcb_client import FalhaExternaBCB

    with patch("src.bcb_client.listar_comunicados", return_value=COMUNICADO_LISTA), \
         patch("src.bcb_client.detalhes_comunicado", return_value=COMUNICADO_DETALHES), \
         patch(
             "src.main.buscar_selic_anterior_via_api", side_effect=FalhaExternaBCB("instável")
         ), \
         patch(
             "src.main.gerar_mensagens_comunicado", return_value=("decisão", "explicação")
         ) as mock_gerar, \
         patch("src.main.enviar_mensagem") as mock_enviar:
        processado = main.verificar_comunicado()

    # Selic anterior é um enriquecimento opcional — sua falha não trava o Comunicado.
    assert processado is True
    mock_enviar.assert_called()
    assert mock_gerar.call_args.args[3] is None


ATA_LISTA = [
    {"nroReuniao": 270, "dataReferencia": "2026-06-23", "dataPublicacao": "2026-06-30"}
]
ATA_DETALHES = {"textoAta": "<p>Seção A: diagnóstico.</p>"}


def test_ata_sem_novidade_nao_altera_estado_nem_notifica(estado_arquivo, historico_dir):
    estado.salvar_estado(ultima_ata=270)

    with patch("src.bcb_client.listar_atas", return_value=ATA_LISTA), \
         patch("src.main.enviar_mensagem") as mock_enviar:
        processado = main.verificar_ata()

    assert processado is False
    mock_enviar.assert_not_called()


def test_ata_novidade_notifica_salva_historico_e_atualiza_estado(estado_arquivo, historico_dir):
    with patch("src.bcb_client.listar_atas", return_value=ATA_LISTA), \
         patch("src.bcb_client.detalhes_ata", return_value=ATA_DETALHES), \
         patch(
             "src.main.gerar_analise_ata",
             return_value=("resumo", "riscos", "diagnóstico", "expectativas"),
         ), \
         patch("src.main.enviar_mensagem") as mock_enviar:
        processado = main.verificar_ata()

    assert processado is True
    assert mock_enviar.call_count == 4
    assert estado.carregar_estado()["ultima_ata"] == 270
    assert (historico_dir / "atas" / "270.json").exists()
    assert (historico_dir / "atas" / "270.md").exists()


def test_ata_idempotencia_segunda_execucao_nao_notifica(estado_arquivo, historico_dir):
    with patch("src.bcb_client.listar_atas", return_value=ATA_LISTA), \
         patch("src.bcb_client.detalhes_ata", return_value=ATA_DETALHES), \
         patch(
             "src.main.gerar_analise_ata",
             return_value=("resumo", "riscos", "diagnóstico", "expectativas"),
         ), \
         patch("src.main.enviar_mensagem"):
        main.verificar_ata()

    with patch("src.bcb_client.listar_atas", return_value=ATA_LISTA), \
         patch("src.main.enviar_mensagem") as mock_enviar_2:
        processado = main.verificar_ata()

    assert processado is False
    mock_enviar_2.assert_not_called()


def test_ata_falha_externa_aborta_sem_marcar_processado(estado_arquivo, historico_dir):
    from src.analise import FalhaExternaAnthropic

    with patch("src.bcb_client.listar_atas", return_value=ATA_LISTA), \
         patch("src.bcb_client.detalhes_ata", return_value=ATA_DETALHES), \
         patch(
             "src.main.gerar_analise_ata",
             side_effect=FalhaExternaAnthropic("chave inválida"),
         ), \
         patch("src.main.notificar_falha") as mock_notificar:
        processado = main.verificar_ata()

    assert processado is False
    assert estado.carregar_estado()["ultima_ata"] is None
    mock_notificar.assert_called_once()


def test_ata_sem_texto_aborta_sem_marcar_processado(estado_arquivo, historico_dir):
    with patch("src.bcb_client.listar_atas", return_value=ATA_LISTA), \
         patch("src.bcb_client.detalhes_ata", return_value={"textoAta": ""}), \
         patch("src.main.notificar_falha") as mock_notificar:
        processado = main.verificar_ata()

    assert processado is False
    assert estado.carregar_estado()["ultima_ata"] is None
    mock_notificar.assert_called_once()


def test_reprocessa_apos_falha_quando_chamada_externa_volta_a_funcionar(estado_arquivo, historico_dir):
    from src.analise import FalhaExternaAnthropic

    with patch("src.bcb_client.listar_comunicados", return_value=COMUNICADO_LISTA), \
         patch("src.bcb_client.detalhes_comunicado", return_value=COMUNICADO_DETALHES), \
         patch(
             "src.main.gerar_mensagens_comunicado",
             side_effect=FalhaExternaAnthropic("chave inválida"),
         ), \
         patch("src.main.notificar_falha"):
        main.verificar_comunicado()

    assert estado.carregar_estado()["ultimo_comunicado"] is None

    with patch("src.bcb_client.listar_comunicados", return_value=COMUNICADO_LISTA), \
         patch("src.bcb_client.detalhes_comunicado", return_value=COMUNICADO_DETALHES), \
         patch(
             "src.main.gerar_mensagens_comunicado",
             return_value=("decisão ok", "explicação ok"),
         ), \
         patch("src.main.enviar_mensagem") as mock_enviar:
        processado = main.verificar_comunicado()

    assert processado is True
    assert mock_enviar.call_count == 2
    assert estado.carregar_estado()["ultimo_comunicado"] == 270
