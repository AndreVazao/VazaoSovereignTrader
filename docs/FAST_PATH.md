# Fast Path / Slow Learning

O motor tem dois caminhos separados:

- **Fast Path:** evento WebSocket -> sinal previamente validado -> decisão determinística -> autorização de risco -> Order Manager.
- **Slow Learning:** resultados, estados e eventos seguem para aprendizagem, validação e persistência sem bloquear o caminho de mercado.

## Segurança

O `FastPathRouter` não possui credenciais nem acesso direto às exchanges. O `FastPathExecutor` recebe explicitamente as funções de autorização e ordem.

Por defeito:

- `fast_path.enabled = false`;
- `fast_path.allow_real = false`;
- o caminho REAL rápido permanece bloqueado até existir uma política específica, testada e aprovada.

PAPER pode ser ativado para medir latência, rejeições, slippage e qualidade do sinal.

## Caminho crítico

O Fast Path não chama LLM, backtest, aprendizagem ou I/O pesado. O `FastPathMetrics` mede o custo de avaliação e execução.

Um evento só pode avançar quando é fresco, tem direção válida e corresponde a um lead/lag previamente elegível com confiança e expectativa mínimas. Mesmo depois disso, a autorização final continua fora do Fast Path.

## Próxima integração

A integração com o WebSocket deve alimentar este router através de uma callback mínima. O resultado deve seguir para o Risk Engine e Order Manager existentes. A aprendizagem continua assíncrona.

> Aprender continuamente sem colocar a aprendizagem no caminho crítico da execução.
