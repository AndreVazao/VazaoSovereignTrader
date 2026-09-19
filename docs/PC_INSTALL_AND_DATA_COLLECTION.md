# PC install + continuous learning data collection

## Instalação Windows

A partir da raiz:

    powershell -ExecutionPolicy Bypass -File .\scripts\setup_windows.ps1

O script cria o ambiente Python, instala as dependências, cria config.local.json, instala Chromium do Playwright e prepara as pastas de dados.

Verificação:

    powershell -ExecutionPolicy Bypass -File .\scripts\verify_pc_install.ps1

## Recolha contínua

    .\PC_ENGINE\.venv\Scripts\python.exe .\PC_ENGINE\tools\run_market_data_collector.py

O serviço observa streams públicos de Binance, Coinbase e OKX. Não precisa de API keys.

Artefactos:
- websocket_events.jsonl: tape normalizado.
- websocket_lead_lag.jsonl: candidatos cross-venue.
- lead_lag_learning.json: aprendizagem PAPER agregada.
- state_signature_learning.jsonl e state_outcomes.jsonl: aprendizagem PAPER existente.

O collector não envia ordens, não levanta fundos e não ativa REAL.

## Pipeline

Recolher -> aprender -> validar fora da amostra -> testar PAPER -> revisão de risco -> REAL controlado.

Uma relação elegível continua a ser PAPER; não é autorização para negociar.
