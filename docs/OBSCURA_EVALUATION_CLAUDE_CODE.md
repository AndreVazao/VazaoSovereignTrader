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
3. Comparação com Chromium headless sob condições equivalentes, se o protocolo da versão instalada for compatível.
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
- **Benchmark:** executar apenas após confirmar que o protocolo de controlo da Obscura é compatível; publicar resultados brutos e condições.
- **Integração experimental:** só se o benchmark justificar, atrás de feature flag e com testes de contrato.
- **Hardware físico:** quando o PC estiver disponível; até lá, BLOCKED/NOT RUN.

## Segurança

Não usar credenciais reais nem copiar cookies/perfis. Não publicar segredos nos logs/artefactos. Respeitar rate limits e termos dos sites. Usar fixtures locais controladas. Não alterar o motor de execução financeira nem ativar live trading.
