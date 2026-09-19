# VazaoSovereignTrader Mobile

Cockpit Android para controlar o PC_ENGINE à distância.

## Segurança

- O APK não contém chaves Binance/BingX.
- O APK só envia comandos para a API do PC.
- O PC continua a ser o único executor.
- Para acesso remoto, use uma rede privada como Tailscale. Não exponha a porta 8765 diretamente à Internet.
- O token deve ser definido no PC através de VST_LOCAL_TOKEN; não use o valor de exemplo.

## Configuração

1. Instale Tailscale no PC e no Android e entre na mesma tailnet.
2. No PC, obtenha o IP Tailscale (normalmente 100.x.y.z).
3. No APK, coloque http://100.x.y.z:8765.
4. Coloque o mesmo VST_LOCAL_TOKEN no campo Token.
5. Comece sempre em PAPER.
6. Para REAL, execute a validação no PC e só depois use ARM REAL + a frase exata de confirmação.

## Build

O workflow android-apk.yml gera o APK como artefacto do GitHub Actions. Também é possível compilar localmente com Buildozer.
