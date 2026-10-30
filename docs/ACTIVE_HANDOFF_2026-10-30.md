# ACTIVE HANDOFF — VazaoSovereignTrader — 2026-10-30

## Ordem de prioridade
1. Tornar o cérebro/runtime robusto, headless e independente do cockpit/escritório virtual.
2. Fazer o APK abrir e navegar de forma fiável; manter testes de emulador e inspecionar artefactos atuais.
3. Suportar Windows e Linux, com preferência por Linux Server LTS mínimo em servidores/department workers dedicados quando compatível.
4. Preparar instalação adaptativa por capacidades e função autorizada da máquina.
5. Manter documentação e memória sincronizadas, uma PR/branch de implementação ativa de cada vez.

## Estado Git confirmado neste checkpoint
- PR #520, correções de safe-area e navegação Android: merged; os testes de emulador anteriores passaram. Isso não prova instalação/arranque no telefone físico nem ligação ao runtime real.
- PR #521: aberta em `docs/cross-platform-runtime-policy-2026-10-30`; HEAD observado `bb2e359b1cd3d35bcdd6396570c71deb931c38fe`. Contém `docs/CROSS_PLATFORM_RUNTIME_POLICY.md`, `docs/ADAPTIVE_INSTALLATION_AND_NODE_ROLES.md`, `docs/OBSCURA_EVALUATION_CLAUDE_CODE.md` e `.github/workflows/obscura-cloud-smoke.yml`. Os checks do commit final ainda precisam de confirmação; não declarar merge.
- PR #519 (Obscura) será fechada depois de transferidos para #521 o plano e o smoke workflow. O benchmark comparativo não foi transferido porque o contrato CDP/servidor não está confirmado; não afirmar vantagem de desempenho.
- Só a PR #521 deve ficar aberta no produto neste checkpoint. PRs fechadas podem deixar branches remotas; não afirmar que branches foram apagadas sem confirmação explícita do GitHub.
- Main do produto era `1672fdd8a6ce1c0dc4b4f66ead3c31fdf1ea6d88` na base da PR #521; confirmar SHA atual antes de integrar.

## Decisões de arquitetura
- Windows e Linux são plataformas suportadas. Linux Server LTS mínimo é a preferência para cérebro headless e nós dedicados, não uma exigência universal.
- A instalação deve começar com diagnóstico sem alterações; detetar OS/arquitetura/CPU/RAM/disco e propor componentes/perfil. Não conceder permissões a partir do hostname/fingerprint; requer enrollment/autorização explícitos.
- Perfis pretendidos: brain-server, department-worker, research-worker, memory-node, desktop-cockpit e office-visualizer. Cada nó executa apenas funções autorizadas e adequadas aos seus recursos.
- Core, departamentos, API/cockpit e visualização são camadas separadas. Fechar/crashar UI ou renderização 3D não pode parar o cérebro.
- Em máquinas limitadas, reduzir concorrência e desativar por defeito 3D, browsers persistentes e modelos locais pesados.
- PAPER/read-only por defeito; sem ordens reais, transferências, chaves reais em CI, portas públicas automáticas ou alterações de segurança do OS.
- Obscura permanece opcional. Só integrar no caminho de pesquisa se testes funcionais e benchmark repetível mostrarem compatibilidade e vantagem real face ao browser existente.

## APK / escritório virtual
- PR #520 melhorou safe areas e navegação com labels ASCII e foi integrada. Testes de emulador passaram, com demonstração offline do escritório.
- O escritório continua a ser uma camada de visualização/demo offline; não afirmar que já está ligado ao runtime real.
- Teste físico Android/ADB e pairing PC↔telefone/Tailscale permanecem NOT RUN/BLOCKED até o utilizador ter PC/dispositivo disponível.
- Próxima tarefa: revalidar workflows atuais no main, obter APK de run atual, inspecionar screenshots/logcat e confirmar arranque/navegação no emulador. Depois preparar instruções de instalação simples para o telefone. Não reutilizar screenshots antigas como prova atual.

## Próximos passos concretos
1. Verificar os checks exatos da PR #521 e o workflow Obscura cloud smoke; resolver falhas antes de merge.
2. Integrar a documentação consolidada numa única PR, sem apagar evidência histórica útil. Arquivar/substituir handoffs contraditórios por um apontador para este handoff atual.
3. Atualizar AndreOS memory com este estado e os blockers.
4. Priorizar APK: build atual, emulador, artefactos, instruções de instalação e teste físico quando possível.
5. Auditar runtime/core no código atual e correr testes CI disponíveis; separar claramente PASS, FAIL, BLOCKED e NOT RUN.
6. Só depois começar implementação incremental de `vst doctor --json`, manifesto de componentes e adaptadores de serviço por OS.

## Regras de trabalho
- Uma PR/branch de implementação ativa por vez; branches curtas, mudanças pequenas.
- Não fazer merge com checks pendentes/falhados ou com artefactos não inspecionados quando relevantes.
- Não apagar documentos técnicos sem verificar se contêm evidência/decisões únicas; substituir documentos contraditórios por um handoff autoritativo e marcar o resto como histórico.
- Não declarar testes de hardware físico, benchmark ou integração que não tenham sido executados.
- Nenhuma alteração ao DGM-MAT; projeto separado.
