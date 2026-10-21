# Sovereign Trader — inventário do escritório virtual

**Estado:** proposta visual para revisão humana.  
**Data:** 2026-10-21  
**Autoridade:** o Runtime do Sovereign Trader continua a ser a única fonte de verdade. Os compartimentos abaixo não implicam que existam agentes autónomos operacionais para cada função.

## Objetivo

Representar o sistema como um edifício 3D explodido, com pisos e compartimentos legíveis, para o proprietário validar nomes, fronteiras e departamentos antes de aumentar a fidelidade visual. O escritório é uma camada de observação e controlo; nunca substitui nem bloqueia o motor.

## Núcleo de direção

1. **CEO / Cérebro Sovereign Trader** — receção principal das instruções em linguagem natural, coordenação e encaminhamento para departamentos. O avatar oficial do proprietário deve ser inserido a partir do asset já aprovado no repositório; não usar uma pessoa fictícia como se fosse o proprietário.
2. **Receção / Orquestração de pedidos** — opcional como área de entrada visual; pode encaminhar para o CEO ou para um departamento. Não é um segundo motor nem uma autoridade paralela.
3. **Sala de reuniões / Planeamento** — espaço visual para decisões, revisões e resumo de estado; só apresenta atividade confirmada pelo backend.

## Departamentos funcionais propostos

| Nome visual | Responsabilidade | Estado a mostrar quando ligado |
|---|---|---|
| **Market Radar** | Detetar eventos, movimentos e potenciais diferenças temporais nos feeds; emitir candidatos com evidência e qualidade de dados | Frescura, sequência, confiança e timestamp de origem/receção separados |
| **Comparação entre Exchanges** | Comparar instrumentos equivalentes entre venues, normalização de símbolos, preços, profundidade, taxas, slippage e inventário; validar se a diferença é executável | Comparação por venue, custos estimados, liquidez, inventário e motivos de rejeição |
| Integrações de Exchanges | Adaptadores, símbolos, limites de API, saúde REST/WebSocket e reconexão | Estado por exchange, erros e idade do último evento |
| Investigação | Recolher fontes, documentação e hipóteses verificáveis | Fonte, timestamp, confiança e conclusão |
| Análise | Avaliar sinais, consistência, contexto e evidência | Hipótese, evidência e estado da validação |
| **Resposta Rápida / Execução Controlada** | Receber apenas oportunidades validadas; avaliar urgência e preparar resposta PAPER. Qualquer execução futura fica atrás de todos os gates e autorização explícita | Candidato recebido, gates cumpridos/falhados, decisão e motivo; nunca contorna risco |
| Laboratório PAPER / Replay | Testes determinísticos, replay, simulação de taxas e slippage | Resultado de teste, amostra e limitações |
| Controlo de Risco | Guardas, limites, inventário e prontidão | Bloqueios e motivos explícitos; autoridade sempre no servidor |
| Memória Central de Aprendizagem | Conhecimento local partilhado entre departamentos | Proveniência, data, versão e estado de validação |
| Auditoria / Observabilidade | Eventos, comandos, decisões e métricas do Runtime | Eventos reais com timestamps de origem e receção separados |
| Recuperação / Saúde do sistema | Reconciliação, estado de conectores e recuperação após falhas | Estado confirmado, tentativas e próxima ação |
| Intervenção Humana / Aprovações | Autenticação, confirmação e pedidos que exigem o operador | Pedidos pendentes, expiração e decisão do utilizador |

## Laboratórios e infraestrutura

- **Laboratório de Estratégias**: separado visualmente do departamento de Resposta Rápida; só PAPER nesta fase.
- **Memória Central de Aprendizagem**: tem uma sala visual própria e é também um serviço transversal consumido por todos os departamentos; a sala é uma representação da memória, não um segundo armazenamento.
- **Infraestrutura / Cofre lógico**: representa segurança, armazenamento e estado de fundos. Não implica movimento real de fundos; nenhuma transferência é permitida pelo mockup.
- **Sala de Dispositivos**: estado do cockpit PC, app/ APK e ligação privada. A ligação remota planeada usa Tailscale após o encontro inicial; a interface não deve expor segredos.
- **Zona de Trabalho do Operador**: espaço opcional de revisão de relatórios e configuração visual.

## Fluxo principal

Operador → CEO/Receção → departamento selecionado → memória central e evidência partilhada → resposta ao operador. Cada departamento pode ter conversa própria; o CEO continua a ser o destino por omissão. A memória de aprendizagem é local e partilhada no Runtime. A futura partilha entre dispositivos deve transferir apenas conhecimento validado, nunca credenciais, saldos ou acesso pessoal.

## Regras de visualização e segurança

