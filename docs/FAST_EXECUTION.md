# Fast Execution

O Fast Execution Path é uma camada de baixa latência para oportunidades de lead/lag já validadas.

## Princípios

1. WebSocket/public market data é o caminho de entrada.
2. O Fast Path usa apenas conhecimento já aprendido e validado.
3. Eventos fora da janela temporal são rejeitados.
4. Confiança e expectativa líquida mínima são obrigatórias.
5. O Fast Path não chama LLM e não aprende durante a oportunidade.
6. A decisão passa sempre pelo `risk_check` fornecido pelo chamador.
7. O router não possui acesso próprio às exchanges.
8. Sem executor configurado, o resultado é apenas uma aceitação lógica — nenhuma ordem é enviada.

## Separação de responsabilidades

```text
WebSocket
   |
   v
FastPathEngine  ---> rejeita stale / sinal desconhecido
   |
   v
Risk Engine     ---> exposição, regime, limites, cooldown, modo
   |
   v
FastExecutionRouter
   |
   v
Order Manager / Executor
```

O Learning Engine permanece fora do caminho crítico. Ele atualiza estatísticas em background; o Fast Path consome somente sinais persistidos que já foram considerados elegíveis.

## Segurança

Esta camada não autoriza REAL, não contorna `RealModeGuard`, não altera limites de risco e não cria ordens por conta própria. A integração real deve fornecer explicitamente um executor depois de todas as verificações normais.
