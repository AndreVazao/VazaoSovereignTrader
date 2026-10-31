# VST — origem dos agentes e identidade visual

**Estado:** requisito de produto aprovado; contrato de identidade documentado. Não implica que todos os agentes existentes já tenham metadados de origem nem que o renderer já desenhe robots.

## Regra visual

- **Agentes existentes/criados por André ou pela equipa humana:** preservar os avatares e o aspeto que já têm. Não converter retroativamente os personagens existentes em robôs.
- **Agentes/departamentos criados, recrutados ou instanciados pelo Sovereign Trader:** usar uma figura de robô como sinal visual de origem automática.
- A origem é uma propriedade de identidade persistida, não inferida pelo aspeto, nome, capacidade, personalidade ou número de agentes.
- Se a origem for desconhecida ou a proveniência não puder ser verificada, mostrar um marcador neutro/desconhecido; nunca presumir que o agente foi criado pela IA.
- A enfermaria e a oficina mantêm o marcador de origem original: um robô continua a ser reconhecível como agente criado pelo VST mesmo quando está em reparação/quarentena.

## Metadados mínimos de proveniência

Cada agente deve ter um registo persistente, versionado e auditável com:
- `agent_id` único e estável;
- `origin_type`: `human_created`, `vst_created`, `imported_verified` ou `unknown`;
- `created_by` (identificador do operador, do VST/CEO ou da instalação que o criou);
- `created_at` e versão do esquema;
- evento/razão de criação e, quando aplicável, ID da tarefa ou autorização que pediu a criação;
- `parent_agent_id` ou ID da fábrica/serviço de criação, se aplicável;
- hash/referência auditável do evento de criação, sem segredos;
- estado de validação da proveniência.

Os campos de origem devem ser definidos no backend e persistidos na criação. O renderer recebe-os pela API/eventos autorizados e escolhe o avatar. Não confiar em campos de origem enviados pelo próprio agente ou escolhidos pelo frontend.

## Distinguir crescimento real de crescimento aparente

A contagem de robôs não é, por si só, prova de evolução. O painel de expansão deve distinguir:
1. agentes criados;
2. agentes que passaram validação e estão ativos;
3. agentes em formação/testes;
4. agentes suspensos, em quarentena ou desativados;
5. departamentos e capacidades efetivamente disponibilizados;
6. tarefas concluídas com evidência e resultados verificados;
7. custo de recursos e falhas por agente/departamento.

A criação de um agente só conta como expansão operacional depois de passar os critérios de validação definidos. Animações, agentes de demonstração e personagens offline não entram nas métricas reais. Os IDs e eventos devem ser deduplicados para que reinícios ou restaurações não inflem a contagem.

## Segurança e ciclo de vida

- Um agente novo não herda automaticamente permissões de trading, credenciais, acesso à memória privada nem autoridade de outro agente.
- A criação deve ser autorizada pelo backend, ter limites de taxa/recursos, registo de auditoria e validação de identidade única.
- A restauração de backup preserva os IDs e a proveniência; importar o mesmo agente não cria um agente novo.
- Se a proveniência estiver ausente/corrompida, definir `unknown` e investigar; não reconstruir origem por suposição.
- O renderer pode ter placeholders para o modo offline, mas deve identificá-los como simulação e não incluí-los em métricas reais.

## Critérios de aceitação

- Testes de criação humana, criação VST, importação verificada e origem desconhecida.
- Testes de reinício/restore confirmam que origem e IDs persistem sem duplicação.
- O frontend não consegue transformar um agente humano em `vst_created` alterando apenas a UI.
- Os avatares humanos existentes mantêm o seu aspeto; os novos agentes VST aparecem com avatar robótico.
- Contadores distinguem personagens demonstrativos de agentes persistidos e validados.
- O estado de saúde (enfermaria/quarentena/oficina) é independente da origem visual.

**Estado atual:** este documento fixa o requisito e o contrato de proveniência. A integração com o modelo de dados existente, a lógica autoritativa de criação, as métricas de expansão e a alteração do renderer Android/desktop continuam pendentes e devem ser implementadas com testes antes de serem anunciadas como funcionais.
