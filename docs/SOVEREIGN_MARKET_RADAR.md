# Sovereign Market Radar

## Objetivo

O **Sovereign Market Radar (SMR)** é a camada central de observação e futura inteligência de mercado do VazaoSovereignTrader.

A finalidade não é tentar prever o futuro com certeza nem encontrar uma plataforma que saiba antecipadamente se o preço vai subir ou descer. A finalidade é construir uma visão própria do mercado, combinando várias fontes em tempo real e aprendendo quais sinais tendem a antecipar movimentos com vantagem estatística.

Princípio:

```text
Mais informação + melhor contexto + menor latência + validação estatística
                 != previsão garantida
```

O SMR procura **probabilidade e vantagem estatística**, não certezas.

## Estado atual — Fase 1

A primeira implementação observacional já existe em:

- `PC_ENGINE/radar/market_radar.py`
- `PC_ENGINE/tools/run_market_radar.py`
- `tests/test_market_radar.py`

Nesta fase o radar:

- consulta dados públicos através do CCXT;
- recolhe preço, bid, ask, volume e timestamps;
- regista timestamp local e timestamp fornecido pela exchange quando disponível;
- calcula uma medida descritiva de pressão cross-exchange;
- deteta **eventos candidatos** de lead/lag entre venues;
- guarda as observações em `PC_ENGINE/data/radar/observations.jsonl`;
- não possui qualquer caminho para enviar ordens;
- não altera o sinal da estratégia principal.

### Limitação importante da Fase 1

Esta versão usa polling REST através do CCXT para evitar introduzir uma dependência adicional antes da validação do modelo de dados. Os eventos de lead/lag são, portanto, **candidatos de investigação**, não prova de latência negociável.

O timestamp local mede quando a resposta foi recebida pelo PC. O timestamp da exchange pode representar uma origem diferente dependendo da API. Não se deve tratar a diferença entre ambos como latência exata do matching engine.

A próxima evolução de baixa latência deverá usar streams/WebSockets oficiais e sincronização de relógio adequada.

## Arranque do radar

A partir da raiz do projeto:

```bash
python PC_ENGINE/tools/run_market_radar.py --cycles 20
```

Execução contínua:

```bash
python PC_ENGINE/tools/run_market_radar.py
```

Exemplo com uma única fonte e ativo para diagnóstico:

```bash
python PC_ENGINE/tools/run_market_radar.py --exchanges binance --symbols BTC/USDT --interval 2 --cycles 30
```

O runner imprime um resumo JSON por ciclo. Os dados completos ficam no JSONL local e devem permanecer fora do Git através do `.gitignore`.

## Arquitetura alvo

```text
                    MARKET DATA
                         |
                         v
              SOVEREIGN MARKET RADAR
                         |
        +----------------+----------------+
        |                |                |
        v                v                v
   CROSS-EXCHANGE    ORDER FLOW       DERIVATIVES
        |                |                |
        |                |                +-- Open Interest
        |                |                +-- Funding
        |                |                +-- Liquidations
        |                |                +-- Basis
        |                |
        |                +-- Aggressive buys/sells
        |                +-- Book imbalance
        |                +-- Spread
        |                +-- Liquidity
        |
        +-- Binance
        +-- BingX
        +-- OKX
        +-- Bybit
        +-- Coinbase
        +-- outras fontes elegíveis
                         |
                         v
                   LEAD/LAG ENGINE
                         |
                         v
                   MARKET STATE
                         |
              +----------+----------+
              |                     |
              v                     v
       TECHNICAL LAYER        CANDLESTICK LAYER
       EMA / ATR / VWAP       patterns / context
              |                     |
              +----------+----------+
                         |
                         v
                  SIGNAL CONFLUENCE
                         |
                         v
                    AI COUNCIL
                         |
                         v
                    RISK ENGINE
                         |
                         v
                      EXECUTOR
                   Binance / BingX
```

## Fontes de dados

A implementação deve privilegiar **WebSockets/streams oficiais** para dados de mercado de baixa latência quando disponíveis. REST fica como complemento, recuperação, snapshots e dados que não tenham stream adequado.

