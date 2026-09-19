# State Signature Learning

Converte Market State em assinaturas discretas e aprende resultados históricos em PAPER.

Hierarquia: assinatura completa -> regime/trend/volatility/action -> regime/action -> regime.

A elegibilidade exige amostras mínimas, média líquida positiva, win rate mínimo e lower bound de 95% positivo. Não altera limites de risco, não ativa REAL e não executa ordens.

Executar: python PC_ENGINE/tools/run_state_signature_learning.py
