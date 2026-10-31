# VST — origem dos agentes e identidade visual

**Estado:** requisito de produto aprovado; contrato documentado e primeira política pura de avatar/métricas implementada em `PC_ENGINE/tools/agent_identity.py`. Ainda não está ligada ao registo persistente de agentes nem ao renderer Android/desktop.

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

## Primeira política implementada

`PC_ENGINE/tools/agent_identity.py` introduz uma política pura, sem efeitos laterais:
- origem VST validada → avatar `robot`;
- origem humana ou importação verificada → avatar existente;
- origem desconhecida, ID vazio ou proveniência não validada → avatar neutro;
- métricas deduplicadas por `agent_id`, excluindo registos não persistidos, não validados e placeholders;
- separação de contagens para ativos, quarentena e inativos.

Testes em `tests/test_agent_identity.py` cobrem estas regras e a deduplicação de agentes repetidos após restore. Os resultados CI para o HEAD atual ainda têm de ser confirmados. Esta política não prova que o backend já persiste a origem nem que o renderer já mostra robôs.

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

**Estado de integração:** modelo persistente de agentes, criação autoritativa, métricas de expansão e renderer Android/desktop continuam pendentes e devem ser implementados com testes antes de serem anunciados como funcionais.
