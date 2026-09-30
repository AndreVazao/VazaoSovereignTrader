# Build e instalação

## PC Windows

O workflow Windows EXE pode ser executado manualmente em GitHub Actions ou por uma tag pc-vX.Y.Z.

Artefacto: VazaoSovereignTrader-Windows.zip.

Para uma instalação a partir do código-fonte, usar:

    powershell -ExecutionPolicy Bypass -File .\scripts\setup_windows.ps1

Depois:

    powershell -ExecutionPolicy Bypass -File .\scripts\configure_windows_secrets.ps1
    powershell -ExecutionPolicy Bypass -File .\scripts\verify_pc_install.ps1
    powershell -ExecutionPolicy Bypass -File .\scripts\install_windows_autostart.ps1

O runtime fica preparado em PAPER, com recolha pública de market data e reinício automático no arranque do Windows. A recolha WebSocket não requer API keys.

O dashboard fica no próprio PC em:

    http://127.0.0.1:8765/dashboard

### O que começa a recolher dados

O engine PAPER já possui um PaperMarketCollector integrado para OHLCV, estados de mercado, confluence e outcomes. A tarefa separada VazaoSovereignTrader-MarketData acrescenta o tape WebSocket de trades públicos de Binance, Coinbase e OKX, incluindo candidatos de lead/lag e medições de latência observacional.

Isto permite ao trader começar a acumular evidência sem ativar contas privadas nem execução REAL.

## Android

O workflow Android APK pode ser executado manualmente ou por uma tag mobile-vX.Y.Z. O APK é publicado como artefacto.

O Android liga ao PC através do IP Tailscale do PC na rede privada. Não expor a porta do Trader diretamente à Internet.

## Operação fora de casa

PC ligado e sem suspensão. Tailscale ligado no PC e no telefone. O APK usa o endpoint privado do PC.

Fluxo:

    telefone -> Tailscale -> API do PC -> engine.

O telefone não guarda chaves de exchange nem executa trades; é cockpit de comando.

## Regras de operação

PAPER primeiro. REAL só depois de validação estatística, replay/PAPER e revisão do Risk Engine.

## Ponte de intervenção humana

O PC e o telefone são independentes. Se o PC encontrar um login, 2FA/OTP, CAPTCHA ou outra barreira humana, cria um pedido persistente no Human Interaction Bridge. Quando o telefone estiver disponível através da Tailscale, mostra o pedido e envia a intervenção de volta ao PC.

A fila de pedidos é persistente, mas dados sensíveis não são: passwords, OTPs e outros segredos enviados pelo telefone ficam apenas em RAM no processo do PC até serem consumidos. O browser mantém a sessão local no PC. CAPTCHA/2FA são sempre intervenção humana normal, sem bypass.


## Estudo estatístico PAPER

O nó local pode executar `PC_ENGINE/tools/run_paper_study.py` sobre `PC_ENGINE/data/radar/market_states.jsonl`. O harness é observacional e produz `PC_ENGINE/data/radar/paper_study_report.json` com:
- outcomes líquidos de custos;
- separação cronológica train/test;
- walk-forward por folds;
- análise por regime;
- Monte Carlo bootstrap com seed determinística;
- comparação configurável entre todos os sinais e sinais de maior confiança/confluência.

Nenhuma etapa do estudo envia ordens, altera risco ou promove REAL. O objetivo é transformar a acumulação contínua de dados em evidência estatística antes de qualquer decisão de execução.


## Validação temporal do WebSocket

Antes de interpretar lead/lag como evidência económica, o nó pode executar `PC_ENGINE/tools/validate_websocket_timing.py`. A validação verifica timestamps de exchange/local, latência de receção, duplicados, eventos fora de ordem e consistência entre `exchange_lag_ms` e `receive_lag_ms`.

O relatório `PC_ENGINE/data/radar/websocket_timing_validation.json` só marca `eligible_for_economic_interpretation` quando os gates temporais configurados passam. Um resultado bloqueado não é transformado em sinal de trading.


## Estudos PAPER contínuos

O Market Data Collector passou a executar automaticamente, por defeito a cada 15 minutos, o estudo estatístico local e a validação temporal do WebSocket. Os relatórios ficam em `PC_ENGINE/data/radar/paper_study_report.json` e `PC_ENGINE/data/radar/websocket_timing_validation.json`.

A periodicidade, custos, horizonte, número de folds, Monte Carlo e thresholds temporais são configuráveis em `paper_study` no `config.local.json`. O ciclo continua estritamente PAPER/observacional e falha fechado: relatórios nunca alteram risco nem autorizam REAL.


## Gate temporal para REAL

A readiness de REAL agora exige, por defeito, um relatório `websocket_timing_validation.json` **fresco** e com `eligible_for_economic_interpretation=true`. Se o relatório estiver ausente, expirado ou bloqueado, a readiness permanece `LOCKED`.

Isto não ativa REAL nem substitui preflight, reconciliação, Risk Engine ou RealModeGuard; acrescenta apenas uma proteção adicional contra interpretar lead/lag temporalmente inválido como evidência económica.


## Estado da investigação no cockpit

O endpoint autenticado `/research/status` expõe, em modo somente leitura, o estado dos relatórios PAPER contínuos (`paper_study_report.json` e `websocket_timing_validation.json`), idade dos artefactos, intervalo configurado e conteúdo estatístico disponível. O endpoint nunca envia ordens, altera risco ou promove REAL.


## Relatório de saúde da instalação Windows

`verify_pc_install.ps1` passa a gerar `PC_ENGINE/data/logs/installation_health.json` depois de concluir as verificações. O relatório regista versão do schema, timestamp UTC, runtime Python, configuração PAPER, dependências, Playwright, resultado da suite Python, presença das duas Scheduled Tasks e se o token local está disponível na sessão.

A ausência das Scheduled Tasks é reportada como estado, não como erro, porque o script de verificação pode ser executado antes da instalação do autostart. O relatório é local e não contém tokens ou credenciais.


## Cockpit — investigação PAPER

O painel local inclui agora um bloco de investigação contínua com amostras, média líquida em bps, volume do conjunto OOS e estado da validação temporal WebSocket. O resumo detalhado mostra walk-forward, regimes e Monte Carlo. Tudo é somente leitura e não controla execução.


## Diagnóstico operacional

O cockpit autenticado inclui **Diagnóstico operacional**, consolidando em modo PAPER:
- estado do motor, watchdog, preflight e reconciliação;
- estado e idade do Market Data Collector;
- eventos por venue e último evento por venue/símbolo;
- reconnect/error counters;
- tamanho e crescimento dos dados locais;
- exportação do snapshot para `vazao-operational-diagnostics.json`.

Endpoints autenticados:
- `GET /diagnostics` — requer `read_private_state`.
- `GET /diagnostics/export` — requer `read_private_state`.

O diagnóstico é observacional: não envia ordens, não ativa REAL e não depende de cloud.
