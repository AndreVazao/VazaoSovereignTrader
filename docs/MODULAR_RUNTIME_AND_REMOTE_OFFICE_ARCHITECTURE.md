# VST — runtime modular, migração de nós e escritório remoto

**Estado:** decisão arquitetural para implementação incremental; não significa que todos os serviços já estejam implementados.
**Âmbito:** exclusivamente VazaoSovereignTrader.

## Objetivo operacional imediato

O primeiro ambiente continua a ser o PC antigo existente. Não exigir compra de hardware, GPU dedicada, Linux imediato ou servidor gráfico separado. O cérebro deve ser eficiente, headless quando possível, seguro por defeito e fácil de migrar para outra máquina. O cockpit atual deve permanecer leve para Android e PCs modestos.

## Princípios inegociáveis

1. **Brain-first:** priorizar correção, observabilidade, recuperação, memória, coordenação, controlo de risco e execução PAPER. A visualização não pode atrasar nem parar o cérebro.
2. **Separação por contratos:** core, departamentos, memória, browser/research, API de controlo, cockpit e renderização são componentes separados comunicando por interfaces versionadas.
3. **Um PC primeiro, multi-nó depois:** todos os componentes podem inicialmente correr no mesmo PC, sem introduzir chamadas de rede entre módulos locais desnecessariamente. A distribuição por máquinas usa os mesmos contratos através de adaptadores de transporte.
4. **Migração sem reconstrução:** configuração declarativa por perfil de nó, estado persistente com versões/migrações, instalação idempotente e exportação/importação documentada. Segredos não são copiados automaticamente nem incluídos em backups/artefactos.
5. **Windows e Linux:** manter compatibilidade. Linux Server LTS mínimo é a preferência para um futuro nó headless dedicado, mas não há migração obrigatória do PC atual nem alegações de velocidade sem benchmark.
6. **Degradação graciosa:** falha do cockpit, renderer, browser ou nó remoto não deve derrubar o core. Componentes indisponíveis ficam explicitamente degradados/offline; não fingir saúde.
7. **Recursos limitados:** diagnosticar CPU, RAM, arquitetura e disco; limitar concorrência; manter browser persistente, 3D e tarefas pesadas opcionais. A deteção de capacidades recomenda perfis, mas nunca concede permissões.
8. **Segurança:** PAPER/read-only por defeito; sem credenciais reais em CI, sem portas públicas automáticas, sem contornar MFA/CAPTCHA/anti-bot e sem atribuir autoridade a uma máquina só por hostname/fingerprint.

## Perfis de nó previstos

- `brain-server`: coordenação, filas, políticas, memória e serviços centrais headless.
- `department-worker`: um ou vários departamentos autorizados.
- `research-worker`: recolha/leitura e tarefas de investigação, sem autoridade de trading por defeito.
- `memory-node`: persistência/índice de aprendizagem, se a carga futura justificar separação.
- `desktop-cockpit`: interface local leve de controlo/diagnóstico.
- `office-visualizer`: cliente ou serviço de apresentação do escritório; sempre opcional.
- `browser-worker`: adaptador de navegação isolado, com Obscura experimental e Chromium como fallback validado.

Os perfis são objetivos de arquitetura, não instaladores já concluídos. No PC antigo podem coexistir num único processo/host quando for seguro e compatível.

## Fronteiras e contratos

- **Core API / eventos:** expor estado estruturado versionado: tarefas, estados de serviço, saúde, resultados, alertas e permissões. Autenticação, autorização por função, timeouts, limites e auditoria são obrigatórios antes de acesso remoto.
- **Persistência:** armazenamento local autoritativo no nó configurado; migrações versionadas; backups restauráveis; não tratar o renderer ou o cockpit como fonte de verdade.
- **Agentes/departamentos:** tarefas com IDs, idempotência, cancelamento, timeout e estado persistido. Workers de investigação não herdam permissões de risco/execução.
- **Browser adapter:** interface comum de navegação com timeouts, limites, captura sanitizada de erros, cancelamento e classificação de compatibilidade. Cada motor tem health check e circuit breaker.
- **Cockpit:** cliente fino, com modos selecionáveis e fallback automático. Pode funcionar em chat simples sem carregar/renderizar o edifício. Não contém lógica crítica de trading.
- **Renderer do escritório:** recebe apenas estado autorizado e transforma-o em imagem/interação. Não decide se uma tarefa foi realmente executada. Deve carregar recursos gráficos de forma tardia/opcional e nunca ser dependência do core.
- **Estado real vs visual:** animações decorativas podem existir em modo offline, mas tarefas, progresso e atividade de agentes só são apresentados como reais quando confirmados pelo backend. O modo offline deve estar identificado de forma explícita.

## Modos visuais e pré-avaliação do equipamento