- Só mostrar pessoas, atividade, números, latência ou estado como reais se vierem de uma fonte verificável. Caso contrário, identificar como demonstração ou deixar “desconhecido”.
- O motor corre headless e continua a funcionar se o escritório fechar, bloquear ou perder rede.
- Nunca manter locks do motor durante renderização, serialização, pedidos HTTP ou confirmação da UI.
- Atualizações visuais limitadas e coalescidas; saturação pode reduzir detalhe/frequência ou desligar o escritório, sem mudar política de risco.
- Tokens só em memória de página/cabeçalhos; nunca em URL, logs ou armazenamento persistente do browser.
- Nenhuma ordem real, transferência ou ativação de modo REAL faz parte deste trabalho.

## Decisões aprovadas pelo proprietário — 2026-10-21

- CEO/Cérebro no piso superior.
- Market Radar e Comparação entre Exchanges são departamentos distintos.
- Investigação e Análise permanecem separados.
- Memória Central tem sala visual própria e serviço transversal partilhado.
- Existe departamento próprio de Resposta Rápida, subordinado a todos os gates de dados, custos, liquidez, inventário e risco. Nesta fase, trabalha em PAPER; nenhuma ordem real está autorizada.

## Limite de fidelidade

Este documento consolida o shell e as capacidades documentadas no código existente, mas é um inventário visual para validação, não uma afirmação de que cada departamento já está implementado como agente independente.


## Renderização adaptativa: uma planta, vários níveis de fidelidade

A planta e o inventário acima são o **modelo canónico**. Não se criam edifícios ou departamentos diferentes por dispositivo. Cada sala deve ter um ID estável e um estado semântico independente da forma gráfica; os renderizadores apresentam esse mesmo modelo como chat, 2D com palitos, pixel-art, 2.5D, 3D detalhado ou modo cinemático.

- **PC antigo/recursos limitados:** perfil económico por omissão, planta 2D, figuras simples, gráficos leves, sem sombras/partículas e animação mínima.
- **Telefone capaz:** pode usar 3D detalhado se os recursos e o desempenho observados o permitirem; caso contrário, desce para 2.5D/2D.
- **PC potente:** pode usar 3D detalhado ou cinemático, desde que permaneça dentro do orçamento de desempenho.
- **Modo chat-only:** alternativa permanente, não uma falha nem um modelo separado do sistema.

A deteção inicial deve ser conservadora, sem benchmark gráfico pesado. Quando não houver métricas de hardware fiáveis, começar leve; permitir escolha manual; observar frame time e pressão de memória e reduzir qualidade rapidamente se necessário. Assets de alta definição só são carregados quando usados e libertados ao baixar o perfil. Pausar animações em segundo plano e coalescer atualizações visuais. A falha do renderizador deve fazer fallback para 2D/chat sem interromper o Runtime.

A adaptação pode reduzir detalhe, frequência de animação e taxa de refrescamento visual, mas **nunca** altera a planta, a memória central, as permissões, os gates de risco ou o ciclo de trading. Confirmar CPU, RAM, fluidez e tráfego com medições reais em cada classe de dispositivo antes de afirmar que um perfil está validado.


## Hierarquia de agentes e chefias — decisão do proprietário (2026-10-21)

### Regra de comando

A hierarquia oficial é **Operador → CEO → Chefes de Departamento → Subchefes/Agentes especializados**.

- O **CEO é o ponto central de comando** e comunica operacionalmente com os chefes de departamento, não com cada subagente.
- Cada departamento tem exatamente um **chefe principal**, responsável por distribuir tarefas, acompanhar dependências, validar resultados e entregar ao CEO um relatório consolidado.
- Quando a carga ou complexidade o justificar, o chefe pode nomear um **subchefe/coordenador** para uma frente de trabalho; esse subchefe coordena os agentes dessa frente e reporta ao chefe principal.
- Os agentes especializados reportam ao seu subchefe, quando exista, ou diretamente ao chefe do departamento. Não enviam relatórios operacionais paralelos ao CEO.
- O utilizador pode abrir a conversa do CEO (destino por omissão) ou selecionar um departamento; nesse caso fala com o **chefe desse departamento**, e não com um subagente escolhido aleatoriamente.
- Departamentos podem trocar eventos estruturados e consultar a Memória Central, mas pedidos, atribuição de tarefas, conflitos de prioridade e conclusões sobem pela cadeia hierárquica. Não se criam cadeias paralelas nem se duplicam ordens.
- Alertas críticos de risco devem ser emitidos imediatamente pelo canal de segurança definido, mas continuam a identificar o chefe responsável, a evidência e o motivo. Nenhum chefe pode anular os gates de risco.
- Estes nomes são **indicativos de função/identidade lógica**; não afirmam que os agentes já estejam implementados ou ativos. O Runtime deverá registar ID, função, estado, supervisor, tarefa, timestamps e proveniência de cada relatório.

