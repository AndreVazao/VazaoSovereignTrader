# Evolução PAPER → REAL

O trader só pode chegar a REAL por etapas verificáveis. Nenhuma camada de aprendizagem ou IA pode contornar o Risk Engine, o Executor ou os bloqueios de segurança.

## Fase 0 — PAPER controlado
- Radar, WebSocket, derivados e Market State ativos.
- Confluence e State Outcome recolhem evidência.
- Fees, slippage e rejeições simulados.
- Sem capital real.

## Fase 1 — PAPER validado
- Walk-forward e validação por regime positivos.
- Expectancy líquida positiva após custos.
- Sem dependência de um único sinal/exchange.
- Champion/Challenger permanece sem auto-switch.
- Watchdog e recovery testados.

## Fase 2 — REAL protegido, capital mínimo
- Apenas Spot.
- Apenas Read + Spot Trade.
- Withdrawals desativados.
- Futures/leverage desativados.
- Allowlist de símbolos.
- Limites de exposição inferiores aos limites PAPER.
- Kill switch físico/lógico.
- Confirmação explícita do operador antes de ativar REAL.
- Logs e ledger de cada ordem.

## Fase 3 — REAL gradual
- Aumento de capital apenas após métricas estáveis.
- Hard stops de perda diária/semanal mantidos.
- Nenhum aumento automático de risco baseado apenas em lucro recente.
- Reavaliação periódica por regime, slippage e qualidade de execução.

## Fase 4 — REAL adaptativo sob governança
- Challenger só pode ser promovido por regra explícita e revisão dos dados.
- Alterações de estratégia/configuração ficam versionadas.
- Degradação estatística força redução ou PAUSE, nunca aumento de risco.

## Gate obrigatório
`Market State → Outcome Validation → Readiness Gate → Risk Engine → RealModeGuard → Order Manager → Exchange`

O `RealReadinessGate` apenas classifica o estado como `LOCKED` ou `READY_FOR_PROTECTED_REAL_REVIEW`. Não ativa REAL.

O AI Council pode aconselhar, mas nunca executa, altera limites de risco ou desbloqueia REAL.

## Critérios que não autorizam REAL
- sequência curta de lucro;
- backtest isolado;
- win rate sem custos;
- resultado de um único ativo ou exchange;
- score elevado de IA sem evidência estatística;
- aprovação do Readiness Gate sem confirmação e guard operacional separados.
