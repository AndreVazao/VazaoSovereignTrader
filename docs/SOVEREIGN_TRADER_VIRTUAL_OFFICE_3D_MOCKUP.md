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


## Renderização adaptativa por dispositivo — requisito obrigatório

A planta, os nomes dos departamentos, as ligações e o contrato de estado são únicos. Só muda a forma de os desenhar. A escolha de qualidade nunca pode alterar a lógica de negócio, a memória partilhada, a autorização, o estado do Runtime ou a política de risco.

### Perfis de apresentação

| Perfil | Quando escolher | Representação |
|---|---|---|
| **Chat / acessibilidade** | Preferência do utilizador, falha gráfica ou dispositivo sem capacidade | Conversa, estado e listas; sem cena 3D |
| **Económico / PC antigo** | RAM/CPU/GPU limitadas, bateria baixa ou pressão de memória | Planta 2D, silhuetas/palitos, gráficos simples, sem sombras, partículas, reflexos ou animação contínua |
| **Pixel / baixo detalhe** | Capacidade modesta, mas com preferência por espaço visual | Edifício pixel-art, personagens e movimentos em baixa frequência |
| **2.5D / equilibrado** | Dispositivo intermédio | Pisos em perspetiva, sprites/ícones, animações curtas e gráficos simplificados |
| **3D detalhado** | Dispositivo com GPU/RAM suficientes | Edifício explodido, compartimentos, personagens e animações limitadas |
| **Cinemático / alta definição** | Hardware forte, ecrã adequado e orçamento de desempenho disponível | Materiais e iluminação avançados, personagens detalhadas, câmara/zoom e movimento em tempo real com limites |

O telefone não recebe automaticamente o perfil mais leve: se suportar o orçamento de desempenho e o utilizador quiser, pode apresentar 3D detalhado. Da mesma forma, um PC antigo deve começar no perfil económico, mesmo que o ecrã seja grande. O perfil pode ser alterado manualmente e deve poder descer de qualidade imediatamente.

### Seleção e adaptação

1. Começar com uma deteção conservadora e barata de capacidades disponíveis; não executar testes gráficos pesados no arranque.
2. Considerar classe do dispositivo, memória disponível quando a plataforma a expõe, capacidade gráfica, dimensão/escala do ecrã, estado térmico/bateria quando acessível e desempenho observado.
3. Se a plataforma não expuser dados fiáveis, escolher o perfil económico/equilibrado e permitir seleção manual.
4. Monitorizar frame time, pressão de memória, falhas e tempo de resposta; baixar perfil antes de a interface bloquear. Subir gradualmente só após estabilidade sustentada.
5. Respeitar preferências de reduzir movimento, contraste, leitor de ecrã e navegação por teclado/toque. Disponibilizar sempre a alternativa chat-only.
6. Descarregar modelos, texturas e cenas de alta resolução apenas quando necessários; libertá-los ao descer de perfil. Evitar manter várias cenas completas em memória.
7. Limitar taxa de animação e atualização visual; pausar animações fora do ecrã/aba inativa. Os dados recebidos devem ser coalescidos para mostrar o estado mais recente, sem acumular uma fila ilimitada.
8. Se a renderização falhar, cair para 2D/chat sem perder a sessão nem afetar o Runtime.

### Separação entre modelo e renderizador

- **Modelo canónico:** planta, pisos, salas, departamentos, rotas de navegação, IDs estáveis e relações entre salas.
- **Estado canónico:** snapshots/eventos autenticados do Runtime; desconhecido continua desconhecido.
- **Renderizadores intercambiáveis:** chat, 2D/palitos, pixel, 2.5D, 3D e cinemático.
- **Política de desempenho:** a interface adapta fidelidade e frequência; nunca pede ao Runtime que reduza a frequência do ciclo de trading nem altera gates de risco.
- **Controlo:** o utilizador pode escolher um perfil fixo ou automático. A seleção de renderizador não altera permissões nem desbloqueia comandos.

### Critérios de aceitação

- A mesma sala/ID e o mesmo estado aparecem em todos os perfis; só muda a representação.
- O perfil económico não carrega assets 3D pesados, não usa animação contínua e mantém navegação e conversa funcionais.
- Trocar de perfil não reinicia nem bloqueia o motor, não perde comandos confirmados e não altera decisões de trading.
- Sob pressão ou falha gráfica, a interface degrada graciosamente para 2D/chat.
- Medir CPU, memória, frame time e tráfego no PC antigo real e no telefone real antes de declarar um perfil validado. Os valores de desempenho não devem ser inventados nem declarados validados sem medição.
