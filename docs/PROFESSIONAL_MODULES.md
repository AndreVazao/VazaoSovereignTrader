# Módulos profissionais adicionados

Estes módulos existem para preparar o VazaoSovereignTrader para operação real com menos risco operacional e melhor qualidade de decisão.

## 1. Pre-flight checker

Arquivo: `PC_ENGINE/core/preflight.py`

Verifica antes do arranque:

- exchanges ativas;
- símbolos configurados;
- ticker válido;
- regras de mercado carregáveis;
- saldo disponível quando possível;
- avisos especiais em REAL.

Se `engine.preflight_required = true`, o motor bloqueia o start quando existem erros críticos.

## 2. Exchange Rules Engine

Arquivo: `PC_ENGINE/core/exchange_rules.py`

Normaliza e valida ordens com base nas regras reais da exchange:

- `min_qty`;
- `step_size`;
- `tick_size`;
- `min_notional`;
- precision de quantidade/preço.

Evita ordens inválidas antes de chegarem à exchange.

## 3. Paper Broker realista

Arquivo: `PC_ENGINE/core/paper_broker.py`

Simula:

- fees;
- slippage;
- spread;
- rejeição opcional.

Isto torna o PAPER menos fantasioso e mais próximo do REAL.

## 4. Order Manager

Arquivo: `PC_ENGINE/core/order_manager.py`

Centraliza execução:

- valida regras;
- bloqueia duplicados;
- executa paper fills;
- chama exchange real apenas quando `paper=false`.

## 5. Recovery Manager

Arquivo: `PC_ENGINE/core/recovery.py`

Guarda posições abertas em `PC_ENGINE/data/runtime_state.json`.

Ao reiniciar, tenta recuperar posições locais anteriores.

## 6. Watchdog

Arquivo: `PC_ENGINE/services/watchdog.py`

Verifica:

- internet;
- exchange/ticker.

Se falhar, o motor entra em `SAFE_MODE`.

## 7. Replay Backtester

Arquivo: `PC_ENGINE/backtest/replay.py`

Permite testar a estratégia contra candles históricos com:

- fees;
- slippage;
- P&L;
- drawdown;
- win/loss;
- profit factor.

## 8. Weekly Reporter

Arquivo: `PC_ENGINE/reports/weekly_report.py`

Gera relatórios JSON e CSV por semana com:

- trades;
- wins/losses;
- winrate;
- P&L;
- melhor/pior trade;
- P&L por ativo.

## 9. Champion / Challenger

Arquivo: `PC_ENGINE/learning/champion_challenger.py`

Permite comparar uma estratégia ativa contra estratégias alternativas em PAPER.

Regra: challenger nunca assume controlo automático. Apenas recomenda revisão.

## 10. AI Council stub

Arquivos:

- `PC_ENGINE/ai_council/stub.py`
- `PC_ENGINE/ai_council/decision_mapper.py`

Preparado para futura integração com TradingAgents.

Regra obrigatória:

```text
AI Council só sugere.
Risk Engine decide.
Executor age.
```

## 11. Sovereign Market Radar — arquitetura definida

Documento principal: `docs/SOVEREIGN_MARKET_RADAR.md`

O **Sovereign Market Radar (SMR)** será a camada central de inteligência de mercado. O objetivo é combinar dados de várias fontes em tempo real, estudar microestrutura e aprender relações de **lead/lag** entre mercados, sem assumir que uma exchange é sempre mais rápida que outra.

A arquitetura prevista inclui:

- streams/WebSockets oficiais quando disponíveis;
- cross-exchange intelligence;
- order flow e desequilíbrio de book;
- volume, spread e liquidez;
- open interest, funding, basis e liquidações quando disponíveis;
- notícias/eventos como contexto, nunca como ordem direta;
- análise multi-timeframe;
- Market Pressure Score;
- aprendizagem por símbolo e regime;
- medição de latência e qualidade dos timestamps;
- validação com fees, spread e slippage;
- out-of-sample e Champion/Challenger antes de qualquer influência em REAL.

O SMR **não executa ordens**. A cadeia continua:

```text
Market Radar -> evidência
Strategy     -> sinal candidato
AI Council  -> conselho opcional
Risk Engine -> autoriza/bloqueia
Executor    -> executa
```

Importante: uma diferença temporal entre exchanges não constitui automaticamente uma oportunidade. A vantagem só é considerada válida se sobreviver a latência, spread, fees, slippage, concorrência e testes fora da amostra.

## Estado atual

Os módulos 1–6 já estão integrados no `PC_ENGINE/core/engine.py`.

Backtest, weekly reporter, champion/challenger e AI council já existem como blocos preparados. Champion/challenger e AI council stub já são referenciados pelo motor.

O módulo de candlesticks também foi integrado como camada de confirmação da estratégia; os padrões não criam entradas isoladamente.

O **Sovereign Market Radar está documentado como arquitetura alvo**, mas **a implementação do radar, streams multi-exchange e Lead/Lag Engine ainda não deve ser considerada concluída**.

## Próximo passo técnico

Antes de REAL:

1. Testar no Windows 10.
2. Corrigir imports/path se necessário.
3. Rodar PAPER por 14 dias.
4. Validar relatórios.
5. Implementar e medir o Sovereign Market Radar primeiro em modo observacional/PAPER.
6. Só depois preparar confirmação dupla para REAL.
