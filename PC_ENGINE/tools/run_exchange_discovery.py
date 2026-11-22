from __future__ import annotations

import argparse
import json

import ccxt

from PC_ENGINE.radar.venue_discovery import VenueDiscoveryRegistry


def main() -> int:
    parser = argparse.ArgumentParser(
        description="List VST exchange catalogue entries and unverified CCXT discovery leads."
    )
    parser.add_argument(
        "--candidates",
        default="PC_ENGINE/config/exchange_candidates.json",
        help="Optional local JSON file with candidate venue metadata.",
    )
    parser.add_argument(
        "--include-ccxt-leads",
        action="store_true",
        help="List additional exchange IDs available in the installed CCXT package; these are unverified leads.",
    )
    args = parser.parse_args()

    registry = VenueDiscoveryRegistry(args.candidates)
    payload = {
        "mode": "public_research_only",
        "catalogue": [venue.to_dict() for venue in registry.list_venues()],
        "ccxt_discovery_leads": (
            registry.ccxt_candidates(getattr(ccxt, "exchanges", []))
            if args.include_ccxt_leads else []
        ),
        "safety": {
            "private_account_access": "disabled",
            "financial_mutations": "disabled",
            "candidate_discovery_grants_no_trust_or_permissions": True,
        },
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
