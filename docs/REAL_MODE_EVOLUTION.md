# Evolução PAPER → REAL

O trader só pode chegar a REAL por etapas verificáveis. Nenhuma camada de aprendizagem ou IA pode contornar o Risk Engine, o Executor ou os bloqueios de segurança.

## Fase 0 — PAPER controlado
- Radar, WebSocket, derivados e Market State ativos.
- Confluence e State Outcome recolhem evidência.
- Fees, slippage e rejeições simulados.
- Sem capital real.

**Saída:** dados suficientes para validar qualidade operacional e estatística.

## Fase 1 — PAPER validado
- Walk-forward e validação por regime positivos.
- Expectancy líquida positiva após custos.
- Sem dependência de um único sinal/exchange.
- Champion/Challenger permanece sem auto-switch.
- Watchdog e recovery testados.

**Saída:** aprovação manual para sandbox/conta de teste quando disponível.

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

**Saída:** estabilidade operacional real durante período de observação.

## Fase 3 — REAL gradual
- Aumento de capital apenas após métricas estáveis.
- Limites de perda diária/semanal mantidos como hard stops.
- Nenhum aumento automático de risco baseado apenas em lucro recente.
- Reavaliação periódica por regime, slippage e qualidade de execução.

## Fase 4 — REAL adaptativo sob governança
- Challenger pode ser promovido somente por regra explícita e revisão dos dados.
- Alterações de estratégia/configuração ficam versionadas.
- Qualquer degradação estatística força redução ou PAUSE, nunca aumento de risco.

## Gate obrigatório
`Market State → Outcome Validation → Risk Engine → RealModeGuard → Order Manager → Exchange`

O AI Council pode aconselhar, mas nunca executa, altera limites de risco ou desbloqueia REAL.

## Critérios que ainda NÃO autorizam REAL
- Uma sequência curta de lucro.
- Backtest isolado.
- Win rate sem custos.
- Resultado de um único ativo.
- Resultado de uma única exchange.
- Modelo de IA com score elevado sem evidência estatística.
