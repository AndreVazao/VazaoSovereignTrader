# Sovereign Trader — mockup 3D explodido do escritório

**Data:** 2026-10-21  
**Tipo:** conceito visual / revisão de arquitetura, não captura de estado em direto.

## Assets neste diretório

- `../virtual_office/design/sovereign_trader_exploded_office.svg` — vista isométrica em camadas do edifício, com os departamentos propostos.
- `../virtual_office/design/sovereign_trader_floor_plan.svg` — planta funcional simplificada para discutir proximidade e circulação entre salas.

Os SVG são assets vetoriais editáveis por texto e mantêm-se na repository. A imagem gerada na conversa é uma referência visual; não a tratar como render fiel de um edifício já implementado nem como evidência de agentes ativos. A vista de referência gerada nesta sessão tem composição conceptual e pode conter pequenos erros de texto ou detalhes decorativos. A versão SVG do repositório é a fonte de nomes para revisão.

## Como ler o edifício

- **Piso superior de direção:** CEO/Cérebro (destino de conversa por omissão), receção e sala de reuniões. O avatar do CEO deve vir do ficheiro de avatar oficial aprovado, sem inventar uma identidade substituta.
- **Piso de mercado:** integrações de exchanges, Market Radar (deteção de eventos) e Comparação entre Exchanges (normalização e avaliação de diferenças entre venues).
- **Piso de inteligência:** investigação, análise e memória central.
- **Piso de validação:** laboratório PAPER/replay, estratégias, controlo de risco e Resposta Rápida/Execução Controlada (separada, inicialmente apenas PAPER e sempre subordinada aos gates de risco).
- **Piso transversal de controlo:** risco, auditoria, recuperação e intervenção humana.
- **Piso técnico/subsolo:** infraestrutura, persistência e dispositivos; “cofre” é metáfora visual, não autorização para transferir fundos.

A disposição vertical é uma convenção de visualização, não dependência arquitetural. Os departamentos são funções lógicas; não se deve pressupor um processo, thread ou agente independente por cada sala sem implementação correspondente.

## Regras de fidelidade

1. O Runtime é a autoridade. A UI só observa e envia pedidos autenticados permitidos.
2. Mostrar “desconhecido” quando os dados não são confirmados. Não inventar latência, preços, lucros, pessoas ativas ou contagens.
3. Não ligar o mockup a execução real. Os próximos testes usam adaptadores simulados e PAPER.
4. CEO é o destino de conversa por omissão; o operador também pode selecionar um departamento e falar diretamente com ele.
5. A memória central de aprendizagem é partilhada localmente entre as funções; o escritório não cria uma memória paralela.
6. O escritório adapta fidelidade ao hardware: modo simples/2D, pixel/low-detail, 2.5D, 3D detalhado e, mais tarde, modo cinematográfico. Chat-only permanece sempre disponível.
7. O backend deve continuar a operar se o cliente estiver desligado ou sob carga.

## Decisões aprovadas pelo proprietário — 2026-10-21

- CEO no piso superior.
- Market Radar e Comparação entre Exchanges em salas/departamentos separados.
- Investigação e Análise separados.
- Memória Central representada por sala visual e serviço transversal.
- Departamento dedicado de Resposta Rápida, sem autoridade para contornar validação, custos, inventário, risco ou aprovação humana.

O próximo passo de design é alinhar todos os compartimentos nos SVG com estas decisões e depois mapear cada estado visual para uma fonte real do backend antes de animar ou ligar dados em direto.
