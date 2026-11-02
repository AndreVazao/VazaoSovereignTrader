# VST — Estado mestre e plano de execução
**Data:** 2026-11-01  
**Repositório:** AndreVazao/VazaoSovereignTrader  
**PR de trabalho única:** #522 — modular runtime foundations and Android office validation  
**Branch:** fix/android-office-layout-2026-10-30  
**HEAD verificado antes desta documentação:** 1cd99862ac7590b9b60f364f921fd7e218a65e32

Este documento é a passagem de contexto operacional. Atualizar quando houver mudanças verificadas; distinguir sempre implementação, CI, inspeção visual e teste físico. Não inferir conclusão a partir de um workflow verde.

## Decisão de produto e prioridades
1. **Cérebro VST primeiro:** serviço headless, autónomo e resiliente; o cockpit/escritório não pode bloquear nem degradar o ciclo de mercado, risco, persistência ou execução.
2. **Escritório virtual em paralelo:** visualização útil, responsiva e fiel ao mockup; não é autoridade sobre o estado real dos agentes.
3. **Distribuíveis separados:** backend/cérebro, frontend desktop e APK Android. Backend/desktop com direção Windows + Linux; clientes remotos através de ligação autenticada, preferencialmente Tailscale. Não abrir portas públicas nem tornar a cloud indispensável ao motor local.
4. **Uma única PR/branch ativa de implementação.** Consolidar trabalho útil nesta PR; não criar PR concorrente. Fazer merge apenas quando checks do HEAD exato estiverem verdes, artefactos relevantes forem inspecionados e bloqueadores de aceitação estiverem resolvidos.
5. **Sem serviços pagos obrigatórios.** Não comprar nem integrar AlgoMaker. Ideias úteis podem ser estudadas a partir de fontes abertas e implementadas independentemente.
6. **Segurança inegociável:** PAPER/read-only por defeito; nenhuma ordem real, movimento de fundos ou permissão REAL decorrente de testes/documentação/IA; nenhuma chave ou credencial no Git.

## Estado Git e validação verificada
A PR #522 foi consultada diretamente e está OPEN, merged=false, mergeable=true. HEAD atual na consulta: 1cd99862ac7590b9b60f364f921fd7e218a65e32.

Workflows concluídos para esse HEAD:
- Windows EXE — **success**, run 1036, ID 41225355136.
- Android APK — **success**, run 196, ID 41225355149.
- Obscura cloud smoke / comparação Chromium — **success**, run 73, ID 41225355112.
- Trading engine PAPER smoke — **success**, run 124, ID 41225355148.
- Python tests — **success**, run 3335, ID 41225355178.
- Diorama Virtual Office Prototype (VM) — **success**, run 55, ID 41225355195.
- Android Emulator UI Smoke — **FAILURE**, run 153, ID 41225355226.

**Resultado: não fazer merge.** A falha de Emulator é um bloqueador de CI no HEAD atual. Além disso, existe uma falha de aceitação visual confirmada por screenshots do APK instalado no telemóvel físico: o ecrã de chat aparece quase todo preto/com navegação estreita; a página Office mostra cartões/retângulos esquemáticos, não o edifício isométrico acordado. Teste físico não deve ser declarado passado.

Comentário de aceitação visual já registado na PR: https://github.com/AndreVazao/VazaoSovereignTrader/pull/522#issuecomment-6555357347. O comentário identifica MOBILE_APP/ui.py / BuildingPreview como desenho esquemático e explica que o protótipo Diorama não está integrado no APK de produção.

