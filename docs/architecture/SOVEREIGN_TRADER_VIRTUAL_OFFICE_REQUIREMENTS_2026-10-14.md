# Vazão Sovereign Trader — Requisitos do Escritório Virtual Dedicado
**Data:** 2026-10-14  
**Estado:** proposta documental; ainda não implementada nem aprovada para execução  
**Âmbito:** exclusivamente `AndreVazao/VazaoSovereignTrader`

## 1. Decisão do proprietário

Criar, numa fase futura, um **escritório virtual exclusivo do Vazão Sovereign Trader**. Este escritório é um projeto independente e não deve ser incorporado no DGM-MAT, Mades, AndreOS ou em qualquer outro programa. Não partilha departamentos, agentes, estado operacional, identidade visual obrigatória, dados de execução nem controlos de outros projetos. Eventuais bibliotecas comuns só poderão ser consideradas mais tarde, através de avaliação explícita de dependências, licença, segurança e isolamento; não são pressupostas por esta nota.

Esta branch regista a intenção e os requisitos. **Não altera `main`, não implementa o escritório, não ativa trading REAL e não autoriza alterações operacionais.**

## 2. Tipologia atual do Sovereign Trader — referência para o desenho

O README da branch `main` descreve o programa como um sistema de trading automatizado **local-first**, com controlo de risco e arquitetura PC + móvel:

- **PC_ENGINE:** motor local concebido para funcionar continuamente e ser o núcleo operacional.
- **MOBILE_APP:** cockpit remoto para observar e controlar o motor.
- **shared:** contratos partilhados entre PC e aplicação Android.
- **PAPER-first:** modo PAPER por defeito; a interface visual não pode contornar os gates de risco ou autorizar REAL.
- **Estratégia e análise de mercado:** estratégia EMA/ATR/VWAP com filtro de regime, features de padrões de velas, Sovereign Market Radar, Capital Opportunity Engine, análise de order flow/L2 e investigação de hipóteses.
- **Conselho de IA opcional:** pode aconselhar, mas não é executor de ordens.
- **Risk Engine e RealModeGuard:** autoridade de risco e bloqueio independentes da estratégia e da apresentação visual.
- **Persistência e auditoria:** ledger, eventos de investigação, evidência, readiness, logs e mecanismos de recuperação/reconciliação.
- **Integrações de execução:** API, browser, Android e ponte humana, com controlos próprios e confirmação explícita para operações reais.
- **Segurança:** chaves fora do GitHub, API local autenticada, permissões mínimas e sem permissões de levantamento nas exchanges.

Estes pontos foram identificados no README atual e servem de mapa inicial, não como auditoria completa do código. Antes de implementar, confirmar cada agente, serviço, worker, fila, fonte de dados e estado através do código, contratos, testes e runtime.

## 3. Objetivo do escritório

Disponibilizar uma representação navegável do trabalho real do Sovereign Trader, para o operador conseguir perceber:

1. Que componentes/agentes estão ativos, parados, ocupados, bloqueados ou em erro.
2. Que tarefa ou investigação cada componente está a executar e qual foi a última ação confirmada.
3. Como os componentes comunicam: remetente, destinatário, motivo, timestamp, estado, correlação/ID, resultado e evidência.
4. Que fontes e plataformas cada investigação consulta — por exemplo, exchanges, feeds públicos, documentação, notícias ou páginas web — distinguindo claramente fontes planeadas, tentadas, consultadas e verificadas.
5. Como uma observação do Radar se transforma (ou não) numa hipótese, sinal candidato, validação, revisão de risco e resultado PAPER.
6. O que está à espera de dados, validação, intervenção humana ou recuperação, e porquê.
7. Como está a saúde do motor, dos coletores, da investigação, da persistência e das integrações.

O escritório deve apresentar factos provenientes de eventos reais. Não inventar conversas, pesquisas, tarefas, lucros, ordens, estados ou relações para tornar a cena mais animada.

