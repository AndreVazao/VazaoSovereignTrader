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

## Produto de distribuição: três aplicações separadas (decisão de arquitetura, 2026-10-31)

A distribuição final deve ter **três artefactos instaláveis**, sem os confundir num único processo:

1. **VST Backend** — pacote/instalador próprio para Windows e Linux. Instala o motor headless, os serviços comuns e os departamentos selecionados. Deve suportar instalação de todos os departamentos numa máquina ou distribuição de departamentos por vários PCs. O backend é soberano: não depende de qualquer UI, renderer, APK ou sessão gráfica para continuar a funcionar.
2. **VST Desktop** — frontend de desktop instalável separadamente para Windows e Linux. Inclui cockpit, conversação e escritório virtual opcional. Liga-se a um backend local ou remoto autorizado. Fechar, reiniciar ou atualizar o frontend não pode parar o backend.
3. **VST Android** — APK separado. Funciona como cliente móvel para conversação, estado, alertas e comandos autorizados; não aloja o cérebro nem substitui o backend.

“Três aplicações” não significa necessariamente três formatos binários iguais: Windows poderá produzir instaladores/executáveis Windows; Linux deverá ter um pacote/instalador nativo ou bundle executável equivalente; Android produz APK. O formato de empacotamento concreto será escolhido após avaliar o runtime e as dependências existentes, sem prometer um .exe nativo em Linux.

### Sistemas operativos e matriz de validação

- **Windows:** backend e desktop são alvos de distribuição; manter e validar o instalador Windows existente.
- **Linux:** backend e desktop são alvos explícitos de primeira classe. Criar adaptadores de serviço/arranque próprios do Linux; não reutilizar scripts Windows por suposição. Validar numa VM Linux em CI e, quando a máquina reconstruída chegar, numa instalação limpa de Linux.
- **Android:** APK independente; validar em emulador e depois no telefone físico.
- **Migração/fallback:** a instalação limpa Linux é a primeira experiência na nova máquina. Medir arranque, CPU, RAM, estabilidade e compatibilidade; só considerar Windows se houver evidência de incompatibilidade ou desempenho insuficiente.

### Rede, acesso remoto e autenticação

- **Tailscale** é a via preferida para ligar dispositivos autorizados fora da LAN; dentro de casa, preferir LAN quando adequada. A ligação de rede não substitui autenticação da aplicação, autorização por função, logs nem proteção de comandos.
- O utilizador faz manualmente os logins e aprova autenticações, dispositivos, permissões e credenciais quando forem pedidos. Nunca embutir credenciais, tokens Tailscale ou chaves privadas nos instaladores, no repositório, no APK ou em logs.
- O setup deve detetar e explicar que falta autenticação, abrir/instruir o passo de login e aguardar confirmação; não tentar contornar MFA, prompts ou aprovações humanas.
- O VST não deve depender de Vercel para o funcionamento local do cérebro. Qualquer registo/descoberta externa será opcional, com fallback LAN/Tailscale e sem bloquear o runtime local quando o serviço externo estiver indisponível.
- Não abrir portas públicas nem expor uma API de controlo sem autenticação forte, autorização, transporte protegido, limites de pedidos e auditoria. Os frontends são clientes não autoritativos; o backend valida cada comando.

### Fases de entrega

1. Preservar a segurança e a execução headless do cérebro; auditar os caminhos de arranque, paragem, recuperação e modo PAPER.
2. Formalizar um contrato de API autenticada e de estado entre backend, desktop e Android.
3. Separar os entrypoints e manifests de empacotamento do backend e desktop, sem duplicar lógica crítica.
4. Implementar e testar instalação/remoção em Windows e Linux, serviços de arranque opcionais, atualização, logs, recuperação e migração de departamentos.
5. Manter o APK como cliente fino e validar orientação, layout e reconexão.
6. Fazer teste de instalação limpa Linux na máquina nova e recolher métricas antes de decidir se é necessário Windows.

**Estado honesto:** esta secção regista a arquitetura-alvo acordada. Não significa que os três instaladores finais, o backend Linux, a ligação Tailscale integrada ou a instalação distribuída já estejam implementados. A PR atual continua a ser validada; cada capacidade só será marcada como concluída depois de existir código e teste reproduzível.
## Backend onboarding, Obscura, credenciais locais e recuperação (decisão de produto, 2026-10-31)

### Consola do backend antes do escritório

