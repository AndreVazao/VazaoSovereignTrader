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
