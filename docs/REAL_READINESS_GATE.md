# Real Readiness Gate

O `RealReadinessGate` é uma barreira de avaliação, não um desbloqueador de ordens.

## Objetivo

Transformar a pergunta `estamos prontos para REAL?` numa lista verificável de bloqueios. Dados ausentes são tratados como falha; o sistema nunca inventa métricas.

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
- teste explícito de execução/rejeição/recovery PAPER concluído
- zero erros críticos no log atual

## Regra

Qualquer check falhado mantém `LOCKED`.

Mesmo com todos os checks aprovados, o gate só devolve `READY_FOR_PROTECTED_REAL_REVIEW`. Não muda o modo, não lê/escreve credenciais, não altera limites de risco e não envia ordens.

## Ativação protegida

A API exige duas condições independentes:

1. readiness `READY_FOR_PROTECTED_REAL_REVIEW`;
2. `RealModeGuard` armado pelo operador com a frase `EU ACEITO O RISCO`.

A autorização dura cinco minutos por defeito e é consumida uma única vez quando o pedido para `REAL` é aceite. `STOP`, `PAPER` e `DISARM` removem a autorização.

Endpoints de controlo:

- `GET /readiness`
- `POST /real/arm`
- `POST /real/disarm`
- `POST /mode`

Todos exigem `X-Token`.

## Ordem de segurança

`Market State → Outcome Validation → Readiness Gate → RealModeGuard → Risk Engine → Order Manager → Exchange`

O AI Council não pode contornar esta sequência.

**Nota:** readiness não é garantia de lucro nem de segurança absoluta. REAL continua a exigir revisão operacional, Spot-only, sem levantamentos, sem futures/leverage e limites conservadores.
