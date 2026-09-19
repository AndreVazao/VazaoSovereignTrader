# Controlo remoto PC + telemóvel

## Arquitetura

    Android APK
        |
        | private network (recommended: Tailscale)
        v
    PC_ENGINE API :8765
        |
        +--> Risk Engine
        +--> RealModeGuard
        +--> Order Manager
        +--> Binance/BingX APIs

As credenciais de exchange ficam exclusivamente no PC. O telemóvel nunca recebe API keys.

## Acesso remoto recomendado

Use Tailscale para criar uma rede privada entre o PC e o telemóvel.

No PC:
1. Instale Tailscale.
2. Inicie a tailnet.
3. Confirme o IP Tailscale.
4. Defina uma variável de ambiente forte chamada VST_LOCAL_TOKEN.
5. Inicie o trader.
6. Teste localmente antes de sair de casa.

No Android:
1. Instale Tailscale.
2. Entre na mesma tailnet.
3. Instale o APK.
4. URL do PC: http://100.x.y.z:8765.
5. Token: o mesmo definido no PC.

A rede privada fornece a camada de transporte. O header X-Token continua obrigatório.

## REAL

REAL permanece protegido por duas camadas:
1. Readiness do sistema;
2. autorização temporária do RealModeGuard com a frase EU ACEITO O RISCO.

O APK não pode contornar estas regras.

## 24/7 no Windows

Use scripts/install_windows_autostart.ps1 para criar uma tarefa de arranque. A tarefa reinicia o processo quando o PC reinicia; o engine continua a ter watchdog, recovery e SAFE_MODE.

Antes de ativar REAL:
- testar PAPER;
- validar preflight;
- confirmar ledger/recovery;
- validar dados e outcomes;
- confirmar permissões da API da exchange: Read + Spot Trade apenas;
- Withdraw desligado;
- Futures/leverage desligado.

Nunca abra a porta 8765 no router com port-forward.
