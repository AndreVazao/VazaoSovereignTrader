# Controlo remoto PC + telemóvel — estado e limites

## Estado atual

A ligação PC ↔ Android através de Tailscale é a arquitetura pretendida, mas a descoberta automática, o emparelhamento e o controlo remoto ainda não estão certificados de ponta a ponta nesta versão. O APK e o escritório virtual não devem ser tratados como prova de que a ligação operacional está concluída.

Validar primeiro o backend local no PC. Não expor a API na Internet nem fazer port-forward da porta 8765.

## Arquitetura pretendida

```text
Android cockpit
      |
      | Tailscale / rede privada autenticada
      v
PC_ENGINE API :8765
      |
      +--> estado e comandos PAPER
      +--> Risk Engine / persistência / diagnóstico
      +--> fontes públicas de market data (read-only)
```

O telefone é um cockpit de observação e comando. Não recebe chaves de exchange nem executa operações financeiras. A cloud não deve transportar ordens nem ser necessária para o motor local continuar a funcionar.

## Pré-requisitos locais no PC

1. Instalar e validar o backend local.
2. Gerar `VST_LOCAL_TOKEN` com `scripts/ensure_windows_token.ps1`, ou definir um valor próprio com `scripts/configure_windows_secrets.ps1`.
3. Confirmar `GET /health` em `http://127.0.0.1:8765/health`.
4. Confirmar que os endpoints autenticados rejeitam pedidos sem token.
5. Manter o engine em PAPER e a API ligada a loopback durante a validação inicial.

## Emparelhamento Android/Tailscale

Quando o cliente e a descoberta estiverem validados:

1. Instalar Tailscale no PC e no Android e juntá-los à mesma tailnet.
2. Confirmar a identidade do dispositivo por um mecanismo confiável; um header enviado pelo cliente não prova identidade Tailscale.
3. Usar o endereço privado do PC e o token local através do canal autenticado.
4. Testar reconexão, expiração de sessão, dispositivo não autorizado e perda de rede.
5. Não declarar o controlo remoto pronto até os testes físicos PC/Android passarem.

## Arranque 24/7 no Windows

O instalador empacotado não cria tarefas agendadas nem inicia serviços automaticamente. Primeiro validar o arranque manual, o health check, o collector e a recuperação.

Para instalações a partir do código-fonte, `scripts/install_windows_autostart.ps1` é um opt-in separado que cria tarefas de arranque para o engine e o collector. Só executar depois de validação física bem-sucedida e decisão explícita do operador.

## Limites de segurança atuais

- PAPER-only; não ativar REAL/LIVE.
- Não configurar chaves privadas nem permissões de trading.
- Não executar ordens, transferências ou levantamentos.
- Não contornar autenticação, MFA, prompts ou políticas Tailscale.
- Não abrir a porta 8765 publicamente.
