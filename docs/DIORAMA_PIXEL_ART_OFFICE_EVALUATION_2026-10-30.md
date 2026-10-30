# Avaliação técnica — Diorama para o escritório virtual VST

**Data:** 2026-10-30  
**Estado:** candidato de visualização; analisado documentalmente, ainda não integrado nem executado no VST.  
**Repositório avaliado:** https://github.com/sloemo01/diorama  
**Licença indicada no repositório:** MIT (confirmar novamente no momento de copiar ficheiros/assets).

## Decisão

Aproveitar o Diorama como referência técnica e candidato a um protótipo visual isolado. **Não substituir a aplicação Kivy/Android, não copiar o projeto inteiro e não acoplar Three.js ao cérebro do trader nesta fase.** Primeiro fechar a validação do APK e da interface atual; depois comparar um protótipo mínimo com critérios objetivos.

O Diorama é um playbook/kit de cenas de diorama pixel-art em Three.js, não uma aplicação de escritório multi-piso pronta. A sua câmara de três quartos fixa, composição em laje, paleta limitada, dithering/contorno e personagens articuladas podem aproximar o escritório do estilo visual pretendido sem confundir a ilustração com atividade real.

## Partes potencialmente reutilizáveis

- **Composição/câmara:** vista isométrica ou de três quartos, proporções consistentes e cena que enquadra o edifício inteiro.
- **Estilo visual:** paleta controlada, silhuetas nítidas, materiais simples e pixel-art mais legível do que bonecos de texto.
- **Animação determinística:** cenas parametrizadas pelo tempo permitem congelar uma pose e repetir exatamente uma captura.
- **QA visual:** scripts descritos pelo projeto para capturas, frames, strips, personagens isoladas, margens e teletransporte podem inspirar testes reproduzíveis.
- **Fluxo de trabalho:** definir a folha de estilo e a composição antes de criar muitos assets; validar por screenshots antes de expandir.

## Limites e custos

- Three.js/WebGL introduz uma segunda stack de renderização face à UI Kivy atual; não assumir que melhora o consumo, arranque ou compatibilidade Android sem medir.
- A câmara fixa e a cena de diorama não fornecem, por si só, navegação real entre pisos/salas, menus laterais, conversas, zoom de utilizador, acessibilidade ou orientação portrait/landscape.
- A QA descrita requer Node e ferramentas/dependências como Three.js, esbuild e Playwright; confirmar versões, licença e compatibilidade antes de incorporar qualquer ficheiro.
- Não copiar media/preview nem assets de terceiros sem verificar origem, licença e atribuição. O estado MIT do repositório não concede automaticamente direitos sobre assets externos nele referenciados.
- Um render bonito não pode bloquear nem competir com o motor de trading. A camada gráfica deve continuar opcional, isolada e sem autoridade sobre estados financeiros.

## Workflow de protótipo em VM

Foi adicionado `.github/workflows/diorama-office-prototype.yml`. O workflow, quando executado, usa uma VM Ubuntu do GitHub Actions para clonar e verificar o commit do playbook Diorama, instalar Node/Three.js/Playwright e renderizar um protótipo visual isolado de uma sala com três postos e avatares low-poly/pixel-like. Captura três viewports (390×844, 844×390 e 1180×820), verifica canvas, erros JavaScript e rótulo DEMO OFFLINE, e publica PNGs + `report.json` como artefacto por 14 dias. O protótipo é temporário e não altera a app nem importa assets externos do Diorama.

**Limitação importante:** o repositório Diorama é um playbook e um kit de módulos, não uma app pronta para abrir; por isso, esta VM é uma prova visual baseada em Three.js e no fluxo determinístico recomendado, não uma execução direta de uma demo oficial do Diorama.

