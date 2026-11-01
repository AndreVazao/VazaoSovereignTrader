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
