# Segurança operacional

## Regras obrigatórias

1. Começar em PAPER.
2. API keys das exchanges devem ter apenas:
   - leitura
   - spot trading
   - sem withdraw
3. Nunca usar futures/leverage na primeira fase.
4. Nunca guardar chaves reais no GitHub.
5. Nunca automatizar missões, quizzes, cupões, cliques ou UI das exchanges.
6. Verificar logs semanalmente.
7. Se houver drawdown forte, respeitar o KILL_SWITCH.

## Variáveis locais recomendadas

No Windows PowerShell:

```powershell
setx VST_LOCAL_TOKEN "troca-este-token"
setx BINANCE_KEY "valor-local"
setx BINANCE_PRIVATE "valor-local"
setx BINGX_KEY "valor-local"
setx BINGX_PRIVATE "valor-local"
```

Fecha e reabre o terminal depois do `setx`.

## Passagem para REAL

Antes de REAL:

- pelo menos 14 dias em PAPER
- logs sem erros graves
- drawdown semanal controlado
- saldo pequeno na exchange
- API sem withdraw

Trocar para REAL com o motor parado.
