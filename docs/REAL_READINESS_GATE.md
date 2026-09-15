# Real Readiness Gate

O `RealReadinessGate` é uma barreira de avaliação, não um desbloqueador de ordens.

## Objetivo

Transformar a pergunta `estamos prontos para REAL?` numa lista verificável de bloqueios.

Checks atuais:

- PAPER mode
- preflight OK
- mínimo de 1.000 Market States
- mínimo de 1.000 outcomes
- pelo menos 1 combinação elegível após custos e intervalo de confiança
- walk-forward OK
- regime validation OK
- watchdog saudável
- recovery saudável
- testes de execução PAPER concluídos
- zero erros críticos

## Regra

Qualquer check falhado mantém `LOCKED`.

Mesmo com todos os checks aprovados, o gate só devolve `READY_FOR_PROTECTED_REAL_REVIEW`. Não muda o modo, não lê/escreve credenciais, não altera limites de risco e não envia ordens.

A ativação futura terá de passar por um `RealModeGuard` separado e por confirmação explícita do operador.

## Ordem de segurança

`Market State → Outcome Validation → Readiness Gate → Risk Engine → RealModeGuard → Order Manager → Exchange`

O AI Council não pode contornar esta sequência.
