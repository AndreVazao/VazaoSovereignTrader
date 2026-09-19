from __future__ import annotations
import argparse, json
from pathlib import Path
from PC_ENGINE.learning.state_signature import StateSignatureLearningEngine
from PC_ENGINE.radar.market_state import MarketStateStore

def main():
    p=argparse.ArgumentParser(); p.add_argument("--limit",type=int,default=10000); p.add_argument("--cost-bps",type=float,default=28.0); p.add_argument("--min-samples",type=int,default=30); args=p.parse_args()
    states=MarketStateStore().recent(limit=max(1,args.limit)); engine=StateSignatureLearningEngine(cost_bps=args.cost_bps,min_samples=args.min_samples); stats=engine.evaluate(states)
    out=Path("PC_ENGINE/data/radar/state_signature_learning.jsonl"); out.parent.mkdir(parents=True,exist_ok=True)
    with out.open("w",encoding="utf-8") as h:
        for row in stats: h.write(json.dumps(row.__dict__,separators=(",",":"),sort_keys=True)+"\n")
    print(json.dumps({"states":len(states),"signatures":len(stats),"eligible":sum(r.eligible for r in stats),"output":str(out)},indent=2))

if __name__=="__main__": main()
