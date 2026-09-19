# Build e instalação

## PC Windows

O workflow Windows EXE pode ser executado manualmente em GitHub Actions ou por uma tag pc-vX.Y.Z.

Artefacto: VazaoSovereignTrader-Windows.zip.

O ZIP contém o EXE e a configuração de exemplo. O primeiro arranque deve ser PAPER e o token VST_LOCAL_TOKEN deve existir no ambiente do PC.

O dashboard fica no próprio PC em http://127.0.0.1:8765/dashboard.

## Android

O workflow Android APK pode ser executado manualmente ou por uma tag mobile-vX.Y.Z. O APK é publicado como artefacto.

O Android liga ao PC através do IP Tailscale do PC na rede privada. Não expor a porta do Trader diretamente à Internet.

## Operação fora de casa

PC ligado e sem suspensão. Tailscale ligado no PC e no telefone. O APK usa o endpoint privado do PC.

Fluxo:
telefone -> Tailscale -> API do PC -> engine.

O telefone não guarda chaves de exchange nem executa trades; é cockpit de comando.

## Regras de operação

PAPER primeiro. REAL só depois de validação estatística, replay/PAPER e revisão do Risk Engine.
