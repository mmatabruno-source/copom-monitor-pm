import json
import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORICO_DIR = os.path.join(RAIZ, "historico")

DIRETORIO_POR_TIPO = {
    "comunicado": os.path.join(HISTORICO_DIR, "comunicados"),
    "ata": os.path.join(HISTORICO_DIR, "atas"),
}


def _caminho(tipo, nro_reuniao, extensao):
    diretorio = DIRETORIO_POR_TIPO[tipo]
    os.makedirs(diretorio, exist_ok=True)
    return os.path.join(diretorio, f"{nro_reuniao}.{extensao}")


def _escrever_atomico(caminho, conteudo):
    arquivo_temporario = f"{caminho}.tmp"
    with open(arquivo_temporario, "w", encoding="utf-8") as f:
        f.write(conteudo)
    os.replace(arquivo_temporario, caminho)  # grava tudo ou nada, nunca um arquivo pela metade


def salvar_publicacao(tipo, nro_reuniao, dados, markdown):
    caminho_json = _caminho(tipo, nro_reuniao, "json")
    _escrever_atomico(caminho_json, json.dumps(dados, ensure_ascii=False, indent=2) + "\n")

    caminho_md = _caminho(tipo, nro_reuniao, "md")
    _escrever_atomico(caminho_md, markdown)

    return caminho_json, caminho_md


def carregar_publicacao_anterior(tipo, nro_reuniao_atual):
    diretorio = DIRETORIO_POR_TIPO[tipo]
    if not os.path.isdir(diretorio):
        return None

    numeros = []
    for nome_arquivo in os.listdir(diretorio):
        if not nome_arquivo.endswith(".json"):
            continue
        try:
            numero = int(nome_arquivo[: -len(".json")])
        except ValueError:
            continue
        if numero < nro_reuniao_atual:
            numeros.append(numero)

    if not numeros:
        return None

    nro_anterior = max(numeros)
    caminho_json = _caminho(tipo, nro_anterior, "json")
    with open(caminho_json, "r", encoding="utf-8") as f:
        return json.load(f)
