from __future__ import annotations

import json
import time
from pathlib import Path

from PC_ENGINE.core.paper_broker import PaperBroker
from PC_ENGINE.core.order_manager import OrderManager
from PC_ENGINE.core.exchange_rules import ExchangeRulesEngine
from PC_ENGINE.core.walk_forward import WalkForwardEvaluator
from PC_ENGINE.core.regime_validation import RegimeAwareValidator
from PC_ENGINE.radar.state_outcomes import StateOutcomeEngine

DATA_DIR = Path("PC_ENGINE/data/radar")
VALIDATION_DIR = DATA_DIR / "validation"


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _all_validation_rows_passed(results: list[dict]) -> bool:
    """Readiness requires every evaluated validation slice to pass."""
    return bool(results) and all(bool(row.get("passed")) for row in results)


def run_execution_smoke_test() -> dict:
    """Exercise only the PAPER execution primitives; never touches an exchange."""
    rules = ExchangeRulesEngine()
    broker = PaperBroker(fee_pct=0.001, slippage_pct=0.0005, reject_probability=0.0)
    manager = OrderManager(rules, broker)
    checks = {"paper_fill": False, "duplicate_block": False, "invalid_order_block": False}

    # The rules engine needs exchange metadata, so this test intentionally
    # validates the broker itself plus duplicate/invalid protections through
    # small fake exchange metadata objects supplied by the rules engine.
    class FakeExchange:
        name = "paper-smoke"

    exchange = FakeExchange()
    try:
        fill = broker.fill("BTC/USDT", "buy", 0.01, 100.0)
        checks["paper_fill"] = fill.fill_price > 100.0 and fill.fee > 0.0
    except Exception:
        checks["paper_fill"] = False

    # Duplicate protection is deterministic at OrderManager level even when
    # an exchange rejects metadata; the call must never become a real order.
    try:
        manager.last_client_order["paper-smoke:BTC/USDT:buy:0.01"] = time.monotonic()
        blocked = manager.buy(exchange, "BTC/USDT", 0.01, 100.0, paper=True)
        checks["duplicate_block"] = blocked.ok is False and "duplicate" in blocked.reason.lower()
    except Exception:
        checks["duplicate_block"] = False

    try:
        invalid = manager.buy(exchange, "BTC/USDT", 0.0, 100.0, paper=True)
        checks["invalid_order_block"] = invalid.ok is False
    except Exception:
        checks["invalid_order_block"] = False

    passed = all(checks.values())
    return {
        "generated_ts_ms": int(time.time() * 1000),
        "passed": passed,
        "ok": passed,
        "paper_only": True,
        "checks": checks,
        "reason": "all paper execution smoke checks passed" if passed else "one or more paper execution checks failed",
    }


def run(data_dir: str | Path | None = None) -> dict:
    data_root = Path(data_dir) if data_dir is not None else DATA_DIR
    validation_dir = data_root / "validation"
    data_root.mkdir(parents=True, exist_ok=True)
    validation_dir.mkdir(parents=True, exist_ok=True)

    states = _read_jsonl(data_root / "market_states.jsonl")
    outcome_engine = StateOutcomeEngine()
    outcomes = outcome_engine.evaluate(states)
    outcome_engine.save(outcomes, str(data_root / "state_outcomes.jsonl"))

    walk = WalkForwardEvaluator(data_dir=data_root).evaluate()
    walk_results = walk.get("results", [])
    walk_passed = _all_validation_rows_passed(walk_results)
    _write_json(validation_dir / "walk_forward.json", {
        "generated_ts_ms": int(time.time() * 1000),
        "ok": walk_passed,
        "passed": walk_passed,
        "paper_only": True,
        "source": "confluence_outcomes.jsonl",
        "results": walk_results,
    })

    regime = RegimeAwareValidator(data_dir=data_root).evaluate()
    regime_results = regime.get("results", [])
    regime_passed = _all_validation_rows_passed(regime_results)
    _write_json(validation_dir / "regime_validation.json", {
        "generated_ts_ms": int(time.time() * 1000),
        "ok": regime_passed,
        "passed": regime_passed,
        "paper_only": True,
        "source": "confluence_outcomes.jsonl",
        "results": regime_results,
    })

    execution = run_execution_smoke_test()
    _write_json(validation_dir / "execution_test.json", execution)

    eligible = sum(1 for row in outcomes if row.eligible)
    return {
        "generated_ts_ms": int(time.time() * 1000),
        "market_state_rows": len(states),
        "outcome_rows": len(outcomes),
        "eligible_outcomes": eligible,
        "walk_forward_ok": walk_passed,
        "regime_validation_ok": regime_passed,
        "execution_test_ok": bool(execution["ok"]),
        "paper_only": True,
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
