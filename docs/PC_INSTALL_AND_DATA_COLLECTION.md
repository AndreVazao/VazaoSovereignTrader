# PC install + continuous learning data collection

## Objetivo

A instalação do PC deixa o VazaoSovereignTrader preparado para funcionar em PAPER, recolher dados públicos continuamente e construir a base de evidência para os estudos do trader.

A recolha inicial não precisa de API keys de exchange. O PC observa feeds públicos e guarda os dados localmente.

## Instalação Windows

A partir da raiz do repositório:

    powershell -ExecutionPolicy Bypass -File .\scripts\setup_windows.ps1

O instalador prepara:

- ambiente Python isolado;
- dependências do PC;
- Chromium do Playwright;
- config.local.json local, sem secrets;
- diretórios persistentes de dados, logs e perfis browser.

Depois configura o token local da API:

    powershell -ExecutionPolicy Bypass -File .\scripts\configure_windows_secrets.ps1

Verificação completa:

    powershell -ExecutionPolicy Bypass -File .\scripts\verify_pc_install.ps1

A verificação compila o runtime, valida dependências, verifica os defaults de segurança, executa a suíte Python e confirma a disponibilidade do Playwright.

## Operação 24/7

Depois da verificação:

    powershell -ExecutionPolicy Bypass -File .\scripts\install_windows_autostart.ps1

São instaladas duas tarefas do Windows:

- VazaoSovereignTrader — engine PC, PAPER-first.
- VazaoSovereignTrader-MarketData — recolha pública WebSocket contínua.

Ambas reiniciam automaticamente após falhas.

A tarefa de market data é independente do engine: se o engine parar, a fita pública continua a ser recolhida; se um feed cair, os adapters WebSocket fazem reconnect.

## Recolha manual

Para iniciar apenas a recolha WebSocket:

    .\PC_ENGINE\.venv\Scripts\python.exe .\PC_ENGINE\tools\run_market_data_collector.py

O serviço observa inicialmente Binance, Coinbase e OKX. Não precisa de API keys.

## Artefactos

- PC_ENGINE/data/radar/websocket_events.jsonl — tape normalizado.
- PC_ENGINE/data/radar/websocket_lead_lag.jsonl — candidatos cross-venue.
- PC_ENGINE/data/radar/websocket_latency_edges.jsonl — medições temporais observacionais.
- PC_ENGINE/data/radar/lead_lag_learning.json — aprendizagem PAPER agregada.
- PC_ENGINE/data/radar/state_signature_learning.jsonl e state_outcomes.jsonl — aprendizagem PAPER existente.

O collector não envia ordens, não levanta fundos e não ativa REAL.

## Pipeline

    recolher -> aprender -> validar OOS -> testar PAPER -> revisão de risco -> REAL controlado

Uma relação elegível continua a ser evidência PAPER, não autorização para negociar.
