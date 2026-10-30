# Sovereign Trader — avaliação cloud-first da Obscura

**Objetivo:** avaliar se a Obscura pode ser um motor headless leve para tarefas de pesquisa/leitura dos agentes do VazaoSovereignTrader, sem depender do PC do utilizador, do Desktop Commander, do Claude Code ou dos testes do DGM-MAT.

**Estado:** avaliação automatizada em cloud em curso. Este documento não declara resultados de benchmark que ainda não tenham sido medidos. Os resultados de cada execução devem distinguir PASS, FAIL, BLOCKED e NOT RUN.

## Decisão de arquitetura inicial

- Não integrar Obscura no caminho crítico do Trader antes de existir evidência.
- Manter o adaptador de browser atual como fallback; Obscura deve ser um adaptador opcional e isolado.
- PAPER/read-only por defeito. Sem credenciais reais, perfis autenticados, ordens, transferências ou operações financeiras.
- Não usar o modo stealth para contornar proteções de exchanges. O teste avalia desempenho/compatibilidade, não evasão.
- Obscura publica o seu código sob Apache-2.0, segundo o repositório oficial: https://github.com/h4ckf0r0day/obscura. Não copiar o seu código para o Trader; instalar apenas artefactos/releases oficiais e registar a versão.

## O que a cloud consegue testar sem o PC

1. Disponibilidade do binário Linux oficial, arranque, versão e encerramento.
2. Navegação a uma página HTML local controlada, leitura de título/texto e execução JavaScript.
3. Comportamento em DOM dinâmico, timeouts, URL inválido e servidor indisponível, quando o ambiente permitir.
4. Benchmark repetível em runner Linux contra Chromium headless usando a mesma página local, número de repetições, timeout e condições. Registar versão, mediana, p95 quando houver amostra suficiente, taxa de sucesso e RSS/CPU se medidos de forma fiável.
5. Testes de integração Playwright via CDP, apenas depois de confirmar o protocolo suportado pela versão instalada.
6. Guardar logs sanitizados e resultados JSON/Markdown como artefactos de workflow.

A cloud **não** substitui testes no PC antigo: consumo de RAM, drivers, fontes, firewall, latência local, interação com o cockpit e estabilidade prolongada no hardware real continuam por validar. Não declarar esses testes como PASS.

## Critérios antes de integrar

- Sem falhas críticas de segurança ou estabilidade.
- Tarefas funcionais de leitura corretas e taxa de sucesso consistente.
- Vantagem de desempenho/recursos medida e repetível que justifique o custo de manter outro motor.
- Compatibilidade documentada com as páginas e APIs realmente usadas pelos departamentos.
- Fallback para o motor atual em páginas incompatíveis, sem bloquear o trabalho dos agentes.

Resultado possível: ADOTAR, ADOTAR PARCIALMENTE, MANTER COMO ESTÁ ou INCONCLUSIVO. Não escolher critérios depois de observar os resultados para favorecer um motor.

## Plano de execução

- **Fase A — CI/cloud:** executar testes Linux isolados com páginas de teste locais e recolher artefactos. Nenhum acesso ao PC do utilizador é necessário.
- **Fase B — benchmark:** comparar Obscura e Chromium com tarefas equivalentes; separar resultados de arranque frio/aquecido e publicar resultados brutos.
- **Fase C — integração experimental:** só se a fase B justificar, criar adaptador opcional sob feature flag e testes de contrato, sem substituir o browser atual.
- **Fase D — validação física:** quando o PC estiver disponível, repetir o subconjunto relevante no hardware do utilizador. Até lá, marcar como BLOCKED/NOT RUN.

## Segurança operacional

Não usar credenciais reais nem copiar cookies/perfis. Não publicar segredos nos logs ou artefactos. Respeitar rate limits e termos dos sites. Usar primeiro fixtures locais controladas. Não fazer alterações ao motor de execução financeira e não ativar live trading.