Fontes inicialmente previstas:

- Binance;
- BingX;
- OKX;
- Bybit;
- Coinbase;
- outras exchanges apenas quando houver justificação de qualidade, liquidez, cobertura e API oficial.

O projeto deve usar APIs oficiais e respeitar os termos de utilização de cada plataforma. Não será feita automação de missões, cliques, promoções, quizzes ou outras ações proibidas pelas exchanges.

## Lead/Lag Engine

Esta é a componente experimental mais importante do SMR.

Em vez de assumir que uma exchange lidera outra, o sistema deve medir isso empiricamente.

Para cada evento relevante, guardar pelo menos:

- timestamp com precisão adequada à fonte;
- exchange/fonte;
- símbolo;
- preço;
- retorno/movimento;
- volume;
- spread;
- liquidez disponível;
- características do order book quando disponíveis;
- order-flow/agressão quando disponível;
- regime de volatilidade;
- contexto temporal;
- resposta posterior das outras exchanges;
- resultado do sinal.

Exemplo conceptual:

```text
EVENTO #183742

OKX       t=09:41:12.384
Bybit     t=09:41:12.391
Coinbase  t=09:41:12.407
Binance   t=09:41:12.429
BingX     t=09:41:12.451
```

O sistema não deve concluir automaticamente que os 45–70 ms observados representam uma vantagem negociável. Deve acumular muitos eventos, controlar qualidade dos timestamps, custos de execução e falsos sinais e calcular a significância/expectancy fora da amostra.

## Aprendizagem por regime

A liderança pode mudar com o contexto. O SMR deve separar, quando houver amostra suficiente:

- baixa vs. alta volatilidade;
- sessões/horários;
- tendência vs. range;
- eventos de notícia;
- movimentos de liquidação;
- condições de liquidez;
- símbolo/ativo;
- timeframe;
- exchange de execução.

Exemplo de saída interna:

```text
BTC

OKX -> Binance       confiança histórica: 0.63
Coinbase -> Binance  confiança histórica: 0.59
Bybit -> Binance     confiança histórica: 0.55

Regime atual: alta volatilidade
Sinal líder ativo: OKX -> Binance
```

Estes números são apenas ilustrativos. Nunca devem ser colocados como factos antes de serem medidos pelo sistema.

## Market Pressure Score

O radar pode produzir um score normalizado entre -1 e +1, agregando evidências independentes:

```text
Cross-exchange      +0.81
Order flow           +0.68
Volume               +0.64
Liquidations         +0.71
Open interest        +0.48
Funding              +0.21
Trend                +0.71
Candlesticks         +0.43

Confluence           +0.67
Confidence            78%
```

O score não é uma previsão garantida. É uma representação compacta da evidência disponível naquele instante.

Na Fase 1, o score de pressão é **descritivo** e limitado aos movimentos observados entre snapshots. Ainda não é um input de trading.

## Multi-timeframe

A arquitetura alvo deve separar função por horizonte:

```text
milissegundos/segundos = microestrutura e lead/lag
1m                     = execução
5m                     = momentum
15m                    = estrutura
1h                     = regime
4h                     = contexto
```

A configuração final deverá ser validada por backtest e PAPER. Não assumir que uma configuração é lucrativa apenas por parecer intuitiva.

## Derivativos e liquidações

Quando dados fiáveis estiverem disponíveis, o SMR pode combinar:

- open interest;
- funding;
- basis;
- liquidações;
- agressão compradora/vendedora;
- alterações de liquidez.

Exemplo conceptual de confluência:

```text
BTC sobe
+ open interest aumenta
+ compras agressivas aumentam
+ short liquidations aumentam
+ liquidez do lado vendedor diminui
```

Isto pode representar um contexto de pressão compradora, mas continua sujeito a confirmação e falhas.

## Notícias e eventos externos

Notícias não devem gerar BUY/SELL diretamente.

Pipeline previsto:

```text
EVENTO
  -> relevância para o ativo
  -> classificação
  -> surpresa/contexto
  -> reação observada no mercado
  -> confirmação por preço/volume/order flow
```

