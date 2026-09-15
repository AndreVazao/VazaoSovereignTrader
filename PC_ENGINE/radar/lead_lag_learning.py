from __future__ import annotations

import json, math, statistics, time
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

@dataclass(frozen=True)
class LearningStat:
    leader: str; follower: str; symbol: str; direction: str; horizon_ms: int
    samples: int; wins: int; response_rate: float; shrunk_response_rate: float
    mean_return_bps: float; median_return_bps: float; mean_net_bps: float
    stddev_net_bps: float; expectancy_bps: float; lower_95_bps: float; upper_95_bps: float
    mean_lag_ms: float; min_lag_ms: int; max_lag_ms: int; confidence: float; eligible: bool

class LeadLagLearningEngine:
    """Offline/PAPER learner for observed cross-exchange lead/lag candidates.

    It measures future follower response at several horizons, subtracts estimated
    round-trip costs, shrinks small samples toward neutral, and only marks a
    relationship eligible when sample size and positive-confidence tests pass.
    It never creates or executes exchange orders.
    """
    DEFAULT_HORIZONS_MS = (100, 250, 500, 1000, 2000, 5000)

    def __init__(self, data_dir: str | Path = "PC_ENGINE/data/radar", min_samples: int = 100,
                 fee_bps_per_side: float = 10.0, slippage_bps_per_side: float = 4.0,
                 response_threshold_bps: float = 2.0, prior_strength: float = 20.0):
        self.data_dir = Path(data_dir); self.min_samples = max(1, int(min_samples))
        self.cost_bps = 2 * (float(fee_bps_per_side) + float(slippage_bps_per_side))
        self.response_threshold_bps = max(0.0, float(response_threshold_bps))
        self.prior_strength = max(1.0, float(prior_strength))

    @staticmethod
    def _read(path: Path) -> list[dict[str, Any]]:
        if not path.exists(): return []
        out=[]
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                row=json.loads(line)
                if isinstance(row, dict): out.append(row)
            except json.JSONDecodeError: pass
        return out

    def candidates(self) -> list[dict[str, Any]]:
        rows=self._read(self.data_dir/"websocket_lead_lag.jsonl"); unique={}
        for r in rows:
            try:
                k=(r["symbol"],r["leader"],r["follower"],r["direction"],int(r["leader_exchange_ts_ms"]),int(r["follower_exchange_ts_ms"]))
                unique[k]=r
            except (KeyError,TypeError,ValueError): pass
        return list(unique.values())

    def events(self) -> list[dict[str, Any]]:
        rows=self._read(self.data_dir/"websocket_events.jsonl"); out=[]
        for row in rows:
            e=row.get("event",row)
            try:
                e=dict(e); e["exchange_ts_ms"]=int(e["exchange_ts_ms"]); e["local_ts_ms"]=int(e["local_ts_ms"])
                e["price"]=float(e["price"]); e["exchange"]=str(e["exchange"]); e["symbol"]=str(e["symbol"])
                if e["price"]>0: out.append(e)
            except (KeyError,TypeError,ValueError): pass
        return sorted(out,key=lambda x:(x["exchange_ts_ms"],x["local_ts_ms"]))

    @staticmethod
    def _price_at(events, exchange, symbol, target):
        best=None
        for e in events:
            if e["exchange"]==exchange and e["symbol"]==symbol and e["exchange_ts_ms"]>=target:
                if best is None or e["exchange_ts_ms"]<best["exchange_ts_ms"]: best=e
        return None if best is None else best["price"]

    def _outcomes(self, c, events, horizons):
        ex,sym,start=c["follower"],c["symbol"],int(c["follower_exchange_ts_ms"])
        entry=self._price_at(events,ex,sym,start)
        if not entry or entry<=0: return []
        sign=1 if str(c["direction"]).upper()=="UP" else -1; out=[]
        for h in horizons:
            future=self._price_at(events,ex,sym,start+h)
            if future is None: continue
            raw=(future-entry)/entry*10000; directional=raw*sign; net=directional-self.cost_bps
            out.append((h,directional,net,directional>=self.response_threshold_bps,int(c["exchange_lag_ms"])))
        return out

    @staticmethod
    def _mean(v): return statistics.fmean(v) if v else 0.0
    @staticmethod
    def _ci(v):
        if len(v)<2: return (v[0],v[0]) if v else (0.0,0.0)
        m=statistics.fmean(v); return m-1.96*statistics.stdev(v)/math.sqrt(len(v)),m+1.96*statistics.stdev(v)/math.sqrt(len(v))

    def learn(self, horizons_ms=None):
        horizons=tuple(sorted(set(horizons_ms or self.DEFAULT_HORIZONS_MS))); events=self.events(); buckets=defaultdict(list)
        for c in self.candidates():
            try:
                for h,r,n,w,lag in self._outcomes(c,events,horizons):
                    k=(c["leader"],c["follower"],c["symbol"],str(c["direction"]).upper(),h); buckets[k].append((r,n,w,lag))
            except (KeyError,TypeError,ValueError): pass
        stats=[]
        for (leader,follower,symbol,direction,h), rows in buckets.items():
            ret=[x[0] for x in rows]; net=[x[1] for x in rows]; wins=sum(x[2] for x in rows); lags=[x[3] for x in rows]; n=len(rows)
            rate=wins/n if n else 0; shrunk=(wins+self.prior_strength*.5)/(n+self.prior_strength) if n else .5; lo,hi=self._ci(net)
            eligible=n>=self.min_samples and self._mean(net)>0 and lo>0
            stats.append(LearningStat(leader,follower,symbol,direction,h,n,wins,round(rate,6),round(shrunk,6),round(self._mean(ret),4),round(statistics.median(ret),4),round(self._mean(net),4),round(statistics.stdev(net),4) if n>1 else 0.0,round(self._mean(net),4),round(lo,4),round(hi,4),round(self._mean(lags),2),min(lags),max(lags),round(min(1,n/max(self.min_samples,1)),4),eligible))
        stats.sort(key=lambda s:(s.eligible,s.expectancy_bps,s.samples),reverse=True); self._persist(stats); return stats

    def _persist(self, stats):
        self.data_dir.mkdir(parents=True,exist_ok=True)
        (self.data_dir/"lead_lag_learning.json").write_text(json.dumps({"generated_at_ms":time.time_ns()//1_000_000,"paper_only":True,"round_trip_cost_bps":self.cost_bps,"min_samples":self.min_samples,"stats":[asdict(s) for s in stats]},ensure_ascii=False,indent=2),encoding="utf-8")

    def eligible_signals(self, stats=None):
        return [{"symbol":s.symbol,"leader":s.leader,"follower":s.follower,"direction":s.direction,"horizon_ms":s.horizon_ms,"expectancy_bps":s.expectancy_bps,"confidence":s.confidence,"samples":s.samples,"paper_only":True} for s in (stats or self.learn()) if s.eligible]
