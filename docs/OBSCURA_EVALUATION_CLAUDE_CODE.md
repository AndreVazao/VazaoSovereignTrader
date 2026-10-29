# Sovereign Trader — Plano autónomo de auditoria local e avaliação da Obscura

**Objetivo:** quando este documento for entregue ao Claude Code no PC do utilizador, executar uma auditoria local repetível do VazaoSovereignTrader e uma comparação técnica entre Obscura e Chromium + Playwright. Produzir evidências e um relatório Markdown na branch de trabalho, depois sincronizar os resultados com o GitHub.

**Estado deste documento:** plano de execução; não é prova de que os testes locais foram executados. Não declarar nenhum resultado antes de o medir.

## 0. Regras de execução autónoma

Trabalha autonomamente, sem pedir confirmação a cada passo, dentro do âmbito abaixo. Primeiro inspeciona o repositório, as instruções locais e o estado do Git. Cria um plano curto e executa-o até ao fim. Em caso de falha, recolhe diagnóstico, tenta uma alternativa segura e continua os restantes testes. Não fiques bloqueado por um teste que não possa ser realizado.

Não pedir ao utilizador autorização repetidamente para operações normais e reversíveis de diagnóstico, instalação de dependências de desenvolvimento, execução de testes, criação de diretórios temporários, captura de logs, instalação de um APK de desenvolvimento no dispositivo explicitamente ligado e criação de commits na branch de trabalho dedicada a esta auditoria.

**Não contornar** prompts de segurança do sistema operativo, permissões Android/ADB, autenticação MFA/CAPTCHA, políticas de rede ou controlos de acesso. Se uma autorização privilegiada, segredo, dispositivo ou confirmação de segurança for realmente indispensável, não a simules nem a contornes: regista o bloqueio, executa os testes restantes e continua. Não solicitar segredos ao utilizador no chat.

### Limites de segurança obrigatórios

- Sovereign Trader permanece em PAPER/read-only. Não ativar live trading, não submeter ordens, não movimentar fundos e não testar levantamentos.
- Não usar credenciais reais nas suites automáticas ou em CI.
- Não escrever palavras-passe, API keys, tokens, cookies, cabeçalhos de autenticação ou dados pessoais em logs, screenshots, artefactos ou relatórios.
- Não copiar perfis de browser autenticados para o Git, para a cloud ou para o telemóvel.
- Não desativar controlos de segurança para conseguir um teste verde.
- Não fazer merge de alterações de código automaticamente. Publicar numa branch dedicada e abrir/atualizar PR apenas se apropriado.
- Nunca sobrescrever alterações locais do utilizador. Se a working tree estiver suja, inspecionar e preservar; não usar reset --hard, clean -fd, checkout destrutivo ou stash/pop sem avaliar consequências.
- Não declarar um teste aprovado sem evidência reproduzível. Distinguir PASS, FAIL, BLOCKED e NOT RUN.

## 1. Preparação e sincronização GitHub → PC

1. Confirmar o repositório correto: `AndreVazao/VazaoSovereignTrader`.
2. Inspecionar `git status --short --branch`, branch atual, remotes, commits locais e alterações não commitadas.
3. Ler as instruções do projeto (incluindo `AGENTS.md`, `CLAUDE.md`, README e docs relevantes, caso existam).
4. Consultar GitHub e confirmar o estado atual de `main`, PRs e checks. Não confiar apenas nos SHAs fixados neste documento; este documento pode ficar desatualizado.
5. Sincronizar a branch de trabalho com o código validado atual sem destruir alterações locais. Preferir fetch e uma branch nova a operações destrutivas. Não integrar alterações de uma PR que ainda não esteja mergeada ou validada.
6. Criar/usar uma branch com nome semelhante a `test/obscura-local-audit-YYYY-MM-DD`, baseada na versão validada mais recente de `main`.
7. Registar SHA inicial, sistema operativo, arquitetura, versão Python, Node (se necessário), Git, ADB e Tailscale. Redigir segredos e identificadores sensíveis.

## 2. Inventário do Sovereign Trader

Inspecionar e documentar, com caminhos de ficheiros reais:

