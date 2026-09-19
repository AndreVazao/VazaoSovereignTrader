# Remote Human Interaction Bridge

Quando o navegador do PC ficar bloqueado por uma interação humana — login, palavra-passe, 2FA/OTP, consentimento, CAPTCHA ou outro desafio — o Trader cria um pedido no Human Interaction Bridge. O pedido fica disponível no cockpit Android através da API privada Tailscale.

O PC não precisa que o telefone esteja ligado quando o pedido é criado. O telefone também não precisa de estar ligado nesse momento. O pedido é persistido como metadados e fica pendente até existir comunicação.

## Segurança

- Passwords, OTPs e outros segredos não são gravados em disco pelo bridge.
- A resposta sensível permanece apenas em RAM até ser consumida pelo processo do PC.
- O telefone não recebe chaves de exchange.
- Tailscale é o canal recomendado; não expor a API diretamente à Internet.
- CAPTCHA/2FA são realizados pelo humano; não existe bypass de mecanismos anti-bot.
- O navegador continua no PC. O telefone é o painel remoto para a intervenção humana.

## Estados

PENDING -> RESPONDED -> CONSUMED, ou PENDING -> CANCELLED.

A fila persistente permite que PC e telefone desapareçam temporariamente da rede sem perder o pedido. O conteúdo secreto de uma resposta não é recuperável depois de o processo do PC terminar; o utilizador volta a introduzi-lo se necessário.

## Tipos previstos

LOGIN, OTP, CAPTCHA, APPROVAL e CUSTOM.

## Integração do navegador

O browser collector/executor deve criar um pedido quando deteta que não consegue prosseguir sem uma pessoa. Depois de receber a resposta, deve aplicar a ação localmente na mesma sessão Playwright. A sessão persistente por plataforma permite continuar sem reiniciar o fluxo.

O bridge é um control-plane, não um cofre de segredos e não um bypass de CAPTCHA.
