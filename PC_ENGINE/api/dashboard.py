from __future__ import annotations

DASHBOARD_HTML = """
<!doctype html>
<html lang="pt">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Vazao Sovereign Trader</title>
  <style>
    body { margin: 0; font-family: Arial, sans-serif; background: #0b1020; color: #e8eefc; }
    header { padding: 18px; background: #111933; border-bottom: 1px solid #24304f; }
    h1 { margin: 0; font-size: 22px; }
    .wrap { padding: 16px; display: grid; gap: 14px; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); }
    .card { background: #121a33; border: 1px solid #24304f; border-radius: 14px; padding: 14px; box-shadow: 0 8px 24px rgba(0,0,0,.25); }
    .big { font-size: 28px; font-weight: 700; }
    .muted { color: #93a4c7; font-size: 13px; }
    button { border: 0; border-radius: 10px; padding: 12px 14px; margin: 4px; color: #07101f; font-weight: 700; cursor: pointer; }
    .start { background: #36d399; }
    .pause { background: #fbbf24; }
    .stop { background: #fb7185; }
    .mode { background: #93c5fd; }
    input { width: 100%; padding: 10px; border-radius: 10px; border: 1px solid #33415f; background: #090d1a; color: #e8eefc; box-sizing: border-box; }
    pre { white-space: pre-wrap; word-break: break-word; max-height: 260px; overflow:auto; }
    table { width: 100%; border-collapse: collapse; }
    td, th { border-bottom: 1px solid #24304f; padding: 8px; text-align: left; }
    .ok { color: #36d399; } .bad { color:#fb7185; } .warn { color:#fbbf24; }
  </style>
</head>
<body>
  <header><h1>Vazao Sovereign Trader — Painel Local</h1><div class="muted">Tudo local. PAPER por defeito. Risk Engine manda.</div></header>
  <div class="wrap">
    <div class="card">
      <div class="muted">Token local</div>
      <input id="token" type="password" placeholder="VST_LOCAL_TOKEN" />
      <br/><br/>
      <button class="start" onclick="cmd('/start')">INICIAR</button>
      <button class="pause" onclick="cmd('/pause')">PAUSAR</button>
      <button class="stop" onclick="cmd('/stop')">PARAR</button>
      <button class="mode" onclick="setMode('PAPER')">PAPER</button>
      <button class="mode" onclick="setMode('REAL')">REAL</button>
      <button class="mode" onclick="cmd('/preflight')">PREFLIGHT</button>
    </div>
    <div class="card"><div class="muted">Estado</div><div id="status" class="big">---</div><div id="mode" class="muted">---</div></div>
    <div class="card"><div class="muted">Saldo / Equity</div><div id="balance" class="big">---</div></div>
    <div class="card"><div class="muted">P&L</div><div id="pnl" class="big">---</div></div>
    <div class="card"><div class="muted">Watchdog</div><pre id="watchdog">---</pre></div>
    <div class="card"><div class="muted">Champion / Challenger</div><pre id="champion">---</pre></div>
    <div class="card" style="grid-column: 1 / -1;"><div class="muted">Ativos</div><table><thead><tr><th>Ativo</th><th>Score</th><th>Regime</th></tr></thead><tbody id="assets"></tbody></table></div>
    <div class="card" style="grid-column: 1 / -1;"><div class="muted">Posições abertas</div><pre id="positions">---</pre></div>
    <div class="card" style="grid-column: 1 / -1;"><div class="muted">Logs</div><pre id="logs">---</pre></div>
  </div>
<script>
function headers(){ return {'X-Token': document.getElementById('token').value, 'Content-Type':'application/json'}; }
async function cmd(path){ try { await fetch(path,{method:'POST',headers:headers()}); await refresh(); } catch(e){ alert(e); } }
async function setMode(mode){ try { await fetch('/mode',{method:'POST',headers:headers(),body:JSON.stringify({mode})}); await refresh(); } catch(e){ alert(e); } }
async function refresh(){
  try {
    const r = await fetch('/status',{headers:headers()});
    const d = await r.json();
    document.getElementById('status').textContent = d.status || '---';
    document.getElementById('mode').textContent = 'Modo: ' + (d.mode || '---');
    document.getElementById('balance').textContent = (d.balance||0).toFixed(2) + ' / ' + (d.equity||0).toFixed(2);
    document.getElementById('pnl').textContent = 'Hoje ' + ((d.pnl_today_pct||0)*100).toFixed(2) + '% | Semana ' + ((d.pnl_week_pct||0)*100).toFixed(2) + '% | DD ' + ((d.drawdown_pct||0)*100).toFixed(2) + '%';
    document.getElementById('watchdog').textContent = JSON.stringify(d.watchdog||{}, null, 2);
    document.getElementById('champion').textContent = JSON.stringify(d.champion_challenger||{}, null, 2);
    const assets = document.getElementById('assets'); assets.innerHTML='';
    const scores = d.asset_scores || {}; const regimes = d.regimes || {};
    Object.keys(scores).forEach(k => { assets.innerHTML += `<tr><td>${k}</td><td>${Number(scores[k]).toFixed(2)}</td><td>${regimes[k]||''}</td></tr>`; });
    document.getElementById('positions').textContent = JSON.stringify(d.open_positions||{}, null, 2);
    document.getElementById('logs').textContent = (d.logs||[]).slice(-30).join('\n');
  } catch(e) { document.getElementById('status').textContent='OFFLINE / TOKEN'; }
}
setInterval(refresh, 4000); refresh();
</script>
</body>
</html>
"""
