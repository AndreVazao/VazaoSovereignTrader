# Derivatives Radar

O Derivatives Radar recolhe **apenas dados públicos** de derivados e transforma-os em contexto observacional para o motor de confluência.

## Dados

- Funding rate
- Open interest quando suportado pela exchange
- Mark price e index price quando disponíveis
- Basis mark-vs-index em bps
- Evolução preço/OI entre observações

## Regra de segurança

Este módulo não autentica contas, não envia ordens, não altera leverage e não decide sozinho BUY/SELL. A evidência entra na `ConfluenceEngine` com peso limitado e continua PAPER-only.

## Interpretação

- Funding positivo: possível crowding de longs, tratado como pressão contrária.
- Funding negativo: possível crowding de shorts, tratado como pressão favorável aos longs.
- Preço e OI a subir em conjunto: participação no movimento atual.
- Preço a subir com OI a cair: pode ser short covering e recebe interpretação mais fraca.
- Basis positivo/negativo é contexto, não sinal autónomo.

Se uma exchange não disponibilizar um campo, o valor fica `None`; não é inferido artificialmente.
