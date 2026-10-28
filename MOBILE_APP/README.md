# VazaoSovereignTrader Mobile

Cockpit Android para controlar o PC_ENGINE à distância.

## Candlestick Pattern Library

A camada PAPER de candlesticks foi expandida e alinhada com a camada de evidência. O detector cobre reversões, indecisão e continuação, incluindo engulfing, harami, tweezers, piercing/dark cloud, stars, three soldiers/crows e rising/falling three methods.

Os padrões são features contextuais e passam por custos, confluence, evidence e Risk Engine. Não autorizam ordens nem REAL.

Documentação: docs/CANDLESTICK_PATTERN_LIBRARY.md.

## Segurança

- O APK não contém chaves Binance/BingX.
- O APK só envia comandos para a API do PC.
- O PC continua a ser o único executor.
- Para acesso remoto, use uma rede privada como Tailscale. Não exponha a porta 8765 diretamente à Internet.
- O token deve ser definido no PC através de VST_LOCAL_TOKEN; não use o valor de exemplo.

## Configuração

O endpoint do PC é guardado no armazenamento privado da aplicação após uma ligação bem-sucedida. O token não é persistido; após reiniciar a aplicação, introduz o token manualmente. A aplicação volta a tentar comunicar enquanto estiver aberta.

Para o assistente de configuração inicial por USB e o estado exato das funcionalidades, consulta [Android first pairing](../docs/ANDROID_FIRST_PAIRING.md).

1. Instale Tailscale no PC e no Android e entre na mesma tailnet.
2. No PC, obtenha o IP Tailscale (normalmente 100.x.y.z).
3. No APK, coloque http://100.x.y.z:8765.
4. Coloque o mesmo VST_LOCAL_TOKEN no campo Token.
5. Comece sempre em PAPER.
6. Para REAL, execute a validação no PC e só depois use ARM REAL + a frase exata de confirmação.

## Build

O workflow android-apk.yml gera o APK como artefacto do GitHub Actions. Também é possível compilar localmente com Buildozer.


## Intervenção humana remota

Quando o PC encontrar login, 2FA/OTP, CAPTCHA ou outra interação humana, o pedido aparece automaticamente no cockpit do telefone quando a ligação Tailscale estiver disponível. O navegador continua aberto no PC e a intervenção é aplicada nessa sessão.

- O pedido é persistente no PC, por isso não se perde se o telefone estiver offline.
- O telefone não precisa de estar ligado quando o pedido é criado.
- Passwords/OTP introduzidos no telefone são enviados apenas para a intervenção atual e não são gravados pelo Human Interaction Bridge.
- CAPTCHA é resolvido manualmente pelo utilizador; não existe bypass.


## Readiness PAPER

O cockpit pode consumir a readiness autenticada do PC para acompanhamento remoto. A readiness é informativa e PAPER-only: histórico, tendência temporal e scorecard não autorizam execução REAL.

Endpoints de diagnóstico disponíveis no PC:
- /readiness/history
- /readiness/trend
- /readiness/scorecard
- /readiness/timeline

A autenticação continua a usar VST_LOCAL_TOKEN e o acesso remoto recomendado é Tailscale.


## Startup diagnostics and mobile release gate

The current cockpit keeps a canonical status model separate from the per-page status labels, avoiding Kivy widget re-parenting when navigating between lazily-created pages. The chat scroll view is explicitly retained for auto-scroll. If cockpit construction raises a Python exception, the app now shows a small diagnostic screen instead of silently closing; it records the exception class and traceback frames in the app's private `startup_error.log` when storage is available. The log is local-only and is not sent to the PC. The diagnostic screen includes a retry action.

The Android workflow now runs source syntax/structure checks before Buildozer. These checks and a successful APK build do **not** prove that the APK launches on a physical phone; the user-reported immediate crash still requires a fresh APK plus Android launch/logcat smoke test before installation is considered ready.


## Escritório virtual offline (protótipo móvel)

A página **Escritório** pode ser aberta sem ligar ao PC_ENGINE. É uma demonstração local para testar navegação, dimensões e legibilidade no telefone; não mostra preços, P&L, ordens nem agentes reais e não envia comandos ao motor.

Perfis disponíveis:
- **2.5D leve** — cartões de departamentos.
- **Pixel / 8-bit** — representação textual em blocos.
- **Palitinhos** — representação simplificada.
- **Compacta** — cartões menores para ecrãs apertados.
- **HD 3D (futuro)** — opção de pré-visualização que faz fallback para 2.5D, porque um renderer 3D real ainda não está incluído.

A planta inclui CEO, Market Radar, Comparação de Exchanges, Investigação, Análise, Memória Central, Resposta Rápida, Controlo de Risco e PAPER Lab. Esta versão serve para validar o fluxo visual básico offline; não prova o desempenho num telefone físico nem substitui os testes de arranque/logcat do APK.


## Virtual office rendering profiles

The office starts in **2.5D leve** and stores the chosen visual profile only in the app's private local storage (office_preferences.json). Supported profiles are 2.5D leve, Pixel/8-bit, Palitinhos and Compacta. **HD 3D is a future placeholder**, not a real renderer; it falls back to 2.5D. If the local preference cannot be read or written, the cockpit continues with the lightweight default. This preference does not enable the brain, networking, market feeds or trading. The physical Android device still needs a USB/ADB install, launch and logcat check before release readiness can be claimed.
