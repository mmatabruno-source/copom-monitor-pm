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


def extrair_secoes_ata(texto_ata_html):
    """Mantém o HTML estruturado em seções A/B/C/D conforme retornado pela API do BCB.

    A API já entrega o texto em seções; aqui apenas garantimos uma estrutura mínima
    (string não vazia) — o parsing fino de seções é feito pelo próprio prompt da Anthropic,
    que recebe o HTML diretamente (data-model.md, campo `texto_estruturado`).
    """
    if not texto_ata_html or not texto_ata_html.strip():
        raise ValueError("Texto da Ata vazio — não é possível gerar análise")
    return texto_ata_html


def gerar_analise_ata(texto_estruturado, analise_ata_anterior=None):
    instrucoes_comparacao = (
        "No item 4, compare explicitamente com a sinalização da Ata anterior fornecida abaixo, "
        "indicando o que mudou."
        if analise_ata_anterior
        else "Não há Ata anterior processada no histórico; omita qualquer comparação no item 4."
    )

    prompt = (
        "Você é um analista de investimentos. Com base na Ata do Copom abaixo, gere uma análise "
        "crítica em português com exatamente 6 itens, nesta ordem:\n"
        "1. Decisão objetiva — Selic, variação, votação\n"
        "2. Diagnóstico do Copom — atividade, inflação, expectativas Focus, fiscal, externo\n"
        "3. Balanço de riscos\n"
        f"4. Sinalização (forward guidance). {instrucoes_comparacao}\n"
        "5. Leitura por classe de ativo — renda fixa, câmbio, bolsa, crédito privado\n"
        "6. Sugestão de mensagem ao cliente (2-3 frases)\n\n"
        f"Texto da Ata atual:\n{texto_estruturado}"
    )

    if analise_ata_anterior:
        prompt += f"\n\nAnálise da Ata anterior (para comparação de tom):\n{analise_ata_anterior}"

    return _chamar_claude(prompt)
