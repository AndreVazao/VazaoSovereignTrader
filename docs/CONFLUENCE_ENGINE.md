# Confluence Engine

## Objetivo

O Confluence Engine junta evidências independentes antes de apresentar uma sugestão descritiva de BUY/SELL/HOLD.

Fluxo:

```text
EMA/VWAP/ATR + Candlesticks + Market Radar + Lead/Lag + Regime
                         ↓
                  Confluence Score
                         ↓
                    Risk Engine
                         ↓
                     Executor
```

O módulo não cria nem autoriza ordens. `paper_only=True` é permanente nesta fase.

## Pesos iniciais

- técnica: 40%
- candlesticks: 15%
- radar: 15%
- lead/lag: 20%
- regime: 10%

Os pesos são normalizados e podem ser configurados futuramente.

## Regras de segurança

1. Uma única fonte não pode gerar BUY/SELL.
2. São exigidas pelo menos duas fontes independentes alinhadas.
3. Evidências conflitantes reduzem o score.
4. Lead/lag sozinho nunca cria entrada.
5. O resultado é uma camada de evidência; o Risk Engine continua sendo a autoridade.
6. Antes de qualquer integração com REAL, deve existir validação out-of-sample/walk-forward com custos reais estimados.

## Execução

```text
python PC_ENGINE/tools/run_confluence_demo.py
```

Os testes foram adicionados, mas precisam ser executados no ambiente local/CI antes de considerar o módulo validado.