## Trabalho já existente — cérebro/runtime
- PC_ENGINE/tools/doctor.py tem --probe-renderer opcional; usa Chromium/Playwright local já instalado, sem descarregar browsers nem navegar para URLs externas. Falhas/ambiguidade resultam em renderer unknown.
- PC_ENGINE/tools/component_plan.py e tests/test_component_plan.py: plano puro e fail-closed de componentes; chat mantém cérebro headless, pixel adiciona escritório leve e enhanced/3D só se explicitamente suportado. **Ainda não ligado ao instalador.**
- tests/test_runtime_doctor.py: recomendações conservadoras para capacidades de renderização.
- Auditoria do instalador Inno Setup: build/ms-playwright serve o worker browser/research e não deve ser removido como se fosse dependência gráfica 3D.
- Obscura continua experimental. A comparação sintética de arranque não demonstra superioridade sobre Chromium persistente nem em páginas reais de exchanges; não selecionar automaticamente nem permitir bypass dos controlos de rede.
- Arquitetura modular/headless e modos visuais chat, pixel, enhanced, 3d, auto são documentados; nem todos estão implementados e não devem ser anunciados como concluídos.
- Outras áreas existentes/documentadas: Sovereign Market Radar e recolha multi-exchange; Capital Opportunity Engine; investigação autónoma isolada do hot path; Data Quality Gates; Evidence Ledger; learning loop; Champion/Challenger; OOS/walk-forward; stress de custos; readiness persistente; reconciliação de ordens/fills; idempotência; recovery; isolamento multi-owner e Risk Engine.
- A presença de componentes não prova que a cadeia end-to-end esteja completamente integrada ou operacional. Continuar a medir e testar as lacunas.

## Plano de execução — cérebro

### B0 — Bloqueadores de integração imediatos
- [ ] Inspecionar logs da falha do Android Emulator UI Smoke (run 153), reproduzir e corrigir a causa real.
- [ ] Voltar a executar workflows relevantes no novo HEAD e confirmar resultados do HEAD exato.
- [ ] Verificar ligação entre component planner, diagnóstico e instalador antes de alterar Inno Setup; definir contratos/testes do ciclo de instalação/upgrade/uninstall primeiro.
- [ ] Fazer revisão de regressões sobre PAPER smoke, recuperação, risco, APIs autenticadas e invariantes financeiras.
- [ ] Manter o cérebro desacoplado de UI, IA externa, Obscura e conectividade cloud.

### B1 — Pipeline de evidência e comparação de estratégias
- [ ] Inventariar o harness PAPER existente antes de criar novos componentes.
- [ ] Garantir caminho de replay comum e reprodutível, datasets/manifests versionados e timestamps de evento/receção.
- [ ] Comparar trend, momentum, breakout e mean reversion por símbolo/timeframe/regime com os mesmos pressupostos.
- [ ] Incluir fees, spread, slippage, funding/borrow quando aplicável, latência, liquidez, fill probability e adverse selection.
- [ ] Exigir splits cronológicos, no-look-ahead, walk-forward/OOS, Monte Carlo, stress de custos e contagem/incerteza da amostra.
- [ ] Guardar evidências append-only com versões de estratégia/dados e motivos para PASS, INSUFFICIENT_EVIDENCE ou BLOCKED.
- [ ] Não promover candidato nem ativar REAL automaticamente a partir de métricas de backtest.

### B2 — Radar e robustez operacional
- [ ] Validar streams/WebSockets, timestamps de origem/receção, sincronização do relógio, freshness e reconexão.
- [ ] Separar falhas por exchange e tornar capacidades desconhecidas indisponíveis em vez de as presumir.
- [ ] Cobrir todos os consumidores de market data com Data Quality Gates.
- [ ] Testar crash/restart, resultados de execução ambíguos, fills parciais/múltiplos e reconciliação sem duplicação.
- [ ] Melhorar diagnósticos determinísticos exportáveis, saúde do collector, armazenamento e leases de serviços opcionais.
- [ ] Confirmar que endpoints de controlo exigem autenticação e que cloud não transporta ordens nem é necessária para funcionamento local.

## Plano de execução — escritório virtual

### O0 — Corrigir aceitação visual
- [ ] Rever logs do workflow de Emulator que falhou.
- [ ] Substituir o BuildingPreview esquemático em MOBILE_APP/ui.py por uma cena isométrica/voxel real leve, integrada no ecrã Office de produção.
- [ ] Usar como referência a imagem aprovada: vista superior angular do edifício aberto/corte frontal, paredes e pisos visíveis, salas distintas, secretárias, monitores, agentes voxel e etiquetas legíveis.
- [ ] Manter CEO no piso superior; Market Radar e comparação de exchanges separados; Investigação e Análise distintos; Memória Central como sala e serviço transversal; resposta rápida separada sob limites de risco.
- [ ] Vista inicial deve mostrar o edifício completo. Selecionar uma divisão faz zoom para essa divisão; permitir zoom in/out e regressar à vista geral.
- [ ] Chat é uma página separada do escritório. Corrigir navegação estreita e conteúdo preto/vazio.
- [ ] Adaptar portrait, landscape e tablet sem deformar proporções; garantir que rotação real muda a composição. Validar screenshots e OCR com asserções robustas, sem aceitar falsos positivos.
- [ ] Não afirmar que Diorama VM é integração de produção: é apenas protótipo isolado até o renderer ser incorporado e validado no APK.

