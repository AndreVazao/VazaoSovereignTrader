# Sovereign Trader — instalação adaptativa e funções por máquina

**Estado:** contrato de arquitetura para implementação incremental.  
**Âmbito:** VazaoSovereignTrader; independente do DGM-MAT.

## Objetivo

A instalação deve reconhecer as capacidades e o sistema operativo da máquina, propor um perfil compatível e instalar apenas os componentes necessários para a função autorizada. O objetivo não é instalar automaticamente todos os departamentos em todas as máquinas nem prometer maior velocidade apenas por usar Linux.

## Princípios obrigatórios

1. **Um runtime, vários perfis de nó.** O mesmo código-base suporta Windows e Linux; cada instalação ativa apenas os serviços selecionados.
2. **Deteção antes de instalação.** Um preflight identifica OS, arquitetura (x86_64/ARM64), versão suportada, CPU lógica, RAM disponível, espaço em disco, permissões, dependências e conectividade. A deteção não recolhe dados pessoais desnecessários.
3. **Plano explícito antes de alterações.** Mostrar um resumo do que será instalado, atualizado, ativado e quanto espaço poderá ocupar. Instalação de serviços, drivers, firewall, VPN, credenciais ou alterações privilegiadas requer confirmação explícita.
4. **Perfis por função.** Perfis iniciais: brain-server, department-worker, research-worker, memory-node, desktop-cockpit e office-visualizer. Um nó pode alojar mais de uma função se os recursos forem suficientes; a visualização é sempre opcional.
5. **Sem privilégios excessivos.** Serviços correm com conta de serviço e permissões mínimas. Não desativar segurança do sistema, não abrir portas públicas automaticamente e não instalar pacotes globais sem necessidade.
6. **Instalação idempotente e reversível.** Repetir o instalador não duplica serviços nem identidades. Registar versão, componentes, configuração e resultado; oferecer diagnóstico, atualização controlada e desinstalação limpa.
7. **Identidade separada da máquina.** OS, hostname e fingerprint de hardware ajudam a identificar capacidades, mas não substituem installation_id, node_id, department_id ou autorização. Uma máquina detetada não ganha automaticamente permissões, nome de agente, papel CEO nem acesso a dados.
8. **Fail closed na autorização; fail soft na apresentação.** Se o registo/autorização não estiver disponível, não criar uma identidade remota nem abrir acesso. O runtime local pode continuar apenas nas operações seguras previamente autorizadas. Uma falha da UI não deve parar o cérebro.
9. **PAPER/read-only por defeito.** O instalador nunca ativa trading real, não importa chaves de API para testes e não altera limites de risco.
10. **Sem otimizações especulativas.** Não desativar serviços do Windows/Linux ou mudar parâmetros de kernel automaticamente. Medir primeiro e propor alterações separadamente.

## Estratégia de sistema operativo

- **Servidor dedicado/headless:** preferir Linux Server LTS mínimo quando CPU, arquitetura, drivers e ferramentas forem compatíveis.
- **PC pessoal que já usa Windows:** continuar a suportar Windows; não forçar migração. WSL2 pode ser útil para desenvolvimento/testes Linux, mas não é considerado equivalente a um servidor Linux dedicado.
- **Máquina Windows para cockpit/instalação de desktop:** fornecer instalador Windows com os componentes necessários, sem exigir um ambiente Linux.
- **Worker de departamento:** Linux é a opção preferida para novos nós dedicados headless, mas Windows continua válido. A decisão por nó considera recursos, compatibilidade e manutenção, não uma regra universal.
- **Máquina limitada:** desativar por defeito 3D, browser persistente e modelos locais pesados; manter chat/cockpit leve e serviços essenciais. Não iniciar vários agentes concorrentes se o orçamento de RAM/CPU não o permitir.

## Arquitetura de instalação

Separar a lógica em camadas, sem misturar a política de trading com o instalador:

- platform_probe: recolhe capacidades e versão do OS com APIs portáveis.
- capability_profile: calcula limites conservadores e recomenda perfis; nunca concede permissões.
- component_manifest: lista componentes, versões, dependências, hash/assinatura e plataformas suportadas.
- install_plan: apresenta o plano e pede consentimento para ações privilegiadas.
- platform_service_adapter: instala/atualiza serviços através de systemd no Linux e do mecanismo suportado no Windows (Windows Service ou Task Scheduler, conforme o componente).
- node_enrollment: obtém identidade e autorização por fluxo autenticado; não deriva permissões do hostname ou fingerprint.
- health_report: comunica versão, papel autorizado, capacidades resumidas, saúde e componentes ausentes, sem segredos.
- rollback/uninstall: reverte apenas componentes que o instalador gere; nunca mata processos alheios nem apaga dados do utilizador sem confirmação.

A implementação deve começar por um comando de diagnóstico sem alterações, por exemplo vst doctor --json, e por um manifesto de componentes validado. Só depois se acrescenta instalação automática por etapas.

## Descoberta e distribuição de departamentos

1. A instalação deteta recursos e apresenta perfis compatíveis.
2. O utilizador escolhe o perfil; a identidade e o papel são aprovados pelo fluxo de enrollment/registo.
3. O runtime confirma versão de protocolo, permissões e política local.
4. A coordenação distribui tarefas apenas a nós autorizados e saudáveis, respeitando limites de CPU/RAM, filas, timeout e cancelamento.
5. Um departamento indisponível aparece como ausente/degradado; nunca é fingido como saudável.
6. A comunicação normal entre nós usa a rede privada aprovada. Vercel serve para descoberta/registo quando disponível, não como caminho obrigatório de todas as mensagens internas.
7. Se um nó cair, tarefas repetíveis podem ser reatribuídas; tarefas com estado devem ser recuperadas com idempotência e sem duplicar ações.
8. Um worker de pesquisa não recebe automaticamente chaves de exchange, permissões de risco ou autoridade de execução.

## Critérios de validação antes de chamar a instalação de automática

- Testar preflight em Windows e Linux, incluindo arquitetura não suportada, permissões insuficientes e pouco espaço em disco.
- Verificar que o modo diagnóstico não altera o sistema.
- Testar instalação, atualização, repetição idempotente, falha a meio, rollback e desinstalação em máquinas/VMs descartáveis.
- Validar hashes/assinaturas e impedir downgrade não autorizado.
- Testar que fechar o cockpit/escritório não termina os serviços do cérebro.
- Testar recursos limitados e garantir que o supervisor reduz concorrência em vez de esgotar a máquina.
- Verificar ausência de segredos em logs, artefactos e relatórios.
- Executar CI em Windows e Linux; marcar testes de hardware físico como NOT RUN até serem executados.
- Medir CPU, RAM, throughput, latência interna e estabilidade em cargas equivalentes antes de alegar ganhos de velocidade.

## Estado

Este documento define o contrato de comportamento pretendido; não declara que um instalador adaptativo já esteja implementado. A implementação deve ser incremental, com testes e PRs pequenos. Até lá, não instalar nem configurar serviços automaticamente em máquinas do utilizador.
