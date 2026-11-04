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


### Preparação do teste local com Desktop Commander — 2026-11-02
- O utilizador confirmou que o Desktop Commander está agora disponível na conta ChatGPT principal (`vazao.andre@gmail.com`); a conta secundária `aiamorchato@gmail.com` não é a conta-alvo para a execução local.
- Criado `prompts/PROMPT_MASTER_LOCAL_WINDOWS_BACKEND_E2E.md`: procedimento completo para validar o backend headless no PC Windows antigo, com segurança PAPER/read-only, confirmação de identidade do build, instalação, diagnóstico, ciclo start/stop/restart, persistência SQLite/vault, isolamento de rede e recolha de evidências. Inclui condições explícitas de paragem e proíbe ações financeiras reais.
- Criado `docs/templates/LOCAL_WINDOWS_BACKEND_E2E_REPORT_TEMPLATE.md`: matriz de testes e estrutura para relatório detalhado com evidências, hashes, erros, resultados bloqueados e plano de correções.
- O relatório final e as evidências sanitizadas devem ficar em `artifacts/local-validation/<timestamp>/` no checkout local e numa pasta local separada. Desktop Commander não deve fazer commit/push automaticamente; o relatório será revisto antes de ser anexado ou integrado.
- Regra de segurança: só instalar o artefacto Windows produzido para o HEAD exato e com workflow de build verificado. Se não existir um artefacto validado, marcar instalação E2E como BLOCKED e executar apenas verificações locais não destrutivas. Não desinstalar/reinstalar nem migrar dados sem backup verificado e autorização explícita.
- Commits de preparação: `4fde608a37cd257f88a5da40df064686dd0d0d60` (Prompt Master) e `e428ac2c7be492462557b69fd6748de252f2991a` (template de relatório). A documentação desta atualização segue no mesmo PR/branch.
- Estado CI observado no HEAD `e428ac2c7be492462557b69fd6748de252f2991a`: Python, Windows EXE, Trading PAPER smoke, APK, Emulator UI, Obscura e Diorama ainda estavam em execução/na fila. Não instalar até confirmar build Windows e verificações de segurança no HEAD final.


## 2026-11-02 — local Windows backend audit tooling

- Added `scripts/vst_local_backend_audit.ps1`: read-only inventory for the installed Windows backend. It records executable SHA-256, sanitized allowlisted config fields, loopback `/health` response, engine-running flag, owner-scoped startup report summaries, vault directory/file counts, and scheduled-task state.
- The script does not start/stop processes, change config, enumerate full environment variables, read/report credential values, submit orders, or make public-network requests. A failed/unreachable health endpoint is recorded as NOT RUN; API liveness is explicitly not treated as engine readiness.
- Added PowerShell parser validation for the audit script to `.github/workflows/windows-exe.yml`, so the next Windows EXE run checks script syntax before packaging.
- Updated `prompts/PROMPT_MASTER_LOCAL_WINDOWS_BACKEND_E2E.md` to require running the audit and attaching its Markdown/JSON output to the evidence index.
- Latest source changes are on the existing PR #522 / branch `fix/android-office-layout-2026-10-30`; do not create a second active PR. New commits require fresh exact-HEAD CI and a new Windows installer artifact before local installation.
- Limitations are explicit: this audit is observational and does not prove vault continuity, perform migration, test authenticated private endpoints, or establish end-to-end trading readiness. Those remain separate gated tests. Keep PAPER/read-only; no REAL credentials or orders.


## Atualização de execução — 2026-11-02, ciclo de persistência headless

- A prioridade foi corrigida para cérebro/backend primeiro; a UI Android fica em segundo plano.
- HEAD de trabalho atualizado nesta sequência:
  - `05b3feeeb458778bf3e5b8bd6e0c6f88af1ea5d6` — adicionou `tests/test_headless_lifecycle_persistence.py`.
  - `70f088b2945e55c7d3e82e8e3a3ec83058969bc1` — corrigiu o teste para passar configuração PAPER explicitamente.
