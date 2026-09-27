# Candlestick Pattern Library

## Objetivo

O motor de candlesticks do VazaoSovereignTrader transforma formações OHLCV em evidência contextual PAPER. Um padrão nunca é, por si só, uma autorização de ordem.

## Biblioteca atual

### Uma vela

- Doji
- Dragonfly Doji
- Gravestone Doji
- Spinning Top
- Hammer
- Inverted Hammer
- Hanging Man
- Shooting Star
- Bullish Marubozu
- Bearish Marubozu

### Duas velas

- Bullish Engulfing
- Bearish Engulfing
- Piercing Line
- Dark Cloud Cover
- Bullish Harami
- Bearish Harami
- Tweezer Bottom
- Tweezer Top

### Três velas

- Morning Star
- Evening Star
- Three Inside Up
- Three Inside Down
- Three White Soldiers
- Three Black Crows

### Cinco velas / continuação

- Rising Three Methods
- Falling Three Methods

## Contexto

O detector usa tendência, geometria do corpo/sombras e confirmação multi-vela. Não assume gaps rígidos como requisito universal porque o universo principal inclui mercados 24/7.

O mesmo padrão pode ter leituras diferentes conforme tendência, regime, localização estrutural, liquidez e confirmação posterior. Por isso a camada de candlesticks é combinada com regime, order flow, custos, confluence, evidence e Risk Engine.

## Evidência e aprendizagem

- PC_ENGINE/core/candlestick_patterns.py — detector/feature engine usado pela estratégia.
- PC_ENGINE/core/candlestick_evidence.py — camada de evidência PAPER para scoring e aprendizagem.

A expansão deve manter o vocabulário alinhado entre as duas camadas. A validação estatística posterior determina quais padrões têm utilidade por símbolo, regime, horizonte e cenário de custos.

## Segurança

Esta biblioteca não envia ordens, não altera o Risk Engine, não promove Champion/Challenger e não desbloqueia REAL. O valor operacional do padrão só existe depois de passar pelas restantes gates do sistema.
