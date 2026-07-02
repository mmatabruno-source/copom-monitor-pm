# Quickstart: Validação de Robustez e Resiliência Operacional

Guia para validar manualmente, após a implementação, que cada garantia desta feature
funciona de ponta a ponta. Pressupõe ambiente local com `pip install -r requirements.txt`.

## Pré-requisitos

- Repositório clonado, dependências instaladas.
- Variáveis de ambiente `ANTHROPIC_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
  não são necessárias para os testes automatizados (tudo mockado) — apenas para os
  passos manuais opcionais ao final.

## 1. Suíte de testes automatizados (cobre a maior parte das garantias)

```bash
pytest -q
```

**Esperado**: todos os testes passam, incluindo os novos:
- `tests/unit/test_bcb_client.py` — retry só ocorre para erro transitório (SC-002); erro
  permanente (404) não gera novas tentativas.
- `tests/unit/test_telegram.py` — retry por bloco não reenvia blocos já entregues
  (FR-005); token nunca aparece no texto de uma exceção (FR-006, SC-003).
- `tests/unit/test_analise.py`, `test_historico.py`, `test_notificar_falha.py` — cobrem
  sucesso e falha dos módulos antes sem testes (FR-008).
- `tests/integration/test_main_fluxo_completo.py` — cenário em que a Ata falha de forma
  inesperada depois do Comunicado já ter sido processado com sucesso: o estado do
  Comunicado continua salvo, e a execução não propaga a exceção (FR-001, FR-009, SC-001).

## 2. Verificar isolamento de falha manualmente

```bash
python -c "
from unittest.mock import patch
from src import main
with patch('src.main.verificar_comunicado', return_value=True), \
     patch('src.main.verificar_ata', side_effect=RuntimeError('bug simulado')):
    main.main()
"
echo \"código de saída: \$?\"
```

**Esperado**: o processo não propaga o `RuntimeError` (código de saída 0), confirmando
que o step "Commitar histórico" do workflow rodaria normalmente mesmo após essa falha.

## 3. Verificar ausência do token nos logs (manual, opcional)

```bash
TELEGRAM_BOT_TOKEN="token-fake-123" TELEGRAM_CHAT_ID="0" python -c "
import logging; logging.basicConfig(level=logging.ERROR)
from src.telegram import enviar_mensagem
try:
    enviar_mensagem('teste')
except Exception as exc:
    assert 'token-fake-123' not in str(exc), 'token vazou na exceção!'
    print('OK: token não vazou')
"
```

**Esperado**: imprime `OK: token não vazou` (a chamada real ao Telegram falha por token
inválido, mas a mensagem de erro não deve conter o valor do token).

## 4. Verificar resumo de execução no log

Rodar o passo 2 acima com `logging.basicConfig(level=logging.INFO)` e conferir que a
última linha de log é o resumo estruturado (FR-007), legível sem precisar abrir os logs
detalhados anteriores.

## 5. Dependências fixas

```bash
grep -E "==" requirements.txt
```

**Esperado**: as três linhas (`requests`, `anthropic`, `pytest`) têm versão exata
(`==`), não intervalo (SC-006).
