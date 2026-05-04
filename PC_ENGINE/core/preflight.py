from __future__ import annotations

from dataclasses import dataclass
from typing import List

from PC_ENGINE.core.exchange_rules import ExchangeRulesEngine


@dataclass
class PreflightResult:
    ok: bool
    errors: List[str]
    warnings: List[str]


class PreflightChecker:
    def __init__(self, config: dict, rules: ExchangeRulesEngine):
        self.config = config
        self.rules = rules

    def run(self, exchanges: dict) -> PreflightResult:
        errors: List[str] = []
        warnings: List[str] = []

        if not exchanges:
            errors.append("no exchange enabled")

        mode = str(self.config.get("mode", "PAPER")).upper()
        if mode == "REAL":
            warnings.append("REAL mode configured: confirm manually before start")

        symbols = self.config.get("symbols", [])
        if not symbols:
            errors.append("no symbols configured")

        for name, exchange in exchanges.items():
            try:
                exchange.fetch_balance()
            except Exception as exc:
                if mode == "REAL":
                    errors.append(f"{name}: balance check failed: {exc}")
                else:
                    warnings.append(f"{name}: balance check unavailable in paper/public mode: {exc}")

            for symbol in symbols:
                try:
                    ticker = exchange.fetch_ticker(symbol)
                    price = float(ticker.get("last") or 0)
                    if price <= 0:
                        errors.append(f"{name}:{symbol}: invalid ticker price")
                    self.rules.load_symbol_rules(exchange, symbol)
                except Exception as exc:
                    errors.append(f"{name}:{symbol}: market/rules check failed: {exc}")

        return PreflightResult(ok=not errors, errors=errors, warnings=warnings)
