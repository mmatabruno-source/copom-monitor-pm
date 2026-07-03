import logging
import os
from datetime import datetime, timedelta, timezone

import requests

from src.notificar_falha import notificar_falha

WORKFLOW = "monitor-copom.yml"
TIMEOUT_SEGUNDOS = 30
LIMITE_HORAS_SEM_EXECUCAO = 30
QUANTIDADE_PARA_FALHAS_REPETIDAS = 3

logger = logging.getLogger(__name__)


def consultar_execucoes(repositorio, token):
    """Retorna a lista de execuções recentes do workflow principal, mais recente
    primeiro, ou None se a consulta à API do GitHub falhar (contracts/github-actions-api.md).
    """
    url = f"https://api.github.com/repos/{repositorio}/actions/workflows/{WORKFLOW}/runs"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    try:
        resposta = requests.get(
            url, headers=headers, params={"per_page": 5}, timeout=TIMEOUT_SEGUNDOS
        )
    except requests.RequestException as exc:
        logger.error("Falha ao consultar execuções do workflow no GitHub: %s", exc)
        return None

    if resposta.status_code != 200:
        logger.error(
            "API do GitHub Actions retornou status %s ao listar execuções", resposta.status_code
        )
        return None

    return resposta.json().get("workflow_runs", [])


def avaliar_execucoes(execucoes):
    """Decide se deve alertar a partir da lista de execuções (data-model.md)."""
    if not execucoes:
        return {"deve_alertar": False, "motivo": None, "ultima_execucao_em": None}

    ultima_execucao_em = execucoes[0]["created_at"]
    momento_ultima = datetime.strptime(ultima_execucao_em, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc
    )
    if datetime.now(timezone.utc) - momento_ultima > timedelta(hours=LIMITE_HORAS_SEM_EXECUCAO):
        return {
            "deve_alertar": True,
            "motivo": "sem_execucao_recente",
            "ultima_execucao_em": ultima_execucao_em,
        }

    concluidas = [execucao for execucao in execucoes if execucao.get("conclusion") is not None]
    ultimas = concluidas[:QUANTIDADE_PARA_FALHAS_REPETIDAS]
    if len(ultimas) == QUANTIDADE_PARA_FALHAS_REPETIDAS and all(
        execucao["conclusion"] == "failure" for execucao in ultimas
    ):
        return {
            "deve_alertar": True,
            "motivo": "falhas_repetidas",
            "ultima_execucao_em": ultima_execucao_em,
        }

    return {"deve_alertar": False, "motivo": None, "ultima_execucao_em": ultima_execucao_em}


MENSAGEM_POR_MOTIVO = {
    "sem_execucao_recente": "nenhuma execução bem-sucedida recente do workflow principal",
    "falhas_repetidas": "as últimas execuções do workflow principal falharam repetidamente",
}


def main():
    repositorio = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")

    execucoes = consultar_execucoes(repositorio, token)
    if execucoes is None:
        return

    resultado = avaliar_execucoes(execucoes)
    if resultado["deve_alertar"]:
        notificar_falha(
            "verificação de saúde do monitoramento", MENSAGEM_POR_MOTIVO[resultado["motivo"]]
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
