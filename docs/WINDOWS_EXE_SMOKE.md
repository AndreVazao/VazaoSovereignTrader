# Windows EXE — Build e Smoke Test

## Objetivo

Validar o pacote Windows do VazaoSovereignTrader de forma determinística antes de considerar a distribuição do executável.

O workflow é infraestrutura de validação. Não altera o comportamento de trading, não ativa REAL e não substitui os gates de Risk Engine/RealModeGuard.

## Quando corre

.github/workflows/windows-exe.yml corre em execução manual, pull requests que alterem o workflow Windows, PC_ENGINE, requirements-pc.txt, scripts ou o README raiz, pushes em main e tags pc-v*.

## Pipeline

1. instala Python 3.11;
2. instala requirements-pc.txt e PyInstaller;
3. cria o executável one-file;
4. cria uma configuração de smoke isolada;
5. desliga Radar, Shared Intelligence, Research e Confluence nessa configuração;
6. inicia o EXE num diretório de runtime separado;
7. verifica se o processo não termina prematuramente;
8. consulta http://127.0.0.1:8765/health;
9. encerra o processo no bloco finally;
10. empacota EXE, configuração, README e launcher PAPER num ZIP;
11. publica o ZIP como artefacto.

## Diagnóstico

Quando o processo termina antes do health-check, o workflow reporta o exit code.

Quando o processo permanece ativo mas /health não responde, o workflow acumula as mensagens de erro das tentativas HTTP e inclui-as na falha final.

Isto é deliberadamente diferente de um timeout silencioso: a falha deve indicar se ocorreu crash imediato ou indisponibilidade do endpoint.

## Critério de sucesso

O smoke só passa quando o executável permanece ativo após o arranque inicial, /health responde HTTP 200 dentro da janela de teste, o processo é encerrado de forma controlada e o pacote final é criado.

Um smoke verde não significa readiness REAL. Significa apenas que o artefacto Windows inicia e expõe o health endpoint no ambiente de CI.

## Relação com a arquitetura de segurança

A cadeia continua: Market Data → Data Quality → Radar/Strategy → Confluence → Opportunity Gate → Risk Engine → RealModeGuard → Execution → Confirmation → Reconciliation.

O Windows smoke valida apenas a camada de distribuição/arranque do processo.

## Próximo passo

Depois de estabilizar o smoke Windows, a evolução natural é a Readiness Diagnostic Timeline, derivada de History + Trend + Scorecard, para tornar as transições de readiness auditáveis e explicáveis.
