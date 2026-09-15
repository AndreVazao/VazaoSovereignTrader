# Order Flow + Breakout

Esta fase adiciona duas fontes de evidência independentes para PAPER:

- **Order Flow**: imbalance entre notional de compras e vendas dos trades públicos WebSocket.
- **Breakout + Volume**: rompimento da máxima/mínima do lookback acompanhado de volume relativo.

## Regras de segurança

As duas estratégias são apenas evidência. Não têm acesso ao executor, não alteram risco e não podem abrir posições isoladamente.

## Order Flow

Os eventos são provenientes do radar WebSocket e usam `price * quantity` para ponderar o fluxo. O sinal exige um número mínimo de trades e um imbalance mínimo. Fluxos extremos também são descartados para evitar interpretar um livro momentaneamente dominado por uma amostra pequena como confirmação confiável.

## Breakout

O preço atual é comparado com máximas/mínimas do lookback anterior. Um rompimento só produz evidência quando existe volume relativo acima do mínimo configurado. ATR é usado para normalizar a magnitude do rompimento.

## Próxima integração

A próxima etapa deve ligar estas evidências ao Confluence e ao armazenamento de resultados PAPER, incluindo regime, timestamp e horizonte. Só depois devemos usar walk-forward/regime validation para decidir quais combinações merecem peso maior.

Esta fase continua PAPER-only e os testes foram adicionados, mas não foram executados nesta alteração.
