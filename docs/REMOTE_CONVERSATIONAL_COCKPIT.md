# Cockpit conversacional remoto — Sovereign Trader
**Data:** 2026-10-19  
**Estado:** requisito de produto documentado; não constitui prova de que o fluxo remoto já esteja operacional.

## Contexto de utilização
O proprietário é motorista de camião articulado e pode estar 20–30 dias fora de casa a viajar pela Europa. O PC doméstico deve poder manter o Sovereign Trader a funcionar, enquanto o proprietário acompanha o sistema e conversa com ele pelo telemóvel, a partir de outro país ou rede.

## Identidade e missão do produto
O Sovereign Trader é uma ferramenta específica para pesquisa, aprendizagem, análise e operação de trading, com controlo de risco. Não é DGM-MAT. Não é uma plataforma geral para construir programas nem deve partilhar dados privados, credenciais, ordens, saldos, posições, estratégias ou permissões com DGM-MAT.

## Cockpit de conversação
- Dar ordens em linguagem natural para pesquisar exchanges, instrumentos, taxas, funding, spreads, liquidez, latência, eventos, campanhas e hipóteses de oportunidade.
- Consultar estado real do PC Engine, PAPER/REAL, readiness, risco, posições, ordens, reconciliação, pesquisas em curso, fontes e resultados.
- Receber relatórios com timestamps, links/fontes, custos estimados, limitações, incerteza e separação entre factos, hipóteses e conclusões.
- Ver pedidos de autenticação/aprovação que persistem até serem resolvidos ou expirarem; não depender de pop-ups locais no PC.
- Receber notificações remotas de bloqueios, pedidos de intervenção, falhas e conclusão de tarefas.
- Retomar depois de interrupções sem perder contexto nem duplicar ordens ou transferências.

## Separação entre investigação, autenticação, aprovação e execução
- Descobrir uma oportunidade ou concluir uma pesquisa **não** autoriza uma ordem.
- Dados públicos e investigação read-only podem ser usados sem permissões de trading, dentro dos limites de segurança configurados.
- Segredos e códigos MFA devem ser inseridos num formulário seguro e encaminhados diretamente ao conector autorizado; nunca no histórico de conversa, logs, push notifications ou relatórios.
- Aprovações devem estar vinculadas ao utilizador/dispositivo e à ação exata, ter resumo de instrumento, lado, quantidade, tipo de ordem, venue, exposição/custos estimados, validade e riscos, e ser revogáveis/expiráveis.
- REAL permanece fechado salvo passagem explícita por readiness, Risk Engine, RealModeGuard, autenticação do operador, reconciliação e todos os gates existentes. Não contornar gates através do chat ou de notificações.
- Ordens, cancelamentos, mudanças de configuração de risco e transferências/levantamentos são ações distintas e devem exigir as autorizações apropriadas. Nunca assumir sucesso de uma operação com resultado desconhecido; reconciliar com a exchange.
- Quando não existirem credenciais, dados atuais, permissões ou confirmação, declarar o bloqueio em vez de inventar resultados.

## Conectividade e segurança
- PC_ENGINE continua a autoridade para risco, estado, decisão e execução; MOBILE_APP/cockpit é cliente remoto.
- Preferir ligação privada autenticada (por exemplo, Tailscale). Rendezvous público, se usado, deve limitar-se a descoberta/presença, sem se tornar plano de execução ou armazenamento de conversas.
- Não expor a API local diretamente à Internet. Validar autenticação e autorização em todas as rotas HTTP/WebSocket e em cada comando.
- Manter segregação de owner/dispositivo e proteção contra replay, expiração e revogação. Falha de rede deve bloquear ações não confirmadas, sem bloquear indevidamente o ciclo local de mercado.
- O estado de cada tarefa deve ser persistente e verificável; o cockpit nunca deve inventar atividade ou apresentar animação como prova de trabalho.

## Critérios de aceitação
- [ ] Dar uma ordem de investigação a partir do telemóvel e acompanhar o ID/estado da tarefa.
- [ ] Receber um relatório com fontes e timestamp, sem alegações de vantagem sem evidência.
- [ ] Receber remotamente e resolver um pedido de autenticação/aprovação enquanto o PC está em casa.
- [ ] Testar segredos e MFA sem persistência em chat/logs/notificações.
- [ ] Confirmar que nenhuma mensagem comum no chat consegue ultrapassar gates de REAL.
- [ ] Testar perda de rede, resultado desconhecido e reconciliação sem ordens duplicadas.
- [ ] Confirmar UI legível em Android e reconexão depois de suspensão/reinício.
- [ ] Testar segurança de acesso remoto antes de declarar o cockpit pronto para uso fora de casa.

## Próximos passos
1. Auditar crash do APK e o endpoint de mensagens do PC Engine; distinguir defeitos de UI de capacidades reais do cérebro.
2. Auditar autenticação/pairing, sessões, APIs e conectividade privada antes de expor controlo remoto.
3. Validar fluxo de tarefas e pedidos de aprovação em PAPER/read-only.
4. Implementar notificações e formulários de credenciais protegidos.
5. Só após os testes, considerar qualquer caminho de execução remota sensível.
