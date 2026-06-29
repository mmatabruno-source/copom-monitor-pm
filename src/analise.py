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


SEPARADOR_COMUNICADO = "===DETALHE_COMUNICADO==="


def gerar_mensagens_comunicado(texto_bruto, nro_reuniao, data_publicacao, selic_anterior=None):
    """Retorna (mensagem1, mensagem2): duas mensagens distintas para o Telegram.

    `mensagem1` é a decisão objetiva (Selic antes/depois); `mensagem2` é a explicação
    do tom, leitura prática e justificativas. O balanço de riscos de alta/baixa não entra
    aqui — fica reservado para a análise da Ata, publicada na semana seguinte.
    """
    contexto_selic_anterior = (
        f"A taxa Selic vigente antes desta reunião era {selic_anterior}% a.a.; use esse valor "
        "como \"Antes\"."
        if selic_anterior is not None
        else "Não há registro confiável da taxa Selic anterior a esta reunião. Extraia-a do "
        "próprio texto do Comunicado somente se ela estiver explicitamente mencionada; caso "
        "contrário, omita as linhas \"Antes\" e \"O Copom reduziu/elevou/manteve...\" desta "
        "mensagem, mantendo apenas o valor resultante da Selic."
    )

    prompt = (
        "Você é um analista de investimentos especializado em política monetária brasileira, "
        "escrevendo para mensagens de Telegram. Use Markdown do Telegram (*negrito*, sem "
        "cabeçalhos #, sem tabelas). Com base no Comunicado do Copom abaixo, gere DUAS "
        "mensagens distintas em português. Separe-as exatamente com uma linha contendo só "
        f"\"{SEPARADOR_COMUNICADO}\" (nada mais nessa linha).\n\n"
        f"{contexto_selic_anterior}\n\n"
        "MENSAGEM 1 — decisão objetiva, seguindo EXATAMENTE este formato (preencha os "
        "colchetes, mantenha os emojis e a formatação em negrito com um único asterisco). "
        "Siga o template literalmente: não adicione nenhuma explicação de jargão, parênteses "
        "ou qualquer texto além do especificado abaixo:\n\n"
        f"📢 *Decisão do Copom (R. {nro_reuniao}) - {data_publicacao}*\n\n"
        "📉 O Copom [reduziu/elevou/manteve] a Selic em [X] p.p.\n"
        "▪️ *Antes:* [taxa anterior]% a.a.\n"
        "▪️ *Depois:* [taxa resultante]% a.a.\n\n"
        f"{SEPARADOR_COMUNICADO}\n\n"
        "MENSAGEM 2 — explicações do Copom, seguindo EXATAMENTE esta estrutura (preencha o "
        "conteúdo, mantenha os emojis e a formatação em negrito):\n\n"
        "ℹ️ *Explicações do Copom*\n\n"
        "🗣️ *Tom do comunicado*: no máximo 1 frase curta e direta descrevendo o tom, evitando "
        "jargão (ex.: prefira \"cauteloso e sem sinalização explícita sobre os próximos "
        "passos\" a \"hawkish/dovish\" ou \"forward guidance\"), comparando com o padrão de "
        "comunicação anterior quando fizer sentido.\n\n"
        "💡 *Leitura prática*: no máximo 1 frase curta e direta sobre o que isso significa na "
        "prática para o ritmo dos próximos passos da política monetária.\n\n"
        "📍 *Justificativas apresentadas*:\n\n"
        "Bullets com \"▪️\" (no MÁXIMO 5 — selecione e condense apenas os motivos mais "
        "relevantes para uma decisão de portfólio, mesmo que o Comunicado apresente mais "
        "pontos), cada um em UMA frase curta reescrevendo o motivo apresentado pelo Copom — o "
        "porquê, não só o fato —, sem desdobramentos, contexto adicional ou exemplos.\n\n"
        f"Resumo feito com Claude Sonnet 4.6 a partir do comunicado de {data_publicacao} do "
        "Banco Central. Na próxima semana, você receberá maiores explicações, partindo da "
        "Ata emitida pelo próprio Bacen.\n\n"
        "Regras para a Mensagem 2:\n"
        "- Contorne termos difíceis sempre que houver alternativa simples em português (ex.: "
        "prefira \"preço do dólar\" a \"câmbio\", \"juros\" a termos técnicos evitáveis, "
        "\"sem sinalização explícita sobre os próximos passos\" a \"forward guidance\"). "
        "Não explique jargão entre parênteses — quando um termo for realmente inevitável "
        "(ex.: Selic, p.p.), use-o direto, sem explicação. A pesquisa Focus deve ser sempre "
        "referida apenas como \"pesquisa Focus\", sem explicação adicional.\n\n"
        "Regras para as duas mensagens:\n"
        "- Priorize concisão acima de tudo: frases curtas e diretas, cortando qualquer "
        "informação que não seja essencial para uma decisão de portfólio.\n"
        "- Seja direto, sem introduções genéricas e sem redundância entre as duas mensagens.\n\n"
        f"Texto do Comunicado:\n{texto_bruto}"
    )

    texto = _chamar_claude(prompt)

    if SEPARADOR_COMUNICADO in texto:
        mensagem1, mensagem2 = texto.split(SEPARADOR_COMUNICADO, 1)
    else:  # fallback defensivo — não deveria ocorrer, mas evita perder a notificação
        mensagem1, mensagem2 = texto, ""

    return mensagem1.strip(), mensagem2.strip()


