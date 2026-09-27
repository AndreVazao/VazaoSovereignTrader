# Readiness Diagnostic Timeline

## Objetivo

Tornar o histórico de readiness explicável sem introduzir qualquer poder de execução. A timeline transforma snapshots persistidos em eventos de transição cronológicos.

## Componentes observados

- BASE
- AUDIT
- LEARNING
- CHAMPION
- EXECUTION
- READINESS_TREND

## Evento

Cada transição contém:

- `timestamp_ms` — instante da mudança;
- `component` — componente afetado;
- `from_status` e `to_status` — estado anterior e novo;
- `direction` — DEGRADING, RECOVERING ou CHANGING;
- `detail` — detalhe do snapshot que iniciou o novo estado;
- `previous_timestamp_ms` — início do estado anterior;
- `duration_ms` — tempo que o estado anterior permaneceu ativo.

Os eventos são ordenados deterministicamente por timestamp, componente e estado destino. O histórico com timestamps duplicados ou snapshots malformados é rejeitado em fail-closed.

## API

`GET /readiness/timeline`

Requer o scope autenticado de leitura privada. Filtros opcionais:

- `component`
- `direction`
- `from_status`
- `to_status`
- `limit`

Exemplo conceptual: `/readiness/timeline?component=AUDIT&direction=DEGRADING&limit=20`.

A resposta inclui `paper_only: true`. A timeline não altera candidatos, Champion/Challenger, Risk Engine, RealModeGuard ou execução.

## Relação com Trend e Scorecard

- History guarda os snapshots.
- Trend resume estabilidade temporal global.
- Scorecard resume o estado por componente e identifica direção/streak.
- Timeline explica as transições concretas entre snapshots.

Esta separação evita transformar um diagnóstico em autorização de trading.
