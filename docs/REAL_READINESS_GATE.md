# Real Readiness Gate

O bot continua em **PAPER por defeito**. Um PASS nunca ativa REAL nem envia ordens.

## Checks

- PAPER mode
- preflight OK
- mínimo de 1.000 Market States
- mínimo de 1.000 outcomes
- pelo menos 1 outcome elegível
- walk-forward OK
- regime validation OK
- watchdog saudável
- recovery saudável
- execution/rejection/recovery test explícito OK
- zero erros críticos no log atual

Ficheiros de validação ausentes são falhas, nunca sucesso assumido.

## Fluxo protegido

```text
PAPER
 -> /readiness
 -> READY_FOR_PROTECTED_REAL_REVIEW
 -> /real/arm com "EU ACEITO O RISCO"
 -> /mode {"mode":"REAL"}
 -> autorização consumida uma vez
 -> engine.set_mode("REAL")
```

A autorização expira em cinco minutos por defeito e é consumida uma única vez. `STOP`, `PAPER` e `DISARM` removem a autorização.

## API

- `GET /readiness`
- `POST /real/arm`
- `POST /real/disarm`
- `POST /mode`

Os endpoints de controlo exigem `X-Token`.

## Limites

O gate é de prontidão, não é garantia de lucro ou segurança absoluta. Antes de REAL continuam obrigatórios Spot-only, Read + Spot Trade, withdrawals desativados, futures/leverage desativados, allowlist, limites conservadores, kill switch e revisão operacional.