### O1 — Estado operacional honesto
- [ ] Sem backend confirmado, mostrar claramente DEMO/OFFLINE e apenas animações locais.
- [ ] Só mostrar progresso de trabalho/estado real quando confirmado por estado autenticado do backend.
- [ ] Não deixar animações, rendering ou comunicação do cockpit bloquear o motor.
- [ ] Modos de qualidade adaptativos: chat, pixel, enhanced, 3D e auto; fallback conservador quando capacidade desconhecida.
- [ ] Validar APK gerado no CI por inspeção dos artefactos e, quando o utilizador tiver o telemóvel disponível, recolher teste físico. Não alegar teste físico sem evidência.

## Ordem de merge e continuidade
1. Diagnosticar e corrigir a falha de Emulator no HEAD atual.
2. Integrar a cena isométrica real na UI de produção e resolver a falha de aceitação visual.
3. Continuar em paralelo tarefas do cérebro, sem diluir a revisão da PR ativa; cada alteração deve ter testes focados e evidência.
4. Executar CI completo no HEAD final e inspecionar artefactos APK/emulator/screenshot.
5. Confirmar branch/HEAD/checks atuais; fazer merge de #522 só quando tudo estiver verde e os critérios de aceitação estiverem satisfeitos.
6. Após merge, verificar main e artefactos pós-merge; só então abrir a próxima branch de trabalho.

## Limites e regras de reporte
- Não dizer corrigido, integrado, testado no telemóvel ou pronto sem evidência.
- Não confundir protótipo VM, build APK, smoke de emulador e teste físico.
- Não usar credenciais reais nem executar ordens reais.
- Não introduzir compras, serviços pagos obrigatórios, portas públicas ou dependências cloud críticas.
- Ao retomar, começar por verificar estado atual da PR #522 e falha de Emulator run 153, porque esta documentação foi escrita para HEAD 1cd99862ac7590b9b60f364f921fd7e218a65e32.


## Atualização de execução — 2026-11-01, depois do primeiro registo
- Commit de documentação: 8fd0f2ad55ce22bdf6d762853fcb8d9fb169a12d.
- O log do Emulator run 153 foi inspecionado. O build e instalação do APK funcionaram; o teste falhou porque, após o toque em 50%,78%, o OCR ainda encontrou o ecrã de escolha inicial (incluindo o botão “USAR ESCRITÓRIO VIRTUAL”) e não o ecrã do escritório. Isto indica que a coordenada de toque não selecionou a ação esperada; não é prova de crash da app.
- Ajustei o cenário Maestro para tocar mais abaixo, em 50%,92%: commit 55f233b7d9f707e592d4bafeced0d0939e5ea4c3. A correção ainda precisa de CI para confirmar que a escolha é acionada.
- Comecei a substituir o preview esquemático em MOBILE_APP/ui.py por uma cena geométrica isométrica local com piso em losango, paredes traseiras/laterais abertas, separadores, secretárias, monitores, agentes voxel e etiquetas de salas. Commit 5ecc6087206e932566279ad22d2e480572ecc623. Esta alteração ainda NÃO está validada por APK/emulador nem por teste físico; rever a escala e a legibilidade nas capturas antes de a considerar aceite.
- Próxima ação imediata: consultar checks no HEAD mais recente, abrir os artefactos de screenshot, corrigir erros de renderização/OCR e ajustar a composição. Não fazer merge enquanto houver qualquer check vermelho ou a cena ainda não corresponder visualmente à referência.

- Iteração seguinte: o contrato de teste MOBILE_APP/test_startup_contract.py também foi atualizado para esperar a nova coordenada de toque e o título da cena isométrica (commit b59c653516894f810f88a64dec0ba509cec29b36). A área da cena foi aumentada e o título da vista foi atualizado em MOBILE_APP/ui.py (commit a45c9f3c82a616f44baa580b4cc34e1221fe967d).
- HEAD da última consulta: a45c9f3c82a616f44baa580b4cc34e1221fe967d. Os novos workflows ainda não estavam disponíveis na consulta imediatamente após o commit; verificar novamente antes de assumir qualquer resultado.

