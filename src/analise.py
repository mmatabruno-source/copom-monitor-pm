import os

import anthropic

MODELO = "claude-sonnet-4-6"


class FalhaExternaAnthropic(Exception):
    pass


def _cliente():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    return anthropic.Anthropic(api_key=api_key)


def _chamar_claude(prompt):
    try:
        resposta = _cliente().messages.create(
            model=MODELO,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:  # qualquer erro da SDK (timeout, rate limit, 5xx) é falha externa
        raise FalhaExternaAnthropic(f"Falha na chamada à API da Anthropic: {exc}") from exc

    texto = "".join(bloco.text for bloco in resposta.content if hasattr(bloco, "text"))
    if not texto.strip():
        raise FalhaExternaAnthropic("Resposta vazia da API da Anthropic")

    return texto


def gerar_analise_comunicado(texto_bruto):
    prompt = (
        "Você é um analista de investimentos. Com base no Comunicado do Copom abaixo, "
        "gere uma análise em português com exatamente 2 itens, nesta ordem:\n"
        "1. Decisão objetiva — Selic resultante, variação em p.p., votação\n"
        "2. Sinalização (forward guidance) — tom hawkish/dovish/neutro\n\n"
        f"Texto do Comunicado:\n{texto_bruto}"
    )
    return _chamar_claude(prompt)
