# Lead/Lag Validation

O Trader separa descoberta de validação.

IN-SAMPLE é usado para descobrir e calibrar relações. OUT-OF-SAMPLE é um período posterior que não participa na descoberta.

Uma relação só fica estável quando tem amostra mínima, expectancy líquida positiva nos dois períodos, intervalo de confiança de 95% do período OUT acima de zero e taxa de resposta mínima.

Métricas: amostras IN/OUT, taxa de resposta, expectancy líquida, mediana do atraso e intervalo de confiança.

Esta camada é exclusivamente PAPER/observacional. stable=true significa que a relação passou os critérios estatísticos configurados; não é autorização para REAL.

Próximo passo: replay/PAPER executor com fill, slippage e latência de execução.
