# VazaoSovereignTrader

Sistema privado, local-first, para trading automatizado com controlo de risco.

## Filosofia

- **PC_ENGINE** é o cérebro 24/7.
- **MOBILE_APP** é o cockpit: iniciar, pausar, parar e observar.
- **shared** contém contratos comuns entre PC e APK.
- Tudo começa em **PAPER** por defeito.
- Nenhuma chave de API deve ser colocada no GitHub.

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

Objetivos do Radar:

- observar Binance, BingX, OKX, Bybit, Coinbase e outras fontes elegíveis;
- privilegiar WebSockets/streams oficiais quando disponíveis nas fases seguintes;
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

Os eventos de lead/lag da Fase 1 são apenas candidatos de investigação porque a recolha inicial usa polling CCXT. Não tratamos timestamps de resposta como prova de vantagem negociável. A próxima fase deve migrar a recolha crítica para streams/WebSockets e depois medir a vantagem em PAPER/out-of-sample.

Arquitetura detalhada: `docs/SOVEREIGN_MARKET_RADAR.md`.

## Capital Opportunity Engine

O Trader agora possui uma camada separada para transformar evidência histórica do Radar em candidatos de oportunidade com foco em eficiência de capital.

Ela mede atraso observado, consistência, movimento bruto, custos estimados, edge líquido e capital requerido. Uma oportunidade só aparece como CANDIDATE depois de ultrapassar os mínimos configurados; isso não autoriza REAL.

```bash
python PC_ENGINE/tools/run_capital_opportunities.py
```

Saída: PC_ENGINE/data/radar/capital_opportunities.jsonl.

Documentação: docs/CAPITAL_OPPORTUNITY_ENGINE.md.

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


## State Signature Learning

O motor PAPER inclui assinaturas hierárquicas de Market State para aprender padrões sem explosão combinatória. A aprendizagem é descritiva e nunca autoriza REAL.

`python PC_ENGINE/tools/run_state_signature_learning.py`

O artefacto é `PC_ENGINE/data/radar/state_signature_learning.jsonl`.

A mesma recolha também produz `PC_ENGINE/data/radar/state_outcomes.jsonl`, com resultados por símbolo, ação e regime depois de custos. Este segundo artefacto serve como validação independente da aprendizagem por assinatura e ajuda a detetar divergências entre padrões de estado e resultado agregado.

## CI

A suíte passou de 25 jobs por ficheiro para um job único que executa todos os testes. Isto reduz ruído e emails quando existe falha de infraestrutura. Runs antigos da mesma branch são cancelados automaticamente.


## PC 24/7 + controlo remoto

- scripts/setup_windows.ps1 prepara o ambiente Windows.
- scripts/install_windows_autostart.ps1 cria arranque automático e reinício após falhas.
- docs/REMOTE_MOBILE_SETUP.md descreve o acesso remoto pelo Android.
- O acesso remoto recomendado usa Tailscale; não fazer port-forward da porta 8765.
- A API exige VST_LOCAL_TOKEN; não existe token de fallback.
- GET /health é apenas health-check; comandos e /status exigem o token.

## APK Android

O cockpit Android inclui:
- INICIAR / PAUSAR / RETOMAR / PARAR;
- PAPER;
- ARM REAL / REAL / DESARMAR;
- estado, equity, P&L, drawdown, watchdog e logs.

O workflow .github/workflows/android-apk.yml cria um APK debug como artefacto quando executado manualmente ou quando é criado um tag mobile-v*.


## Prontidão PC + móvel

A camada de aprendizagem PAPER agora cruza dois sinais independentes: assinatura hierárquica do Market State e outcomes agregados por símbolo/regime/ação. O consenso só acrescenta um pequeno bónus descritivo quando ambos confirmam o mesmo contexto.

Para preparar um PC Windows novo:

```powershell
.scriptssetup_windows.ps1
.scriptsconfigure_windows_secrets.ps1
# abrir uma nova PowerShell
.scriptserify_pc_install.ps1
.scriptsinstall_windows_autostart.ps1
```

O cockpit Android usa a mesma API autenticada, testa a ligação, mostra readiness e permite controlar o PC à distância. A ligação remota recomendada é Tailscale; a porta 8765 não deve ser exposta por port-forward.


## Browser Execution

O Trader inclui agora uma camada isolada para plataformas que só funcionam por browser.

- Chromium/Playwright com perfil persistente por plataforma.
- Login inicial manual e reutilização da sessão local.
- Dry-run: prepara a ordem sem a submeter.
- Live browser trading bloqueado por defeito.
- Confirmação explícita para permitir envio real.
- Auditoria JSONL de todas as tentativas.
- Screenshot de evidência em erros.
- Configuração específica da plataforma fica fora do código do motor.

Documentação: `docs/BROWSER_AUTOMATION.md`.

Instalação do runtime Chromium:

```
python -m playwright install chromium
```

A camada browser não contorna CAPTCHA, 2FA, anti-bot ou outros mecanismos de segurança da plataforma.
