# Fast Path / Slow Learning

O motor tem dois caminhos deliberadamente separados:

- **Fast Path:** evento WebSocket -> sinal previamente validado -> decisão determinística -> Risk Engine -> Order Manager.
- **Slow Learning:** resultados e eventos seguem para aprendizagem, validação e persistência sem bloquear o caminho de mercado.

## Segurança

O `FastPathExecutor` não conhece exchanges nem possui autoridade própria. O chamador fornece a autorização final e a função de ordem.

Por defeito:

- `fast_path.enabled = false`;
- `fast_path.allow_real = false`;
- REAL rápido permanece bloqueado até existir uma política de risco/execution gate específica.

A ativação PAPER pode ser usada para medir latência, rejeições, slippage e qualidade dos sinais antes de qualquer autorização REAL.

## Objetivo de latência

O caminho crítico não chama LLM, backtest, aprendizagem ou I/O pesado. A métrica `evaluation_ns`/`latency_ns` permite acompanhar o custo de decisão e execução.

Uma oportunidade de lead/lag só é candidata quando o evento é fresco, existe um sinal elegível e a expectativa/confiança mínimas são satisfeitas.

## Princípio

> Aprender continuamente sem colocar a aprendizagem no caminho crítico da execução.
