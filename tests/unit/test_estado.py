import json

from src import estado


def test_salvar_ultimo_comunicado_nao_afeta_ultima_ata(tmp_path, monkeypatch):
    arquivo_estado = tmp_path / "estado.json"
    arquivo_estado.write_text(json.dumps({"ultima_ata": 268, "ultimo_comunicado": None}))
    monkeypatch.setattr(estado, "ESTADO_PATH", str(arquivo_estado))

    resultado = estado.salvar_estado(ultimo_comunicado=270)

    assert resultado["ultimo_comunicado"] == 270
    assert resultado["ultima_ata"] == 268


def test_salvar_ultima_ata_nao_afeta_ultimo_comunicado(tmp_path, monkeypatch):
    arquivo_estado = tmp_path / "estado.json"
    arquivo_estado.write_text(json.dumps({"ultima_ata": None, "ultimo_comunicado": 270}))
    monkeypatch.setattr(estado, "ESTADO_PATH", str(arquivo_estado))

    resultado = estado.salvar_estado(ultima_ata=271)

    assert resultado["ultima_ata"] == 271
    assert resultado["ultimo_comunicado"] == 270


def test_carregar_estado_quando_arquivo_nao_existe(tmp_path, monkeypatch):
    arquivo_estado = tmp_path / "nao-existe.json"
    monkeypatch.setattr(estado, "ESTADO_PATH", str(arquivo_estado))

    resultado = estado.carregar_estado()

    assert resultado == {"ultima_ata": None, "ultimo_comunicado": None}
