# PC — checklist de prontidão PAPER

## Instalação e validação inicial

Para instalação a partir do código-fonte:

1. Windows 10/11 com Python 3.11+.
2. Executar `scripts/setup_windows.ps1`.
3. Executar `scripts/ensure_windows_token.ps1` para gerar o token local se ainda não existir.
4. Opcionalmente, executar `scripts/configure_windows_secrets.ps1` para definir um token próprio com entrada segura.
5. Fechar e reabrir PowerShell para carregar a variável de ambiente.
6. Executar `scripts/verify_pc_install.ps1`.
7. Executar `scripts/verify_public_market_data.ps1` e inspecionar `market_data_bootstrap.json`, incluindo venues READY e degradadas.
8. Iniciar manualmente com `scripts/windows_run_pc_engine.bat`.
9. Confirmar resposta HTTP 200 em `http://127.0.0.1:8765/health`.

Para instalação pelo pacote Windows, não é necessário instalar Python. O instalador inclui o helper em `%LOCALAPPDATA%\VazaoSovereignTrader\scripts\ensure_windows_token.ps1`. Executá-lo, fechar e reabrir PowerShell e iniciar o EXE a partir dessa nova sessão para herdar `VST_LOCAL_TOKEN`. Consultar `docs/WINDOWS_ONE_CLICK_INSTALL.md` para os comandos completos.

A verificação leve não executa a suíte Python completa por defeito. Usar testes focados e evitar a suíte integral/endurance enquanto o collector estiver ativo numa máquina com pouca memória.

## Invariantes obrigatórias nesta fase

- `mode=PAPER`.
- `radar.observational_only=true`.
- `autonomous_execution.allow_real=false`.
- `autonomous_execution.auto_promote_real=false`.
- Não configurar API keys privadas de exchanges.
- Não conceder permissões de trading, transferências ou levantamento.
- Market data inicial deve usar apenas endpoints públicos/read-only.
- O token `VST_LOCAL_TOKEN` protege a API local e não é uma credencial de exchange.

## Collector público

Primeiro executar um teste limitado com `--run-seconds 120`. Confirmar encerramento limpo e estado STOPPED em `market_data_health.json`. Só depois iniciar manualmente a recolha contínua, se o operador assim decidir.

## Arranque automático e operação 24/7

Não instalar autostart durante a validação inicial. O instalador Windows empacotado não cria tarefas agendadas nem inicia engine/collector. Para uma instalação a partir do código-fonte, `scripts/install_windows_autostart.ps1` é uma opção separada, que só deve ser executada após validação física bem-sucedida e decisão explícita do operador.

## Comando remoto

Usar uma rota privada autenticada, preferencialmente Tailscale, depois de validar a configuração e identidade do dispositivo. Não fazer port-forward da porta 8765 no router.

## Critério de aceitação local

A instalação só fica validada no PC quando o operador confirmar manualmente o arranque, health check, leitura de dados públicos, encerramento limpo do collector e preservação dos dados. Um workflow CI verde não substitui esta validação física.
