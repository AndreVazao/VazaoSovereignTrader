# Build e instalação

## PC Windows

O workflow `Windows EXE` pode ser executado manualmente em GitHub Actions ou por uma tag `pc-vX.Y.Z`. Produz um ZIP portátil e um instalador Inno Setup. Os artefactos CI não equivalem, por si só, a uma release formal nem a uma instalação validada no PC de destino.

### Instalação a partir do código-fonte

Executar na raiz do repositório:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_windows.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\configure_windows_secrets.ps1
```

O script de configuração recolhe apenas `VST_LOCAL_TOKEN`, usado para autenticar a API local. Não recolhe nem armazena chaves de exchanges. Fechar e reabrir o terminal para carregar a variável de ambiente.

Depois executar:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\verify_pc_install.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\verify_public_market_data.ps1
```

A verificação leve compila código Python do projeto, valida dependências, Playwright e invariantes PAPER. Não executa a suíte Python completa por defeito. A verificação de market data usa endpoints públicos/read-only e não necessita de API keys.

Iniciar o engine manualmente depois das verificações:

```powershell
.\scripts\windows_run_pc_engine.bat
```

O dashboard fica no próprio PC em:

`http://127.0.0.1:8765/dashboard`

O instalador empacotado também é manual-first: não inicia engine/collector, não cria tarefas agendadas e não ativa autostart. O script `scripts/install_windows_autostart.ps1` é um opt-in separado para instalações a partir do código-fonte, apenas depois de validação física e decisão explícita. Não o executar durante a primeira validação.

### Collector público

Para validar o collector de forma limitada e permitir o encerramento limpo:

```powershell
.\PC_ENGINE\.venv\Scripts\python.exe .\PC_ENGINE\tools\run_market_data_collector.py --run-seconds 120
```

Depois de confirmar o estado final STOPPED em `PC_ENGINE/data/radar/market_data_health.json`, pode ser iniciado manualmente em modo contínuo omitindo `--run-seconds`. A recolha usa dados públicos e permanece observacional/PAPER.

## Android

O workflow Android APK pode ser executado manualmente ou por uma tag `mobile-vX.Y.Z`. O APK é publicado como artefacto.

O Android liga ao PC através de uma rota privada autenticada, preferencialmente Tailscale. Não expor a porta do Trader diretamente à Internet.

## Operação fora de casa

O PC deve permanecer ligado e sem suspensão quando for necessário operar continuamente. Tailscale no PC e no telefone é a rota privada prevista; a ligação remota ainda deve ser validada de ponta a ponta. O telefone é um cockpit de comando e não guarda chaves de exchange.

## Regras de operação atuais

O âmbito desta fase é exclusivamente PAPER e recolha pública/read-only. Não configurar chaves privadas de exchange, não ativar REAL/LIVE e não executar operações financeiras. Os requisitos de readiness REAL documentados noutros capítulos são referências arquiteturais futuras, não instruções para a instalação ou validação atuais.

## Ponte de intervenção humana

O PC e o telefone são independentes. Se o PC encontrar um login, 2FA/OTP, CAPTCHA ou outra barreira humana, cria um pedido persistente no Human Interaction Bridge. A intervenção é humana e normal; não há bypass de CAPTCHA, 2FA ou anti-bot.

## Estudos PAPER

O harness local pode produzir outcomes líquidos de custos, separação cronológica train/test, walk-forward, análise por regime e Monte Carlo. Nenhuma etapa envia ordens, altera risco ou promove REAL. Os relatórios são evidência de investigação, não prova de rentabilidade nem autorização para negociar.

## Diagnóstico

O cockpit autenticado pode expor diagnósticos observacionais, incluindo estado do engine, watchdog, preflight, reconciliação, idade do collector, eventos por venue, contadores de reconnect/erro e crescimento de dados. O diagnóstico não envia ordens nem depende da cloud.
