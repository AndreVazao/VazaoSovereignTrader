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
- Modo PAPER obrigatório por defeito.
- Ledger local JSONL para auditoria.
- Mobile Kivy como controlo remoto.
- Preparado para Binance e BingX via CCXT.
- Integração futura com TradingAgents como conselho opcional, não executor.

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
