from __future__ import annotations

import argparse
import json

from PC_ENGINE.autonomy.paper_reconciliation import PaperAutonomyReconciler


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconcile autonomous PAPER intents with paper fills/runs.")
    parser.add_argument("--output", default="PC_ENGINE/data/paper/autonomous_reconciliation.json")
    args = parser.parse_args()
    report = PaperAutonomyReconciler(output_path=args.output).reconcile()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
