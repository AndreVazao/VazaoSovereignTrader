# Multi-Strategy Engine

O VazaoSovereignTrader recolhe evidência independente de duas estratégias adicionais em PAPER:

- **Momentum Multi-Timeframe**: EMA rápida/lenta e retorno recente em timeframes reais. Não cria candles de 5m/15m/1h/4h a partir de 1m.
- **Mean Reversion**: procura desvios do VWAP em regimes laterais e evita volatilidade alta.

## Fluxo

```text
OHLCV / regimes / radar
        |
        +--> Trend EMA/ATR + candlesticks
        +--> Momentum MTF
        +--> Mean Reversion
        +--> Lead/Lag
        +--> Regime
        |
        v
    CONFLUENCE
        |
        v
    RISK ENGINE
        |
        v
     EXECUTOR
```

As novas estratégias produzem apenas `StrategyEvidence`. Não têm acesso ao executor, não alteram limites de risco e não podem abrir posições isoladamente.

## Momentum MTF

Timeframes recomendados: `5m`, `15m`, `1h` e `4h`. A evidência só ganha força quando existe alinhamento em pelo menos dois timeframes. ATR é usado como filtro de atividade.

## Mean Reversion

Exige dados suficientes, desvio mínimo do VWAP e ATR dentro de uma faixa configurável. Em `FLAT_*` é permitida; em `HIGH` é bloqueada.

## Confluence

As duas estratégias entram como fontes independentes de evidência. Os pesos são normalizados e a regra de múltiplas evidências continua ativa. Contradições reduzem o score.

## Validação

Os testes estão em `tests/test_multi_strategy.py`. Esta fase continua **PAPER-only**. Os testes ainda não foram executados nesta alteração.
