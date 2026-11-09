# Quickstart Windows 10 — PAPER

## 1. Instalar dependências

Na raiz do repositório, executar:

```powershell
scripts\windows_setup.bat
```

Isto cria o ambiente Python, instala as dependências do PC e cria `PC_ENGINE/config/config.local.json` se ainda não existir.

## 2. Configurar o token local

Executar:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\configure_windows_secrets.ps1
```

O script pede apenas `VST_LOCAL_TOKEN`, usando entrada segura. Não pede nem guarda chaves de exchange. Fechar esta janela e abrir uma nova PowerShell.

## 3. Verificar a instalação

```powershell
.\scripts\verify_pc_install.ps1
.\scripts\verify_public_market_data.ps1
```

A primeira verificação compila o código do projeto, valida dependências, Playwright e segurança PAPER. Não executa a suíte completa por defeito. A segunda consulta dados públicos/read-only; não precisa de API keys.

## 4. Iniciar manualmente em PAPER

```powershell
.\scripts\windows_run_pc_engine.bat
```

Depois abrir:

`http://127.0.0.1:8765/dashboard`

Health check básico:

`http://127.0.0.1:8765/health`

O estado e os comandos autenticados exigem `VST_LOCAL_TOKEN`.

## 5. Segurança da fase atual

- Manter `mode=PAPER`.
- Manter `autonomous_execution.allow_real=false` e `auto_promote_real=false`.
- Não configurar chaves privadas nem permissões de trading nas exchanges.
- Não ativar LIVE/REAL nem executar operações financeiras.
- Não instalar autostart durante a primeira validação.

O instalador Windows empacotado também não inicia serviços nem cria tarefas agendadas. Qualquer autostart posterior é uma decisão separada, depois de validação local.

## 6. Backtest local opcional

O script `scripts/windows_backtest_btc.bat` usa candles públicos e executa um replay local. Continua a ser investigação/PAPER; não envia ordens.