A referência visual inicial é o protótipo de escritório isométrico pixelado: visão geral do edifício, seleção de uma sala e entrada nessa sala com zoom/perspetiva mais próxima. Não exigir que todas as salas e etiquetas sejam legíveis simultaneamente num ecrã de telemóvel.

Modos previstos, com disponibilidade condicionada às capacidades reais do dispositivo:
- `chat`: interface textual leve, sem motor gráfico do escritório;
- `pixel`: escritório isométrico de baixa complexidade, com salas/agentes e zoom por sala;
- `enhanced`: materiais, animações e resolução superiores, se o dispositivo suportar;
- `3d`: experiência 3D mais avançada, opcional e futura;
- `auto`: selecionar o modo mais capaz dentro dos limites medidos, permitindo sempre reduzir manualmente a qualidade.

O conjunto de modos é um objetivo de produto; nem todos estão implementados nesta versão. O modo `chat` deve permanecer disponível em todos os equipamentos compatíveis com o runtime base.

### Contrato de capability check do instalador

O instalador deve fazer uma pré-avaliação **antes de instalar componentes opcionais** e gerar um relatório legível e versionado. Avaliar, conforme o sistema operativo permita:
1. sistema operativo, arquitetura e versão mínima suportada;
2. CPU, RAM disponível/total e espaço em disco;
3. disponibilidade de aceleração gráfica e APIs necessárias ao renderer escolhido (por exemplo, WebGL/WebGL2 verificado no runtime real do front-end, não presumido apenas pelo nome da placa);
4. resolução/orientação do ecrã e capacidades de entrada relevantes;
5. dependências base versus dependências específicas de cada modo.

Regras obrigatórias:
- instalar primeiro apenas o runtime base/headless e componentes selecionados necessários;
- não descarregar nem instalar dependências 3D pesadas se o utilizador não escolher esse modo ou se a pré-avaliação indicar incompatibilidade;
- manter chat e controlo do core disponíveis se o renderer falhar, não iniciar ou perder aceleração gráfica;
- se o teste for inconclusivo, usar o perfil seguro mais leve e explicar o motivo; não inferir suporte gráfico a partir de CPU/RAM apenas;
- permitir executar novamente o diagnóstico e alterar o modo mais tarde, sem reinstalação integral sempre que a arquitetura permitir;
- capability check é read-only, sem pedidos de rede, alterações privilegiadas ou criação de serviços durante a fase de diagnóstico;
- hardware/capacidades apenas recomendam compatibilidade e qualidade visual: nunca concedem permissões de trading, acesso remoto ou autoridade de nó.

A deteção gráfica deve ser implementada por adaptadores específicos de plataforma e validada em CI/VM e em dispositivos reais. O atual `PC_ENGINE/tools/doctor.py` já verifica plataforma, arquitetura, CPU/RAM, configuração, dependências Python e disco de forma read-only; **ainda não é um detector completo de GPU/WebGL nem um instalador adaptativo**. Não anunciar essas capacidades como implementadas antes dos testes correspondentes.

### Estado do instalador Windows existente

A auditoria de `installer/VazaoSovereignTrader.iss` mostra que o instalador atual empacota `build/ms-playwright` e agenda o motor e o coletor de mercado no início de sessão. O pacote Playwright pertence ao worker de browser/pesquisa do VST; não deve ser confundido com dependências de renderização 3D do escritório, nem removido sem mapear os consumidores reais. O instalador atual **ainda não** oferece seleção de modos visuais nem usa `component_plan.py`. A integração deverá ser feita quando os componentes gráficos opcionais e as suas dependências estiverem definidos e cobertos por testes de instalação/desinstalação. Não alterar o arranque dos serviços de trading como efeito secundário de uma escolha visual.

## Escritório remoto: fases, não requisito inicial

### Fase A — agora
Cockpit Android/desktop leve e apresentação local de baixa complexidade. Corrigir primeiro o APK e a responsividade. Sem serviço gráfico dedicado.

### Fase B — cliente web local/remoto
Separar os componentes visuais do backend através de uma API autenticada e eventos de estado. O browser do utilizador desenha o escritório; a transmissão é apenas dos dados necessários. Esta opção evita codificar vídeo e normalmente consome menos largura de banda.

### Fase C — renderização remota, se justificada
Se um motor 3D futuro exigir GPU ou recursos acima do dispositivo, uma máquina opcional `office-visualizer` poderá renderizar e transmitir vídeo (por exemplo, via WebRTC) enquanto recebe comandos de interação. Chat, alertas e estado continuam por canais de dados independentes. Avaliar latência, largura de banda, CPU/GPU e recuperação antes de adotar.

**Não tornar streaming obrigatório.** Se o serviço gráfico cair ou a rede estiver indisponível, o cockpit simples deve continuar utilizável e o core deve continuar a trabalhar. A imagem remota não substitui autenticação, autorização ou logs de estado.

