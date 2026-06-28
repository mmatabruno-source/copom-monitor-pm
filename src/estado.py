import json
import os

ESTADO_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "estado.json")


def carregar_estado():
    if not os.path.exists(ESTADO_PATH):
        return {"ultima_ata": None, "ultimo_comunicado": None}
    with open(ESTADO_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def salvar_estado(ultima_ata=None, ultimo_comunicado=None):
    estado = carregar_estado()
    if ultima_ata is not None:
        estado["ultima_ata"] = ultima_ata
    if ultimo_comunicado is not None:
        estado["ultimo_comunicado"] = ultimo_comunicado
    with open(ESTADO_PATH, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return estado
