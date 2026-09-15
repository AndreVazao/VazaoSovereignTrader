# State Outcome Engine

Camada PAPER que mede o que aconteceu depois de cada `MarketState` com ação BUY/SELL.

## Métrica

Para cada símbolo, ação, regime e horizonte:

`net_bps = directional_return_bps - round_trip_cost_bps`

Horizontes padrão: 1s, 5s, 15s, 1m e 5m.

A saída agrega amostras, win rate, média, mediana e limite inferior aproximado de 95%.

Uma combinação só fica `eligible` quando cumpre simultaneamente o mínimo de amostras, expectancy líquida positiva, win rate mínimo e limite inferior positivo.

## Segurança

É uma camada de observação/aprendizagem. Não cria ordens, não altera o Risk Engine e não desbloqueia REAL.
