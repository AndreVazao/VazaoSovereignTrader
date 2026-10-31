# VST — origem dos agentes e identidade visual

**Estado:** política de avatar/métricas, registo persistente JSON e uma fronteira inicial de criação autorizada foram implementados com testes dedicados. A fronteira ainda não está ligada ao scheduler/API de produção nem ao renderer Android/desktop.

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
- evento/razão de criação e ID de autorização/tarefa quando aplicável;
- `parent_agent_id` ou ID da fábrica/serviço de criação, se aplicável;
- hash SHA-256 do evento de criação, sem segredos;
- estado de validação da proveniência.

Os campos de origem devem ser definidos no backend e persistidos na criação. O renderer recebe-os pela API/eventos autorizados e escolhe o avatar. Não confiar em campos de origem enviados pelo próprio agente ou escolhidos pelo frontend.

## Código implementado

### Política de identidade

`PC_ENGINE/tools/agent_identity.py`:
- origem VST validada → avatar `robot`;
- origem humana ou importação verificada → avatar existente;
- origem desconhecida, ID vazio ou proveniência não validada → avatar neutro;
- métricas deduplicadas por `agent_id`, excluindo registos não persistidos, não validados e placeholders;
- separação de contagens para ativos, quarentena e inativos.

Testes: `tests/test_agent_identity.py`.

### Registo persistente inicial

`PC_ENGINE/core/agent_registry.py`:
- guarda registos versionados em JSON com escrita atómica;
- requer ID, origem explícita, autor, razão e ID de autorização para registar criação;
- criação repetida com os mesmos metadados é idempotente; conflito de proveniência é rejeitado;
- restauro/importação valida o hash do evento, mantém o ID e rejeita proveniência adulterada;
- estado operacional (por exemplo, quarentena) é separado da origem visual;
- se o ficheiro estiver corrompido ou o esquema for desconhecido, recusa sobrescrever os dados.

Testes: `tests/test_agent_registry.py`. O chamador continua responsável por autenticar e autorizar a criação antes de chamar o registo; o módulo não substitui o controlo de acesso nem é ainda o registo autoritativo usado por todo o runtime.

### Fronteira de criação autorizada (implementação inicial)

`PC_ENGINE/core/agent_lifecycle.py` introduz `AgentLifecycle`, que chama um autorizador de controlo-plane confiável antes de escrever no registo. `create_vst_agent()` fixa a origem como `vst_created` no backend, sem aceitar uma origem fornecida pelo cliente; `create_human_agent()` regista explicitamente origem humana. Se o autorizador não devolver um ID de autorização válido, a criação falha sem persistir o agente. Testes em `tests/test_agent_lifecycle.py` cobrem autorização, falha fechada e origem humana.

**Limite importante:** o autorizador é uma dependência injetada e tem de ser fornecido por um controlo-plane autenticado; este módulo não implementa autenticação por si. A fronteira ainda não foi ligada ao caminho real de criação/scheduler/API do runtime, e não altera os avatares da aplicação.

## Distinguir crescimento real de crescimento aparente

A contagem de robôs não é, por si só, prova de evolução. O painel de expansão deve distinguir:
1. agentes criados;
2. agentes validados e ativos;
3. agentes em formação/testes;
4. agentes suspensos, em quarentena ou desativados;
5. departamentos e capacidades efetivamente disponibilizados;
6. tarefas concluídas com evidência e resultados verificados;
7. custo de recursos e falhas por agente/departamento.

Animações, agentes de demonstração e personagens offline não entram nas métricas reais. Os IDs e eventos devem ser deduplicados para que reinícios ou restaurações não inflem a contagem.

## Segurança e ciclo de vida

- Um agente novo não herda automaticamente permissões de trading, credenciais, acesso à memória privada nem autoridade de outro agente.
- A criação deve ser autorizada pelo backend, ter limites de taxa/recursos, registo de auditoria e validação de identidade única.
- A restauração de backup preserva os IDs e a proveniência; importar o mesmo agente não cria um agente novo.
- Se a proveniência estiver ausente/corrompida, definir `unknown` e investigar; não reconstruir origem por suposição.
- Placeholders offline devem estar identificados como simulação e não entrar nas métricas reais.

## Critérios de aceitação

- Testes de criação humana, criação VST, importação verificada e origem desconhecida.
- Testes de reinício/restore confirmam que origem e IDs persistem sem duplicação.
- O frontend não consegue transformar um agente humano em `vst_created` alterando apenas a UI.
- Os avatares humanos existentes mantêm o seu aspeto; os novos agentes VST aparecem com avatar robótico.
- Contadores distinguem personagens demonstrativos de agentes persistidos e validados.
- O estado de saúde (enfermaria/quarentena/oficina) é independente da origem visual.

**Integração pendente:** ligar `AgentLifecycle` ao caminho real de criação de agentes e à API autenticada, definir migração segura para agentes existentes sem proveniência, fornecer identidades confiáveis ao renderer e desenhar o avatar robótico no renderer Android/desktop. Não anunciar a experiência visual como funcional até esses passos e os testes correspondentes passarem.
