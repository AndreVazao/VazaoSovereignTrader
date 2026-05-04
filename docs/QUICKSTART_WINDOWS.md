# Quickstart Windows 10

## 1. Instalar

Na raiz da repo, dá duplo clique em:

```text
scripts/windows_setup.bat
```

Isto cria o ambiente Python, instala dependências e cria `PC_ENGINE/config/config.local.json` se ainda não existir.

## 2. Arrancar o PC_ENGINE

Dá duplo clique em:

```text
scripts/windows_run_pc_engine.bat
```

Depois abre no browser:

```text
http://127.0.0.1:8765/dashboard
```

O painel vai pedir o token local configurado na variável de ambiente `VST_LOCAL_TOKEN`. Se ainda não definiste, usa o valor default apenas para testes locais e altera antes de usar em rede.

## 3. Preflight

No dashboard, carrega em:

```text
PREFLIGHT
```

O motor verifica exchanges, símbolos, tickers e regras de mercado.

## 4. Iniciar em PAPER

No dashboard:

```text
INICIAR
```

O modo default é PAPER.

## 5. Backtest rápido BTC

Dá duplo clique em:

```text
scripts/windows_backtest_btc.bat
```

Isto usa candles públicos da Binance e imprime um replay simples com P&L, trades, wins/losses, drawdown e profit factor.

## 6. Segurança

Antes de REAL:

- rodar PAPER pelo menos 14 dias;
- confirmar preflight sem erros;
- validar backtests;
- usar API com withdraw desligado;
- não usar futures/leverage na fase inicial.