O backend deve disponibilizar uma consola administrativa local, utilizável sem desktop cockpit ou Android. A consola serve para setup inicial, diagnóstico, estado dos serviços, configuração de departamentos, gestão de autenticação e pedidos de intervenção humana. Não deve oferecer um canal de execução de ordens que contorne o ExecutionGate, RealModeGuard ou as políticas de risco existentes. A consola pode ser CLI e/ou interface local mínima; a escolha concreta depende da auditoria dos entrypoints existentes.

### Dependências e navegação

- O instalador do backend deve declarar e verificar as dependências necessárias, com versões fixadas e testes de integridade; deve distinguir dependências obrigatórias do core de motores opcionais de browser.
- Obscura deve ser instalada/configurada como motor candidato de navegação se a licença, distribuição, dependências e testes de segurança o permitirem. Chromium permanece fallback até benchmark repetível demonstrar adequação por tarefa.
- O browser worker deve ter health check, timeouts, limites de recursos, logs sem segredos e fallback. Navegação não pode converter diretamente conteúdo de páginas em comandos de trading nem contornar autenticação, MFA, CAPTCHA ou proteções das exchanges.
- Para integração de exchange, preferir API oficial quando disponível e autorizada. Browser/sessões persistentes só devem ser usados de acordo com os termos da plataforma. A configuração de credenciais de trading deve privilegiar chaves API com permissões mínimas, sem permissão de levantamento quando desnecessária, e restrições de IP quando suportadas.

### Vault local e autenticação

- Credenciais, cookies/sessões, tokens e segredos são dados locais de cada instalação/organização; nunca entram na memória partilhada, logs, telemetria, artefactos CI ou repositório.
- O vault deve cifrar dados em repouso usando mecanismos de sistema operativo quando disponíveis (por exemplo, Windows DPAPI/Credential Manager ou Linux Secret Service/keyring) e permitir um segredo mestre alternativo bem protegido quando não existir integração de sistema adequada. Não guardar passwords em texto simples nem incluir chaves de desencriptação junto dos dados cifrados.
- O acesso ao vault deve exigir desbloqueio local e aplicar bloqueio automático/inatividade. Operações sensíveis devem ter logs de auditoria sem incluir o segredo. A autenticação da aplicação e a autorização por função continuam obrigatórias mesmo numa rede privada.
- A primeira autenticação é interativa: o utilizador introduz os dados no ecrã seguro e completa MFA, SMS, passkey ou aprovação externa. Depois disso, a aplicação pode reutilizar tokens ou sessões renováveis que a plataforma disponibilize legitimamente; não pode prometer login invisível permanente. Se uma sessão expirar ou a exchange exigir nova confirmação, cria um pedido de aprovação e pausa apenas a tarefa afetada.
- Não pedir nem guardar o e-mail/password principal de uma exchange se uma API key restrita ou OAuth oficial satisfizer o caso de uso. Nunca guardar PINs de uso único como credenciais permanentes.

### USB de recuperação

A pen de recuperação deve ser um export cifrado, não uma cópia em claro do vault. Deve incluir apenas a configuração selecionada, manifestos de versões, perfis de departamentos e segredos explicitamente escolhidos pelo utilizador; por defeito, não exportar sessões/cookies ativos. O export exige desbloqueio, uma frase-passe forte ou chave separada, e confirmação explícita. Deve permitir restaurar em máquina nova sem transportar uma chave de desencriptação dentro da própria pen; após restauro, pedir desbloqueio e autenticação adicional quando necessário. Oferecer também uma opção de recuperação sem segredos, que restaura configuração e exige login de novo.

### Fronteira de memória partilhada entre organizações

A memória de aprendizagem partilhada pode conter apenas conhecimento técnico permitido e com proveniência, por exemplo, padrões de comportamento de mercado, resultados agregados e lições de investigação aprovadas. Não pode conter saldos, volumes financeiros privados, posições, histórico identificável de ordens, credenciais, e-mails, cookies, tokens, dados pessoais ou configurações privadas. Aplicar allowlist explícita de campos, redacção, validação antes da publicação e testes negativos que tentem introduzir segredos. Por defeito, a partilha é opt-in por categoria e os dados privados permanecem locais.

### Critérios mínimos de aceitação

