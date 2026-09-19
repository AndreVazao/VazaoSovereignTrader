from __future__ import annotations
import json, math, statistics, time
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

@dataclass(frozen=True)
class ValidationRow:
    leader: str
    follower: str
    symbol: str
    direction: str
    horizon_ms: int
    in_samples: int
    out_samples: int
    in_expectancy_bps: float
    out_expectancy_bps: float
    in_response_rate: float
    out_response_rate: float
    in_median_lag_ms: float
    out_median_lag_ms: float
    out_ci_low_bps: float
    out_ci_high_bps: float
    out_net_positive: bool
    stable: bool

class LeadLagValidationEngine:
    def __init__(self, data_dir="PC_ENGINE/data/radar", split_ratio=0.70, min_in_samples=50, min_out_samples=30, cost_bps=28.0, response_threshold_bps=2.0):
        self.data_dir=Path(data_dir); self.split_ratio=min(.9,max(.5,float(split_ratio)))
        self.min_in_samples=max(1,int(min_in_samples)); self.min_out_samples=max(1,int(min_out_samples))
        self.cost_bps=max(0.,float(cost_bps)); self.response_threshold_bps=max(0.,float(response_threshold_bps))

    def _read(self,name):
        p=self.data_dir/name
        if not p.exists(): return []
        out=[]
        for line in p.read_text(encoding="utf-8").splitlines():
            try:
                x=json.loads(line)
                if isinstance(x,dict): out.append(x)
            except json.JSONDecodeError: pass
        return out

    @staticmethod
    def _price_at(events,venue,symbol,target):
        xs=[e for e in events if e.get("exchange")==venue and e.get("symbol")==symbol and int(e.get("exchange_ts_ms",-1))>=target]
        return None if not xs else min(xs,key=lambda e:int(e["exchange_ts_ms"])).get("price")

    def _outcome(self,c,events,horizon):
        try:
            venue,symbol=str(c["follower"]),str(c["symbol"]); start=int(c["follower_exchange_ts_ms"])
            entry=self._price_at(events,venue,symbol,start); future=self._price_at(events,venue,symbol,start+horizon)
            if not entry or not future: return None
            raw=(float(future)-float(entry))/float(entry)*10000.; sign=1 if str(c["direction"]).upper()=="UP" else -1
            directional=raw*sign
            return directional-self.cost_bps,directional>=self.response_threshold_bps,int(c["exchange_lag_ms"])
        except (KeyError,TypeError,ValueError,ZeroDivisionError): return None

    @staticmethod
    def _ci(values):
        if len(values)<2: return (values[0],values[0]) if values else (0.,0.)
        m=statistics.fmean(values); margin=1.96*statistics.stdev(values)/math.sqrt(len(values))
        return m-margin,m+margin

    def validate(self,horizon_ms=1000):
        candidates=self._read("websocket_lead_lag.jsonl"); events=self._read("websocket_events.jsonl")
        timestamps=sorted(int(c["leader_exchange_ts_ms"]) for c in candidates if "leader_exchange_ts_ms" in c)
        if not candidates or not events or not timestamps: return []
        split_at=timestamps[max(0,min(len(timestamps)-1,int(len(timestamps)*self.split_ratio)))]
        buckets=defaultdict(lambda:{"in":[],"out":[]})
        for c in candidates:
            try:
                ts=int(c["leader_exchange_ts_ms"]); outcome=self._outcome(c,events,horizon_ms)
                if outcome is None: continue
                key=(str(c["leader"]),str(c["follower"]),str(c["symbol"]),str(c["direction"]).upper())
                buckets[key]["in" if ts<split_at else "out"].append(outcome)
            except (KeyError,TypeError,ValueError): pass
        rows=[]
        for (leader,follower,symbol,direction),parts in buckets.items():
            inside,outside=parts["in"],parts["out"]
            if not inside or not outside: continue
            inn=[x[0] for x in inside]; out=[x[0] for x in outside]
            in_rate=sum(x[1] for x in inside)/len(inside); out_rate=sum(x[1] for x in outside)/len(outside)
            lo,hi=self._ci(out)
            stable=(len(inside)>=self.min_in_samples and len(outside)>=self.min_out_samples and statistics.fmean(inn)>0 and statistics.fmean(out)>0 and lo>0 and out_rate>=.55)
            rows.append(ValidationRow(leader,follower,symbol,direction,int(horizon_ms),len(inside),len(outside),
                round(statistics.fmean(inn),4),round(statistics.fmean(out),4),round(in_rate,4),round(out_rate,4),
                round(statistics.median(x[2] for x in inside),2),round(statistics.median(x[2] for x in outside),2),
                round(lo,4),round(hi,4),lo>0,stable))
        rows.sort(key=lambda r:(r.stable,r.out_expectancy_bps,r.out_samples),reverse=True)
        self.data_dir.mkdir(parents=True,exist_ok=True)
        (self.data_dir/"lead_lag_validation.json").write_text(json.dumps({
            "generated_at_ms":time.time_ns()//1_000_000,"paper_only":True,"split_ratio":self.split_ratio,
            "split_timestamp_ms":split_at,"horizon_ms":horizon_ms,"cost_bps":self.cost_bps,
            "min_in_samples":self.min_in_samples,"min_out_samples":self.min_out_samples,
            "rows":[asdict(r) for r in rows]},ensure_ascii=False,indent=2),encoding="utf-8")
        return rows
