# PC — checklist de prontidão

## Instalação

1. Windows 10/11 com Python 3.11+.
2. Executar `scripts/setup_windows.ps1`.
3. Executar `scripts/configure_windows_secrets.ps1`.
4. Abrir uma nova PowerShell.
5. Executar `scripts/verify_pc_install.ps1`.

## PAPER obrigatório antes de REAL

- Confirmar `mode=PAPER`.
- Abrir `http://127.0.0.1:8765/dashboard`.
- Executar PREFLIGHT.
- LIGAR e deixar o collector trabalhar 24/7.
- Verificar `market_states.jsonl`, `state_signature_learning.jsonl` e `state_outcomes.jsonl`.
- Executar a validação PAPER.
- Não ativar REAL enquanto os gates de readiness estiverem bloqueados.

## REAL protegido

- API da exchange: Read + Spot Trade apenas.
- Withdraw desligado.
- Futures/leverage desligado.
- REAL exige readiness atual, preflight atual e autorização temporária.
- O PC é o único componente que possui chaves de exchange.
- O telemóvel só envia comandos autenticados; nunca recebe chaves da exchange.
- Se houver posições recuperadas no arranque, o sistema bloqueia a passagem para REAL até reconciliação manual.

## 24/7

Executar `scripts/install_windows_autostart.ps1` depois da verificação.
O watchdog/recovery continuam ativos. O PC deve permanecer ligado à internet.

## Comando remoto

Usar Tailscale entre PC e Android. Não fazer port-forward da porta 8765 no router.
O token `VST_LOCAL_TOKEN` continua obrigatório mesmo dentro da rede privada.

## Limite importante

Pronto para usar no PC significa **operacionalmente preparado**, não garantia de lucro nem validação económica de uma estratégia. REAL só deve ser usado depois de dados PAPER suficientes e dos gates passarem.