## Obscura e Chromium: estratégia de browser

- O motor atual/Chromium continua a ser fallback conhecido; Obscura só pode ser preferida depois de testes funcionais e comparação repetível.
- Não usar apenas o tempo de um comando isolado para concluir que Obscura é “mais rápida”. Comparar o mesmo fixture, mesma máquina cloud, mesmo conjunto de repetições e mesma tarefa, reportando mediana, dispersão e taxa de sucesso.
- Health check por motor, timeout curto, circuit breaker e fallback imediato quando o motor primário falha ou excede o orçamento. A falha de ambos termina a tarefa como falha explícita/retryable; não bloqueia o departamento inteiro.
- Seleção inicial baseada em compatibilidade e resultados medidos por classe de tarefa. Não mudar de motor continuamente por pequenas variações de latência.
- CI usa apenas páginas sintéticas locais, sem credenciais, cookies ou operações financeiras. Não usar stealth para contornar proteções de exchanges.
- O fetcher oficial existente (`PC_ENGINE/opportunity/source_ingestion.py`) tem allowlist exata, limites de resposta e transporte HTTPS com IP validado/pinado. Não substituir esse controlo por uma chamada de browser que volte a resolver DNS sem pinning: a integração Obscura para fontes públicas exige uma fronteira de rede equivalente ou egress controlado, validação de host/caminho/redirect e testes SSRF antes de ativar. O benchmark CLI isolado não valida esses controlos.
- Até existir benchmark válido, Obscura fica experimental e não é o motor primário de pesquisas críticas.

## Plano incremental de implementação

1. Auditar o core existente e os contratos reais antes de criar abstrações duplicadas.
2. Consolidar testes headless de core e garantir que fechar a UI não interrompe o runtime.
3. **Incremento implementado, validação CI pendente:** `PC_ENGINE/tools/doctor.py` fornece diagnóstico JSON read-only e `--probe-renderer` tenta uma prova local de WebGL/WebGL2 sem instalar browser ou usar URLs externas; `tests/test_runtime_doctor.py` cobre recomendações conservadoras e fallback em caso de renderer desconhecido.
4. **Planeador de componentes implementado, sem executar instalação:** `PC_ENGINE/tools/component_plan.py` transforma as recomendações num plano fail-closed. `chat` inclui apenas brain headless + cockpit chat; `pixel` acrescenta apenas o renderer pixelado; `enhanced`/`3d` só são incluídos quando o diagnóstico recomenda explicitamente esses modos. Se o relatório estiver ausente/incompatível ou o modo não for suportado, não seleciona componentes gráficos avançados. Testes em `tests/test_component_plan.py`. O planeador não instala pacotes, não inicia serviços e não faz rede.
5. Validar o probe/planeador em CI, Windows/Linux e equipamento real; integrar a seleção no instalador existente apenas depois de confirmar os testes e rever os manifests/dependências atuais.
6. Implementar perfis declarativos, limites conservadores e adaptadores de serviço Linux/Windows sem alterações privilegiadas implícitas.
7. Definir interface do browser, timeouts, health check e fallback; só integrar Obscura após benchmark e validar a fronteira de rede/pinning.
8. Definir API/eventos do cockpit com autenticação/autorização e estado de saúde real.
9. Validar exportação/restauro/migração em CI/VM descartável; documentar o que exige nova autenticação manual.
10. Só então avaliar cliente web e renderização remota.

## Métricas obrigatórias

CPU, RAM, tempo de arranque, taxa de sucesso, latência p50/p95, timeouts, reinícios, consumo de rede e recuperação. Separar medições cloud de medições no PC físico. Nenhum ganho é declarado sem dados comparáveis.

## Segurança e estado de trading

PAPER/read-only continua padrão. Nenhuma ordem real ou movimentação de fundos em CI. Um resultado de browser não pode acionar trading diretamente: resultados devem passar por validação, políticas e controlos de risco existentes. Toda a integração futura deve preservar proveniência e auditoria.

## Estado atual

- Arquitetura alvo documentada.
- PC antigo continua a primeira plataforma; compra de máquinas não é requisito.
- Linux é preferência futura para servidor headless compatível, não condição para avançar agora.
- Renderer dedicado/streaming: FUTURO, não implementado.
- Modos chat/pixel/enhanced/3D e capability check adaptativo: requisitos arquiteturais documentados; ainda não são todos implementados.
- Browser Obscura vs Chromium: benchmark cloud sintético concluído; os resultados não comprovam superioridade em páginas reais nem justificam seleção de produção.
- Migração multi-nó/instalador adaptativo: arquitetura definida; implementação por etapas pendente.
- `vst doctor --json`: protótipo read-only criado; testes Python passaram no HEAD `93370f7dfc35d6ae2f9ba7085fa23032c173d09f`. A deteção de GPU/WebGL ainda falta.