- Browser manager, connectors e Playwright PAPER adapter.
- Configuração de headless/headed e perfis persistentes.
- API/backend, autenticação, memória de aprendizagem, market-data health e endpoints read-only.
- Scripts de build Windows EXE, testes e workflows GitHub Actions.
- APK, configuração de build Android, logs de crash e instruções ADB.
- Configuração de rede local e Tailscale, discovery/rendezvous e dependências Vercel, sem imprimir segredos.
- Os pontos em que browser session/authentication se ligam (ou ainda não se ligam) ao cockpit.
- Confirmar por código e testes que a camada de browser não autoriza operações financeiras.

Não presumir que funcionalidades descritas em documentação já estão implementadas. Citar ficheiros, funções e comandos que comprovem as conclusões.

## 3. Auditoria de testes do Trader

Executar a suite e os checks documentados pelo projeto, usando o ambiente suportado. No mínimo:

1. Instalar dependências de desenvolvimento a partir dos manifests/lockfiles existentes.
2. Executar os testes Python da forma recomendada pelo repo.
3. Executar lint, type-check, security checks ou testes adicionais que já existam e sejam aplicáveis.
4. Executar o workflow/build do Windows EXE se for possível no host local; caso contrário, consultar os checks do GitHub Actions e marcar o teste local como NOT RUN (não confundir com PASS).
5. Testar endpoints read-only e autenticação com tokens de teste efémeros, sem segredos reais.
6. Testar os estados sem autenticação, autenticado, sessão expirada, backend indisponível e recuperação.
7. Confirmar PAPER/read-only e que não há ordens nem transferências. Usar mocks/stubs ou ambiente de teste.
8. Repetir os testes relevantes depois de qualquer correção.

Não alargar o âmbito com refactors não relacionados. Corrigir apenas falhas pequenas, diretamente relacionadas com a auditoria e de baixo risco; separar as correções dos resultados do benchmark e documentar cada alteração. Se uma falha revelar uma mudança arquitetural, reportar em vez de a improvisar.

## 4. Laboratório Obscura vs Chromium + Playwright

### 4.1 Descoberta e instalação

- Consultar a documentação e as releases oficiais atuais de https://github.com/h4ckf0r0day/obscura e registar URL, versão/tag, SHA/checksum do artefacto, arquitetura e data.
- Usar o artefacto oficial apropriado para o sistema operativo; não executar scripts de instalação remotos sem inspecionar o conteúdo.
- Isolar a instalação em diretório temporário/virtual environment apropriado. Não substituir a instalação atual do Chromium, Playwright ou browser manager do Trader.
- Não ativar flags de stealth para contornar os controlos das exchanges. O objetivo é compatibilidade e desempenho, não evasão.
- Se não existir binário compatível com o host, tentar a alternativa oficial segura documentada (por exemplo, container ou build a partir do código-fonte, apenas se ferramentas/recursos estiverem disponíveis); se isso for inviável, documentar o bloqueio e continuar com análise estática e CI.
- Confirmar a licença publicada e guardar a referência. Não incorporar código-fonte de Obscura no Trader.

### 4.2 Comparação justa

Executar tarefas equivalentes em ambos os motores, com as mesmas URLs de teste, número de repetições, viewport, condições de rede e limites de timeout. Fazer uma ronda de aquecimento e pelo menos 10 repetições por caso quando o ambiente o permitir. Registar todos os resultados brutos; reportar mediana, p95 quando houver amostra suficiente, taxa de sucesso e dispersão. Não comparar uma execução fria de um motor com uma execução aquecida do outro sem assinalar a diferença.

Usar primeiro páginas locais controladas (servidor de teste com HTML estático, JavaScript, DOM dinâmico, formulários sintéticos, navegação e erros simulados). Usar páginas públicas apenas para smoke tests, respeitando limites e termos dos sites. Não enviar credenciais a serviços externos.