- Correção adicional da análise geométrica do formulário: 92% do ecrã também fica abaixo do botão. O toque foi corrigido para 65%, onde o CTA “USAR ESCRITÓRIO VIRTUAL” deve estar no layout atual; o contrato de teste foi alinhado. Commits: Maestro 0541831905ebc9ce8178044945638f343a9fb153; teste 6359357a2cd69dfc1fea86c5d69311f01ee84aad. A nova execução precisa confirmar a coordenada; se o layout mudar, preferir uma asserção visual/fluxo mais robusto.

## Deskforce study and phased implementation — 2026-11-01

Status: reference study only; no Deskforce code imported. Keep the VST brain as the authority for task state, risk policy, memory and trading permissions. Deskforce/Pixel Office are inspiration, not replacements.

Architecture ideas to evaluate against existing VST code before adding abstractions:
- Keep UI/cockpit as a thin client; renderer failure or closure must not interrupt headless market/risk/learning loops.
- Persist task lifecycle and recovery state in the authoritative backend; verify scheduler/API integration before claiming end-to-end recovery.
- Keep model-provider adapters behind contracts with timeouts, cancellation, budgets and secret-safe logs.
- Require explicit authenticated authorization and audit for sensitive actions; health status or model output must never grant trading authority.
- Office animation is DEMO/OFFLINE unless an authenticated backend confirms agent/task state.

Phased plan:
1. Stabilize #522: inspect current APK/emulator artifacts, improve mobile hierarchy so the building is the primary viewport, reduce redundant CEO artwork/cards, make room selection/zoom discoverable, and preserve portrait/landscape proportions.
2. Add/strengthen focused layout and state-contract tests; run APK build and emulator screenshots, inspect artifacts, and document any remaining visual limitations.
3. Compare the runtime/scheduler/persistence implementation with Deskforce concepts; implement only concrete gaps, with unit tests and no duplicate queue/store.
4. Merge only when every required check is green on the exact HEAD and visual acceptance is met. Then verify main and open the next branch/PR only after #522 is merged, preserving one open implementation PR.

Do not claim physical-phone validation without evidence. Keep trading PAPER/read-only; no real orders, real credentials, public ports, or mandatory paid services.

### Implementation phase 1 — mobile visual hierarchy (2026-11-01)
- `MOBILE_APP/ui.py`: removed the separate decorative CEO wall-art card from the Office page so the isometric building appears earlier; reduced the offline notice from 82dp to 62dp; made the building card height adapt to viewport height within 220–340dp; reduced the separate offline animation panel from 170dp to 126dp.
- `MOBILE_APP/test_startup_contract.py`: added a source contract guarding the new hierarchy and adaptive building height.
- Commits made on the existing PR branch: `5620b65f3ff89833956ea0067ca13b550f8cfe22` (UI) and `bf8b582ce6e1cf63be4c7762d250dfcbfaf7e65d` (test). Documentation update for Deskforce is commit `8ddcaa130fc44ed9469bce5e93406840a4dfa076`.
- Status: implementation committed, but CI for the newest HEAD and fresh emulator screenshots are still required. Do not treat source-contract tests as visual acceptance. Next: wait for checks, inspect portrait/landscape/tablet screenshots, then adjust scene framing/room selection based on evidence.


## Follow-up validation — 2026-11-02

- Exact HEAD `6252c3087712bef3fcdf501f1647f5d9f05cf2e9`: Python, Android APK, Windows EXE, Diorama VM, Obscura and PAPER smoke passed; Android Emulator UI Smoke failed at the office-navigation stage.
- Failure artifact showed the app alive on the first-run chooser; no office screenshot was produced. Comparing the 1080x1920 chooser capture with the Maestro tap target revealed the configured 71% vertical point landed below the office CTA (the button center is around 60%).
- Updated `.maestro/android-office-smoke.yaml` and its source-contract assertion to tap `50%, 60%`. This is a test-coordinate correction based on the captured UI, not yet a passing validation.
- Next gate: wait for fresh checks on the resulting exact HEAD, inspect office/portrait/landscape/tablet screenshots, and merge only when every required workflow is green. Physical-phone validation remains unconfirmed.


## Mudança de prioridade — 2026-11-02: pausa visual, foco exclusivo no cérebro

