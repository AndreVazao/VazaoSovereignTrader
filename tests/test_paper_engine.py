from PC_ENGINE.paper.engine import PaperExecutionEngine
def test_paper_fill_and_net_pnl(tmp_path):
 e=PaperExecutionEngine(str(tmp_path),fee_bps=10,slippage_bps=0); f=e.execute({"symbol":"BTC/USDT","venue":"binance","side":"BUY"},capital=1000,entry_price=100,exit_price=101); assert f.status=="FILLED"; r=e.run_result(); assert r.gross_pnl>0 and r.net_pnl<r.gross_pnl
def test_partial_and_reject(tmp_path):
 e=PaperExecutionEngine(str(tmp_path),partial_fill_ratio=.5); assert e.execute({"symbol":"ETH/USDT"},capital=1000,entry_price=100).status=="PARTIAL"; e2=PaperExecutionEngine(str(tmp_path/"r"),reject_probability=1); assert e2.execute({"symbol":"ETH/USDT"},capital=1000,entry_price=100,seed=0).status=="REJECTED"
