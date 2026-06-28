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
        "Você é um analista de investimentos especializado em política monetária brasileira, "
        "escrevendo para uma mensagem de Telegram. Use Markdown do Telegram (*negrito*, sem "
        "cabeçalhos #, sem tabelas). Com base no Comunicado do Copom abaixo, escreva em "
        "português, direto e sem introduções genéricas, com exatamente estas duas seções, "
        "nesta ordem:\n\n"
        "*Decisão do Copom*\n"
        "- Selic resultante e variação em p.p.\n"
        "- Votação (unânime ou dividida)\n\n"
        "*Sinalização*\n"
        "- O que o tom da comunicação indica sobre os próximos passos da política monetária\n\n"
        "Regras:\n"
        "- Sempre que usar jargão de mercado (Selic, p.p., hawkish/dovish, forward guidance "
        "etc.), explique brevemente entre parênteses na primeira vez que aparecer.\n"
        "- Seja direto, sem redundância.\n\n"
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


SEPARADOR_ATA = "===DETALHE==="


def gerar_analise_ata(texto_estruturado, analise_ata_anterior=None):
    """Retorna (resumo, detalhe): duas mensagens distintas para o Telegram.

    `resumo` é curto e escaneável (decisão + sugestão de investimento + leitura por ativo);
    `detalhe` é mais longo mas direto, sem repetir o conteúdo do resumo.
    """
    instrucoes_comparacao = (
        "Compare explicitamente com a sinalização da Ata anterior fornecida abaixo, "
        "indicando o que mudou."
        if analise_ata_anterior
        else "Não há Ata anterior processada no histórico; omita qualquer comparação."
    )

    prompt = (
        "Você é um analista de investimentos especializado em política monetária brasileira, "
        "escrevendo para mensagens de Telegram. Use Markdown do Telegram (*negrito*, sem "
        "cabeçalhos #, sem tabelas). Com base na Ata do Copom abaixo, gere DUAS mensagens "
        "distintas em português. Separe-as exatamente com uma linha contendo só "
        f"\"{SEPARADOR_ATA}\" (nada mais nessa linha).\n\n"
        "MENSAGEM 1 — resumo executivo, curto e escaneável (poucas frases por seção), "
        "nesta ordem:\n"
        "*Decisão do Copom*: retome muito brevemente a decisão (Selic, variação, votação) "
        "em 1-2 frases.\n"
        "*Sugestão para investimentos*: 2-3 frases objetivas e acionáveis sobre como "
        "posicionar portfólio diante dessa decisão.\n"
        "*Leitura por classe de ativo*: bullets curtos para renda fixa, câmbio, bolsa e "
        "crédito privado.\n\n"
        f"{SEPARADOR_ATA}\n\n"
        "MENSAGEM 2 — análise completa, direta e acionável, sem repetir o que já foi dito "
        "na Mensagem 1, nesta ordem:\n"
        "*Diagnóstico do Copom*: só os pontos de atividade, inflação, expectativas Focus "
        "(pesquisa de mercado com projeções econômicas), fiscal e externo que são relevantes "
        "para decisão de portfólio.\n"
        "*Balanço de riscos*: principais riscos de alta e de baixa para a Selic.\n"
        f"*Sinalização (forward guidance)*: o que o Copom indicou sobre os próximos passos. "
        f"{instrucoes_comparacao}\n"
        "*Mensagem pronta para cliente*: 2-3 frases que o leitor pode copiar e adaptar para "
        "comunicar a um cliente.\n\n"
        "Regras para as duas mensagens:\n"
        "- Sempre que usar jargão (Selic, p.p., hawkish/dovish, Focus, forward guidance etc.), "
        "explique brevemente entre parênteses na primeira vez que aparecer em cada mensagem.\n"
        "- Seja direto e acionável: cada seção deve ajudar a decidir algo, não só descrever.\n"
        "- Não inclua introduções genéricas.\n\n"
        f"Texto da Ata atual:\n{texto_estruturado}"
    )

    if analise_ata_anterior:
        prompt += f"\n\nAnálise da Ata anterior (para comparação de tom):\n{analise_ata_anterior}"

    texto = _chamar_claude(prompt)

    if SEPARADOR_ATA in texto:
        resumo, detalhe = texto.split(SEPARADOR_ATA, 1)
    else:  # fallback defensivo — não deveria ocorrer, mas evita perder a notificação
        resumo, detalhe = texto, ""

    return resumo.strip(), detalhe.strip()
