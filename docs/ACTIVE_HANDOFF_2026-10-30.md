# ACTIVE HANDOFF — VazaoSovereignTrader — 2026-10-30 (atualizado)

## Prioridades vigentes
1. Cérebro/runtime headless, modular, seguro, observável e migrável; PC antigo continua o primeiro ambiente.
2. Corrigir e validar APK/escritório Android com artefactos do commit atual.
3. Windows e Linux suportados; Linux Server LTS mínimo é preferência futura para nós dedicados compatíveis, sem migração obrigatória agora.
4. Obscura vs Chromium: avaliar em cloud Linux com smoke e benchmark repetível; não afirmar vantagem antes dos resultados.
5. Escritório remoto/streaming é uma capacidade futura opcional; cockpit/chat leve não pode depender do renderer.

## Estado Git confirmado nesta atualização
- PR #521 foi merged em main: documentação de política multiplataforma, perfis adaptativos e avaliação cloud Obscura.
- PR #519 está fechada sem merge para evitar duas PRs ativas; o plano e o workflow Obscura foram transferidos para main via PR #521. O benchmark comparativo agora é desenvolvido na branch ativa de #522.
- PR #522 é a única PR de implementação aberta neste bloco: https://github.com/AndreVazao/VazaoSovereignTrader/pull/522
- Branch: `fix/android-office-layout-2026-10-30`. Confirmar o HEAD antes de interpretar resultados de Actions; qualquer commit novo invalida a evidência de commits anteriores.
- Não declarar branch remota apagada sem confirmação explícita do GitHub.

## Decisões de arquitetura
- O primeiro deployment continua no PC antigo; não exigir nova máquina, GPU dedicada ou servidor gráfico.
- Core, departamentos, memória, browser/research, API/cockpit e visualização são fronteiras separadas. Falha da UI/renderer/browser não deve parar o cérebro.
- Um PC primeiro: módulos locais comunicam-se por interfaces internas sem introduzir rede desnecessária; os mesmos contratos permitem distribuir componentes depois.
- Perfis futuros: brain-server, department-worker, research-worker, memory-node, desktop-cockpit, office-visualizer e browser-worker. São alvos arquiteturais, não todos implementados.
- Migração exige configuração declarativa, estado versionado, backup/restauro e enrollment/autorização explícitos. Identidade/autoridade não deriva do hostname/fingerprint.
- Linux Server LTS é preferido para futuro nó headless compatível, mas Windows continua suportado. Benchmark de OS no hardware físico = NOT RUN.
- Renderização remota/vídeo é FASE FUTURA. Primeiro manter cockpit leve; depois avaliar cliente web por API/eventos. Streaming (ex. WebRTC) só se um motor gráfico futuro justificar GPU remota.
- Obscura é experimental; Chromium/adaptador suportado continua fallback. Não implementar seleção automática de produção até funcionalidade, compatibilidade, fallback e benchmark serem comprovados.
- PAPER/read-only por defeito; sem ordens reais, transferências, credenciais reais em CI, portas públicas automáticas ou bypass de MFA/CAPTCHA/anti-bot.

## APK / escritório virtual
- O screenshot físico fornecido pelo utilizador revelou layout apertado e avatares sobrepostos; o utilizador também reportou ausência de rotação.
- PR #522 reduz largura da navegação em telemóvel, ajusta a grelha a 1/2/3 colunas, substitui caracteres por figuras pixel-art leves e tenta adaptar layout ao resize.
- `MOBILE_APP/buildozer.spec` usa `orientation = all`, mas é experimental devido a falha histórica do Buildozer com esse valor. Não afirmar rotação resolvida sem build + screenshots portrait/landscape/tablet inspecionadas.
- Run APK #126 (41110052887) e Emulator UI Smoke #83 (41110053343) falharam antes da compilação/emulador porque o teste de contrato esperava a frase antiga `demonstração offline; sem tarefa real confirmada`, removida quando as personagens de texto foram substituídas. O teste foi atualizado para verificar o aviso offline efetivamente apresentado; revalidar num run novo.
- Não há APK/capturas atuais validados destes runs falhados. Artefactos de runs anteriores não provam o estado atual.
- Escritório continua demo offline, não ligado ao runtime real. Validação física Android/ADB e ligação PC↔telefone permanecem NOT RUN/BLOCKED.

## Obscura vs Chromium — estado
- Workflow: `.github/workflows/obscura-cloud-smoke.yml`.
- Foi acrescentada comparação cloud no mesmo runner Ubuntu: fixture HTML local, execução JS/DOM, smoke funcional e 7 repetições por motor, com medições e JSON de resultados como artefacto.
- O benchmark inclui o arranque do processo e é limitado a fixture sintética; não demonstra vantagem em exchanges nem no PC antigo.
- Resultado do novo workflow ainda não consultado nesta atualização; estado do benchmark = PENDING/NOT RUN até obter run/artefacto atual.
- Fallback runtime: Chromium/adaptador atual; ainda não declarar implementado um failover automático de produção. Nenhuma integração Obscura no caminho crítico até testes repetíveis justificarem.

## Próximos passos
1. Confirmar HEAD atual da #522 e runs Actions associados a esse HEAD.
2. Obter logs completos de falhas; corrigir causa real sem enfraquecer testes.
3. Confirmar o workflow Obscura cloud, inspecionar smoke-report e benchmark.json; repetir se inconclusivo.
4. Corrigir APK/smoke; inspecionar screenshots atuais e disponibilizar APK apenas quando o artefacto atual existir.
5. Auditar o core/runtime atual e implementar incrementalmente diagnóstico read-only, manifesto de componentes e adaptadores multiplataforma, evitando abstrações duplicadas.
6. Atualizar memória persistente AndreOS após checkpoint validado.

## Regras de trabalho
- Uma única PR/branch ativa de implementação de cada vez.
- Não fazer merge com checks pendentes/falhados ou sem inspeção dos artefactos visuais relevantes.
- Não apagar documentos que contenham evidência única; manter este handoff como estado atual e marcar documentos antigos como históricos quando necessário.
- Separar PASS, FAIL, BLOCKED e NOT RUN. Não declarar hardware físico, benchmark ou integração que não tenha sido executado.
- Não trabalhar no DGM-MAT; é um projeto separado.
