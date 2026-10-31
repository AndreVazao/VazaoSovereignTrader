# Sovereign Trader — avaliação cloud-first da Obscura

**Objetivo:** avaliar se a Obscura pode ser um motor headless leve para tarefas de pesquisa/leitura dos agentes do VazaoSovereignTrader, sem depender do PC do utilizador, do Desktop Commander, do Claude Code ou dos testes do DGM-MAT.

**Estado:** avaliação experimental; não declarar vantagem de desempenho antes de resultados repetíveis. Distinguir PASS, FAIL, BLOCKED e NOT RUN.

## Decisão inicial

- Não integrar Obscura no caminho crítico do Trader antes de existir evidência.
- Manter o adaptador de browser atual como fallback; Obscura é opcional e isolada.
- PAPER/read-only por defeito. Sem credenciais reais, perfis autenticados, ordens, transferências ou operações financeiras.
- Não usar stealth para contornar proteções de exchanges.
- Instalar apenas artefactos/releases oficiais e registar a versão; não copiar código do projeto Obscura para o Trader.

## O que a cloud pode testar

1. Disponibilidade do binário Linux oficial, arranque, versão e encerramento.
2. Navegação a uma página HTML local controlada, leitura de título/texto e execução JavaScript.
3. Comparação funcional e temporal com Chromium headless na mesma VM Linux, usando uma fixture HTML local e tarefa DOM/JavaScript equivalente.
4. Guardar logs sanitizados e resultados como artefactos de workflow.

A cloud não substitui testes no PC antigo: consumo de RAM, drivers, firewall, integração com cockpit e estabilidade prolongada no hardware real continuam por validar. Não declarar esses testes como PASS.

## Critérios de decisão

- Funcionalidade correta e taxa de sucesso consistente.
- Sem falhas críticas de segurança ou estabilidade.
- Vantagem de desempenho/recursos medida e repetível que justifique manter outro motor.
- Fallback para o motor atual em páginas incompatíveis, sem bloquear os agentes.

Resultados possíveis: ADOTAR, ADOTAR PARCIALMENTE, MANTER COMO ESTÁ ou INCONCLUSIVO.

## Plano

- **Cloud/CI:** smoke test com página local sintética e evidência guardada como artefacto.
- **Benchmark cloud:** workflow `.github/workflows/obscura-cloud-smoke.yml` executa 7 repetições por motor na mesma VM, mede tempo de processo completo, mediana/mínimo/máximo, taxa de sucesso e publica JSON/saídas como artefacto. O teste compara apenas uma fixture local sintética, incluindo arranque do processo; não mede navegação real em exchanges nem latência de mercado.
- **Decisão automática:** o relatório pode indicar qual motor foi mais rápido nesta fixture ou INCONCLUSIVE; não muda a configuração do runtime. A seleção automática em produção só deve ser implementada depois de vários tipos de tarefa, testes de fallback/circuit breaker e compatibilidade real.
- **Fallback de runtime:** Chromium/adaptador existente continua como fallback; a PR do benchmark não afirma que existe já um adaptador de seleção/failover implementado.
- **Integração experimental:** só se o benchmark justificar, atrás de feature flag e com testes de contrato.
- **Hardware físico:** quando o PC estiver disponível; até lá, BLOCKED/NOT RUN.

## Segurança

Não usar credenciais reais nem copiar cookies/perfis. Não publicar segredos nos logs/artefactos. Respeitar rate limits e termos dos sites. Usar fixtures locais controladas. Não alterar o motor de execução financeira nem ativar live trading.


## Atualização 2026-10-30 — benchmark headless cloud

Foi adicionado um benchmark reproduzível ao workflow Obscura cloud smoke:
- Binário Obscura Linux obtido da release oficial.
- Chromium/Chrome headless instalado no mesmo runner.
- Página HTML sintética servida em localhost, com JavaScript que altera um elemento DOM.
- Smoke funcional para ambos os motores.
- Sete repetições por motor para a mesma operação aproximada; registo de sucessos/falhas e latências de processo completas (incluem arranque).
- Artefacto JSON com medições brutas e decisão limitada à fixture.

**Limitações:** esta medição não demonstra que Obscura é mais rápida em páginas complexas, exchanges, APIs reais ou no PC antigo. Não mede uso de RAM/GPU de forma rigorosa, nem estabilidade prolongada. O resultado do workflow deve ser consultado antes de decidir; até lá, estado = NOT RUN/INCONCLUSIVE. O benchmark não altera a seleção do browser em produção e não integra Obscura no caminho crítico.


## Primeiro benchmark cloud concluído — resultado restrito (2026-10-30)

Run GitHub Actions `41117040323`, workflow `Obscura cloud smoke and Chromium comparison`, commit medido `ac11fe96f0c67d6a8926ed1787322356fbb96551`, artifact `obscura-chromium-cloud-evidence` (ID `13005848220`, retenção até 2026-11-13).

- Obscura `0.2.5`: smoke funcional PASS; 7/7 execuções; mediana **23,65 ms**, mínimo 19,52 ms, máximo 26,79 ms.
- Chromium/Chrome headless: smoke funcional PASS; 7/7 execuções; mediana **728,61 ms**, mínimo 691,79 ms, máximo 741,52 ms.
- A medição inclui o arranque de um processo novo em cada repetição. Por isso, parte importante da diferença pode ser o custo de inicialização do Chrome CLI; não compara um browser Chromium persistente nem sessões reutilizadas.
- Fixture: HTML sintético local com JavaScript que define `javascript-ok`; nenhuma exchange, autenticação, cookie ou operação financeira foi usada.

**Interpretação:** PASS para o smoke local de ambos; evidência preliminar de que o comando one-shot da Obscura é muito mais rápido nesta fixture. **Não é prova** de que Obscura seja globalmente mais rápida ou mais adequada para pesquisas de mercado. Decisão atual: manter Obscura como candidato prioritário para mais testes cloud; Chromium permanece fallback. Antes de alterar a seleção de produção, medir várias tarefas, cold/warm starts, compatibilidade de páginas, estabilidade, timeout/fallback e consumo de recursos. O runtime ainda não implementa um failover automático apenas por este resultado.