## 4. Renderização adaptável ao hardware

A experiência deverá escolher um nível de detalhe com base em medições e permitir ao operador alterar manualmente o modo:

- **Modo económico:** 2D simples, bonecos de palitos/ícones, pouca ou nenhuma animação, baixo consumo de RAM/CPU, compatível com computadores antigos.
- **Modo equilibrado:** escritório isométrico 2.5D ou low-poly, animações discretas e etiquetas de estado.
- **Modo avançado:** 3D mais detalhado em máquinas que o suportem sem prejudicar o motor de trading.

A escolha automática deve considerar RAM/CPU disponíveis, capacidade gráfica, suporte WebGL, FPS e carga do sistema, com degradação progressiva quando a máquina está ocupada. O modo económico deve ser a opção segura inicial até existirem medições. A visualização nunca pode competir com o ciclo de mercado nem alterar a lógica de trading; se necessário, reduz-se ou fecha-se o renderer, mantendo o PC_ENGINE operacional.

A navegação deve funcionar também sem 3D: lista/árvore de componentes, filtros, pesquisa e painéis acessíveis por teclado.

## 5. Espaços e componentes visuais candidatos

A disposição final só será decidida depois de mapear a arquitetura real. Como metáfora opcional, o escritório pode incluir:

- **Sala de controlo / direção:** estado global, saúde, modo PAPER/REAL, bloqueios, alertas e aprovações pendentes.
- **Radar e recolha de mercado:** exchanges/feeds efetivamente ligados, símbolos, qualidade dos dados, latência e ciclos de recolha.
- **Investigação e fontes:** pedidos, hipóteses, páginas/fontes consultadas, resultados e evidência em falta.
- **Estratégias e validação:** sinais candidatos, regime, walk-forward, OOS, stress de custos e resultados por símbolo/timeframe.
- **Risco e capital:** limites, exposição, drawdown, cooldowns, readiness e razões para autorizar/bloquear.
- **Execução e reconciliação:** preparação, submissão, fills confirmados, resultados ambíguos, ledger e recuperação.
- **Persistência, auditoria e saúde:** eventos, snapshots, workers, erros, watchdog e dependências.
- **Cockpit do operador:** ações já suportadas pela API, com permissões, autenticação, confirmação e auditoria correspondentes.

Estes são nomes de áreas conceptuais, não uma afirmação de que cada uma é um agente autónomo. Só se deve desenhar um boneco separado quando existir um agente/worker/serviço real ou uma entidade operacional explicitamente modelada.

## 6. Inspecionar agentes e comunicação

Ao selecionar um boneco/componente, mostrar apenas informação disponível e autorizada:

- identificador e tipo real (agente, worker, serviço, collector ou subsistema);
- estado atual e hora da última atualização;
- tarefa, objetivo e ID de correlação;
- dependências, fila e bloqueadores;
- mensagens/eventos enviados e recebidos, com destinatário e resultado;
- pesquisas/fonte de dados: estado de acesso e timestamp, URL/plataforma quando permitido, evidência obtida e limitações;
- logs relevantes, testes/evidências e próximo passo conhecido.

Deve ser possível filtrar a comunicação por componente, tarefa, período, tipo de evento e estado. A vista não deve expor API keys, tokens, cookies, sessões de browser, dados pessoais desnecessários ou conteúdo secreto. As URLs e consultas devem ser filtradas quando possam conter credenciais.

## 7. Separação crítica entre observação, decisão, risco e execução

A representação visual deve refletir, sem fundir, as fronteiras existentes:

```
Market data / Radar -> Evidence -> Strategy candidate
                  -> optional AI advice
Strategy candidate -> Risk Engine / readiness gates
Risk approval      -> execution layer
Execution response -> authoritative reconciliation / ledger
```

