# Escritório virtual adaptativo e investigação de vantagens entre mercados
**Data:** 2026-10-19  
**Estado:** proposta de arquitetura e investigação; não constitui prova de vantagem lucrativa nem autorização para trading REAL.

## 1. Objetivo
O Sovereign Trader deve ter um escritório virtual que torne o trabalho real do sistema observável, acompanhável e escalável. O escritório é uma visualização do estado operacional — não um simulador de atividade. A experiência de cockpit conversacional remoto permanece uma interface separada, mas pode abrir diretamente tarefas, alertas, relatórios e departamentos relevantes.

## 2. Representação adaptativa à capacidade do PC
O sistema deve escolher um perfil visual de acordo com a capacidade e o orçamento de recursos disponíveis:
- **Lite:** 2D simples/pixel art, animações mínimas, baixa utilização de CPU/RAM/GPU; adequado a hardware fraco.
- **Standard:** escritório 2D/2.5D com salas, mesas, agentes, gráficos e indicadores de estado.
- **Advanced:** ambiente 3D opcional, maior detalhe e visualizações ricas quando o hardware permite.

A escolha deve ser baseada em medição de capacidade e desempenho, com fallback manual e automático. A visualização deve poder reduzir animações, taxa de atualização e efeitos sem reduzir a frequência/qualidade da recolha de dados, do motor de risco ou do processamento de mercado. A GPU serve a apresentação; não é prova de maior inteligência. A interface móvel deve usar uma vista compacta/responsiva, não forçar o cenário de PC num ecrã pequeno.

## 3. Edifício e departamentos
O escritório pode começar pequeno e crescer conforme o número real de conectores, tarefas, serviços e agentes habilitados. A expansão visual deve ser consequência de configuração/estado real, não de animações ou agentes fictícios.

Departamentos possíveis, sujeitos à implementação efetiva:
- **Sala por exchange/venue:** por exemplo Binance, BingX e outras que venham a ser suportadas, com estado do conector, frescura dos dados, mercados cobertos, limites, erros e resultados.
- **Market Data & Order Book:** trades, livro de ordens, spreads, profundidade, timestamps e qualidade de feed.
- **Candlesticks & Technical Analysis:** OHLCV, padrões/indicadores e hipóteses técnicas; distinguir cálculo de hipótese de previsão confirmada.
- **Cross-Venue Timing & Lead-Lag:** sincronização temporal, deteção de movimentos relativos, atrasos aparentes e estabilidade estatística.
- **News & Event Research:** pesquisa web, anúncios oficiais, listagens, eventos e fatores macro, com URL, hora de publicação e hora de recolha.
- **Fees, Liquidity & Execution Quality:** taxas, funding, slippage, profundidade, latência, limites, tamanho executável e custos de entrada/saída.
- **Risk & Portfolio:** exposição, limites, drawdown, concentração, risco de venue, reconciliação e circuit breakers.
- **Paper Lab & Validation:** simulações, replay de mercado, benchmarks, testes fora da amostra e monitorização de degradação.
- **Fast Execution:** componente de risco elevado, desativado por defeito e bloqueado a PAPER até que os gates e critérios de evidência sejam satisfeitos.

A atribuição de uma sala a uma exchange não significa que cada sala tenha de executar uma estratégia independente. Os dados devem poder ser comparados por um modelo de instrumentos e timestamps canónicos.

## 4. Investigação de diferenças temporais entre venues
A hipótese é que alguns venues ou mercados reajam em momentos diferentes a informação ou movimentos comuns. O sistema deve investigar se existe uma vantagem observável e executável, não assumir que a diferença temporal é uma previsão garantida.

Para cada par de venues/instrumentos, recolher e analisar:
- relógios sincronizados e timestamps de evento, exchange, receção local e decisão;
- diferenças de símbolo, cotação, contrato, tick size, lot size, index/mark price e regras de mercado;
- trades e snapshots/deltas de order book com verificação de sequência e frescura;
- latência de rede e processamento, perdas de mensagens, gaps e reconexões;
- spread, profundidade disponível, volume, fees, funding, slippage e custos de entrada/saída;
- frequência, duração, magnitude, direção e reversão do lead-lag;
- comportamento em diferentes regimes e instrumentos, com intervalos de confiança e casos em que a hipótese falha.

A pesquisa deve evitar confundir timestamps de publicação/receção com o momento económico do evento. Uma diferença entre preços não é automaticamente uma oportunidade: pode refletir instrumentos não equivalentes, liquidez insuficiente, feed atrasado, preço de referência diferente ou custos que absorvem toda a margem.