O objetivo é transformar informação externa em evidência mensurável, e não deixar uma LLM negociar apenas porque uma manchete parece positiva ou negativa.

## Regra de decisão

O SMR **não executa ordens**.

```text
Sovereign Market Radar -> produz evidência
Strategy Engine         -> produz sinal candidato
AI Council              -> interpreta/aconselha quando habilitado
Risk Engine             -> autoriza ou bloqueia
Order Manager/Executor  -> executa
```

Regra de segurança:

> Nenhuma fonte individual pode ordenar uma compra ou venda.

## Medição da vantagem

Antes de permitir que o SMR influencie REAL, cada sinal deverá ser avaliado em PAPER/backtest com:

- fees;
- spread;
- slippage;
- latência estimada;
- taxa de sinais válidos;
- falsos positivos;
- win rate;
- expectancy;
- profit factor;
- drawdown;
- MAE/MFE quando possível;
- estabilidade por período e regime;
- desempenho out-of-sample.

A métrica mais importante não é simplesmente acertar a direção. É saber se existe **expectancy líquida depois dos custos**.

## Proteção contra overfitting

O SMR não pode aprender com uma amostra pequena e concluir que descobriu uma vantagem permanente.

Regras previstas:

1. mínimo de observações antes de atribuir peso relevante;
2. shrinkage/regularização das estimativas;
3. comparação com baseline;
4. validação temporal out-of-sample;
5. separação entre treino, validação e período de avaliação;
6. limites máximos para a influência do radar;
7. monitorização de drift;
8. desligamento de sinais cuja vantagem desapareça;
9. Champion/Challenger antes de promover uma alteração de estratégia.

## Latência e vantagem competitiva

O objetivo não é competir em microssegundos contra firmas HFT com infraestrutura especializada.

A vantagem procurada é a combinação de:

- cobertura de múltiplas fontes;
- deteção de relações entre mercados;
- contexto de mercado;
- aprendizagem de lead/lag;
- execução suficientemente rápida;
- disciplina de risco.

Mesmo uma diferença observada entre timestamps não é automaticamente arbitragem. É necessário provar que a diferença sobrevive a latência, spread, fees, slippage, concorrência e qualidade dos dados.

## Fases de implementação

### Fase 1 — Observação — EM IMPLEMENTAÇÃO

- [x] modelo de snapshots;
- [x] recolha pública via CCXT;
- [x] timestamps locais e da fonte;
- [x] persistência JSONL;
- [x] eventos candidatos de lead/lag;
- [x] pressão descritiva;
- [x] runner CLI;
- [x] testes unitários do detector;
- [ ] WebSockets/streams de baixa latência;
- [ ] sincronização/medição de relógio robusta;
- [ ] dashboard de saúde e latência;
- [ ] agregação estatística histórica.

### Fase 2 — Lead/Lag PAPER

- detetar eventos;
- medir resposta entre exchanges;
- calcular estatísticas por símbolo/regime;
- gerar sinais virtuais;
- medir expectancy líquida.

### Fase 3 — Confluence

- integrar radar com EMA/ATR/VWAP;
- integrar candlesticks como confirmação;
- integrar derivativos;
- criar Market Pressure Score;
- limitar o peso do radar.

### Fase 4 — Champion/Challenger

Comparar:

```text
A = estratégia atual
B = estratégia atual + radar
```

A versão B só poderá ser considerada para promoção se demonstrar vantagem consistente em PAPER e validação out-of-sample.

### Fase 5 — REAL controlado

Somente depois das fases anteriores:

- confirmação explícita;
- limites de risco;
- exposição reduzida;
- monitorização contínua;
- kill switch;
- possibilidade de regressar ao baseline.

## Princípios permanentes

- Não existe previsão garantida.
- Não confiar numa única exchange.
- Não confiar numa única fonte.
- Não confundir atraso de dados com oportunidade negociável.
- Não executar por causa de uma notícia isolada.
- Não permitir que IA ultrapasse o Risk Engine.
- Não promover aprendizagem diretamente para REAL.
- Medir tudo antes de acreditar na vantagem.
