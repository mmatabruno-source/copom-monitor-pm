import json

import pytest

from src import historico


@pytest.fixture
def historico_dir(tmp_path, monkeypatch):
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


def test_salvar_publicacao_grava_json_e_md(historico_dir):
    caminho_json, caminho_md = historico.salvar_publicacao(
        "comunicado", 270, {"selic_resultante": "10,50"}, "# Comunicado 270"
    )

    assert json.loads(open(caminho_json, encoding="utf-8").read()) == {
        "selic_resultante": "10,50"
    }
    assert open(caminho_md, encoding="utf-8").read() == "# Comunicado 270"


def test_carregar_publicacao_anterior_retorna_maior_numero_menor_que_atual(historico_dir):
    historico.salvar_publicacao("comunicado", 268, {"n": 268}, "# 268")
    historico.salvar_publicacao("comunicado", 269, {"n": 269}, "# 269")
    historico.salvar_publicacao("comunicado", 271, {"n": 271}, "# 271")  # posterior, deve ser ignorado

    anterior = historico.carregar_publicacao_anterior("comunicado", 270)

    assert anterior == {"n": 269}


def test_carregar_publicacao_anterior_retorna_none_quando_diretorio_nao_existe(historico_dir):
    assert historico.carregar_publicacao_anterior("ata", 270) is None


def test_carregar_publicacao_anterior_retorna_none_quando_nao_ha_publicacao_anterior(historico_dir):
    historico.salvar_publicacao("ata", 270, {"n": 270}, "# 270")

    assert historico.carregar_publicacao_anterior("ata", 270) is None


def test_carregar_publicacao_anterior_ignora_arquivos_com_nome_nao_numerico(historico_dir):
    diretorio = historico_dir / "comunicados"
    diretorio.mkdir(parents=True)
    (diretorio / "nao-e-numero.json").write_text("{}", encoding="utf-8")
    historico.salvar_publicacao("comunicado", 269, {"n": 269}, "# 269")

    anterior = historico.carregar_publicacao_anterior("comunicado", 270)

    assert anterior == {"n": 269}