- Radar, investigação e conselho de IA não executam ordens por si.
- Um sinal candidato não é uma ordem autorizada.
- Uma submissão não equivale a fill confirmado; um fill não equivale automaticamente a contabilização final.
- A visualização não pode alterar o Risk Engine, o RealModeGuard, os limites, a reconciliação ou o modo PAPER/REAL.
- Não incluir botões decorativos que aparentem executar ações. Cada controlo tem de chamar uma operação existente, autenticada e autorizada.
- Qualquer ação financeira real continua sujeita aos mecanismos de segurança existentes, confirmação explícita, registo auditável e bloqueio por defeito. O escritório não cria uma via alternativa para REAL.
- Se o estado não puder ser confirmado, mostrar **desconhecido/desatualizado**, nunca presumir sucesso.

## 8. Arquitetura recomendada — a validar antes de implementar

1. **Fonte da verdade:** PC_ENGINE, contratos, ledger e eventos persistentes já existentes.
2. **Adaptador de observabilidade:** expõe uma vista read-only, com esquema versionado, sem importar lógica de trading para a interface.
3. **API autenticada:** reutiliza a fronteira local existente e respetivas autorizações; não abrir novas portas à rede nem contornar o token.
4. **Renderer independente:** 2D/2.5D/3D selecionável, que pode reiniciar ou fechar sem interromper o motor.
5. **Cockpit:** filtros, detalhe por componente, linha temporal, pesquisa e alertas.
6. **Testes de contrato:** garantir que os estados visuais correspondem aos estados reais e que falhas da UI não afetam o motor.

Não adicionar uma nova fila de eventos, base de dados ou sistema de agentes antes de verificar se a infraestrutura atual já fornece a informação necessária. Se faltarem eventos, documentar primeiro a lacuna e propor instrumentação mínima.

## 9. Fases futuras

1. **Auditoria read-only:** inventariar agentes, processos, módulos, filas, fontes, endpoints, eventos, testes e dados persistidos.
2. **Contrato de observabilidade:** definir campos, proveniência, atualização, estados desconhecidos, permissões e retenção.
3. **Cockpit económico 2D:** lista e painéis reais, sem avatares animados nem novas ações de trading.
4. **Escritório navegável:** bonecos/ícones para componentes reais, detalhe individual e comunicação rastreável.
5. **Renderização adaptável:** acrescentar isométrico/low-poly e só depois 3D, com benchmark em hardware real.
6. **Verificação de segurança:** testes que provem que falhas do renderer, mensagens malformadas ou comandos não autorizados não alteram trading, risco ou execução.

Cada fase deve usar uma branch própria, testes locais/CI já existentes e PR para revisão. Não fazer merge automático.

## 10. Critérios de aceitação

- Escritório e documentação pertencem exclusivamente ao Vazão Sovereign Trader.
- O motor continua a funcionar se o escritório for fechado, ficar sem rede ou falhar.
- A vista distingue estados reais de estados desconhecidos e mostra timestamp/proveniência.
- É possível identificar tarefas, comunicações e fontes de pesquisa sem expor segredos.
- Os estados e ações são validados contra contratos, API e testes existentes.
- O modo económico é utilizável em hardware limitado; os modos avançados são opcionais.
- Nenhuma animação, consulta de UI ou pesquisa web bloqueia o ciclo de mercado.
- Nenhum controlo visual contorna PAPER-first, Risk Engine, RealModeGuard, autenticação ou confirmação humana.
- Nenhum dado/estado/agente é partilhado implicitamente com DGM-MAT, Mades ou outros programas.

## 11. Fora de âmbito nesta nota

Não implementar o escritório, não criar agentes artificiais, não mudar a arquitetura de trading, não ativar REAL, não instalar dependências, não alterar a branch `main`, não fazer deploy e não modificar outros repositórios. Esta nota regista intenção e requisitos para planeamento futuro.

## Referência inicial

- README do projeto na branch `main`: https://github.com/AndreVazao/VazaoSovereignTrader/blob/main/README.md
