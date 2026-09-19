# Capital Opportunity Engine

O Capital Opportunity Engine transforma evidência histórica do Sovereign Market Radar em candidatos de oportunidade com foco em eficiência de capital.

A pergunta operacional é:

> Entre as oportunidades que o Trader já conseguiu medir, quais apresentam evidência suficiente para merecer estudo com pouco capital?

Não responde que um mercado dará lucro garantido.

## Mede

Por ativo, líder, seguidor e direção:

- número de observações;
- atraso mediano;
- consistência;
- movimento bruto mediano;
- custos estimados;
- edge líquido estimado;
- capital mínimo configurado;
- eficiência de capital.

Eficiência:

edge líquido em bps / capital requerido × 1000

## Custos

Inclui estimativas configuráveis de:

- fee;
- spread;
- slippage;
- margem para latência.

Posteriormente estes valores devem ser substituídos por dados reais de cada plataforma e tipo de ordem.

## Estados

WATCH = existe evidência, mas ainda não há edge líquido ou consistência suficiente.

CANDIDATE = ultrapassou os mínimos configurados e merece validação adicional.

CANDIDATE nunca significa lucro garantido nem autorização para REAL.

## Pouco capital

O capital requerido poderá futuramente considerar:

- mínimo de ordem;
- lote mínimo;
- fee mínimo;
- margem;
- spread;
- liquidez disponível;
- buffer operacional.

A alocação final pertence ao Risk Engine.

## Saída

PC_ENGINE/data/radar/capital_opportunities.jsonl

Exemplo conceptual:

    BTC/USDT | OKX -> Binance | UP | 31 ms | 4.7 bps | capital 100 | CANDIDATE

O exemplo é ilustrativo, não um resultado real.

## Segurança

O motor não envia ordens, não possui chaves privadas e não altera o Risk Engine.

Fluxo futuro:

RADAR -> CANDIDATE -> PAPER -> OUT-OF-SAMPLE -> CHAMPION -> RISK REVIEW -> REAL CONTROLADO

## Execução

    python PC_ENGINE/tools/run_capital_opportunities.py
