# Android Virtual Office — handoff de validação

**Última reconciliação:** 2026-10-30  
**PR ativa:** [#522 — modular runtime foundations and Android office validation](https://github.com/AndreVazao/VazaoSovereignTrader/pull/522)  
**Branch:** `fix/android-office-layout-2026-10-30`  
**Estado:** aberta, não mergeada. Consultar sempre o HEAD atual antes de interpretar CI.

## Regras de validação

- Não fazer merge até os checks relevantes estarem verdes no HEAD final e os artefactos visuais atuais serem inspecionados.
- Build configurado com orientações Android explícitas: `portrait, landscape, portrait-reverse, landscape-reverse`. A configuração, por si só, não prova que a aplicação roda e reorganiza corretamente.
- Precisamos de capturas com o escritório realmente aberto em portrait de telemóvel, landscape de telemóvel e landscape de tablet. Confirmar dimensões, proporções, recortes, sobreposições, legibilidade e rotação real.
- Não declarar teste físico feito: testes no telemóvel físico e no PC continuam pendentes até existir evidência direta.
- O escritório pode abrir sem backend, mas tem de indicar claramente `DEMO OFFLINE · ESCRITÓRIO SEM MOTOR`. Animações/avatares locais são decoração e não provam atividade real de agentes.
- O renderer deve ser leve e opcional; não pode atrasar, bloquear nem comandar o cérebro do trader.

## Estado do PR e CI

PR #522 consolida a correção de layout Android, fundações do runtime modular e avaliação cloud Obscura/Chromium. A configuração de orientação foi alterada ao longo de tentativas anteriores; não reutilizar os estados históricos de builds como prova de sucesso atual.

No checkpoint após a documentação Diorama, o HEAD era `e0b8b287e321c21275c446ca08ac36b8c234082b`; os workflows Android APK, Android Emulator UI Smoke, Python tests e Windows EXE estavam pendentes, Obscura cloud smoke estava em execução, Vercel pendente e Snyk verde. **Esse estado já pode ter mudado porque este documento gera outro commit.** Consultar os checks do novo HEAD antes de qualquer conclusão.

## Layout esperado

- Visão geral do edifício com zoom-out inicial, tipografia pequena mas legível e opção de zoom in/out sem deformar a geometria.
- Portrait e landscape responsivos; navegação compacta no telemóvel; departamentos sem sobreposição nem recorte.
- Pixel-art pode melhorar a apresentação, mas manter modos simples e fallback leve.
- A vista do escritório não deve depender da disponibilidade do backend para renderizar a demonstração offline.

## Workflow VM — capturas do protótipo

- Adicionado `.github/workflows/diorama-office-prototype.yml`: VM Ubuntu, clone verificado do playbook, renderização isolada Three.js/Playwright e artefactos PNG + `report.json` para portrait, landscape e tablet.
- O protótipo não é a app Android nem uma cena oficial já existente no Diorama; é uma experiência descartável baseada no seu estilo/fluxo, sem tocar no renderer Kivy ou no backend.
- Só aceitar a evidência após o workflow correr com sucesso e os artefactos serem descarregados/inspecionados. Não afirmar que existem screenshots até o run publicar o artefacto.

## Avaliação Diorama

A análise documental de `sloemo01/diorama` está registada em [DIORAMA_PIXEL_ART_OFFICE_EVALUATION_2026-10-30.md](DIORAMA_PIXEL_ART_OFFICE_EVALUATION_2026-10-30.md).

Decisão: candidato a protótipo isolado futuro, não integração imediata. O kit Three.js pode inspirar câmara de três quartos, estilo pixel-art, animação determinística e QA visual. Não foi instalado, compilado ou executado; não há medições de desempenho nem prova de compatibilidade Android. Primeiro estabilizar e inspecionar o APK atual. Só depois comparar uma sala com três avatares contra a UI existente, mantendo Kivy como fallback.

## Próximos passos

1. Consultar o HEAD atual e aguardar resultados dos workflows associados a esse commit.
2. Descarregar os artefactos Android atuais e inspecionar capturas portrait, landscape e tablet.
3. Corrigir qualquer recorte/sobreposição e repetir os testes; não confiar apenas em testes contratuais nem em rotação simulada do viewport.
4. Se a UI atual continuar insuficiente, executar o protótipo Diorama isolado com métricas e screenshots reproduzíveis.
5. Atualizar documentação/memória com evidência, não com intenção. Não fazer merge antes dos gates acima.

## Segurança

PAPER/read-only é o padrão. Nenhum protótipo visual precisa de credenciais, chamadas a exchanges ou operações financeiras. Não usar segredos reais em fixtures/logs, não abrir portas públicas nem alterar os controlos de risco para validar o escritório.