Casos mínimos:
- Arranque frio, arranque repetido e encerramento limpo.
- Navegação HTML estático e extração de título/texto/links.
- JavaScript síncrono, temporizadores, fetch/XHR e DOM dinâmico.
- CSS/layout essencial, screenshots e viewport, se suportados.
- Navegação de múltiplas páginas e formulário sintético local.
- Playwright através do método de ligação suportado pela versão atual da Obscura (confirmar documentação; o CDP não é o protocolo nativo de Playwright).
- Timeout, rede indisponível, página inválida, processo terminado e recuperação.
- Persistência de cookies numa origem local sintética, se a interface documentada o suportar. Não usar cookies de exchanges.
- 1, 2 e, se o hardware permitir, 4 sessões concorrentes, sem saturar deliberadamente o PC.
- Repetição prolongada, começando com 100 navegações e aumentando apenas se o consumo/estabilidade permitir.
- Verificar se os resultados de JS, DOM e formulários coincidem com o esperado, não apenas se a navegação devolve exit code 0.

### 4.3 Métricas

Recolher por motor e por caso:
- Tempo de arranque e tempo de navegação (mediana e p95 quando aplicável).
- RAM em repouso, RAM média aproximada e pico RSS; CPU e duração total.
- Taxa de sucesso, timeouts, crashes, erros de console/protocolo.
- Tamanho do artefacto instalado e dependências adicionais.
- Comportamento com concorrência e após reinício.
- Diferenças funcionais e limitações da implementação.
- Versão de cada motor, sistema operativo, CPU/RAM disponível, condições de rede e comandos exatos.

Preferir ferramentas de medição nativas do SO e ferramentas já disponíveis. Se uma métrica não puder ser medida fiavelmente, marcá-la como indisponível; não inventar estimativas. Não usar os valores promocionais do projeto como resultado próprio.

### 4.4 Critérios de decisão

Recomendar uma das opções:
- **ADOTAR:** vantagem material e repetível, compatibilidade suficiente para as tarefas-alvo e nenhuma regressão crítica de segurança/estabilidade.
- **ADOTAR PARCIALMENTE:** Obscura para tarefas simples de pesquisa/leitura e Chromium para páginas complexas/autenticação.
- **MANTER COMO ESTÁ:** benefício pequeno/inconsistente ou incompatibilidades que superam a poupança.
- **INCONCLUSIVO:** ambiente inadequado ou evidência insuficiente; listar exatamente o que falta.

Não definir limiares depois de ver os resultados para favorecer um motor. Antes do benchmark, registar os critérios acordados: sem falhas críticas; taxa de sucesso funcional pelo menos 98% nos casos compatíveis (ou explicar amostra pequena); poupança de RAM medida e repetível para justificar integração; e sem regressões de segurança. A decisão também deve considerar custo de manutenção e compatibilidade com o sistema existente.

## 5. APK, cockpit móvel e ADB

Se existir dispositivo Android ligado e ADB autorizado:

1. Executar `adb devices -l` e confirmar estado `device`. Se aparecer `unauthorized`, não contornar o diálogo no telemóvel; registar BLOCKED e continuar os testes de build.
2. Identificar package/application ID a partir dos ficheiros do projeto, não o adivinhar.
3. Construir o APK com o método documentado e guardar caminho, hash SHA-256 e build output.
4. Instalar/atualizar o APK de desenvolvimento. Antes de desinstalar qualquer app, verificar se isso apagaria dados; preferir atualização normal. Não apagar dados do utilizador.
5. Abrir a app e guardar `adb logcat` limitado ao período do teste. Redigir tokens, dados pessoais e outros segredos.
6. Testar crash-on-launch, orientação/tamanho de ecrã, safe areas/status bar, scroll, botões, navegação, chat e estados de ligação.
7. Testar backend indisponível, token inválido/expirado, ligação recuperada e polling cancelado ao desligar.
8. Capturar screenshots de estados-chave e inspecionar o resultado visual; manter os artefactos privados se contiverem informação sensível.
9. Repetir após correções seguras e reportar regressões.
10. Se o dispositivo não estiver presente, executar build/lint/testes automatizados e marcar os testes físicos como BLOCKED/NOT RUN. Não declarar o APK validado em dispositivo.

## 6. Tailscale, rede e sincronização PC ↔ telefone

