from __future__ import annotations

COCKPIT_HTML = r'''<!doctype html>
<html lang="pt-PT">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Vazao Sovereign Trader</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#08101f;color:#eef4ff;font:15px system-ui,Arial,sans-serif}.top{position:sticky;top:0;padding:14px 16px;background:#0d1629;border-bottom:1px solid #243553;z-index:2}.title{font-size:20px;font-weight:800}.muted{color:#9fb0ca;font-size:13px}.wrap{max-width:1100px;margin:auto;padding:12px;display:grid;gap:12px}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.card{background:#101a2f;border:1px solid #243553;border-radius:16px;padding:15px}.wide{grid-column:1/-1}.label{color:#9fb0ca;font-size:12px;text-transform:uppercase;font-weight:700;letter-spacing:.08em}.big{font-size:26px;font-weight:850;margin-top:5px}.row{display:flex;flex-wrap:wrap;gap:7px;margin-top:8px}button,input{font:inherit;border-radius:11px;padding:12px;border:1px solid #334968}button{cursor:pointer;font-weight:800;border:0;flex:1 1 130px}.go{background:#37d39a}.pause{background:#f6c453}.stop{background:#ff7187}.blue{background:#9ac7ff}input{width:100%;background:#09111f;color:#eef4ff}.ok{color:#37d39a}.bad{color:#ff7187}.warn{color:#f6c453}.venue{display:grid;grid-template-columns:auto 1fr auto;gap:10px;align-items:center;padding:10px 0;border-bottom:1px solid #243553}.dot{width:12px;height:12px;border-radius:50%;background:#f6c453}.dot.green{background:#37d39a}.dot.red{background:#ff7187}.venue-name{font-weight:800}.venue-meta{font-size:12px;color:#9fb0ca}.notice{background:#0b1425;padding:11px;border-radius:12px;margin-top:8px}table{width:100%;border-collapse:collapse}td,th{padding:8px;text-align:left;border-bottom:1px solid #243553}pre{white-space:pre-wrap;max-height:220px;overflow:auto}details{margin-top:10px}summary{cursor:pointer;font-weight:800}@media(max-width:700px){.grid{grid-template-columns:repeat(2,1fr)}}@media(max-width:450px){.grid{grid-template-columns:1fr}.card{padding:13px}button{width:100%}}
</style>
</head>
<body>
<header class="top"><div class="title">Vazao Sovereign Trader</div><div class="muted">Painel simples · PAPER por defeito</div></header>
<main class="wrap">
<section class="card wide"><div class="label">Estado</div><div id="status" class="big">A ligar…</div><div id="mode" class="muted">---</div><div id="health" class="notice">A verificar…</div></section>
<section class="card wide"><div class="label">Controlo</div><div class="row"><button class="go" onclick="cmd('/start')">▶ LIGAR</button><button class="pause" onclick="cmd('/pause')">Ⅱ PAUSAR</button><button class="go" onclick="cmd('/resume')">▶ RETOMAR</button><button class="stop" onclick="cmd('/stop')">■ PARAR</button></div><details><summary>Mais opções</summary><div class="row"><button class="blue" onclick="cmd('/preflight')">✓ VERIFICAR</button><button class="blue" onclick="setMode('PAPER')">PAPER</button><button class="blue" onclick="runValidation()">↻ VALIDAR PAPER</button></div><div id="validation" class="muted"></div></details></section>
<section class="grid"><div class="card"><div class="label">Saldo</div><div id="balance" class="big">---</div></div><div class="card"><div class="label">Hoje</div><div id="pnl" class="big">---</div></div><div class="card"><div class="label">Drawdown</div><div id="dd" class="big">---</div></div><div class="card"><div class="label">Watchdog</div><div id="wd" class="big">---</div></div></section>
<section class="card wide"><div class="label">REAL protegido</div><div id="real" class="big">A verificar…</div><div id="realinfo" class="muted"></div><div class="notice">O botão REAL só funciona quando todas as verificações necessárias estiverem OK.</div><div class="row"><button class="blue" onclick="arm()">🔐 AUTORIZAR REAL</button><button class="stop" onclick="cmd('/real/disarm')">🔒 BLOQUEAR REAL</button><button class="blue" onclick="setMode('REAL')">ATIVAR REAL</button></div><details><summary>Ver verificações</summary><div id="checks"></div></details></section>
<section class="card wide"><div class="label">Assistência pendente</div><div class="muted">Pedidos de informação ou confirmação necessários ao funcionamento do trader.</div><div id="bridge" class="notice">A verificar pedidos pendentes…</div></section>
<section class="card wide"><div class="label">💬 Dizer ao Trader</div><div class="muted">Escreve uma ideia, pergunta ou cola um website. O trader investiga; não transforma a mensagem diretamente numa ordem.</div><textarea id="researchMessage" rows="3" style="width:100%;margin-top:8px;resize:vertical;background:#09111f;color:#eef4ff;border:1px solid #334968;border-radius:11px;padding:12px;font:inherit" placeholder="Ex.: Analisa este website e procura padrões ou ideias que possam melhorar o trader: https://..."></textarea><div class="row"><button class="go" onclick="submitResearch()">ENVIAR AO TRADER</button></div><div id="researchStatus" class="notice">A verificar…</div><details><summary>Investigações recentes</summary><div id="researchList"></div></details></section>

<section class="card wide"><div class="label">🟢🟡🔴 Exchanges / Plataformas</div><div class="muted">Sinalética operacional das venues que o trader observa. Verde = OK · amarelo = em teste/evidência insuficiente · vermelho = indisponível/candidato a revisão.</div><div id="venues" class="notice">A verificar exchanges…</div></section>
<section class="card wide"><div class="label">🧾 Evidência PAPER / prontidão de investigação</div><div class="muted">Checklist de amostras, walk-forward, regimes, custos e bootstrap. Não é autorização de execução REAL.</div><div id="evidenceSummary" class="big">A verificar…</div><div id="evidenceChecks" class="notice">A carregar checklist…</div><details><summary>Relatórios usados</summary><pre id="evidencePaths"></pre></details></section>
<section class="card wide"><div class="label">📊 Investigação PAPER contínua</div><div class="grid"><div class="card"><div class="label">Amostras</div><div id="studySamples" class="big">---</div></div><div class="card"><div class="label">Mean net bps</div><div id="studyMean" class="big">---</div></div><div class="card"><div class="label">OOS</div><div id="studyOos" class="big">---</div></div><div class="card"><div class="label">Timing WebSocket</div><div id="studyTiming" class="big">---</div></div></div><div id="studyMeta" class="notice">A verificar investigação…</div><details><summary>Resumo estatístico</summary><pre id="studyReport">---</pre></details></section>
<section class="card wide"><div class="label">Diagnóstico operacional</div><div id="diagSummary" class="notice">A verificar motor e recolha de mercado…</div><div class="row"><button class="blue" onclick="refreshDiagnostics()">↻ ATUALIZAR DIAGNÓSTICO</button><button class="blue" onclick="exportDiagnostics()">⇩ EXPORTAR DIAGNÓSTICO</button></div><details><summary>Detalhes de operação</summary><pre id="diagDetails">---</pre></details></section><section class="card wide"><div class="label">Ativos</div><table><thead><tr><th>Ativo</th><th>Score</th><th>Regime</th></tr></thead><tbody id="assets"></tbody></table></section>
<section class="grid"><div class="card"><div class="label">Posições</div><pre id="positions">---</pre></div><div class="card"><div class="label">Modelos</div><pre id="models">---</pre></div><div class="card"><div class="label">Eventos</div><pre id="logs">---</pre></div><div class="card"><div class="label">Preflight</div><pre id="preflight">---</pre></div></section>
<section class="card wide"><details><summary>Acesso local</summary><input id="token" type="password" placeholder="Token local, se configurado"><div class="muted">Deixa vazio se não tiveres configurado um token.</div></details></section>
</main>
<script>
const $=id=>document.getElementById(id);const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));const H=()=>({'X-Token':$('token').value,'Content-Type':'application/json'});
async function api(p,o={}){const r=await fetch(p,{...o,headers:{...H(),...(o.headers||{})}});let d={};try{d=await r.json()}catch(e){}if(!r.ok)throw Error(d.error||d.reason||'Operação recusada');return d}
async function cmd(p){try{await api(p,{method:'POST'});refresh()}catch(e){alert(e.message)}}
async function arm(){try{await api('/real/arm',{method:'POST',body:JSON.stringify({phrase:'EU ACEITO O RISCO'})});refresh()}catch(e){alert(e.message)}}
async function setMode(m){try{await api('/mode',{method:'POST',body:JSON.stringify({mode:m})});refresh()}catch(e){alert(e.message)}}
async function runValidation(){try{$('validation').textContent='A validar…';await api('/readiness/run',{method:'POST'});$('validation').textContent='Validação concluída.';refresh()}catch(e){$('validation').textContent='Bloqueada: '+e.message}}
async function refreshDiagnostics(){
try{
 const d=await api('/diagnostics'); const m=d.market_data||{},s=d.storage||{},e=d.engine||{};
 const engineOk=e.status==='RUNNING'||e.status==='PAUSED'; const feedOk=m.ok===true;
 $('diagSummary').innerHTML=(engineOk?'<span class="ok">● Motor '+esc(e.status)+'</span>':'<span class="bad">● Motor '+esc(e.status||'OFF')+'</span>')+' · '+(feedOk?'<span class="ok">● Market data OK</span>':'<span class="bad">● Market data '+esc(m.status||'OFF')+'</span>')+' · Eventos '+Number(m.events_total||0)+' · Dados '+(Number(s.bytes||0)/1048576).toFixed(2)+' MB · Crescimento '+(Number(s.growth_bytes||0)/1024).toFixed(1)+' KB';
 $('diagDetails').textContent=JSON.stringify(d,null,2);
}catch(e){$('diagSummary').innerHTML='<span class="bad">Diagnóstico indisponível: '+esc(e.message)+'</span>'}
}
function exportDiagnostics(){
 const token=$('token').value;
 fetch('/diagnostics/export',{headers:{'X-Token':token}}).then(r=>{if(!r.ok)throw Error('Exportação recusada');return r.blob()}).then(blob=>{const u=URL.createObjectURL(blob);const a=document.createElement('a');a.href=u;a.download='vazao-operational-diagnostics.json';a.click();URL.revokeObjectURL(u)}).catch(e=>alert(e.message));
}
async function refresh(){try{const d=await api('/status');$('status').textContent=d.status||'---';$('mode').textContent='Modo: '+(d.mode||'---');$('health').textContent=d.status==='RUNNING'?'● O BOT ESTÁ A FUNCIONAR':d.status==='PAUSED'?'Ⅱ O BOT ESTÁ PAUSADO':d.status==='SAFE_MODE'?'⚠ MODO SEGURO':'● '+(d.status||'PARADO');$('balance').textContent=(d.balance||0).toFixed(2);$('pnl').textContent=((d.pnl_today_pct||0)*100).toFixed(2)+'%';$('dd').textContent=((d.drawdown_pct||0)*100).toFixed(2)+'%';const w=d.watchdog||{};$('wd').textContent=w.ok===true?'OK':w.ok===false?'ATENÇÃO':'—';$('positions').textContent=JSON.stringify(d.open_positions||{},null,2);$('models').textContent=JSON.stringify(d.champion_challenger||{},null,2);$('preflight').textContent=JSON.stringify(d.preflight||{},null,2);$('logs').textContent=(d.logs||[]).slice(-20).join('\n');const s=d.asset_scores||{},r=d.regimes||{};$('assets').innerHTML=Object.keys(s).map(k=>'<tr><td>'+esc(k)+'</td><td>'+Number(s[k]).toFixed(2)+'</td><td>'+esc(r[k]||'')+'</td></tr>').join('');const p=await api('/autonomous-readiness'),q=p.readiness||{},e=q.evidence||{},review=q.paper_review||{},gatesEnabled=!!(p.ok&&p.autonomous_enabled&&p.allow_real&&p.auto_promote_real),ready=!!(gatesEnabled&&q.ready&&review.ready);$('real').textContent=ready?'PRONTO PARA REAL':'REAL BLOQUEADO';$('real').className='big '+(ready?'ok':'bad');$('realinfo').textContent='Modo atual '+(p.mode||'—')+' · Avaliação REAL · Estados '+(e.market_state_rows||0)+'/'+(e.required_market_state_rows||0)+' · Outcomes '+(e.outcome_samples||0)+'/'+(e.required_outcome_samples||0)+' · Evidências elegíveis '+((e.evidence_quality||{}).eligible_records||0)+' · Autonomia '+(gatesEnabled?'ativa':'desativada ou incompleta');const rows=(q.checks||[]).map(c=>'<div style="padding:7px 0;border-bottom:1px solid #243553"><b>'+esc(c.name)+'</b> — <span class="'+(c.passed?'ok':'bad')+'">'+(c.passed?'OK':'BLOQUEADO')+'</span><div class="muted">'+esc(c.detail||'')+'</div></div>').concat((review.blockers||[]).map(b=>'<div style="padding:7px 0;border-bottom:1px solid #243553"><b>REVISÃO PAPER</b> — <span class="bad">BLOQUEADO</span><div class="muted">'+esc(b)+'</div></div>'));$('checks').innerHTML=rows.join('')||'<div class="muted">Sem verificações disponíveis.</div>'}catch(e){$('status').textContent='OFFLINE / token necessário';$('health').textContent='O painel não conseguiu falar com o motor.'}}
async function refreshBridge(){
try{
 const d=await api('/human-interaction/pending');
 const items=(d.requests||[]).filter(x=>x.status==='PENDING');
 if(!items.length){$('bridge').innerHTML='<span class="ok">✓ Nada pendente</span>';return}
 $('bridge').innerHTML=items.map(x=>{
   const fs=(x.fields||[]).map(f=>'<div class="muted small">'+esc(f.label||f.name)+'</div><input data-human="'+esc(x.request_id)+'" data-field="'+esc(f.name)+'" type="'+(f.type==='secret'?'password':'text')+'" placeholder="'+esc(f.label||f.name)+'">').join('');
   return '<div class="notice"><b>'+esc(x.title)+'</b><div class="muted">'+esc(x.platform)+' · '+esc(x.kind)+'</div><div>'+esc(x.message)+'</div>'+fs+'<div class="row"><button class="go" onclick="respond(\''+x.request_id+'\')">ENVIAR</button><button class="stop" onclick="cancel(\''+x.request_id+'\')">CANCELAR</button></div></div>';
 }).join('');
}catch(e){$('bridge').textContent='Ajuda remota indisponível'}
}
async function respond(id){
 try{const values={};document.querySelectorAll('[data-human="'+id+'"]').forEach(i=>values[i.dataset.field]=i.value);await api('/human-interaction/respond',{method:'POST',body:JSON.stringify({request_id:id,action:'fill',values})});refreshBridge()}catch(e){alert(e.message)}
}
async function cancel(id){
 try{await api('/human-interaction/cancel',{method:'POST',body:JSON.stringify({request_id:id})});refreshBridge()}catch(e){alert(e.message)}
}
async function submitResearch(){
 try{const message=$('researchMessage').value.trim();if(!message)return;$('researchStatus').textContent='A enviar ao cérebro…';await api('/research',{method:'POST',body:JSON.stringify({message})});$('researchMessage').value='';$('researchStatus').innerHTML='<span class="ok">✓ Pedido entregue ao trader.</span>';refreshResearch()}catch(e){$('researchStatus').textContent='Não foi possível enviar: '+e.message}
}
async function refreshEvidenceScorecard(){
 try{
  const d=await api('/evidence-scorecard');
  $('evidenceSummary').textContent=Number(d.requirements_met||0)+' / '+Number(d.requirements_total||0)+' requisitos presentes';
  $('evidenceSummary').className='big '+(Number(d.requirements_missing?.length||0)===1?'ok':'warn');
  $('evidenceChecks').innerHTML=(d.checks||[]).map(x=>'<div class="venue"><span class="dot '+(x.status==='MET'?'green':'red')+'"></span><div><div class="venue-name">'+esc(x.requirement.replaceAll('_',' '))+'</div><div class="venue-meta">'+esc(x.detail||'')+'</div></div><b class="'+(x.status==='MET'?'ok':'bad')+'">'+esc(x.status)+'</b></div>').join('')+'<div class="venue-meta">PAPER only · ordens enviadas: não · autorização REAL: não</div>';
  $('evidencePaths').textContent=JSON.stringify(d.report_paths||{},null,2);
 }catch(e){$('evidenceSummary').textContent='Indisponível';$('evidenceChecks').textContent=e.message}
}
async function refreshVenueHealth(){
 try{
  const d=await api('/venue-health');
  const rows=d.venues||[];
  $('venues').innerHTML=rows.length?rows.map(v=>{
    const cls=v.status==='GREEN'?'green':v.status==='RED'?'red':'';
    const label=v.label||v.status;
    const age=v.age_ms==null?'sem dados':(Math.round(v.age_ms/1000)+'s');
    return '<div class="venue"><span class="dot '+cls+'"></span><div><div class="venue-name">'+esc(v.exchange)+' <span class="'+(v.status==='GREEN'?'ok':v.status==='RED'?'bad':'warn')+'">'+esc(label)+'</span></div><div class="venue-meta">'+esc((v.role||[]).join(' + '))+' · '+esc(v.detail||'')+' · amostras '+Number(v.sample_count||0)+' · idade '+age+'</div></div><b class="'+(v.status==='GREEN'?'ok':v.status==='RED'?'bad':'warn')+'">'+esc(v.decision_hint||'OBSERVAR')+'</b></div>'
  }).join(''):'Sem exchanges configuradas.';
 }catch(e){$('venues').innerHTML='<span class="bad">Sinalética indisponível: '+esc(e.message)+'</span>'}
}
async function refreshStudy(){
 try{
  const d=await api('/research/status');
  const study=d.reports?.paper_study||{}, timing=d.reports?.websocket_timing||{};
  const p=study.payload||{}, o=p.overall||{}, oos=p.chronological_oos?.test||{};
  $('studySamples').textContent=String(p.outcome_samples??'0');
  $('studyMean').textContent=Number(o.mean_net_bps||0).toFixed(2);
  $('studyOos').textContent=(oos.samples||0)+' amostras';
  const eligible=timing.payload?.eligible_for_economic_interpretation===true;
  $('studyTiming').textContent=eligible?'OK':'BLOQUEADO';
  $('studyTiming').className='big '+(eligible?'ok':'bad');
  $('studyMeta').textContent='Estudo: '+(study.status||'—')+' · idade '+(study.age_ms!=null?Math.round(study.age_ms/1000)+'s':'—')+' · timing: '+(timing.status||'—')+' · intervalo '+d.study_interval_minutes+' min';
  $('studyReport').textContent=JSON.stringify({overall:o,chronological_oos:p.chronological_oos,walk_forward:p.walk_forward,regimes:p.regimes,monte_carlo:p.monte_carlo},null,2);
 }catch(e){$('studyMeta').textContent='Investigação indisponível: '+e.message}
}
async function refreshResearch(){
 try{const d=await api('/research');$('researchStatus').innerHTML='<span class="ok">'+d.pending+' pendente(s)</span> · '+d.active+' em análise · '+d.completed+' concluída(s) · '+d.discarded+' descartada(s)';$('researchList').innerHTML=(d.requests||[]).slice(0,8).map(x=>'<div class="notice"><b>'+esc(x.status)+'</b> · '+new Date(x.created_at*1000).toLocaleString()+'<div>'+esc(x.message)+'</div></div>').join('')}catch(e){$('researchStatus').textContent='Pesquisa indisponível'}
}
setInterval(refresh,4000);setInterval(refreshDiagnostics,5000);setInterval(refreshBridge,3000);refresh();refreshDiagnostics();refreshVenueHealth();refreshEvidenceScorecard();refreshBridge();refreshResearch();refreshStudy();
</script></body></html>'''
