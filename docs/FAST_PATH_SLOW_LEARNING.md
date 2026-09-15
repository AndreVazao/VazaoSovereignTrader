# Fast Path + Slow Learning

## Objetivo

O motor não deve esperar pelo Learning Engine para reagir a uma oportunidade curta. A aprendizagem continua em paralelo e atualiza conhecimento validado para utilizações futuras.

## Fast Path

`PC_ENGINE/core/fast_path.py` é uma camada determinística e pequena. Recebe um evento de mercado e sinais de lead/lag já validados e verifica:

1. evento fresco;
2. símbolo e direção válidos;
3. oportunidade previamente elegível;
4. confiança mínima;
5. expectativa líquida mínima;
6. autorização do Risk Engine através de `risk_check`.

A classe **não envia ordens**, não chama LLM e não altera risco. A integração futura deve manter a sequência `Fast Path -> Risk Engine -> Order Manager`.

## Slow Learning

`PC_ENGINE/core/slow_learning.py` fornece uma fila limitada e não bloqueante. O caminho de mercado usa `put_nowait()`: se a fila estiver cheia, o evento de aprendizagem é descartado e contado, mas a decisão de mercado não fica bloqueada.

O worker grava os eventos e pode encaminhá-los para processamento estatístico mais pesado.

## Regra de segurança

Um sinal aprendido não é autorização automática para REAL. Antes de uma ordem real devem continuar a existir as proteções do Risk Engine, RealModeGuard, limites de exposição e Order Manager.

## Dados

Não existe requisito de dados infinito. O sistema pode começar com um conjunto mínimo de evidência para PAPER/protected REAL e aumentar a confiança à medida que recolhe resultados. O aumento de capital ou autonomia deve continuar dependente de validação estatística e qualidade de execução.