- Verificar se o cliente Tailscale está instalado e o estado da ligação através de comandos read-only adequados ao SO.
- Não alterar ACLs, expor portas publicamente, abrir firewall, reconfigurar DNS ou modificar o router automaticamente.
- Testar endpoints locais read-only primeiro; depois testar o endereço Tailscale se houver peer autorizado e disponível.
- Validar que os serviços escutam apenas nas interfaces pretendidas e que endpoints protegidos exigem autenticação.
- Testar interrupção e recuperação de rede, timeouts e estado desconhecido.
- Verificar o fluxo de discovery/Vercel sem publicar segredos e sem transformar Vercel num proxy de credenciais.
- Se for impossível provar uma ligação remota real porque o PC/telefone não estão na mesma rede disponível ou falta peer autorizado, marcar BLOCKED e fornecer comandos/requisitos exatos para repetir mais tarde.

## 7. Resultados, artefactos e limpeza

Guardar outputs em diretório próprio, por exemplo `artifacts/obscura-evaluation/<timestamp>/`. Não guardar segredos, perfis autenticados, dumps completos de cookies, variáveis de ambiente ou dados pessoais. Artefactos grandes podem ser mantidos localmente e referenciados no relatório por caminho/hash; só publicar ficheiros não sensíveis e necessários.

Criar o relatório final em:
`docs/reports/OBSCURA_EVALUATION_REPORT_YYYY-MM-DD.md`

O relatório deve incluir:
- Sumário executivo e recomendação.
- SHA inicial do código e SHA final da branch.
- Ambiente e versões.
- Tabela de testes com PASS / FAIL / BLOCKED / NOT RUN e evidência.
- Tabela comparativa Obscura vs Chromium + Playwright.
- Métricas brutas/estatísticas e limitações.
- Resultados da suite do Trader, EXE, APK/ADB, Tailscale e sincronização.
- Problemas encontrados, causa provável, correções feitas e testes de regressão.
- Riscos conhecidos, tarefas pendentes e passos reproduzíveis.
- Percentagens de prontidão apenas com denominador/critério explícito. Não converter testes não executados em percentagem de sucesso.
- Decisão final: ADOTAR / ADOTAR PARCIALMENTE / MANTER COMO ESTÁ / INCONCLUSIVO.

Criar também um resumo legível por máquina, por exemplo `artifacts/obscura-evaluation/summary.json`, sem segredos, contendo versão dos motores, contagens por estado, métricas e recomendação.

## 8. Commit e sincronização PC → GitHub

1. Executar novamente os testes relevantes depois de preparar o relatório.
2. Verificar `git diff --check`, `git status` e rever cada ficheiro a publicar.
3. Procurar segredos e dados pessoais no diff; remover/redigir antes do commit.
4. Commitar apenas os ficheiros desta auditoria na branch dedicada. Não incluir binários, perfis de browser, APKs grandes ou logs sensíveis.
5. Fazer push da branch e confirmar no GitHub o SHA remoto.
6. Abrir uma PR draft ou atualizar a PR da auditoria, se as permissões disponíveis permitirem. Não fazer merge.
7. Verificar checks do GitHub Actions no SHA publicado. Se falharem, investigar e corrigir apenas alterações da auditoria.
8. Terminar com um resumo objetivo no terminal: relatório, branch, SHA, PR, checks, recomendação e limitações que requerem intervenção humana.

## 9. Modelo mínimo de tabela do relatório

| Área | Resultado | Evidência | Limitações |
|---|---|---|---|
| Testes Python | PASS/FAIL/BLOCKED/NOT RUN | comando + resumo | ... |
| Windows EXE | ... | workflow/artefacto | ... |
| Obscura smoke test | ... | versão + output | ... |
| Chromium + Playwright baseline | ... | versão + output | ... |
| Benchmark de RAM/CPU | ... | dados brutos + método | ... |
| Persistência sintética | ... | teste repetível | ... |
| APK build | ... | hash + build output | ... |
| ADB em dispositivo | ... | logs redigidos + screenshots | ... |
| Tailscale | ... | estado + teste de conectividade | ... |
| Sincronização remota | ... | request/response redigidos | ... |
| Segurança PAPER/read-only | ... | testes/mocks/código | ... |

**Princípio final:** maximizar a execução autónoma sem intervenção do utilizador, mas nunca fingir sucesso, ultrapassar autenticação ou sacrificar segurança para completar uma checklist.