### Chefes oficiais e equipas

| Departamento | Chefe principal | Subagentes / frentes de trabalho | Relatório obrigatório ao CEO |
|---|---|---|---|
| Market Radar | **Atlas** | Feed Watcher (frescura e sequência), Event Scout (movimentos/eventos), Gap Detector (candidatos temporais), Feed Health (reconexão e qualidade) | Eventos candidatos, timestamps de origem/receção, qualidade, atrasos e incertezas |
| Comparação entre Exchanges | **Delta** | Symbol Mapper (instrumentos equivalentes), Price Comparator (preços e profundidade), Cost Analyst (taxas/slippage), Inventory Checker (inventário e executabilidade) | Comparação normalizada, custos, liquidez, inventário e razão de aceitar/rejeitar |
| Integrações de Exchanges | **Bridge** | Binance Adapter, Coinbase Adapter, OKX Adapter e futuros adaptadores; Protocol Watcher; Rate-Limit Monitor | Saúde por venue, cobertura, limites, erros e idade do último evento |
| Investigação | **Sherlock** | Docs Researcher, Source Verifier, Hypothesis Builder, Exchange Researcher | Fontes, data, hipótese, confiança, lacunas e próximos testes |
| Análise | **Athena** | Signal Analyst, Evidence Checker, Regime/Context Analyst, Confidence Reviewer | Evidência consolidada, explicações alternativas, confiança e estado da validação |
| Resposta Rápida / Execução Controlada | **Flash** | Opportunity Triage, Latency Watcher, PAPER Action Planner, Order-Safety Checker | Urgência, vantagem líquida estimada, gates, decisão PAPER e motivo; sem ordens reais nesta fase |
| Laboratório PAPER / Replay | **Turing** | Replay Runner, Scenario Builder, Fee/Slippage Simulator, Regression Tester | Reprodutibilidade, amostras, métricas e limitações dos testes |
| Controlo de Risco | **Sentinel** | Exposure Monitor, Limits Guard, Drawdown Watcher, Risk Gatekeeper | Bloqueios, limites, exposição e motivo explícito; gates não contornáveis |
| Memória Central de Aprendizagem | **Mnemosyne** | Knowledge Curator, Deduplicator, Provenance Tracker, Validation/Expiry Reviewer | Conhecimento novo/alterado, origem, versão, validação e expiração |
| Auditoria / Observabilidade | **Scribe** | Event Auditor, Metrics Reporter, Trace Correlator, Anomaly Reporter | Trilha de eventos, métricas, anomalias e lacunas de observabilidade |
| Recuperação / Saúde do Sistema | **Phoenix** | Heartbeat Monitor, Reconnect Coordinator, State Reconciler, Recovery Tester | Estado de saúde, falhas, tentativas, recuperação e ação pendente |
| Intervenção Humana / Aprovações | **Guardian** | Auth Prompt Coordinator, Approval Queue, Session/Expiry Watcher, Operator Notifier | Aprovações pendentes, expiração, autenticação necessária e decisão do operador |

### Protocolo de comunicação e prevenção de perdas

Cada mensagem interdepartamental e cada relatório deve incluir, no mínimo: `message_id`, `task_id`, departamento e agente de origem, destinatário, prioridade, timestamps de criação e receção, estado, resumo, evidência/referências, confiança, incertezas, dependências e ação pedida. Os resultados extensos ficam na Memória Central ou no armazenamento de evidências; a mensagem transporta um resumo e uma referência estável, não cópias ilimitadas.

O chefe mantém um registo das tarefas recebidas, atribuídas, concluídas, bloqueadas e escaladas. O CEO recebe relatórios consolidados com alterações desde o último relatório, bloqueios, decisões necessárias e próxima ação. Uma tarefa não é considerada concluída apenas porque um subagente respondeu: o chefe verifica a evidência e marca o resultado como aceite, rejeitado ou inconclusivo.

Quando houver divergência entre agentes, o chefe regista as versões e evidências em conflito e pede validação; não apaga silenciosamente a discordância. Se o conflito envolver risco, permissões, dados inválidos ou segurança, a execução fica bloqueada até ser resolvido pelo gate competente. A Memória Central guarda proveniência e estado de validação para evitar que uma hipótese seja reutilizada como facto.

### Estado de implementação

Esta é a **estrutura organizacional aprovada para implementação**. Os nomes identificam os papéis lógicos pretendidos; não significam que existam atualmente 12 agentes autónomos em execução. A implementação deve introduzir primeiro o contrato de mensagens, a supervisão e os relatórios auditáveis; depois ligar os agentes especializados aos departamentos, mantendo execução PAPER/observacional e sem ativar ordens reais.