def extrair_secoes_ata(texto_ata_html):
    """Mantém o HTML estruturado em seções A/B/C/D conforme retornado pela API do BCB.

    A API já entrega o texto em seções; aqui apenas garantimos uma estrutura mínima
    (string não vazia) — o parsing fino de seções é feito pelo próprio prompt da Anthropic,
    que recebe o HTML diretamente (data-model.md, campo `texto_estruturado`).
    """
    if not texto_ata_html or not texto_ata_html.strip():
        raise ValueError("Texto da Ata vazio — não é possível gerar análise")
    return texto_ata_html


SEPARADOR_ATA_1 = "===RISCOS==="
SEPARADOR_ATA_2 = "===DIAGNOSTICO==="
SEPARADOR_ATA_3 = "===EXPECTATIVAS==="


def gerar_analise_ata(texto_estruturado, nro_reuniao, data_publicacao, analise_ata_anterior=None):
    """Retorna (mensagem1, mensagem2, mensagem3, mensagem4): quatro mensagens distintas
    para o Telegram, sem repetir conteúdo entre si.
    """
    instrucoes_comparacao = (
        "Compare explicitamente com a análise da Ata anterior fornecida abaixo, indicando "
        "o que mudou na sinalização do Copom."
        if analise_ata_anterior
        else "Não há Ata anterior processada no histórico; omita qualquer comparação."
    )

    prompt = (
        "Você é um analista de investimentos especializado em política monetária brasileira, "
        "escrevendo para mensagens de Telegram. Use Markdown do Telegram (*negrito*, sem "
        "cabeçalhos #, sem tabelas). Com base na Ata do Copom abaixo, gere QUATRO mensagens "
        "distintas em português. Separe-as exatamente com uma linha contendo só o separador "
        "indicado entre cada uma (nada mais nessa linha).\n\n"
        "MENSAGEM 1 — resumo executivo, curto e escaneável, nesta ordem:\n"
        f"🔎 *Ata do Copom (R. {nro_reuniao}) - {data_publicacao}*\n\n"
        "🗣️ *Decisão*: retome muito brevemente a decisão (Selic, variação, votação) em "
        "1-2 frases.\n\n"
        "💰 *Impacto nos Investimentos*: 2-3 frases objetivas e acionáveis sobre como "
        "posicionar portfólio diante dessa decisão.\n\n"
        "📊 *Leitura por classe de ativo*:\n\n"
        "Bullets com \"▪️\" para renda fixa pós fixada, renda fixa prefixada/IPCA+, preço "
        "do dólar / câmbio, bolsa e crédito privado, cada um em 1 frase curta.\n\n"
        f"{SEPARADOR_ATA_1}\n\n"
        "MENSAGEM 2 — balanço de riscos, sem repetir o que já foi dito na Mensagem 1:\n\n"
        "🔴 *Risco de ALTA para a inflação*:\n\n"
        "Bullets com \"▪️ (i)\", \"▪️ (ii)\" etc., usando exatamente a mesma quantidade de "
        "itens numerados no texto original da Ata para os riscos de alta — nem mais nem "
        "menos —, cada um em UMA frase curta reescrevendo o mecanismo causal, sem "
        "desdobramentos, contexto adicional ou exemplos.\n\n"
        "🟢 *Risco de BAIXA para a inflação*:\n\n"
        "Bullets com \"▪️ (i)\", \"▪️ (ii)\" etc., usando exatamente a mesma quantidade de "
        "itens numerados no texto original da Ata para os riscos de baixa — nem mais nem "
        "menos —, cada um em UMA frase curta reescrevendo o mecanismo causal, sem "
        "desdobramentos, contexto adicional ou exemplos.\n\n"
        "➡️ *Conclusão*: 1 frase indicando se o balanço está assimétrico (para cima ou para "
        "baixo) ou equilibrado, conforme indicado pelo Copom.\n\n"
        f"{SEPARADOR_ATA_2}\n\n"
        "MENSAGEM 3 — diagnóstico econômico, sem repetir o que já foi dito nas mensagens "
        "anteriores:\n\n"
        "🏦 *Diagnóstico econômico*:\n\n"
        "Bullets com \"▪️\" e subtítulo em negrito, cobrindo apenas os tópicos (entre "
        "Atividade, Mercado de trabalho, Inflação, Pesquisa Focus, Fiscal e Cenário externo) "
        "que a Ata efetivamente trata e que são relevantes para uma decisão de portfólio — "
        "omita os que não tiverem conteúdo relevante. Cada bullet deve ser direto e "
        "informativo, sem se limitar a 1 frase quando o conteúdo exigir mais detalhe.\n\n"
        f"{SEPARADOR_ATA_3}\n\n"
        "MENSAGEM 4 — expectativas para próximas decisões, sem repetir o que já foi dito nas "
        "mensagens anteriores:\n\n"
        "📍 *Expectativas para próximas decisões*: o que o Copom indicou sobre o ritmo ou "
        f"direção dos próximos passos. {instrucoes_comparacao}\n\n"
        "Regras para as quatro mensagens:\n"
        "- Contorne termos difíceis sempre que houver alternativa simples em português (ex.: "
        "prefira \"preço do dólar\" a \"câmbio\", \"sem sinalização explícita sobre os "
        "próximos passos\" a \"forward guidance\", evite \"hawkish/dovish\"). Não explique "
        "jargão entre parênteses — quando um termo for realmente inevitável (ex.: Selic, "
        "p.p.), use-o direto, sem explicação. A pesquisa Focus deve ser sempre referida apenas "
        "como \"pesquisa Focus\", sem explicação adicional.\n"
        "- Seja direto e acionável: cada seção deve ajudar a decidir algo, não só descrever.\n"
        "- Não inclua introduções genéricas.\n\n"
        f"Texto da Ata atual:\n{texto_estruturado}"
    )

    if analise_ata_anterior:
        prompt += f"\n\nAnálise da Ata anterior (para comparação de tom):\n{analise_ata_anterior}"

    texto = _chamar_claude(prompt)

    partes = texto.split(SEPARADOR_ATA_1, 1)
    mensagem1 = partes[0]
    resto = partes[1] if len(partes) > 1 else ""

    partes = resto.split(SEPARADOR_ATA_2, 1)
    mensagem2 = partes[0]
    resto = partes[1] if len(partes) > 1 else ""

    partes = resto.split(SEPARADOR_ATA_3, 1)
    mensagem3 = partes[0]
    mensagem4 = partes[1] if len(partes) > 1 else ""

    return mensagem1.strip(), mensagem2.strip(), mensagem3.strip(), mensagem4.strip()
