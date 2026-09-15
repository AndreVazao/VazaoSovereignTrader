# Fast Execution Integration Boundary

Esta etapa prepara a ligação do Fast Path ao executor sem criar um segundo caminho de ordens.

O `FastExecutionRouter` recebe uma função `executor` explicitamente fornecida pelo chamador. A função deve ser construída apenas depois de o Risk Engine, modo de operação e `RealModeGuard` terem autorizado a execução.

O router não conhece exchanges, não possui credenciais e não altera limites. Sem executor configurado, uma oportunidade validada resulta em `executor_not_configured` e nenhuma ordem é enviada.

A telemetria mede avaliações, rejeições, execuções, erros do executor e latência máxima para permitir validar se a otimização realmente melhora o tempo de decisão antes de qualquer uso REAL.
