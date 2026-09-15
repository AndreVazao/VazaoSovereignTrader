# Real Readiness Gate

A avaliação PAPER verifica preflight, Market State, State Outcomes, walk-forward, regime validation, watchdog, recovery, execution tests e erros críticos.

Qualquer falha mantém `LOCKED`. Mesmo quando aprovado, o resultado é apenas `READY_FOR_PROTECTED_REAL_REVIEW`; não ativa REAL, não altera risco, não manipula credenciais e não envia ordens.

A ativação futura exige um `RealModeGuard` separado e confirmação explícita do operador.
