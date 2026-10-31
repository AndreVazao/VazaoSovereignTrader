# VST — referências da identidade visual do escritório

**Estado:** referências visuais aprovadas como direção de design; ainda não são assets integrados na aplicação. Não afirmar que o gabinete já reproduz as imagens de referência até existir um asset versionado, implementação e validação visual no APK/PC.

## Referências aprovadas

1. **Gabinete do CEO — quadro de fundo:** globo financeiro, touro dourado, moedas/barras e seta ascendente. Usar como imagem de destaque atrás da secretária do CEO, sem cobrir avatar, controlos ou indicadores operacionais.
2. **Marca VST — logótipo e paleta:** logótipo “VST / Vazão Sovereign Trader”; azul elétrico, azul-ciano, dourado metálico e preto/azul-marinho profundo. Manter contraste e legibilidade; o dourado é acento e não deve substituir cores semânticas de risco.
3. **Papel de parede dos escritórios:** globo de mercados, painéis financeiros e iluminação tecnológica azul/ciano/violeta. Adaptar a composição por divisão sem copiar informação de mercado para a decoração.

## Regras de implementação

- Tratar as imagens como referências de arte, não como fonte de dados financeiros nem como prova de desempenho.
- Manter o cérebro/headless independente do renderer. Fundos estáticos ou texturas devem ser opcionais e não executar cálculos gráficos no ciclo do motor.
- Respeitar portrait, landscape e tablet; usar crop/letterbox controlado sem deformar divisões nem esconder nomes, agentes ou controlos.
- Fornecer modo de baixo custo e permitir desativar fundos de alta resolução em equipamentos fracos.
- Não adicionar imagens remotas em runtime. Assets finais devem ser versionados e licenciados/verificados antes de empacotar.
- O ecrã offline tem de continuar marcado como demonstração e não pode apresentar preços, ordens ou atividade fictícia como dados reais.

## Próximos passos de implementação

1. Preparar assets locais versionados para o quadro do CEO, logótipo e fundos; confirmar dimensões, compressão e licença.
2. Aplicar a paleta à interface global, preservando vermelho/verde e outros indicadores semânticos de risco.
3. Integrar o quadro apenas na sala do CEO e fundos adequados nas outras salas, com fallback de cor sólida.
4. Gerar APK e capturas portrait/landscape/tablet; inspecionar cortes, contraste, legibilidade e consumo de memória.
5. Confirmar que a interface pode fechar/reiniciar sem afetar o backend.

## Estado atual confirmado no código

- `MOBILE_APP/ui.py` tem uma paleta base escura/ciano e os avatares pixel existentes.
- A decoração final com as três imagens ainda não está integrada; este documento fixa a direção visual para evitar deriva de design.
- A primitiva de avatar robótico só deve representar origem VST quando a proveniência é validada. Identidades desconhecidas/não validadas devem usar marcador neutro.
