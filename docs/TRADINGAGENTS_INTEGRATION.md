# Integração futura com TradingAgents

A repo TradingAgents analisada tem interesse como módulo de análise/aconselhamento no PC, mas não deve ser usada como executor de ordens nem colocada no APK.

## Regra de arquitetura

```text
TradingAgents pensa.
Risk Engine decide.
Executor age.
```

## Uso recomendado

- Módulo opcional `PC_ENGINE/ai_council/`.
- Começa desligado por configuração.
- Produz apenas rating e explicação:
  - Buy
  - Overweight
  - Hold
  - Underweight
  - Sell
- Nunca executa ordens diretamente.

## Porquê não no APK

- Dependências pesadas.
- Consumo de bateria.
- Dependência de LLM/API externa.
- APK deve continuar a ser cockpit leve.

## Futuro adapter

```text
PC_ENGINE/ai_council/
├── tradingagents_adapter.py
├── decision_mapper.py
└── memory_bridge.py
```

O output entra no alocador apenas como peso adicional, nunca como ordem obrigatória.
