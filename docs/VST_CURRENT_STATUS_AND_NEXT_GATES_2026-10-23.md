# VST — estado consolidado e próximos gates

Data: 2026-10-23  
Projeto: Vazão Sovereign Trader (VST)  
Branch-base: `main`

## Objetivo

Registar um checkpoint operacional conciso depois da consolidação recente do parser/sincronizador OKX e da identidade visual VST. Este documento complementa — não substitui — a auditoria de integração existente e não certifica execução em dispositivos reais.

## O que está presente no código/documentação

- **Marca VST:** o README e os documentos de marca identificam Vazão Sovereign Trader como VST; existem fontes SVG para o logótipo e para o ícone compacto. A exportação para PNG/ICO e Android adaptive icon continua por integrar no processo de empacotamento.
- **Dados de mercado:** existem coletores e componentes de reconstrução/sincronização de livros. O sincronizador OKX está em `PC_ENGINE/market_events/okx_book_sync.py`; deve continuar a falhar de forma segura quando sequência, símbolo, validade ou frescura não são fiáveis.
- **Erros de feed:** a evolução recente inclui invalidação perante mensagens malformadas e proteções de sequência/tempo para Coinbase, além de tratamento específico de heartbeat OKX. A presença de código e testes não prova conectividade contínua com exchanges.
- **Avaliação de edge:** o adaptador tipado para avaliação PAPER exige mapeamento explícito de instrumento e unidade de preço. Um preço parecido, um símbolo igual ou uma cotação comum não demonstram equivalência económica.
- **Papel do radar:** observações de trades, top-of-book e depth são capacidades distintas. A receção de mensagens não prova um livro sincronizado; um livro sincronizado não prova que uma oportunidade sobreviva a taxas, spread, slippage, latência e execução.
- **Dispositivos:** a integração real no Windows e Android continua a precisar de evidência obtida nos dispositivos/ambientes-alvo. O estado do cockpit não deve mostrar “ligado” ou “saudável” sem evidência do backend correspondente.

## Gates prioritários

### G1 — Qualidade de dados

- Executar a suite Python no SHA exato candidato a integração.
- Verificar regressões para snapshots antigos, lacunas/duplicados de sequência, dados futuros ou stale, mensagens inválidas, desconexão e recuperação.
- Confirmar que a perda de validade limpa imediatamente a elegibilidade do livro.
- Não habilitar sinais de depth para qualquer venue sem fixtures de protocolo e recuperação adequadas.

### G2 — Instrumentos e edge

- Exigir mapeamento explícito de venue, símbolo, spot/derivativo, ativo base/quote, settlement e multiplicador de contrato quando aplicável.
- Rejeitar comparação entre unidades de preço incompatíveis sem conversão separada e validada.
- Incluir custos e latência realista; desconhecido deve permanecer desconhecido, não convertido em zero.
- Manter avaliação em PAPER/read-only; nenhum resultado de pesquisa deve autorizar ordens por si só.

### G3 — Aplicação e dispositivos

- Integrar os formatos finais de ícone nos alvos reais de empacotamento.
- Testar arranque, paragem, reinício, perda/recuperação de rede e estado de saúde no Windows.
- Testar o cliente Android e a ponte ADB/emulador no ambiente-alvo, registando logs e resultado reproduzível.
- Separar visualização demonstrativa, conectividade real e prontidão operacional.

### G4 — Recuperação e higiene de branches

- Manter PR #485 aberto até rever e integrar os três documentos recuperados: escritório virtual/pesquisa de mercado, roadmap e cockpit conversacional remoto.
- Comparar o conteúdo dos ficheiros, não apenas o número de commits, antes de eliminar branches antigas.
- Não apagar branches com diferenças funcionais ou documentais ainda não avaliadas.
- Branches sem commits exclusivos face a `main` são candidatas à limpeza depois de confirmar que não há trabalho por recuperar noutros locais.

## Evidência e limites

Este checkpoint é uma síntese de código/documentação disponível no repositório. Não afirma que a suite foi executada neste checkpoint, que exchanges estão atualmente ligadas, que Windows/Android passaram E2E, nem que existe rentabilidade comprovada. Esses estados só podem ser promovidos com evidência verificável do commit e do ambiente correspondentes.

## Critério de saída

O VST mantém-se em **PAPER/read-only** até que os gates relevantes tenham evidência registada. A ativação de execução REAL exige uma revisão separada de autorização, risco, idempotência, limites, reconciliação e comportamento de falha; não faz parte deste checkpoint.
