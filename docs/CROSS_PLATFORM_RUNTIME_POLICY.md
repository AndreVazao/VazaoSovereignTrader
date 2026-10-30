# Sovereign Trader — estratégia multiplataforma e escolha do sistema operativo

**Estado:** decisão de arquitetura aprovada para desenvolvimento.  
**Data:** 2026-10-30  
**Âmbito:** VazaoSovereignTrader; não altera nem mistura o DGM-MAT.

## Decisão executiva

1. O Sovereign Trader será desenvolvido para ser instalável e executável em Windows e Linux, evitando dependências desnecessárias de um único sistema operativo.
2. Para um futuro computador dedicado a executar o cérebro continuamente, **Linux Server LTS é a opção preferencial inicial**, desde que o hardware e as ferramentas necessárias sejam compatíveis.
3. Windows continua a ser uma plataforma suportada, especialmente para cockpit/desktop, instalação simples e ferramentas que dependam de Windows.
4. Não recomendar uma migração imediata do PC atual. A decisão deve ser validada com medições reais e com a disponibilidade do utilizador.
5. O núcleo de execução, a interface de controlo e o escritório virtual devem permanecer separados. O cérebro deve continuar a funcionar quando a interface gráfica está fechada ou indisponível.

## Porque preferir Linux para um servidor dedicado

Linux oferece um ambiente natural para serviços headless, automação, SSH, gestão de processos com systemd, scripts e contentores. Uma instalação mínima sem ambiente gráfico pode reduzir o consumo de recursos em comparação com uma instalação Windows com serviços e aplicações de desktop. A diferença real depende da configuração e não é uma garantia de maior velocidade do código.

Linux não elimina latência de rede, limites de APIs, tempos de resposta de exchanges ou atrasos de modelos remotos. A prioridade é reduzir trabalho bloqueante, paralelizar tarefas independentes, reutilizar conexões, limitar concorrência e medir o desempenho.

Referências oficiais:
- Ubuntu Server — requisitos e suporte de arquitetura: https://ubuntu.com/server/docs/system-requirements/
- Microsoft WSL — executar ferramentas Linux em Windows: https://learn.microsoft.com/windows/wsl/
- Microsoft — systemd no WSL: https://learn.microsoft.com/windows/wsl/systemd/

## Arquitetura multiplataforma

- **Core/brain:** serviços headless; sem dependência da UI, do sistema de janelas ou de renderização 3D.
- **Agentes/departamentos:** processos isolados com interfaces de mensagens explícitas; timeouts, limites de concorrência, retries e cancelamento.
- **Persistência:** migrações e formatos de dados portáveis; caminhos de ficheiros através das bibliotecas da linguagem, nunca caminhos absolutos de um sistema específico.
- **Configuração:** variáveis de ambiente e ficheiros de configuração documentados; segredos fora do Git, dos logs e dos artefactos.
- **Serviço e arranque:** adaptadores de deployment para systemd em Linux e Windows Service/Task Scheduler no Windows, sem acoplar a lógica do core a esses mecanismos.
- **Cockpit e escritório virtual:** clientes opcionais que comunicam com o runtime por API autenticada; falhas de renderização não podem parar o cérebro.
- **Rede/remoto:** manter o desenho de descoberta e conectividade aprovado; não assumir que WSL, uma VM ou uma ligação VPN está sempre ativa.
- **Trading:** PAPER/read-only por defeito; sem ordens reais ou movimentação de fundos em testes de CI.

## Regras de implementação

- Evitar dependências exclusivas de Windows ou Linux no núcleo, salvo atrás de adaptadores bem definidos.
- Usar paths portáveis, encoding UTF-8, UTC internamente e conversões explícitas para fusos horários de apresentação.
- Evitar dependências de shell específicas; scripts de build e release devem ter caminhos equivalentes ou executar em runners separados.
- Testar Python e contratos do core em Linux e Windows através de uma matriz de CI.
- Construir artefactos específicos por plataforma e identificar arquitetura (x86_64/ARM64) e dependências nativas.
- Tratar Chromium, Obscura e outros browsers como motores opcionais atrás de uma interface comum; fallback obrigatório para o motor suportado.
- Não adicionar uma VM ao computador do utilizador apenas para obter compatibilidade Linux quando a mesma validação pode correr num runner cloud.
- Não prometer paridade perfeita antes de executar a matriz de CI e os testes em hardware real.

## Plano de validação

1. CI em Linux e Windows para testes unitários, contratos, lint/compilação e testes de integração aplicáveis.
2. Build separado de artefactos de desktop/APK onde aplicável.
3. Smoke test do runtime sem UI e prova de que fechar/reiniciar a UI não termina o core.
4. Testes de recuperação: serviço reiniciado, browser indisponível, timeout de rede, fila cheia e armazenamento temporariamente indisponível.
5. Medições equivalentes de CPU, RAM, latência de tarefas e estabilidade antes de afirmar que um sistema operativo é mais rápido.
6. Testes no PC do utilizador e no futuro computador quando disponíveis. Até lá, marcar explicitamente como BLOCKED/NOT RUN.

## Recomendação para a futura máquina

Se o computador for principalmente um servidor Sovereign Trader, escolher uma distribuição Linux Server LTS suportada e instalar sem ambiente gráfico pesado; administrar remotamente e usar o cockpit noutro dispositivo. Se também for o computador de uso pessoal e depender de aplicações Windows, manter Windows e considerar WSL2 apenas para desenvolvimento/testes Linux — não o tratar automaticamente como equivalente a um servidor Linux dedicado.

Antes de escolher a distribuição final, confirmar CPU/arquitetura, RAM, armazenamento, GPU (se necessária), firmware, compatibilidade de drivers e requisitos das ferramentas de desktop. O hardware e a RAM disponível têm mais impacto do que uma escolha de sistema operativo feita sem medições.

## Estado atual

- **Decisão de arquitetura:** Windows e Linux são alvos de suporte.
- **Preferência para servidor dedicado futuro:** Linux Server LTS.
- **Migração imediata:** não recomendada.
- **Benchmark Windows vs Linux no PC antigo:** NOT RUN; acesso físico não disponível.
- **Teste cloud:** útil para portabilidade e CI, mas não substitui medições do hardware real.
