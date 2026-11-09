# Segurança operacional — âmbito PAPER atual

## Regras obrigatórias

1. O âmbito atual de instalação, testes e operação é exclusivamente PAPER e recolha pública/read-only.
2. Não configurar API keys privadas de exchanges nem permissões de trading nesta fase.
3. Manter `mode=PAPER`, `radar.observational_only=true`, `autonomous_execution.allow_real=false` e `autonomous_execution.auto_promote_real=false`.
4. Não executar ordens, transferências, levantamentos ou operações financeiras.
5. Nunca guardar tokens, passwords, chaves ou ficheiros de configuração local no GitHub.
6. Não automatizar missões, quizzes, cupões, cliques ou interfaces privadas das exchanges.
7. Rever logs e diagnósticos; respeitar imediatamente SAFE_MODE e KILL_SWITCH.

## Token da API local

`VST_LOCAL_TOKEN` autentica comandos e endpoints privados da API local. Não é uma chave de exchange e não concede permissões financeiras.

No Windows, a partir do código-fonte:

- `scripts/ensure_windows_token.ps1` gera um token aleatório para o utilizador Windows se ainda não existir e preserva o valor existente.
- `scripts/configure_windows_secrets.ps1` é uma alternativa para definir um token escolhido pelo operador através de entrada segura.
- Fechar e reabrir o terminal depois de alterar a variável de ambiente.

Não usar exemplos `setx BINANCE_KEY`, `setx BINANCE_PRIVATE` ou equivalentes durante a instalação PAPER. Não introduzir credenciais de exchange no setup.

## Instalador e arranque

O instalador Windows empacotado é manual-first: não inicia o engine/collector, não cria tarefas agendadas e não ativa autostart. Validar primeiro configuração, health check e recolha pública limitada.

`scripts/install_windows_autostart.ps1` é uma opção separada apenas para instalações a partir do código-fonte. Só deve ser executada depois de validação local bem-sucedida e decisão explícita do operador. Não faz parte da primeira instalação nem do instalador empacotado.

## Rede e acesso remoto

- Manter a API ligada a loopback durante a validação local.
- Não fazer port-forward da porta 8765 no router.
- Só introduzir Tailscale/controlo remoto depois de validar autenticação, identidade do dispositivo e reconexão.
- Nunca enviar o token local ou credenciais por logs, relatórios ou commits.

## Fases futuras

Documentação de REAL/LIVE que permaneça no repositório descreve arquitetura ou gates futuros. Não é autorização nem instrução operacional para esta fase. Não ativar REAL/LIVE, não alterar permissões financeiras e não testar com contas reais.
