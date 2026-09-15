# VazaoSovereignTrader

Sistema privado, local-first, para trading automatizado com controlo de risco.

## Filosofia

- **PC_ENGINE** é o cérebro 24/7.
- **MOBILE_APP** é o cockpit: iniciar, pausar, parar e observar.
- **shared** contém contratos comuns entre PC e APK.
- Tudo começa em **PAPER** por defeito.
- Nenhuma chave de API deve ser colocada no GitHub.
- Nada de scraping, automação de missões, cliques ou abuso de plataformas.

## Estado inicial

Esta versão entrega uma base funcional e segura:

- Engine PC local com ciclo autónomo.
- API HTTP local para controlar via APK.
- Multi-ativo: BTC, ETH, BNB, SOL, DOGE.
- Alocação dinâmica de capital por score.
- Risk engine com limites por trade, dia, semana e exposição total.
- Estratégia trend EMA/ATR/VWAP com regime filter.
- Camada de confirmação por padrões de candlestick.
- Modo PAPER obrigatório por defeito.
- Ledger local JSONL para auditoria.
- Mobile Kivy como controlo remoto.
- Preparado para Binance e BingX via CCXT.
- Integração futura com TradingAgents como conselho opcional, não executor.
- **Sovereign Market Radar** documentado como próxima camada de inteligência multi-fonte e lead/lag.

## Sovereign Market Radar

O projeto prevê uma camada central de inteligência própria para combinar dados de múltiplas exchanges e fontes em tempo real.

Objetivos:

- observar Binance, BingX, OKX, Bybit, Coinbase e outras fontes elegíveis;
- privilegiar WebSockets/streams oficiais quando disponíveis;
- medir lead/lag em vez de assumir que uma plataforma é sempre mais rápida;
- estudar order flow, liquidez, volume e microestrutura;
- incorporar open interest, funding, basis e liquidações quando disponíveis;
- usar notícias e eventos apenas como contexto confirmado pelo mercado;
- produzir um **Market Pressure Score**;
- aprender por símbolo, timeframe e regime;
- validar qualquer vantagem depois de fees, spread, slippage e latência.

O Radar **não é uma bola de cristal e não executa ordens**. A arquitetura mantém a separação:

```text
Radar -> evidência
Strategy -> sinal candidato
AI Council -> conselho opcional
Risk Engine -> autoriza/bloqueia
Executor -> executa
```

A implementação do Radar e do Lead/Lag Engine será primeiro observacional/PAPER. Nenhuma suposta vantagem de latência será considerada válida sem validação estatística e out-of-sample.

Arquitetura detalhada: `docs/SOVEREIGN_MARKET_RADAR.md`.

## Aviso

Isto não é aconselhamento financeiro e não garante lucro. Usa apenas APIs oficiais das exchanges, sem withdraw permission, e começa sempre em PAPER.

## Arranque rápido PC

```bash
cd PC_ENGINE
python -m venv .venv
.venv\Scripts\activate
pip install -r ../requirements-pc.txt
copy config\config.example.json config\config.local.json
python main.py
```

Dashboard/API local:

```text
http://127.0.0.1:8765/status
```

## Arranque mobile

```bash
cd MOBILE_APP
buildozer android debug
```

O APK fala com o PC local através do IP da tua rede.

## Segurança obrigatória

Nas exchanges, cria API keys com:

- Read: ligado
- Spot trading: ligado
- Withdraw: desligado
- Futures/leverage: desligado no início

Nunca faças commit de `config.local.json`, `.env`, `*.keystore`, `data/`, `logs/` ou ficheiros com secrets.