Decisão explícita do proprietário: suspender novas alterações de UI/arte do APK enquanto se acelera o backend/cérebro. Não investir ciclos em avatares, renderer, layout ou animações nesta fase. Alterações mínimas na UI só são permitidas se forem necessárias para testar ou desbloquear o backend.

### Auditoria inicial do runtime (código consultado na branch ativa)
- `PC_ENGINE/main.py` seleciona `PaperConfluenceEngine` em modo PAPER quando a confluência está ativa; cria relatório `StartupHealth`; cria a API; o auto-start depende de `engine.auto_start_paper`; por omissão a API usa loopback e fecha o motor no encerramento.
- `PC_ENGINE/core/startup_health.py` escreve um relatório de arranque e considera `recovery_manager_missing` crítico. O modo REAL configurado é degradado para PAPER no relatório, mas esta verificação não substitui uma prova end-to-end de que todas as rotas de execução ficam bloqueadas.
- `PC_ENGINE/tools/health_isolation.py` calcula decisões fail-closed de isolamento, mas o próprio módulo declara que não para workers nem altera o runtime. É uma política, não um supervisor operacional integrado.
- `tests/test_real_controlled_runtime_e2e.py` contém um adaptador sintético controlado que testa a cadeia de ordens com gate REAL explicitamente ativado em teste. Não prova acesso a uma exchange real nem prontidão para trading real.
- O projeto tem testes de recuperação, memória SQLite/backup, PAPER, saúde de market data, risco final e superfícies de execução. A próxima etapa é consolidar esses testes num gate de prontidão único, com evidência legível, em vez de inferir prontidão a partir da presença de módulos.

### Próximo marco de backend: instalação de teste segura
1. Fazer inventário das dependências e dos comandos suportados de arranque/diagnóstico; manter o serviço headless independente do cockpit.
2. Criar/fortalecer um comando de diagnóstico que devolva estado estruturado para configuração, modo PAPER efetivo, recuperação, persistência de memória, serviços/collector, API local e bloqueio de execução REAL.
3. Criar um teste end-to-end de ciclo de vida: iniciar runtime PAPER, consultar saúde autenticada/local, verificar heartbeat e persistência, parar, reiniciar e comprovar recuperação sem duplicação nem promoção de permissões.
4. Executar testes focados e os workflows Python, PAPER smoke e Windows EXE no HEAD exato. Não afirmar que está pronto para PC até o artefacto e o ciclo de arranque serem verificáveis.
5. Produzir uma instrução simples para o primeiro teste local quando o utilizador tiver o PC disponível; sem chaves reais, sem ordens reais, sem portas públicas.

### Critérios para declarar o cérebro pronto para primeiro teste local
- Arranque repetível e encerramento limpo do processo headless.
- Estado `PAPER` efetivo e bloqueio fail-closed de execução real.
- Diagnóstico exportável com falhas explícitas, não apenas um rótulo `RUNNING`.
- Persistência/recovery validados com reinício.
- API limitada a loopback por defeito, controlo autenticado e nenhum segredo registado em logs.
- Windows EXE compilado no HEAD exato e pacote/artefacto inspecionado; teste físico local ainda deve ser marcado como pendente até executado no PC do utilizador.

### Regras para esta fase
- UI visual: **PAUSADA**. Não fazer mais alterações cosméticas no APK.
- Prioridade: backend, diagnóstico, ciclo de vida, segurança, memória/recovery e PAPER end-to-end.
- Modo operacional de desenvolvimento: PAPER/read-only; não ligar contas reais nem enviar ordens.
- Manter uma única PR/branch ativa. A PR #522 permanece aberta; não fazer merge até CI obrigatório e critérios aplicáveis estarem satisfeitos.
- Percentagens reportadas como estimativas separadas de implementação, CI, pacote produzido e teste local real.


