# Mobile Chat Cockpit — 2026-10-08

## Objetivo

O Android deixa de ser apenas um painel de botões e passa a ser o cockpit conversacional do VazaoSovereignTrader, inspirado na ergonomia do ChatGPT:

- sidebar compacta;
- área central de conversa;
- composer de mensagem com envio;
- entrada por voz com transcrição Android para texto;
- páginas separadas para PC, ficheiros, intervenção humana e readiness;
- ligação Tailscale/privada continua a ser o transporte recomendado;
- PAPER continua a ser o modo padrão.

## Arquitetura

Fluxo:

Android UI → token de dispositivo → `POST /assistant/message` → `OperatorAssistantGateway` → superfície existente do PC.

O gateway é uma camada de intenção determinística e **não** é um novo executor de trading.

### Intenções suportadas

- `RESEARCH`: mensagens com linguagem de investigação ou URLs entram na fila `TraderResearchInbox`.
- `STATUS`: perguntas sobre estado/saldo/equity/risco são somente leitura.
- `START`, `PAUSE`, `RESUME`, `STOP`: controlos explícitos são encaminhados para os métodos existentes do engine e continuam sujeitos aos scopes atuais.
- `CHAT`: mensagens não classificadas recebem orientação sobre o que o cockpit consegue fazer.
- `REAL_BLOCKED`: linguagem que peça REAL/live/capital real é recusada; a conversa nunca cria autorização REAL.

## Token móvel

Os dispositivos emparelhados recebem:

- `read_private_state`
- `trade_paper`
- `respond_human_interaction`
- `submit_research`

Não recebem `trade_real` nem permissões de gestão de contas de exchange.

O token de dispositivo continua protegido pelo Android Keystore. O token proprietário continua temporário durante o emparelhamento.

## Voz

A UI usa o Android Speech Recognizer através de `pyjnius`.

- idioma inicial: `pt-PT`;
- o áudio não é enviado diretamente para o PC pelo cockpit;
- a fala é convertida em texto no telefone;
- o texto entra no mesmo composer do chat;
- o utilizador confirma/envia como qualquer outra mensagem.

A build requer `RECORD_AUDIO`.

## Ficheiros

A sidebar mantém a troca segura:

- INBOX = Android → PC;
- OUTBOX = PC → Android;
- sem caminhos arbitrários;
- nomes saneados;
- SHA-256 e limites de upload permanecem no bridge existente.

## Intervenção humana

Login, 2FA, CAPTCHA e confirmações continuam a aparecer no Human Bridge.

Não existe bypass automático.

## Limite deliberado da versão

Esta versão **não finge ter compreensão geral de um LLM**. O gateway atual é determinístico e seguro: entende um conjunto explícito de intenções operacionais e encaminha investigação para o cérebro/worker já existente.

A evolução natural é ligar um modelo conversacional ao mesmo gateway, mantendo o gateway como fronteira de segurança: o modelo poderá interpretar a intenção, mas nunca poderá ultrapassar scopes, gates, SAFE_MODE, autorização REAL ou reconciliação.

## Segurança

- Nenhuma ação REAL é criada pelo chat.
- A UI móvel não recebe credenciais de exchange.
- O PC continua a ser a autoridade de execução.
- UNKNOWN/ambiguidade/reconciliação continuam a ser tratados pelo núcleo existente.
- O gateway não cria uma segunda rota de envio de ordens.

## Validação 2026-10-08

- `py_compile`: main/UI/gateway/server/mobile pairing — passou.
- Gateway + mobile pairing + API: **14 testes passaram**.
- `git diff --check`: passou.
- APK ainda requer build CI e validação física no Redmi Note 15 quando voltar a estar disponível por ADB.