1. Instalar backend numa máquina limpa sem instalar o frontend; abrir a consola e obter diagnóstico útil.
2. Verificar dependências de navegação e demonstrar fallback quando Obscura falha, sem bloquear o core.
3. Introduzir credenciais de teste no vault e confirmar que ficam cifradas; logs e memória partilhada não contêm os valores.
4. Simular sessão expirada/MFA e confirmar pedido claro de intervenção humana, sem loops de login nem falsa indicação de sucesso.
5. Exportar/importar backup cifrado num ambiente descartável; um backup com frase-passe errada deve falhar fechado.
6. Testar que os filtros de memória partilhada rejeitam credenciais, saldos, posições e dados privados.
7. Repetir em Windows e Linux; não declarar compatibilidade de vault até testar a integração de segredos do sistema operativo e o comportamento de recuperação.

**Estado honesto:** consola de backend, vault, integração completa de Obscura, login de exchanges e USB de recuperação são requisitos definidos nesta secção, não funcionalidades já concluídas. Devem ser implementados em incrementos pequenos e testados antes de serem usados com contas reais.

## Recuperação integral da aprendizagem — USB e nó de memória partilhada

A recuperação deve incluir não apenas configuração e perfis de departamentos, mas também o estado de aprendizagem que o Sovereign Trader acumulou. Esta é uma capacidade obrigatória de portabilidade, ainda por implementar e validar.

### Conteúdo a incluir no backup de aprendizagem
- Ledger de evidência e respetivos metadados de proveniência, timestamps, versão de schema e auditoria.
- Observações/resultados de aprendizagem PAPER, avaliações históricas e snapshots derivados que possam ser reconstruídos ou exportados.
- Índices, checkpoints e estado necessário para retomar o processo de aprendizagem, acompanhados de versão do formato e versão do software que os produziu.
- Manifesto de contagens, hashes, intervalo temporal, componentes incluídos/excluídos e validações de integridade.
- Configuração de sincronização e identidade do nó apenas se o utilizador a selecionar; segredos e credenciais continuam excluídos por defeito.

### USB cifrada: exportação e restauro
- Exportação explícita pelo operador para um arquivo cifrado com passphrase/chave separada; a chave não pode ser guardada no mesmo USB ao lado do arquivo.
- Oferecer dois perfis: **recuperação completa** (configuração + aprendizagem elegível + estado local selecionado) e **recuperação apenas de aprendizagem** (ledger, checkpoints, índices e metadados aprovados).
- Importação em nova instalação com validação de assinatura/hash, schema, versão, origem e contagens antes de alterar o estado local. Importar primeiro para staging; só promover após validação completa e confirmação humana.
- Restauro inválido, passphrase incorreta, ficheiro truncado, schema incompatível ou hash divergente deve falhar fechado, sem sobrescrever dados existentes. Criar snapshot do destino antes de promover a importação.
- Segredos, sessões de browser, cookies e credenciais de exchange ficam excluídos por defeito. A recuperação exige reautenticação onde necessário.
- A exportação nunca deve executar ordens, promover modo REAL nem mudar permissões de risco.

### Memória partilhada remota (Vercel, Render ou alternativa)
- O fornecedor de alojamento ainda não está decidido. O contrato deve ser independente do fornecedor e permitir exportar/recuperar a memória sem depender exclusivamente do serviço cloud.
- Tratar a memória partilhada como réplica de conhecimento técnico/mercado explicitamente elegível, não como backup único nem fonte autoritativa de estado privado da organização.
- Cada artefacto de aprendizagem deve incluir proveniência, versão, data, classe de conteúdo, hash e política de retenção; sincronização idempotente e reprocessável.
- Aplicar allowlist positiva de tipos de aprendizagem, redaction e testes negativos para credenciais, cookies, e-mail, dados pessoais, saldos, posições, volumes privados, histórico identificável de ordens e configuração privada.
- A aprendizagem local deve continuar se a cloud estiver indisponível; filas de sincronização persistem localmente e retomam quando a ligação regressar. Não bloquear o cérebro nem descartar aprendizagem local por falha de rede.
- Restauro da memória cloud e importação USB devem passar pelo mesmo validador de schema, proveniência, integridade e privacidade. Deduplicar por identificador/hash para evitar duplicações.
- Não afirmar que “tudo o que aprende” é partilhável: apenas aprendizagem aprovada pelo filtro pode sair da organização. O conjunto completo elegível para recuperação permanece exportável localmente, sob controlo do proprietário.

