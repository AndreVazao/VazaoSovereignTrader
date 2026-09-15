# Walk-Forward Validation

## Objetivo

O VazaoSovereignTrader não deve considerar uma estratégia válida apenas porque apresentou bons resultados no mesmo conjunto de dados usado para aprender.

O módulo `PC_ENGINE/core/walk_forward.py` divide cronologicamente os resultados PAPER em:

1. **treino** — passado mais antigo;
2. **validação** — período posterior, nunca usado para formar a decisão de robustez.

Por defeito, 70% dos resultados são treino e 30% validação.

## Critérios conservadores

Uma combinação `symbol + action + horizon` só passa se houver:

- pelo menos 50 observações de treino;
- pelo menos 30 observações de validação;
- expectancy média líquida positiva na validação;
- win rate da validação >= 50%;
- limite inferior do intervalo de confiança de 95% positivo.

O objetivo é reduzir falsos positivos estatísticos e impedir que uma vantagem aparente seja confundida com ruído.

## Sem leakage temporal

Os resultados são ordenados pelo timestamp de avaliação antes da divisão. Nenhuma observação posterior é movida para o treino.

O módulo é apenas avaliador. Não envia ordens, não altera posições e não ativa REAL.

## Execução

```text
python -m PC_ENGINE.tools.run_walk_forward
```

Ou:

```text
python PC_ENGINE/tools/run_walk_forward.py
```

O resultado é guardado em `PC_ENGINE/data/radar/walk_forward_results.json`.

## Regra de segurança

Mesmo que uma combinação passe no walk-forward, isso **não significa que está pronta para REAL**. Ainda são necessários período PAPER suficiente, custos reais observados, estabilidade entre regimes e validação operacional.
