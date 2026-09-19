from __future__ import annotations
import json,time,uuid
from dataclasses import asdict,dataclass
from pathlib import Path
from typing import Any
@dataclass
class PaperFill:
 fill_id:str; opportunity_id:str; venue:str; symbol:str; side:str; requested_qty:float; filled_qty:float; requested_price:float; fill_price:float; fee:float; slippage_bps:float; latency_ms:float; status:str; timestamp:float
@dataclass
class PaperRunResult:
 run_id:str; status:str; gross_pnl:float; fees:float; net_pnl:float; trades:int; fills:int; partial_fills:int; rejections:int; missed_opportunities:int; started_at:float; finished_at:float
class PaperExecutionEngine:
 def __init__(self,data_dir="PC_ENGINE/data/paper",*,fee_bps=10.0,slippage_bps=2.0,latency_ms=80.0,partial_fill_ratio=1.0,reject_probability=0.0):
  self.root=Path(data_dir); self.root.mkdir(parents=True,exist_ok=True); self.fills_path=self.root/"fills.jsonl"; self.runs_path=self.root/"runs.jsonl"; self.fee_bps=max(0.0,fee_bps); self.slippage_bps=max(0.0,slippage_bps); self.latency_ms=max(0.0,latency_ms); self.partial_fill_ratio=min(1.0,max(0.0,partial_fill_ratio)); self.reject_probability=min(1.0,max(0.0,reject_probability)); self.gross_pnl=self.fees=0.0; self.trades=self.fills=self.partial_fills=self.rejections=self.missed_opportunities=0
 def execute(self,opportunity:dict[str,Any],*,capital:float,entry_price:float,exit_price:float|None=None,seed:float|None=None)->PaperFill:
  self.trades+=1; now=time.time(); symbol=str(opportunity.get("symbol","UNKNOWN")); venue=str(opportunity.get("venue","PAPER")); side=str(opportunity.get("side","BUY")).upper(); qty=float(opportunity.get("quantity") or (capital/entry_price if entry_price>0 else 0.0))
  if qty<=0 or entry_price<=0: self.missed_opportunities+=1; return self._fill(opportunity,venue,symbol,side,qty,0,entry_price,entry_price,0,"INVALID",now)
  if seed is not None and seed<self.reject_probability: self.rejections+=1; return self._fill(opportunity,venue,symbol,side,qty,0,entry_price,entry_price,0,"REJECTED",now)
  filled=qty*self.partial_fill_ratio; self.partial_fills += int(filled<qty); impact=self.slippage_bps/10000; fill_price=entry_price*(1+impact if side=="BUY" else 1-impact); fee=filled*fill_price*self.fee_bps/10000; self.fees+=fee; self.fills+=1
  if exit_price is not None: self.gross_pnl+=(exit_price-fill_price)*filled if side=="BUY" else (fill_price-exit_price)*filled
  return self._fill(opportunity,venue,symbol,side,qty,filled,entry_price,fill_price,fee,"FILLED" if filled>=qty else "PARTIAL",now)
 def record_missed(self,opportunity): self.missed_opportunities+=1
 def run_result(self,run_id=None,started_at=None):
  finished=time.time(); result=PaperRunResult(run_id or uuid.uuid4().hex,"PAPER",self.gross_pnl,self.fees,self.gross_pnl-self.fees,self.trades,self.fills,self.partial_fills,self.rejections,self.missed_opportunities,started_at or finished,finished); self.runs_path.open("a",encoding="utf-8").write(json.dumps(asdict(result))+"\\n"); return result
 def _fill(self,opportunity,venue,symbol,side,requested,filled,requested_price,fill_price,fee,status,timestamp):
  item=PaperFill(uuid.uuid4().hex,str(opportunity.get("opportunity_id",uuid.uuid4().hex)),venue,symbol,side,requested,filled,requested_price,fill_price,fee,self.slippage_bps,self.latency_ms,status,timestamp); self.fills_path.open("a",encoding="utf-8").write(json.dumps(asdict(item))+"\\n"); return item