### Critérios de aceitação
1. Gerar aprendizagem de teste PAPER e exportar pacote completo e pacote só de aprendizagem para armazenamento local/USB.
2. Restaurar em diretório/instalação limpa e verificar igualdade de contagens, hashes, versões e relatórios de auditoria.
3. Passphrase errada, arquivo corrompido, schema desconhecido ou alteração de hash falham sem tocar no estado existente.
4. Testes negativos demonstram que credenciais, cookies, dados pessoais e dados financeiros privados não entram na memória partilhada.
5. Cloud offline não interrompe aprendizagem; após recuperação de rede, a sincronização retoma sem duplicados.
6. Nenhum caminho de importação/exportação pode autorizar trading real ou submeter ordens.


## Enfermaria, quarentena e oficina de reparação (decisão + primeiro núcleo de política)

A enfermaria é uma representação visual de estados reais de saúde do backend, não uma animação que infere falhas por conta própria. O escritório pode mostrar agentes em macas, enfermeiros, técnicos e uma oficina pixelada, mas só quando receber um evento de saúde autenticado e atual. Se não houver ligação ao backend, a interface mostra estado desconhecido/offline; não inventa agentes doentes nem apresenta uma falsa recuperação.

### Estados e comportamento pretendido

- **Healthy:** verificações recentes passaram; o componente pode receber trabalho de acordo com as permissões normais.
- **Degraded:** alertas, erros repetidos ou desempenho fora dos limites. Bloquear novas tarefas ou ações de risco conforme severidade, sem isolar automaticamente quando a política não o exigir.
- **Quarantined:** isolamento explícito/manual ou sinal crítico de integridade/segurança. Bloquear novas tarefas e ações com risco, cortar a comunicação/partilha que possa propagar estado contaminado e preservar logs/evidência para investigação.
- **Recovering:** reparação aplicada e testes iniciais aprovados, mas ainda sem autoridade para regressar ao serviço normal. Manter isolado até aprovação explícita do operador ou política de controlo autorizada.
- **Unknown/offline:** não foi possível confirmar saúde; nunca mostrar como saudável só porque deixou de haver sinais.

### Enfermaria e oficina

1. O diagnóstico cria um incidente com ID, componente/agente/departamento, severidade, timestamps, sinais observados e proveniência.
2. A política de saúde decide a recomendação de degradação/quarentena. O plano de isolamento é aplicado pelo control plane do backend, não pelo renderer.
3. A enfermaria apresenta a lista de incidentes e o estado de cada agente. A oficina corre diagnósticos e reparações permitidas num ambiente isolado, com logs sanitizados.
4. A validação usa testes de saúde, regressão e integridade. A recuperação não elimina o incidente nem a proveniência.
5. A libertação da quarentena é uma transição explícita e auditada. Passar nos testes apenas permite entrar em recuperação; não autoriza por si só trading REAL.
6. Se um departamento estiver isolado, os seus dados/artefactos não podem ser publicados na memória partilhada até serem validados. O core e departamentos não afetados continuam a operar quando a política de dependências permitir.

### Primeiro núcleo de política

Foi acrescentado `PC_ENGINE/tools/health_isolation.py` com uma função pura de decisão e testes em `tests/test_health_isolation.py`. A política recomenda quarentena para sinais críticos ou decisão manual, mantém quarentena pegajosa até verificações de recuperação e bloqueia ações de risco nos estados degradado/quarentenado/em recuperação. O módulo **não executa isolamento real nem altera serviços/permissões**; isso requer integração com o control plane e persistência/auditoria, ainda pendentes.

### Critérios de aceitação antes de ligar à execução real

- Testes para erro crítico, quarentena manual, persistência da quarentena, recuperação incompleta, sinais de warning/error e componente saudável.
- Falha do serviço de saúde resulta em estado desconhecido/conservador, nunca em saúde presumida.
- A quarentena de um departamento impede submissão de tarefas/ações de risco através do backend, incluindo caminhos alternativos e reinícios.
- A UI não pode retirar quarentena nem conceder permissões; todas as transições ficam auditadas.
- Injeção de falha numa área não derruba o core nem contamina a memória partilhada.
- Exercícios de recuperação provam que a evidência fica preservada e que nenhuma reparação/importação promove o modo REAL.

**Estado honesto:** o contrato arquitetural e a primeira política pura estão no branch de trabalho; a integração com serviços, UI/animações, armazenamento de incidentes, quarentena efetiva e oficina executável ainda não estão concluídos. A validação CI desta alteração ainda é necessária.
