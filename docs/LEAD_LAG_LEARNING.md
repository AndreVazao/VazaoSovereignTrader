# Lead/Lag Learning Engine

## Objetivo

Transformar os candidatos observados pelo WebSocket Market Radar em estatística verificável. O motor **não presume** que OKX, Binance, Coinbase ou qualquer outra exchange lidera o mercado; aprende relações por símbolo, direção, par líder/seguidor e horizonte.

## Fluxo

```text
websocket_events.jsonl
        +
websocket_lead_lag.jsonl
        |
        v
LeadLagLearningEngine
        |
        +--> 100 / 250 / 500 / 1000 / 2000 / 5000 ms
        +--> retorno futuro do follower
        +--> custos estimados (fee + slippage)
        +--> taxa de resposta + shrinkage
        +--> intervalo de confiança 95%
        v
lead_lag_learning.json
        |
        v
PAPER-only candidate signals
```

## Regra de elegibilidade

Uma relação só é marcada `eligible=true` quando tem pelo menos `min_samples` observações, expectativa líquida positiva e o limite inferior do intervalo de confiança de 95% também permanece positivo. Amostras pequenas são aproximadas de uma taxa neutra através de shrinkage.

Os custos padrão são 10 bps por lado de fee + 4 bps por lado de slippage, mas são configuráveis no runner. Isto é uma aproximação conservadora e deve ser substituída por custos reais da conta antes de qualquer decisão operacional.

## Segurança

- Sem API keys.
- Sem dados privados.
- Sem criação de ordens.
- Sem ligação ao executor.
- `eligible_signals()` devolve explicitamente `paper_only=true`.
- Resultado estatístico não significa previsão garantida nem vantagem negociável.

## Execução no Windows

```text
scripts\windows_run_lead_lag_learning.bat
```

Ou:

```text
.venv\Scripts\python.exe -m PC_ENGINE.tools.run_lead_lag_learning
```

## Próxima evolução

Antes de qualquer utilização operacional, acrescentar validação temporal out-of-sample, regimes de mercado, buckets de latência, deduplicação por trade-id quando disponível, sincronização de relógio e teste de custo/impacto real. Depois o módulo pode entrar como `challenger` do sistema de estratégias, continuando sem auto-switch.
