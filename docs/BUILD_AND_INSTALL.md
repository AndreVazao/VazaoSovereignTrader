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


## Ponte de intervenção humana

O PC e o telefone são independentes. Se o PC encontrar um login, 2FA/OTP, CAPTCHA ou outra barreira humana, cria um pedido persistente no Human Interaction Bridge. Quando o telefone estiver disponível através da Tailscale, mostra o pedido e envia a intervenção de volta ao PC.

A fila de pedidos é persistente, mas dados sensíveis não são: passwords, OTPs e outros segredos enviados pelo telefone ficam apenas em RAM no processo do PC até serem consumidos. O browser mantém a sessão local no PC. CAPTCHA/2FA são sempre intervenção humana normal, sem bypass.
