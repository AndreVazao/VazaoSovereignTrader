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


## Diagnóstico operacional

O cockpit autenticado inclui agora **Diagnóstico operacional**, que consolida em modo PAPER:
- estado do motor e watchdog/preflight/reconciliação;
- estado do Market Data Collector e idade do heartbeat;
- eventos totais por venue e último evento por venue/símbolo;
- reconnect/error counters;
- tamanho atual dos dados locais e crescimento desde a última leitura;
- exportação do snapshot para `vazao-operational-diagnostics.json`.

Endpoints:
- `GET /diagnostics` — requer `read_private_state`.
- `GET /diagnostics/export` — requer `read_private_state` e devolve o snapshot como ficheiro JSON.

O diagnóstico é observacional. Não envia ordens, não ativa REAL e não depende de cloud.
