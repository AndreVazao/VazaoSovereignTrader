# WebSocket Market Radar — Fase 1.5

## Estado

A camada nativa de WebSocket foi adicionada ao projeto para recolha **pública e observacional** de trades.

Implementação:

- `PC_ENGINE/radar/websocket_radar.py`
- `PC_ENGINE/tools/run_websocket_radar.py`
- `scripts/windows_run_websocket_radar.bat`
- `tests/test_websocket_radar.py`

Dependência adicional:

```text
websocket-client>=1.8.0
```

## Adapters atuais

- Binance spot `@trade`;
- Coinbase Advanced Trade `market_trades`;
- OKX spot `trades`.

BingX e Bybit continuam previstos para adapters dedicados depois de validar os primeiros dados. Não se deve fingir que todos os streams têm a mesma semântica ou relógio.

## Dados recolhidos

Cada evento normalizado contém:

- exchange;
- símbolo;
- preço;
- quantidade;
- lado/agressor quando fornecido;
- timestamp da exchange;
- timestamp de receção no PC;
- latência de receção observada;
- preço anterior da mesma venue;
- movimento em basis points quando calculável.

Os eventos são persistidos em:

```text
PC_ENGINE/data/radar/websocket_events.jsonl
PC_ENGINE/data/radar/websocket_lead_lag.jsonl
```

A pasta `data/` deve permanecer fora do Git.

## Lead/Lag

Um candidato só é registado quando:

1. existe movimento mínimo configurado;
2. existe movimento na outra venue;
3. a direção coincide;
4. os timestamps da fonte estão dentro da janela configurada;
5. o evento anterior e o seguinte podem ser comparados.

Defaults:

```text
min_move_bps = 5
lead_window_ms = 750
```

Estes valores são parâmetros experimentais, **não uma afirmação de vantagem económica**.

## Como executar

Windows:

```text
scripts\windows_run_websocket_radar.bat
```

CLI:

```bash
python -m PC_ENGINE.tools.run_websocket_radar --symbols BTC/USDT,ETH/USDT --exchanges binance,coinbase,okx
```

Teste curto:

```bash
python -m PC_ENGINE.tools.run_websocket_radar --symbols BTC/USDT --exchanges binance,okx --seconds 60
```

## Regra de segurança

O WebSocket Radar:

- não usa API keys;
- não lê saldos;
- não autentica contas;
- não cria ordens;
- não altera a estratégia;
- não influencia REAL.

É exclusivamente uma fonte de observação para a fase de aprendizagem.

## Próxima evolução

Depois de recolher dados reais, o próximo módulo deverá calcular estatísticas por:

- par leader/follower;
- símbolo;
- direção;
- janela de atraso;
- volatilidade;
- tendência/range;
- hora/sessão;
- liquidez;
- custos estimados;
- exchange de execução.

Só depois disso o Radar poderá gerar sinais PAPER. A promoção para REAL exige Champion/Challenger e validação out-of-sample.

## Nota sobre relógios

Timestamp da exchange e timestamp local não são equivalentes a uma medição de latência do matching engine. O sistema deve medir a cadeia completa e considerar sincronização do relógio, rede, processamento, filas, spread, fees, slippage e concorrência.