### Evidência da primeira execução
- Run #6/ID `41131895430` passou e publicou o artefacto `vst-diorama-office-vm-screenshots`; o relatório JSON marcou as três viewports como PASS e não registou erros de JavaScript.
- A inspeção visual manual dos PNGs encontrou um defeito que o teste técnico não detetava: a câmara cortava parte da cena/rótulos em portrait e apertava o enquadramento em landscape. Isto demonstra que um teste de canvas/JS não basta para validar layout.
- Corrigi a fórmula de enquadramento para priorizar a largura da sala em ecrãs estreitos e lancei nova execução no commit `a350679d1dcf3371f0167756bc926d5b97d47a16` (run #7/ID `41132052504`). A inspeção da execução #7 confirmou que a sala fica enquadrada nos três formatos. O segundo defeito visual — o HUD a cobrir o rótulo MARKET RADAR em landscape — foi corrigido colocando o HUD no canto inferior esquerdo. O run #8/ID `41132230066` concluiu com sucesso e os PNGs foram inspecionados: rótulos visíveis e sala inteira enquadrada nos três viewports. O teste continua a ser uma prova visual básica, não uma validação de usabilidade ou desempenho em telemóvel físico.

## Experiência mínima proposta (após estabilizar o APK atual)

1. Criar um protótipo descartável numa pasta/branch isolada, sem dependência do motor VST.
2. Renderizar **uma única sala** do escritório, com três avatares estilizados, secretárias e rótulos curtos; sem rede, contas, dados de mercado ou tarefas reais.
3. Produzir capturas reproduzíveis em telemóvel portrait, telemóvel landscape e viewport de tablet; incluir escala reduzida e zoom, sem deformar a geometria.
4. Medir tempo de arranque, FPS/fluidez observada, RAM aproximada, tamanho de dependências, legibilidade e falhas de orientação em dispositivo/emulador suportado.
5. Comparar lado a lado com a UI atual no mesmo ambiente. Não declarar vencedor sem evidência repetível.
6. Manter a UI Kivy como fallback. Só considerar integração se o protótipo demonstrar ganho visual relevante sem regressão de recursos, compatibilidade ou estabilidade.

## Resultado observado no protótipo VM (2026-10-30)

- Run #8: [GitHub Actions](https://github.com/AndreVazao/VazaoSovereignTrader/actions/runs/41132230066) — sucesso; artefacto `vst-diorama-office-vm-screenshots`.
- O relatório JSON marcou PASS para 390×844, 844×390 e 1180×820; nenhum erro de JavaScript, canvas presente e dimensões corretas.
- Inspeção manual dos três PNGs: cena inteira visível e HUD sem sobrepor os rótulos após a última correção. Em portrait, a sala ocupa uma área relativamente pequena para caber toda; os botões de zoom estão presentes, mas o fluxo de zoom ainda não foi testado automaticamente.
- Isto confirma que o protótipo Three.js pode ser renderizado em Chromium headless/SwiftShader numa VM Linux. **Não confirma** desempenho em Android, qualidade final, integração com Kivy ou que o kit Diorama seja superior à UI atual.

## Critérios de aprovação

- [ ] O edifício/sala mantém proporções em portrait e landscape.
- [ ] A vista geral mostra o espaço sem rótulos sobrepostos; zoom não distorce o edifício.
- [ ] Animações determinísticas podem ser congeladas para screenshots de CI.
- [ ] A interface continua responsiva e menus/conversas não ficam presos ao renderer.
- [ ] Renderer falhado/desativado não afeta backend, PAPER mode nem diagnósticos.
- [ ] Dependências e assets têm origem/licença verificadas.
- [ ] Comparação inclui o hardware/emulador de referência e regista limitações.

## Estado de execução e segurança

- Pesquisa e análise documental concluídas; **não foi instalado, compilado nem testado** o Diorama neste checkpoint.
- Não foi alterado o renderer existente por causa desta avaliação.
- Nenhum serviço de trading, credencial, rede externa ou ação financeira é necessário para o protótipo.
- O escritório permanece uma visualização offline; avatares e animações locais não são prova de trabalho real dos agentes.
- PAPER/read-only continua a ser o padrão. Não fazer merge da PR ativa sem CI e artefactos visuais atuais inspecionados.
