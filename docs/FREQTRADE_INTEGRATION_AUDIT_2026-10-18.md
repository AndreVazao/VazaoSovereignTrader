# Auditoria Freqtrade para integração isolada no VazaoSovereignTrader
Data da análise: 2026-10-18
Estado: proposta técnica/documental; nenhum código de trading foi alterado nem executado.

## Decisão executiva

**Não incorporar o Freqtrade inteiro dentro do motor principal do Sovereign Trader.** Aproveitar os padrões técnicos, o contrato CCXT, os mecanismos de backtesting/dry-run, o tratamento de limitações de exchanges e as ideias de proteção. O Sovereign Trader mantém-se como cérebro soberano de observação, lead/lag, arbitragem entre venues, evidência fora da amostra, gestão de risco e autorização.

A cópia privada `AndreVazao/freqtrade` está licenciada GPL-3.0 e o seu `pyproject.toml` identifica o pacote como Freqtrade, dependente de CCXT, pandas, SQLAlchemy, FastAPI e outros. Copiar ou integrar código-fonte diretamente no repositório principal pode impor obrigações de distribuição GPL a uma obra derivada. Fazer uma revisão de licenciamento antes de qualquer cópia; este documento recomenda reutilização de conceitos e interoperabilidade, não copiar módulos GPL para o core.

## O que foi verificado no repositório Freqtrade

- Repositório privado `AndreVazao/freqtrade`, branch por omissão `main`, licença GPL-3.0.
- `README.md`: estratégia Python, download de OHLCV, backtesting, hyperopt, dry-run, WebUI/Telegram e lista de exchanges spot/futures.
- `pyproject.toml`: Python >=3.11; dependência `ccxt`; pacote opcional de ferramentas de desenvolvimento e testes.
- `freqtrade/exchange/exchange.py`: camada de abstração de exchanges baseada em CCXT, configuração por exchange, validação de funcionalidades, gestão de ordem/livro de mercado e código de integração assíncrona.
- `freqtrade/exchange/__init__.py`: registo de implementações específicas de exchanges.
- `freqtrade/resolvers/exchange_resolver.py`: resolução de classes de exchange específicas com fallback para classe genérica.
- `docs/exchanges.md`: tratamento de diferenças por exchange e rate limits; aconselha a manter rate limiting e documenta que o suporte real varia.
- `docs/configuration.md`: configuração por ficheiro/ambiente e utilização de WebSocket/REST conforme suporte.
- `freqtrade/rpc/api_server`: API local para operações e monitorização do bot; não deve ser exposta publicamente sem controlos de segurança.
- A documentação oficial recomenda começar em Dry-run e alerta que backtesting assume fills e não substitui o forward test.

Fontes:
- Repositório auditado: https://github.com/AndreVazao/freqtrade
- Código da exchange: https://github.com/AndreVazao/freqtrade/blob/main/freqtrade/exchange/exchange.py
- Resolver: https://github.com/AndreVazao/freqtrade/blob/main/freqtrade/resolvers/exchange_resolver.py
- Configuração: https://github.com/AndreVazao/freqtrade/blob/main/docs/configuration.md
- Notas das exchanges: https://github.com/AndreVazao/freqtrade/blob/main/docs/exchanges.md
- Documentação oficial: https://docs.freqtrade.io/en/latest/
- Backtesting e limitações: https://docs.freqtrade.io/en/latest/backtesting/
- CCXT vs Freqtrade: https://docs.ccxt.com/docs/comparisons/ccxt-vs-freqtrade
- Licença GPL-3.0: https://github.com/AndreVazao/freqtrade/blob/main/LICENSE

## O que vale a pena aproveitar

### 1. Padrões de conector CCXT
- Configuração por venue e normalização de símbolos/mercados.
- Descoberta de capacidades por exchange, em vez de presumir que todos suportam os mesmos tipos de ordem/dados.
- Respeito por rate limits, backoff, timeouts, reconexões e falhas transitórias.
- REST para snapshots/reconciliação e WebSocket para streams quando suportados.
- Tratamento explícito de precisão, mínimos de ordem, limites e diferenças spot/futures.
- Separação entre mercado público, estado de conta e operações privadas.

O Sovereign Trader já se descreve no README como preparado para Binance/BingX via CCXT e tem um Sovereign Market Radar observacional. Portanto, o primeiro trabalho é comparar os contratos e capacidades existentes, não adicionar outra camada CCXT em paralelo.

