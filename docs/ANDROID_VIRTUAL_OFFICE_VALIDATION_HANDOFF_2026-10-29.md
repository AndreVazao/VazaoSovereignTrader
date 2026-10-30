# Android Virtual Office — Handoff de validação (2026-10-29)

## Estado confirmado
- Repositório: `AndreVazao/VazaoSovereignTrader`
- PR única ativa: [#520](https://github.com/AndreVazao/VazaoSovereignTrader/pull/520)
- Branch: `feat/virtual-office-runtime-ux-2026-10-29`
- Estado da PR: aberta, não mergeada. Não fazer merge até todos os checks relevantes estarem verdes e as capturas serem inspecionadas.
- HEAD observado durante este checkpoint: `a9c501cc0a94b79d1ceeae306d7e84763c9da1ce`. Confirmar o HEAD antes de confiar em qualquer estado de workflow, porque os runs estão associados a commits específicos.
- O commit `0e5bcd64a054a6ee97e49c1e4634f78ef953ef19` reverteu `MOBILE_APP/buildozer.spec` para `orientation = portrait`, depois de o Buildozer falhar com `orientation = all`.
- Foi corrigido um teste contratual que ainda exigia `orientation = all`; o contrato deve corresponder à configuração de build suportada.

## Último estado de CI observado para o HEAD acima
| Workflow | Run | Estado |
|---|---:|---|
| Android Emulator UI Smoke | #63 / 40962341703 | in_progress |
| Android APK | #106 / 40962341671 | in_progress |
| Python tests | #3261 / 40962341672 | success |
| Windows EXE | #962 / 40962341801 | success |

Estes estados são um instantâneo, não uma garantia de estado atual. Reconsultar GitHub Actions no início da próxima sessão.

## Alterações / teste visual
- `.github/scripts/android-emulator-smoke.sh` tenta abrir explicitamente o escritório virtual com Maestro, captura chooser, viewport portrait, landscape e tablet landscape, verifica a assinatura PNG e as dimensões reais.
- `.maestro/android-office-smoke.yaml` seleciona “USAR ESCRITÓRIO VIRTUAL” e verifica “MARKET RADAR”.
- O APK está configurado como portrait devido à limitação observada do Buildozer. Alterar o tamanho lógico do emulador para landscape **não prova** que o conteúdo rode corretamente; pode continuar recortado, letterboxed ou orientado incorretamente.
- O teste anterior falhou porque a asserção do teste ainda dizia `orientation = all`; não houve artefactos de screenshots nessa execução, pois o job terminou antes de executar o smoke test.
- Não declarar rotação resolvida até inspecionar novas imagens de emulador com o escritório realmente aberto.

## Próximos passos
1. Confirmar o HEAD atual da PR #520 e o estado final dos quatro workflows desse commit.
2. Se APK falhar, ler o log completo do job `build-apk`; se smoke falhar, ler o log completo do job do emulador e corrigir a causa real.
3. Quando o smoke terminar, descarregar os artefactos do run e inspecionar `vst-chooser.png`, `vst-portrait.png`, `vst-landscape.png`, `vst-tablet-landscape.png`, logs e OCR.
4. Confirmar que a captura representa a página do escritório, não apenas o chooser ou splash; confirmar dimensões e legibilidade/recorte do conteúdo.
5. Se a build passar e os artefactos forem válidos, fornecer APK/artifact link instalável ao utilizador e pedir validação física no telefone quando estiver disponível.
6. Manter PR #520 como única PR/branch ativa deste bloco. Não abrir outra PR nem fazer merge enquanto os checks não estiverem verdes e as evidências visuais não forem revistas.

## Limites de segurança e honestidade
- O escritório atual é uma demonstração offline: `DEMO OFFLINE · ESCRITÓRIO SEM MOTOR`. Não tem runtime/backend ligado nem trabalho real dos agentes.
- Nenhuma validação física do telefone foi realizada nesta sessão.
- PC↔telefone, ADB real, Tailscale e rede doméstica continuam dependentes de validação física pelo utilizador.
- Trader permanece PAPER/read-only; não enviar ordens reais, mover fundos, expor portas públicas, alterar router/firewall, nem contornar autenticação/MFA/approval.


## Atualização de continuidade — 2026-10-30 (PR #522)

- PR de correção visual: https://github.com/AndreVazao/VazaoSovereignTrader/pull/522
- Branch: `fix/android-office-layout-2026-10-30`
- HEAD após alterações de avatares: `29e449136603234965bdf4f11e6a279754c17aef`
- O screenshot real fornecido pelo utilizador mostra o painel lateral e o cabeçalho a ocupar espaço excessivo e as figuras a sobreporem-se na cena do escritório.
- Alterações neste checkpoint: a cena offline usa avatares pixel-art desenhados com retângulos leves em vez de caracteres ASCII; os avatares partilham uma linha de base e ocupam três posições horizontais; a grelha de departamentos usa uma coluna em telemóvel portrait, duas em ecrãs intermédios e três em ecrãs largos.
- A PR mantém a configuração `orientation = all` em `MOBILE_APP/buildozer.spec`, mas esta alteração é experimental até ser validada pelo Buildozer e pelo emulador. O histórico documenta uma falha anterior com esta configuração; não assumir que a rotação está resolvida.
- O helper GitHub Actions consultado não devolveu runs associados ao HEAD `29e4491...`; portanto não há evidência disponível nesta consulta de uma build APK ou de capturas atuais. Confirmar Actions diretamente/consultar novos runs antes de afirmar sucesso.
- Não fazer merge: falta build, smoke portrait/landscape/tablet, inspeção de artefactos e estado verde dos checks.
- O escritório continua a ser demo offline; avatares são apenas decoração visual e não representam trabalho real dos agentes. PAPER/read-only permanece padrão.
