# Controlled Restart/Recovery E2E — 2026-10-07

## Objetivo

Fechar a última lacuna entre a prova unitária de recuperação e a prova operacional de durabilidade: um `execution_intent` criado antes de um side effect externo deve sobreviver a uma morte de processo, ser recuperado por identidade exata e só desaparecer depois de uma reconciliação autoritativa.

Este ensaio é **100% controlado**. Não usa exchange real, não envia ordens reais, não movimenta capital e não usa serviços pagos.

## Cenário validado

1. Processo A grava um `execution_intent` durável em `SAFE_MODE`.
2. O processo A é tratado como terminado.
3. Processo B é criado a partir do mesmo `runtime_state.json`.
4. Um adapter controlado expõe uma ordem já aceite pela venue, identificada por `clientOrderId` exato.
5. A recuperação consulta a venue registada no intent e preserva venue, símbolo, lado, quantidade pedida e `client_order_id`.
6. O intent é convertido em `pending_order`; nenhuma execução é repetida.
7. A reconciliação consulta o `order_id` exacto, valida identidade, `filled`, custo e invariantes financeiras.
8. A transação de reconciliação é preparada de forma durável, aplicada e o journal é limpo.
9. A posição e os fluxos financeiros são reconstruídos.
10. Um novo restart não repete a ordem nem duplica efeitos.

## Evidência

Teste:
- `tests/test_controlled_restart_recovery_e2e.py`

Checkpoint:
- **12 passed in 6.67s** nos testes combinados: controlled restart/recovery E2E; controlled REAL runtime E2E; execution intent recovery; pending-order partial reconciliation.

A execução confirma lookup por `client_order_id` exato, identidade preservada, intent removido apenas após resolução, pending removido apenas após estado terminal autoritativo, posição reconstruída e restart posterior sem nova submissão.

## Segurança

Este teste não autoriza REAL.

A autorização REAL continua bloqueada por autorização humana explícita, `RealModeGuard`, `ExecutionGate`, preflight/readiness/reconciliação fresca e validação final imediatamente antes do adapter.

Qualquer UNKNOWN, identidade incompatível, venue indisponível, estado não terminal, dados financeiros inválidos ou evidência stale mantém o sistema fail-closed.

## Próximo gate

Com a durabilidade `execution_intent -> restart -> exact identity -> reconciliation` demonstrada em ambiente controlado, o próximo passo de release é reforçar a evidência do release gate final e manter a ativação REAL exclusivamente como ação explícita do operador. Nenhum teste deve executar uma ordem financeira real.