### 2. Validação de estratégia
Freqtrade fornece um bom conjunto de ideias para backtesting reproduzível, dry-run/forward testing, download de dados, análise de lookahead e análise de indicadores recursivos. Devemos aplicar os princípios à nossa evidência e ao nosso motor de resultados, não substituir os testes cronológicos, a análise de relações líder-seguidor e os mecanismos de risco já existentes.

**Limite importante:** o backtesting padrão do Freqtrade é orientado principalmente a candles/estratégias de pares. Não é, por si só, um motor pronto de arbitragem simultânea cross-exchange com duas pernas, inventário pré-financiado, latência real, fills parciais e risco de execução atómica. O nosso motor precisa de manter esse problema separado.

### 3. Proteções e operational hardening
Reaproveitar os princípios, após revisão do código próprio:
- rate limiting e retries limitados;
- timeouts e estado desconhecido tratado em segurança;
- validação de configuração;
- reconciliação do estado das ordens quando houver integração futura;
- limites por mercado e proteção contra dados obsoletos;
- dry-run explícito, persistência local e auditoria.

Não reutilizar o mecanismo de execução de Freqtrade como autorização para contornar a fronteira de execução do Sovereign Trader.

## Arquitetura proposta

```text
CCXT / APIs públicas de exchange
          |
          v
VST Market Data Adapters (read-only primeiro)
          |
          v
Canonical Market Events
(exchange, instrument, bid/ask/depth, exchange_ts,
 receive_ts, sequence, freshness, quality)
          |
          +--> Lead/Lag Radar
          +--> Executable Cross-Venue Edge
          +--> PAPER Outcome Ledger
          +--> Chronological OOS / cost / regime evidence
          |
          v
Sovereign Risk Engine
          |
          v
Execution Boundary — DISABLED by default
```

Freqtrade deve ser um processo opcional e isolado apenas se uma avaliação posterior provar que as suas funções de backtesting/estratégia acrescentam valor sem duplicar o core. Se executado como processo externo, usar diretório de dados próprio, configuração própria, portas locais limitadas e nenhum segredo real por omissão. Não expor a API Freqtrade à rede nem permitir que ela autorize o modo REAL do Sovereign Trader.

## Plano incremental sem quebrar o projeto

1. **Baseline e inventário (próximo passo):** quando o PC de desenvolvimento estiver online, verificar o estado Git local, as alterações pendentes, os commits e a suite de testes antes de editar.
2. **Mapa de capacidades:** comparar os adaptadores CCXT existentes com as funções relevantes de Freqtrade; identificar lacunas reais e evitar dependências duplicadas.
3. **Contrato de evento canónico:** assegurar que os dados normalizados incluem timestamp da exchange e receção local, bid/ask, profundidade, sequence/update ID, frescura, fonte e qualidade.
4. **Read-only adapter:** testar um venue de cada vez com dados públicos, sem API keys privadas, sem criar ordens e sem mexer no estado de execução.
5. **Testes de contrato:** fixtures offline para símbolos, rate limit, timeout, dados obsoletos, reconexão, order book incompleto e diferença entre snapshot e stream.
6. **Comparação PAPER:** executar lado a lado, sem execução real, e medir frescura, cobertura, latência e divergência com a fonte atual.
7. **Decisão de dependência:** só depois decidir se CCXT já instalado basta, se é útil correr Freqtrade isolado para backtesting de candles, ou se nenhuma integração adicional é necessária.
8. **Licenciamento e segurança:** qualquer código copiado de Freqtrade exige revisão GPL; nenhum segredo no Git, nenhuma chave com permissão de levantamento e nenhuma alteração ao bloqueio REAL.

## Critérios de aceitação

- Nenhum módulo atual de radar/risco/execução é substituído.
- Nenhuma ordem, cancelamento, depósito ou transferência.
- Dados stale, incompletos ou não comparáveis resultam em `NO_EDGE`.
- A indisponibilidade do adaptador não impede o core local de arrancar.
- Testes offline e de segurança passam antes de qualquer merge.
- Freqtrade não pode contornar o Risk Engine nem a autorização humana.
- O benefício tem de ser demonstrado por dados medidos, não por quantidade de exchanges listadas.

## Estado deste incremento

- Auditoria documental do repositório e da documentação oficial concluída.
- Nenhum código Freqtrade foi copiado para o Sovereign Trader.
- Nenhuma chave de API foi lida ou solicitada.
- Nenhuma exchange foi contactada e nenhuma operação financeira foi efetuada.
- PC de desenvolvimento estava offline durante esta sessão; não foi possível validar ou modificar a working tree local nem executar testes localmente.
- Esta proposta está preparada para revisão num pull request documental. O código só deve ser alterado depois de o PC voltar a estar acessível e o estado local ser confirmado.
