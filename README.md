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
- **Sovereign Market Radar** em Fase 1 observacional, com recolha cross-exchange e deteção de eventos candidatos de lead/lag.
- **Market State** unificado em PAPER, agregando evidência e estado de regime.
- **State Outcome Engine** para medir expectancy líquida por horizonte/regime.
- **Real Readiness Gate** que mantém REAL bloqueado até existirem evidências operacionais e estatísticas suficientes.

## Pipeline de segurança

```text
Market Data
    ↓
Market State
    ↓
State Outcomes
    ↓
Readiness Gate
    ↓
Risk Engine
    ↓
RealModeGuard
    ↓
Order Manager
    ↓
Exchange
```

O `Readiness Gate` é apenas avaliador. Mesmo quando aprovado, não ativa REAL, não altera limites, não manipula API keys e não envia ordens.

## Sovereign Market Radar

O Radar é uma camada central de observação que combina dados públicos de múltiplas exchanges e, futuramente, derivados, order flow e fontes externas.

Na Fase 1 já existe:

- `PC_ENGINE/radar/market_radar.py`
- `PC_ENGINE/tools/run_market_radar.py`
- `tests/test_market_radar.py`

Para executar a recolha observacional:

```bash
python PC_ENGINE/tools/run_market_radar.py --cycles 20
```

Os dados são guardados localmente em `PC_ENGINE/data/radar/observations.jsonl`.

Arquitetura detalhada: `docs/SOVEREIGN_MARKET_RADAR.md`.

## State Outcomes

```bash
python PC_ENGINE/tools/run_state_outcomes.py
```

A avaliação usa por defeito os horizontes 1s, 5s, 15s, 1m e 5m e desconta custo round-trip configurado. Não executa ordens.

## Readiness Gate

```bash
python PC_ENGINE/tools/run_real_readiness.py --help
```

O resultado possível é `LOCKED` ou `READY_FOR_PROTECTED_REAL_REVIEW`. O segundo estado ainda exige `RealModeGuard` e confirmação explícita do operador.

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
