from __future__ import annotations
import argparse
from PC_ENGINE.radar.lead_lag_validation import LeadLagValidationEngine

def main():
    p=argparse.ArgumentParser(description="Run PAPER out-of-sample lead/lag validation")
    p.add_argument("--data-dir",default="PC_ENGINE/data/radar")
    p.add_argument("--horizon-ms",type=int,default=1000)
    p.add_argument("--min-in",type=int,default=50)
    p.add_argument("--min-out",type=int,default=30)
    p.add_argument("--cost-bps",type=float,default=28.0)
    a=p.parse_args()
    rows=LeadLagValidationEngine(a.data_dir,min_in_samples=a.min_in,min_out_samples=a.min_out,cost_bps=a.cost_bps).validate(a.horizon_ms)
    print(f"Validated relationships: {len(rows)} | stable: {sum(r.stable for r in rows)}")
    for r in rows[:10]:
        print(f"{r.leader}->{r.follower} {r.symbol} {r.direction} OUT={r.out_expectancy_bps:.2f}bps stable={r.stable}")

if __name__=="__main__":
    main()