- O novo teste cobre, em ambiente temporário, relatório de startup PAPER, integridade de recovery, gravação de uma única observação sintética em SQLite, fecho/reabertura da base e confirmação de que o registo/evento continuam únicos. É um teste de componentes; **não** simula ainda o processo EXE real, o heartbeat do servidor, autenticação HTTP, o serviço collector nem preservação durante uninstall/reinstall.
- Não declarar o teste aprovado até o workflow Python executar no SHA exato `70f088b2945e55c7d3e82e8e3a3ec83058969bc1`. A consulta imediata após o commit ainda não devolveu runs/statuses associados a esse SHA.
- Estado confirmado no último commit com workflows consultáveis (`dc5e42b88f53c2464b86c8c1a7662ec0a89baac8`): Python tests, PAPER smoke, Windows EXE/installer, Android APK e protótipo VM passaram; Android Emulator UI Smoke falhou porque o Maestro não encontrou o texto `USAR ESCRITÓRIO VIRTUAL`. O log mostra que o emulador arrancou, instalou e lançou a aplicação; a falha ocorreu no seletor do ecrã, portanto a hipótese de falha ADB isolada não explica o log observado.
- O status combinado de `dc5e42b...` mantém `security/snyk (andrevazao)=error`; Vercel está `success`. A causa Snyk não foi identificada e não há evidência para a classificar como falso positivo ou vulnerabilidade concreta.
- PR #522 continua aberta e não deve ser merged. Manter apenas esta branch ativa.
- Próximos passos: obter CI para o teste novo no SHA exato; corrigir/explicar Snyk a partir de evidência; depois expandir o lifecycle para testar serviço real em PAPER e heartbeat/stop/restart de forma isolada, sem tocar no vault do proprietário. O teste local no PC continua pendente. Não executar uninstall/reinstall no PC sem backup verificado do vault e autorização explícita.


## Atualização de execução — 2026-11-03, correção do gate de persistência

- A execução Python no merge-ref da PR revelou uma falha real no novo teste: o primeiro arranque de `RecoveryManager` sem snapshot primário nem backup é corretamente classificado como integridade ainda não estabelecida; o teste exigia `READY` antes de criar um baseline. Não alterei a política fail-closed do produto para mascarar isso.
- Corrigi `tests/test_headless_lifecycle_persistence.py` no commit `27fd6183a934fd05a75858b4c23e6ff17db5f1cc`: cria explicitamente um snapshot vazio inicial através de `save_positions({}, runtime_status="OFF")`, reutiliza o mesmo RecoveryManager no segundo ciclo e só depois exige que a integridade esteja válida. A correção está submetida, mas aguarda nova execução de CI; ainda não é PASS.
- Resultado do SHA anterior `03cd18a...`: PAPER smoke SUCCESS; Windows EXE build/installer SUCCESS (incluiu arranque do EXE e resposta HTTP 200 em loopback, ambiente descartável); Android APK SUCCESS; Diorama VM SUCCESS; Obscura cloud smoke SUCCESS; Python suite FAILURE apenas no novo teste (1287 passed, 96 subtests passed, 1 failed); Android Emulator UI Smoke FAILURE.
- O log Android confirma falha no arranque do ADB daemon na porta 5037 e depois falha do toque no botão `USAR ESCRITÓRIO VIRTUAL`. Não é uma falha demonstrada do backend; manter fora do gate do cérebro, mas a PR continua sem aprovação geral.
- Artefacto Windows do run `41538641569`, para SHA PR base `03cd18a...`: ZIP `vazaosovereigntrader-windows`, SHA-256 `67886c49213160780413e41f6c8ac81563a0764245689be69dfe7e91d5844d22`, artifact ID `13185860466`. **Não é artefacto do novo SHA 27fd618...** e não deve ser usado como pacote exato para validação local.
- O status Snyk para `03cd18a...` era `error`; para o novo SHA `27fd618...` passou a `pending` na consulta inicial. A causa original permanece desconhecida; não declarar o gate de segurança resolvido até receber um resultado explicável.
- Não fazer merge, não pedir ainda validação no PC. Continuar a aguardar CI do SHA `27fd618...`, identificar o status Snyk e manter a validação local bloqueada até haver artefacto Windows produzido a partir do SHA exato e gates backend verdes.


---

## Atualização operacional — 2026-11-04

**PR única:** #522  
**Branch:** `fix/android-office-layout-2026-10-30`  
**HEAD de referência desta atualização:** `a9d6b4cdca22d5d1e105a274daae3cb71648dc2c`  
**Estado:** OPEN, não merged. Não iniciar outra PR/branch.