### Backend progress log — 2026-11-02 (continued)
- The latest completed CI run before the newest doctor changes reported Python tests, PAPER smoke, Windows EXE build and Android APK build as successful; Android Emulator UI Smoke still failed. These results are for commit `0c83a99f`, not for the current HEAD, and must not be carried forward as current validation.
- `GET /health` now reports API liveness separately from the engine status, including `engine_running`; tests cover stopped and running snapshots. This prevents an available API from being misread as a running brain.
- `vst doctor` now reports `runtime_readiness` separately from install preflight. Missing startup health is `UNKNOWN`; invalid JSON/schema is `INVALID`; recovery failure/non-PAPER startup is `SAFE_STATE`; only a PAPER startup report with explicit passing mode and recovery checks can report `STARTUP_CHECKS_PASSED`.
- This status is deliberately named `STARTUP_CHECKS_PASSED`, not “fully ready”: it is not proof of an end-to-end lifecycle, active heartbeat, working market-data feed, or successful PC installation.
- Tests were added for missing/invalid startup reports and failed recovery checks. The latest commits are awaiting their own CI results; do not describe them as passed until the exact HEAD has completed its workflows.
- Next engineering task remains the integrated PAPER lifecycle gate: start -> authenticated diagnostics/heartbeat -> persistence -> clean stop -> restart/recovery -> confirm no duplicate pending execution and no permission escalation.


### Persistent learning vault — 2026-11-02
- Added `PC_ENGINE/core/data_vault.py`: stable per-user vault paths, atomic manifest creation, read-only validation. Windows defaults to `%LOCALAPPDATA%\\VazaoSovereignTrader\\vault`; `VST_VAULT_PATH` permits an explicit operator-selected location.
- The vault layout separates `learning/`, `backups/`, `imports/`, `exports/`, and `logs/`. Imports are quarantined and must never be automatically treated as trusted learning or execution authority.
- Engine learning SQLite is now routed to `<vault>/learning/<owner-id>/sovereign-learning.sqlite3`, outside the versioned install directory.
- If the legacy learning database exists and the new vault database does not, startup attempts a consistent SQLite backup copy and leaves the source database untouched. The migration is non-destructive; migration failure must remain visible as learning-memory unavailable.
- Added `tests/test_data_vault.py` for path selection, layout, preservation, missing vault and corrupt manifest cases.
- Updated the Windows local validation Prompt Master to require uninstall/reinstall persistence checks and legacy-database migration verification.
- Important remaining gap: the installer must be verified not to remove the user vault, and the actual Windows package must be tested across uninstall/reinstall. Code-level path separation alone does not prove installer preservation.
- Current commit series has not yet completed CI; do not mark vault tests or Windows packaging as passed until workflows for the exact HEAD finish.


### Backend integration fix — 2026-11-02, continuation
- Found a concrete diagnostics-path mismatch: `PC_ENGINE/main.py` writes startup health to the owner-private path `PC_ENGINE/data/owners/<owner-id>/startup/startup_health.json`, while `vst doctor` previously looked only at `PC_ENGINE/data/startup_health.json`. As a result, a valid engine startup report could be missed and readiness incorrectly remain `UNKNOWN`.
- Updated `PC_ENGINE/tools/doctor.py` to prefer the configured/effective owner's private report and retain the flat path only as a legacy compatibility fallback. Invalid owner IDs are mapped to an isolated impossible namespace instead of reading another owner's report.
- Added `tests/test_doctor_owner_startup_health.py` covering the owner-private report path and preventing invalid owner identity from reading another owner's health report.
- Commits: `4f2524621169e91ccb4a945023a18ba550aec21a` (diagnostic path fix), `ea519ecae61dd59fe41b727ec6ddd97cefbd9b83` (focused tests).
- Validation status: code committed to the existing PR branch. New CI for these exact commits must complete before calling the fix verified. Earlier Python and PAPER smoke successes belonged to the prior HEAD and are not carried forward as validation of this change.
- Next: run the focused doctor tests and full Python workflow; inspect Windows EXE and PAPER smoke on the new HEAD; then continue the integrated PAPER start/health/heartbeat/persist/stop/restart recovery gate. Physical Windows PC testing remains pending.


### Doctor owner-isolation test correction — 2026-11-02
- The Python workflow on merge commit `021a181dec212265da0877eae93e6eb0dff95053` reported 1,286 passed and one failure in the new invalid-owner test. The failure was in the test expectation: for an invalid owner ID, the doctor correctly returned no report path (`None`) rather than exposing a synthetic path string.
- Updated the assertion to require `startup_health_report is None`, while also requiring readiness to remain `UNKNOWN` and `verified is False`. This preserves the security property: an invalid identity cannot resolve another owner's report.
- Correction commit: `223d5b60d4e41245184d851d7003cb7a14ce3104`.
- Fresh CI on this exact commit is required; do not treat the prior run as green. The PR remains open and unmerged.
