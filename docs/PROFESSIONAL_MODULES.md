# Módulos profissionais adicionados

Estes módulos existem para preparar o VazaoSovereignTrader para operação real com menos risco operacional.

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

## Estado atual

Os módulos 1–6 já estão integrados no `PC_ENGINE/core/engine.py`.

Backtest, weekly reporter, champion/challenger e AI council já existem como blocos preparados. Champion/challenger e AI council stub já são referenciados pelo motor.

## Próximo passo técnico

Antes de REAL:

1. Testar no Windows 10.
2. Corrigir imports/path se necessário.
3. Rodar PAPER por 14 dias.
4. Validar relatórios.
5. Só depois preparar confirmação dupla para REAL.