### CI verificado no commit anterior `235aa2f30af3ea37937be8bfb77a5a1d6a677e6c`

- Python tests: PASS.
- Trading engine PAPER smoke: PASS.
- Windows EXE build + installer build + silent install/start/health/uninstall in disposable CI environment: PASS.
- Android APK build: PASS.
- Obscura smoke: PASS.
- Diorama isolated VM prototype: PASS.
- Android Emulator UI Smoke: FAIL. ADB inicialmente reportou `device offline`, recuperou e concluiu o boot; o script Maestro terminou com exit code 1. Isto não é prova de falha do backend Windows.
- Snyk combined status: ERROR no SHA anterior; voltou a PENDING no SHA mais recente. Não declarar segurança aprovada até obter conclusão e detalhe do fornecedor.
- Vercel é apenas preview e não é gate funcional do cérebro.

Artefactos Windows daquele commit:
- Installer run 41597845617, artifact ID 13213940328, SHA-256 ZIP `02f5d4f4bc6c765a7f62749e420a107c45435344751e7dd6501e1ece06d7ab43`.
- EXE package artifact ID 13212459999, SHA-256 ZIP `98ccc0895b8470fcd9fb34222b2ffcce76238877cd3724acb868454861ce963e`.
- **Não usar estes artefactos para validação da versão posterior a `235aa2f`.** Esperar por artefactos Windows do HEAD final exato.

### Correção de persistência em curso

Foi identificado que o caminho de vault anterior `%LOCALAPPDATA%\\VazaoSovereignTrader\\vault` ficava dentro da pasta-base de instalação Inno Setup. A configuração nova separa o vault em:

`%LOCALAPPDATA%\\VazaoSovereignTraderData\\vault`

A localização antiga continua a ser descoberta e preservada em place se existir e a nova ainda não existir. O runtime não move nem apaga automaticamente a base antiga. Nessa situação a auditoria assinala `legacy_inside_install_root`; uninstall/migração física ficam BLOCKED até backup verificado e plano explícito. O override `VST_VAULT_PATH` continua disponível.

Ficheiros alterados nesta correção:
- `PC_ENGINE/core/data_vault.py`: novo diretório de dados separado e função de descoberta legacy.
- `PC_ENGINE/core/engine.py`: preserva vault legacy existente sem cópia/movimentação automática.
- `tests/test_data_vault.py`: testa caminho separado e descoberta legacy.
- `scripts/vst_local_backend_audit.ps1`: inspeciona vault novo e legacy; não declara PASS para legacy dentro da instalação.
- `prompts/PROMPT_MASTER_LOCAL_WINDOWS_BACKEND_E2E.md`: atualiza caminho e bloqueia uninstall se legacy for encontrado.

### Critério para disponibilizar teste local

O primeiro teste no PC será não destrutivo e PAPER/read-only. Exigir:
1. Python tests e PAPER smoke verdes no HEAD exato.
2. Windows installer e EXE artefactos construídos no mesmo HEAD exato, com SHA-256 registado.
3. PowerShell audit script validado em Windows CI.
4. Snyk resolvido ou erro tecnicamente explicado e revisto; não esconder falha de segurança.
5. Prompt Master atualizado e relatório local sanitizado.
6. Nunca testar uninstall/reinstall com dados pessoais sem backup separado, verificado e aprovação explícita.

O teste local pode começar sem aceitar o escritório Android como concluído: a validação do cérebro Windows é independente. A falha do Android fica registada e não deve bloquear o teste backend se os gates Windows/Python/PAPER estiverem verdes. Não alegar validação física antes do relatório do PC.

### Próximas tarefas imediatas
- Aguardar CI do HEAD após a separação do vault.
- Rever os logs do Windows installer e confirmar que o vault novo fica fora de `{app}`; verificar preservação do legacy sem apagar dados.
- Inspecionar o detalhe Snyk, sem assumir falso positivo.
- Se os gates Windows/Python/PAPER passarem, entregar o artefacto e Prompt Master para validação não destrutiva no PC.
- Depois do relatório local, corrigir problemas observados antes de qualquer promoção ou execução REAL.
