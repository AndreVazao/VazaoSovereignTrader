# Autonomous GOD Ultra Execution

O objetivo do Trader é que, quando os pré-requisitos forem comprovadamente satisfeitos, **o próprio bot tome a decisão operacional**: selecionar oportunidades, escolher a venue, dimensionar capital e coordenar várias operações em paralelo.

## O que isto significa

O sistema deixa de ser:

`Radar -> mostra oportunidade -> operador decide`

e evolui para:

`OBSERVAÇÃO -> DESCOBERTA -> VALIDAÇÃO -> SELEÇÃO -> RISK GATE -> EXECUÇÃO AUTÓNOMA -> RESULTADO -> APRENDIZAGEM`

O operador não precisa de escolher manualmente "onde investir" em cada oportunidade. O motor compara as oportunidades elegíveis e decide de acordo com as regras e evidência disponíveis.

## Multi-plataforma e paralelo

Quando existirem várias oportunidades independentes e válidas ao mesmo tempo, o motor pode:

- selecionar várias venues;
- selecionar vários símbolos;
- distribuir capital dinamicamente;
- preparar e enviar ordens em paralelo;
- cancelar sinais que envelheçam durante a execução;
- reduzir ou bloquear novas operações quando os limites de risco forem atingidos.

A execução multi-venue é **coordenada**, mas não é tratada como uma transação atómica: duas exchanges podem aceitar, atrasar ou rejeitar ordens de forma diferente. O Executor precisa de tratar estados parciais, fills incompletos, timeouts e reconciliação.

## GOD Ultra = velocidade + disciplina

"Ultra rápido" não significa simplesmente fazer polling mais depressa.

A prioridade é:

1. WebSocket/stream oficial;
2. timestamps do evento da venue;
3. timestamp de receção local de alta resolução;
4. processamento mínimo no caminho crítico;
5. decisão sem chamadas lentas desnecessárias;
6. validação de preço/liquidez imediatamente antes do envio;
7. execução paralela onde for seguro;
8. reconciliação imediata dos fills.

O sistema deve medir continuamente a latência. Uma página web que parece atualizar primeiro não é considerada vantagem até existir evidência temporal suficiente.

## Pré-requisitos para REAL

O modo autónomo pode existir em PAPER desde já, mas REAL permanece bloqueado até todos os gates necessários estarem satisfeitos, incluindo:

- dados de mercado suficientemente rápidos e fiáveis;
- lead/lag validado;
- validação out-of-sample;
- edge líquido positivo depois de fees, spread, slippage e latência;
- sinal suficientemente fresco;
- liquidez suficiente;
- saúde da venue;
- sincronização/qualidade temporal aceitável;
- Risk Engine aprovado;
- limites de exposição respeitados;
- Real Mode Guard armado/autorizado.

Falhar um gate significa **não executar**.

## Capital

O motor não procura simplesmente a maior oportunidade nominal. Deve considerar a relação entre:

- edge líquido;
- probabilidade/consistência histórica;
- latência;
- liquidez;
- capital necessário;
- capital disponível;
- custos;
- risco;
- correlação entre oportunidades.

Assim pode preferir várias operações pequenas e independentes quando isso produzir uma utilização de capital mais eficiente dentro dos limites definidos.

## Retorno

O objetivo técnico é maximizar a **eficiência do capital dentro das restrições de risco e da evidência medida**, não prometer ou garantir retorno máximo.

Qualquer vantagem descoberta é tratada como hipótese até sobreviver a PAPER, replay e validação out-of-sample. Só depois poderá ser promovida para execução REAL controlada.

## Configuração

A política está em:

`PC_ENGINE/config/config.example.json`

na secção `autonomous_execution`.

Por defeito:

- decisão autónoma: preparada;
- multi-venue: preparado;
- execução paralela: preparada;
- REAL: bloqueado;
- Risk Engine: obrigatório;
- Real Mode Guard: obrigatório.

Esta arquitetura permite evoluir para o modo "GOD Ultra" sem transformar uma hipótese de mercado numa ordem real antes de ela estar comprovada.