## 5. Pipeline de validação antes de qualquer investimento rápido
1. **Discover:** identificar mercados e fontes candidatas; começar com dados públicos/read-only.
2. **Normalize:** mapear instrumentos equivalentes, moedas de cotação, contratos e regras.
3. **Measure:** medir timestamps, lead-lag, qualidade dos feeds e latência real.
4. **Hypothesize:** formular uma regra explícita de entrada, saída, invalidação e horizonte temporal.
5. **Replay/Backtest:** usar dados históricos com taxas e limitações realistas; evitar look-ahead bias e survivorship bias.
6. **Paper/live shadow:** executar sinais em tempo real sem ordens reais, incluindo latência e disponibilidade reais.
7. **Out-of-sample:** validar em períodos e condições não usados na formulação, incluindo mercados adversos.
8. **Risk review:** testar tamanho, liquidez, exposição simultânea, limites, circuit breakers, falhas de API e resultados desconhecidos.
9. **Human approval & readiness:** só considerar uma fase seguinte após critérios documentados, gates existentes e autorização explícita.

Métricas mínimas: PnL líquido de custos, drawdown, taxa de acerto e payoff, número e independência dos eventos, turnover, slippage realizado/estimado, fill rate, tempo de exposição, perdas em falhas, estabilidade por regime e diferença entre resultado simulado e observado. Incluir custos de oportunidade e capital imobilizado quando relevantes.

## 6. Departamento Fast Execution — limite de segurança
Este departamento é uma hipótese de execução de alta velocidade, não uma promessa de lucro. Deve permanecer desligado ou em modo shadow/PAPER por defeito. Uma diferença temporal observada não prova que o sistema sabe antecipadamente o próximo movimento, nem garante que a ordem chegue antes de o preço mudar.

Qualquer futura execução REAL exige, sem exceção:
- instrumentos e mercados autorizados e corretamente normalizados;
- dados frescos e integridade de sequência;
- edge líquido validado fora da amostra e com incerteza quantificada;
- avaliação de fees, slippage, liquidez, funding, latência e custos de falha;
- limites por operação, ativo, venue e exposição agregada, mais kill switch;
- idempotência, reconciliação de ordens e posições, tratamento de timeouts e estado desconhecido;
- readiness, Risk Engine, RealModeGuard, autenticação do operador e restantes gates do projeto;
- confirmação humana apropriada antes de ativar REAL.

Nunca repetir cegamente uma ordem após timeout nem assumir que a posição num venue compensa automaticamente a posição noutro. Compras, vendas, cancelamentos, transferências e levantamentos são ações diferentes e exigem autorizações próprias. O sistema deve ser capaz de concluir que a oportunidade não é executável e não fazer nada.

## 7. Exploração de classes de ativos
O motor de descoberta pode avaliar crypto spot/perpetuals, FX/forex, NFTs e outras classes, mas cada classe requer conectores, dados, unidades, liquidez, custos e regras próprios. Não assumir que uma estratégia validada em cripto se transfere para FX ou NFTs. NFT marketplaces, por exemplo, têm liquidez irregular, custos e mecanismos de execução diferentes; devem ser tratados como uma linha de investigação independente.

Prioridade inicial recomendada: validar o pipeline com um universo limitado de mercados líquidos e dados públicos, antes de ampliar o número de venues/classes. Acrescentar mercados só quando a qualidade de dados, normalização e testes do conector forem suficientes.

## 8. Capital, agregação e risco
O objetivo de somar pequenas vantagens em vários venues deve ser avaliado por retorno líquido agregado, capacidade executável e risco conjunto — não por multiplicação aritmética de ganhos hipotéticos. O capital pode estar bloqueado, os sinais podem ser correlacionados, as taxas podem variar e as oportunidades podem desaparecer antes da execução. Manter separados available, locked, pending, withdrawable, posições, equity e custos. Nenhum saldo deve ser transferido automaticamente só para perseguir uma diferença temporal.

## 9. Veracidade da visualização
- Um personagem representa um agente/processo real e identificável ou deve ser claramente marcado como decoração.
- Movimento entre salas só deve refletir uma transição de tarefa/estado real.
- Indicadores de preço, PnL, latência e atividade devem mostrar origem, hora e frescura.
- Estado desconhecido, stale ou desconectado deve ser explícito.
- A interface pode reduzir animações, mas nunca alterar ou suspender silenciosamente o motor de risco para manter a cena fluida.

## 10. Critérios de aceitação
- [ ] Perfil Lite utilizável em hardware fraco, com limites de CPU/RAM e sem dependência de 3D.
- [ ] Perfil Standard e Advanced opcionais, com fallback automático/manual.
- [ ] A mesma atividade real é representada coerentemente no PC e numa vista móvel compacta.
- [ ] Salas de venue mostram frescura, estado de ligação, instrumentos e qualidade de dados.
- [ ] Lead-lag medido com timestamps explícitos e instrumentos normalizados.
- [ ] Simulação inclui taxas, spread, slippage, latência, liquidez e falhas.
- [ ] Relatórios mostram resultados fora da amostra, incerteza e condições de falha.
- [ ] Fast Execution não pode ultrapassar os gates de REAL nem operar a partir de sinais não validados.
- [ ] Nenhum personagem, agente, oportunidade, lucro ou execução é apresentado como real sem evidência.
